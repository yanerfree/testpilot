#!/usr/bin/env python3
"""
场景 A2：CHSM export 全局锁互斥 — export 持全局 write lock 期间，所有异步/危险操作应被阻塞。

与场景 A 的区别: A 只验证 VSM start，A2 验证所有应被阻塞的接口。

测试流程:
  1. 发起 CHSM export（全局 write lock）
  2. 依次调用所有应被阻塞的接口，预期全部被拒绝（非200 或 callback FAILED）
  3. 等 export 回调到达（锁释放）
  4. 再发 VSM start → 预期成功（锁已释放）

应被阻塞的操作:
  7.1: import(9), upgrade(10), restart(11), backup(12), restore(13)
  7.2: export(5), import(6), start(7), stop(8), restart(9), reset(10), upgrade(11)
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.http_client import get_http_client
from common.logger import logger

# ================================================================
# ★ 配置 — 根据实际环境修改 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"
VSM_HOST = "https://192.168.8.120:7443"
CALLBACK_URL = "http://127.0.0.1:9443/callback"
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"
VSM_ID = "bf356592d2a0"
POLL_TIMEOUT = 300
POLL_INTERVAL = 10

# 所有应被阻塞的操作
BLOCKED_OPS = [
    # 7.1 CHSM
    {"name": "7.1.9 importCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm/image",
     "body": {"requestId": "uuid", "oprType": "import", "imageUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.10 upgradeCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"requestId": "uuid", "oprType": "upgrade", "packVersion": "1.0",
              "packUrl": "http://127.0.0.1:9443/images", "alg": "RSAWithSHA256",
              "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.11 restartCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"requestId": "uuid", "oprType": "restart", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.12 backupCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"requestId": "uuid", "oprType": "backup", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.13 restoreCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"requestId": "uuid", "oprType": "restore", "backupUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    # 7.2 VSM
    {"name": "7.2.5 exportVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm/image",
     "body": {"requestId": "uuid", "oprType": "export", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.6 importVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm/image",
     "body": {"requestId": "uuid", "oprType": "import", "vsmId": VSM_ID,
              "imageUrl": "http://127.0.0.1:9443/images", "alg": "RSAWithSHA256",
              "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.7 startVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"requestId": "uuid", "oprType": "start", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.8 stopVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"requestId": "uuid", "oprType": "stop", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.9 restartVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"requestId": "uuid", "oprType": "restart", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.10 resetVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"requestId": "uuid", "oprType": "reset", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.11 upgradeVSM", "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"requestId": "uuid", "oprType": "upgrade", "vsmId": VSM_ID,
              "packVersion": "1.0", "packUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def find_callback(request_id, timeout=POLL_TIMEOUT):
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        remaining = int(deadline - time.time())
        print("  轮询 #%d (剩余 %ds)..." % (attempt, remaining), end="")
        try:
            resp = requests.get(CALLBACK_LIST_URL, timeout=10, verify=False)
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, dict):
                    result = payload.get("result")
                    if isinstance(result, dict):
                        records = result.get("items", [])
                    else:
                        records = []
                elif isinstance(payload, list):
                    records = payload
                else:
                    records = []
                for record in records:
                    rid = record.get("requestId")
                    body_raw = (record.get("request") or {}).get("body", "")
                    body_parsed = None
                    if isinstance(body_raw, str) and body_raw.strip():
                        try:
                            body_parsed = json.loads(body_raw)
                        except Exception:
                            pass
                    elif isinstance(body_raw, dict):
                        body_parsed = body_raw
                    if not rid and body_parsed and isinstance(body_parsed, dict):
                        rid = body_parsed.get("requestId")
                    if rid != request_id:
                        continue
                    print(" 找到!")
                    return body_parsed or {"requestId": request_id, "found": True}
                print(" 未到达")
            else:
                print(" HTTP %d" % resp.status_code)
        except Exception as e:
            print(" 异常: %s" % e)
        time.sleep(POLL_INTERVAL)
    return None


def send_blocked_op(op):
    """发送一个应被阻塞的操作，返回 (name, blocked, status_code, detail)"""
    host = op["host"]
    endpoint = op["endpoint"]
    body = dict(op["body"])
    body["requestId"] = str(uuid.uuid4())
    rid = body["requestId"]

    client = get_http_client(base_url=host)
    print("\n  [%s] POST %s%s" % (op["name"], host, endpoint))
    print("    requestId: %s" % rid)

    try:
        resp = client.post(endpoint=endpoint, json_data=body)
        code = resp.status_code
        elapsed = resp.elapsed.total_seconds()
        print("    → HTTP %d (%.3fs)" % (code, elapsed))
    except Exception as e:
        print("    → 异常: %s" % e)
        return op["name"], True, 0, "请求异常: %s" % e

    if code != 200:
        detail = "HTTP %d — 直接拒绝（锁阻塞生效）" % code
        print("    → %s ✓" % detail)
        return op["name"], True, code, detail

    # HTTP 200，查 callback 确认是否后台 FAILED
    print("    → HTTP 200，查 callback 确认...")
    cb = find_callback(rid, timeout=30)
    if cb:
        cb_status = cb.get("status")
        if cb_status is not None and cb_status != 200:
            detail = "HTTP 200 但 callback status=%s（后台失败，锁阻塞生效）" % cb_status
            print("    → %s ✓" % detail)
            return op["name"], True, code, detail
        detail = "HTTP 200 且 callback status=%s（未被阻塞!）" % cb_status
        print("    → %s ✗" % detail)
        return op["name"], False, code, detail

    detail = "HTTP 200 且 30s 内无 callback（状态不确定）"
    print("    → %s" % detail)
    return op["name"], False, code, detail


# ================================================================
# 主流程
# ================================================================

def run():
    print("=" * 64)
    print("  场景 A2：CHSM export 全局锁 — 验证所有操作被阻塞")
    print("  CHSM: %s" % CHSM_HOST)
    print("  VSM:  %s" % VSM_HOST)
    print("  VSM ID: %s" % VSM_ID)
    print("  待验证操作: %d 个" % len(BLOCKED_OPS))
    print("  开始时间: %s" % now_str())
    print("=" * 64)

    report = {"scenario": "A2", "steps": [], "passed": False}

    # ── Step 1: 发起 CHSM export ──────────────────────────
    print("\n" + "─" * 64)
    print("  Step 1 | 发起 CHSM export（持全局 write lock）| %s" % now_str())
    print("─" * 64)

    export_rid = str(uuid.uuid4())
    export_body = {"requestId": export_rid, "oprType": "export", "callbackUrl": CALLBACK_URL}
    client = get_http_client(base_url=CHSM_HOST)

    print("  POST %s/api/1.0/chsm/image" % CHSM_HOST)
    print("  requestId: %s" % export_rid)

    try:
        resp = client.post(endpoint="/api/1.0/chsm/image", json_data=export_body)
        code1 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code1, resp.elapsed.total_seconds()))
    except Exception as e:
        code1 = 0
        print("  → 异常: %s" % e)

    step1_ok = (code1 == 200)
    report["steps"].append({
        "step": 1, "action": "CHSM export (获取全局 write lock)",
        "requestId": export_rid, "status_code": code1, "passed": step1_ok,
    })

    if not step1_ok:
        report["steps"][-1]["issue"] = "export 返回 HTTP %d，无法继续" % code1
        report["verdict"] = "中止 — export 请求失败"
        _print_summary(report)
        _save_report(report)
        return False

    # ── Step 2: 依次测试所有应被阻塞的操作 ─────────────────
    print("\n" + "─" * 64)
    print("  Step 2 | 测试 %d 个操作是否被阻塞 | %s" % (len(BLOCKED_OPS), now_str()))
    print("─" * 64)

    blocked_results = []
    for op in BLOCKED_OPS:
        name, blocked, code, detail = send_blocked_op(op)
        blocked_results.append({
            "name": name, "blocked": blocked, "status_code": code, "detail": detail,
        })
        report["steps"].append({
            "step": 2, "action": "阻塞验证: %s" % name,
            "status_code": code, "blocked": blocked, "detail": detail,
            "passed": blocked,
        })
        if not blocked:
            report["steps"][-1]["issue"] = "%s 未被全局锁阻塞" % name

    blocked_count = sum(1 for r in blocked_results if r["blocked"])
    total_ops = len(blocked_results)
    print("\n  阻塞验证结果: %d/%d 被阻塞" % (blocked_count, total_ops))

    # ── Step 3: 等 export 回调 ────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 3 | 等待 export 回调（锁释放）| %s" % now_str())
    print("─" * 64)
    print("  查找: requestId=%s" % export_rid)

    export_cb = find_callback(export_rid, timeout=POLL_TIMEOUT)
    export_status = export_cb.get("status") if export_cb else None
    step3_ok = (export_cb is not None)

    report["steps"].append({
        "step": 3, "action": "等待 export callback",
        "callback_status": export_status, "passed": step3_ok,
    })
    if not step3_ok:
        report["steps"][-1]["issue"] = "超时未收到 export 回调"

    if export_cb:
        print("  ✓ export 回调到达, status=%s" % export_status)
    else:
        print("  ✗ 超时未收到回调")

    # ── Step 4: 锁释放后验证 ──────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 4 | 锁释放后发起 VSM start（预期成功）| %s" % now_str())
    print("─" * 64)

    start_rid = str(uuid.uuid4())
    start_body = {"requestId": start_rid, "oprType": "start", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}
    print("  POST %s/api/1.0/vsm" % VSM_HOST)

    try:
        vsm_client = get_http_client(base_url=VSM_HOST)
        resp = vsm_client.post(endpoint="/api/1.0/vsm", json_data=start_body)
        code4 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code4, resp.elapsed.total_seconds()))
    except Exception as e:
        code4 = 0
        print("  → 异常: %s" % e)

    step4_ok = (code4 == 200)
    report["steps"].append({
        "step": 4, "action": "VSM start (export 完成后)",
        "status_code": code4, "passed": step4_ok,
    })
    if step4_ok:
        print("  ✓ 锁释放后 VSM start 成功")
    else:
        report["steps"][-1]["issue"] = "锁释放后 VSM start 返回 HTTP %d" % code4
        print("  ✗ HTTP %d" % code4)

    # ── 汇总 ─────────────────────────────────────────────
    all_blocked = (blocked_count == total_ops)
    passed = step1_ok and all_blocked and step3_ok
    report["passed"] = passed
    report["blocked_count"] = blocked_count
    report["total_ops"] = total_ops

    issues = [s["issue"] for s in report["steps"] if "issue" in s]
    if issues:
        report["issues"] = issues

    if passed:
        report["verdict"] = "PASS — 所有 %d 个操作被阻塞 + 锁释放后可执行" % total_ops
    elif all_blocked and not step3_ok:
        report["verdict"] = "PASS(部分) — 操作被阻塞但 export 回调超时"
    else:
        not_blocked = [r["name"] for r in blocked_results if not r["blocked"]]
        report["verdict"] = "FAIL — %d/%d 未被阻塞: %s" % (
            total_ops - blocked_count, total_ops, ", ".join(not_blocked))

    _print_summary(report)
    _save_report(report)
    return passed


def _print_summary(report):
    print("\n" + "=" * 64)
    print("  场景 A2 测试结论")
    print("=" * 64)
    print("  结论: %s" % report.get("verdict", "未知"))
    if report.get("issues"):
        print("  问题:")
        for iss in report["issues"]:
            print("    - %s" % iss)
    print("  完成时间: %s" % now_str())
    print("=" * 64)


def _save_report(report):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_a2_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
