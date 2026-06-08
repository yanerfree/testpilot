#!/usr/bin/env python3
"""
场景 E：配置 UPSERT 幂等 — 并发写入同一配置项不应出现 500 UNIQUE 约束冲突。

测试流程:
  对每个配置接口，10 路并发 POST，断言无 500 错误。

对应修复项: #3 配置 saveOrUpdate 改用 UPSERT (HIGH)
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
VSM_HOST = "https://192.168.8.120:7443"                         # VSM 管理接口地址
VSM_ID = "bf356592d2a0"                                           # VSM 配置用的 vsmId
CONCURRENCY = 10                                                # 每个接口的并发数

# ================================================================
# 待测试的配置接口列表 — enabled 改 False 可跳过
# ================================================================
UPSERT_CASES = [
    {
        "enabled": True,
        "case_id": "CE_01",
        "name": "CHSM network",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/network",
        "method": "POST",
        "json_data": {
            "requestId": "uuid",
            "dnsList": ["114.114.114.{i}", "192.168.8.1"],
            "netAddrs": [{"name": "eth{i}", "ip": "192.168.8.121",
                          "mask": "255.255.255.0", "gateway": "192.168.8.1"}],
        },
    },
    {
        "enabled": True,
        "case_id": "CE_02",
        "name": "CHSM ntp",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/ntp",
        "method": "POST",
        "json_data": {"requestId": "uuid", "addr": "ntp.aliyun.com", "syncPeriod": "6{i}"},
    },
    {
        "enabled": True,
        "case_id": "CE_03",
        "name": "CHSM imageuploader",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/imageuploader",
        "method": "POST",
        "json_data": {"requestId": "uuid", "url": "http://127.0.0.1:9443/images"},
    },
    {
        "enabled": True,
        "case_id": "CE_04",
        "name": "CHSM loguploader",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/loguploader",
        "method": "POST",
        "json_data": {"requestId": "uuid", "logServerType": "syslog", "logServerAddress": "192.168.8.1:51{i}"},
    },
    {
        "enabled": True,
        "case_id": "CE_05",
        "name": "CHSM alarmaddress",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/alarmaddress",
        "method": "POST",
        "json_data": {"requestId": "uuid", "url": "http://192.168.8.1:9443/alarm/{i}",
                      "monitoringUrl": "http://192.168.8.1:9443/monitor/{i}"},
    },
    {
        "enabled": True,
        "case_id": "CE_06",
        "name": "CHSM cloudtoken",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/cloudtoken",
        "method": "POST",
        "json_data": {"requestId": "uuid", "cloudToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.concurrent_test_{i}"},
    },
    {
        "enabled": True,
        "case_id": "CE_07",
        "name": "CHSM moocaddress",
        "host": CHSM_HOST,
        "endpoint": "/api/1.0/chsm/moocaddress",
        "method": "POST",
        "json_data": {
            "requestId": "uuid", "ocIp": "192.168.8.1", "ocProtocol": "https", "ocPort": "2663{i}",
            "resourceUrl": "/rest/cloudInfra/v1/resource", "performanceUrl": "/rest/cloudInfra/v1/performance",
            "bizRegionNativeId": "region-{i}", "cloudInfraType": "FusionSphere",
            "dewServiceHost": "kms.cn-north-1.myhuaweicloud.com",
        },
    },
    {
        "enabled": True,
        "case_id": "CE_08",
        "name": "VSM network",
        "host": VSM_HOST,
        "endpoint": "/api/1.0/vsm/network",
        "method": "POST",
        "json_data": {"requestId": "uuid", "vsmId": VSM_ID, "ip": "192.168.8.201", "mask": "24", "gateway": "192.168.8.1"},
    },
    {
        "enabled": True,
        "case_id": "CE_09",
        "name": "VSM token",
        "host": VSM_HOST,
        "endpoint": "/api/1.0/vsm/token",
        "method": "POST",
        "json_data": {"requestId": "uuid", "vsmId": VSM_ID, "token": "tenant_token_{i}", "tenantId": "tenant_{i}"},
    },
]


# ================================================================
# 并发执行
# ================================================================

def _substitute(data, idx):
    """替换 {i} 占位符并刷新 requestId"""
    if isinstance(data, str):
        result = data.replace("{i}", str(idx))
        if result.isdigit():
            return int(result)
        return result
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if k == "requestId":
                out[k] = str(uuid.uuid4())
            else:
                out[k] = _substitute(v, idx)
        return out
    if isinstance(data, list):
        return [_substitute(item, idx) for item in data]
    return data


def run_one_case(case):
    """对单个接口执行 N 路并发，返回 (case_id, passed, detail_str, status_dist)"""
    host = case["host"]
    endpoint = case["endpoint"]
    method = case.get("method", "POST").upper()
    n = CONCURRENCY
    barrier = Barrier(n)

    def _fire(idx):
        client = get_http_client(base_url=host)
        data = _substitute(case["json_data"], idx)
        try:
            barrier.wait(timeout=10)
        except BrokenBarrierError:
            pass
        t0 = time.time()
        try:
            fn = getattr(client, method.lower())
            if method == "DELETE":
                resp = fn(endpoint=endpoint, json_data=data)
            else:
                resp = fn(endpoint=endpoint, json_data=data)
            elapsed = time.time() - t0
            return resp.status_code, elapsed
        except Exception as e:
            return 0, time.time() - t0

    results = []
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_fire, i): i for i in range(1, n + 1)}
        for f in as_completed(futures):
            results.append(f.result())

    status_dist = {}
    for code, _ in results:
        status_dist[code] = status_dist.get(code, 0) + 1

    count_500 = sum(1 for code, _ in results if code >= 500)
    count_err = sum(1 for code, _ in results if code == 0)
    times = [t for _, t in results if t > 0]
    avg_t = sum(times) / len(times) if times else 0

    passed = (count_500 == 0 and count_err == 0)
    detail = "状态码分布: %s | avg=%.3fs" % (status_dist, avg_t)
    if count_500 > 0:
        detail += " | ✗ 有 %d 个 500" % count_500

    return case["case_id"], passed, detail, status_dist


# ================================================================
# 主流程
# ================================================================

def run():
    cases = [c for c in UPSERT_CASES if c.get("enabled", True)]
    print("=" * 64)
    print("  场景 E：配置 UPSERT 幂等")
    print("  修复项: #3 配置 saveOrUpdate 改用 UPSERT (HIGH)")
    print("  CHSM: %s" % CHSM_HOST)
    print("  VSM:  %s" % VSM_HOST)
    print("  并发数: %d" % CONCURRENCY)
    print("  启用用例: %d / %d" % (len(cases), len(UPSERT_CASES)))
    print("=" * 64)

    all_results = []
    total_pass = 0
    total_fail = 0

    for case in cases:
        cid = case["case_id"]
        name = case["name"]
        print("\n  [%s] %s  (%d 路并发 %s %s)" % (cid, name, CONCURRENCY, case.get("method", "POST"), case["endpoint"]))

        case_id, passed, detail, status_dist = run_one_case(case)
        icon = "✓" if passed else "✗"
        print("    %s %s" % (icon, detail))

        if passed:
            total_pass += 1
        else:
            total_fail += 1

        all_results.append({
            "case_id": case_id, "name": name, "passed": passed,
            "detail": detail, "status_distribution": status_dist,
        })

    passed = (total_fail == 0)
    print("\n" + "=" * 64)
    print("  场景 E 汇总: %d 通过, %d 失败, 共 %d 条" % (total_pass, total_fail, len(cases)))
    print("  结论: %s" % ("PASS — 全部接口无 500" if passed else "FAIL — 存在 500 错误"))
    print("=" * 64)

    _save_report({"passed": passed, "total_pass": total_pass, "total_fail": total_fail, "cases": all_results})
    return passed


def _save_report(results):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_e_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
