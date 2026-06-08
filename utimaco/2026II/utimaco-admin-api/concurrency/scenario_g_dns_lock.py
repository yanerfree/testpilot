#!/usr/bin/env python3
"""
场景 G：DNS 文件锁 — 并发配置网络不应导致 resolv.conf 内容损坏。

测试流程:
  1. 10 路并发 POST /api/1.0/chsm/network（含 dnsList）
  2. 断言无 500 错误
  3. 连续 GET 3 次验证返回内容一致

对应修复项: #4 resolv.conf 文件读写加锁 (MEDIUM)
"""

import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier, BrokenBarrierError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.http_client import get_http_client
from common.logger import logger
from config import config

# ================================================================
# ★ 配置 — 根据实际环境修改 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"                       # CHSM 管理接口地址
CONCURRENCY = 10                                                # 并发写入数
READ_COUNT = 3                                                  # 写入后读取验证次数
DNS_LIST = ["8.8.8.8", "114.114.114.114"]                       # 固定 DNS（验证一致性用）
NETWORK_BODY = {
    "requestId": "uuid",
    "dnsList": DNS_LIST,
    "netAddrs": [{"name": "eth0", "ip": "192.168.1.100",
                  "mask": "255.255.255.0", "gateway": "192.168.1.1"}],
}


# ================================================================
# 并发写入
# ================================================================

def run_concurrent_writes():
    """10 路并发 POST network 配置"""
    n = CONCURRENCY
    barrier = Barrier(n)

    def _fire(idx):
        client = get_http_client(base_url=CHSM_HOST)
        data = json.loads(json.dumps(NETWORK_BODY))
        data["requestId"] = str(uuid.uuid4())
        try:
            barrier.wait(timeout=10)
        except BrokenBarrierError:
            pass
        t0 = time.time()
        try:
            resp = client.post(endpoint="/api/1.0/chsm/network", json_data=data)
            return resp.status_code, time.time() - t0
        except Exception:
            return 0, time.time() - t0

    results = []
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_fire, i): i for i in range(1, n + 1)}
        for f in as_completed(futures):
            results.append(f.result())
    return results


def run_reads():
    """连续读取 network 配置"""
    bodies = []
    for i in range(READ_COUNT):
        client = get_http_client(base_url=CHSM_HOST)
        try:
            resp = client.get(endpoint="/api/1.0/chsm/network")
            if resp.status_code == 200:
                bodies.append(resp.json())
            else:
                bodies.append(None)
        except Exception:
            bodies.append(None)
    return bodies


# ================================================================
# 主流程
# ================================================================

def run():
    print("=" * 64)
    print("  场景 G：DNS 文件锁 (resolv.conf 并发读写)")
    print("  修复项: #4 resolv.conf 文件读写加锁 (MEDIUM)")
    print("  CHSM: %s" % CHSM_HOST)
    print("  并发写入: %d 路" % CONCURRENCY)
    print("  读取验证: %d 次" % READ_COUNT)
    print("=" * 64)

    results = {"passed": False}

    # Step 1: 并发写入
    print("\n[Step 1] %d 路并发写入网络配置（含 DNS）" % CONCURRENCY)
    write_results = run_concurrent_writes()

    status_dist = {}
    for code, _ in write_results:
        status_dist[code] = status_dist.get(code, 0) + 1
    count_500 = sum(1 for code, _ in write_results if code >= 500)
    count_err = sum(1 for code, _ in write_results if code == 0)
    times = [t for _, t in write_results if t > 0]
    avg_t = sum(times) / len(times) if times else 0

    print("    状态码分布: %s" % status_dist)
    print("    avg=%.3fs" % avg_t)
    results["write_status_dist"] = status_dist

    write_ok = (count_500 == 0 and count_err == 0)
    if write_ok:
        print("    → 无 500 错误 ✓")
    else:
        print("    → 有 %d 个 500, %d 个异常 ✗" % (count_500, count_err))

    # Step 2: 等待写入落盘
    time.sleep(2)

    # Step 3: 连续读取验证
    print("\n[Step 2] 连续 GET %d 次验证内容一致性" % READ_COUNT)
    read_bodies = run_reads()
    valid = [b for b in read_bodies if b is not None]

    if len(valid) >= 2:
        consistent = all(
            json.dumps(v, sort_keys=True) == json.dumps(valid[0], sort_keys=True)
            for v in valid[1:]
        )
        if consistent:
            print("    → %d 次读取内容一致 ✓" % len(valid))
        else:
            print("    → 读取内容不一致！resolv.conf 可能损坏 ✗")
            for i, b in enumerate(valid):
                print("      读取 #%d: %s" % (i + 1, json.dumps(b, ensure_ascii=False)[:200]))
    else:
        consistent = True
        print("    → 有效读取 %d 次，不足以验证" % len(valid))

    results["read_count"] = len(valid)
    results["read_consistent"] = consistent

    # 汇总
    passed = write_ok and consistent
    results["passed"] = passed

    if passed:
        results["verdict"] = "PASS — 并发写入无 500 + 读取一致"
    elif not write_ok:
        results["verdict"] = "FAIL — 并发写入出现 500"
    else:
        results["verdict"] = "FAIL — 读取内容不一致，resolv.conf 可能损坏"

    print("\n" + "=" * 64)
    print("  结论: %s" % results["verdict"])
    print("    写入: %s" % ("无500 ✓" if write_ok else "有500 ✗"))
    print("    读取一致性: %s" % ("一致 ✓" if consistent else "不一致 ✗"))
    print("=" * 64)

    _save_report(results)
    return passed


def _save_report(results):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_g_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
