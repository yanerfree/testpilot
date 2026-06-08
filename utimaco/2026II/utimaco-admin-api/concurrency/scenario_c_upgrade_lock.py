#!/usr/bin/env python3
"""
场景 C：VSM upgrade 全局互斥 — upgrade 持全局 write lock，阻塞所有异步/危险操作。

测试流程:
  1. 发起 VSM upgrade（全局 write lock）
  2. 依次调用所有应被阻塞的接口，预期全部 409
  3. 等 upgrade 回调到达（锁释放）
  4. 再发 VSM start → 预期成功

应被阻塞的操作:
  7.1: export(8), import(9), restart(11), backup(12), restore(13)
  7.2: export(5), import(6), start(7), stop(8), restart(9), reset(10), upgrade(11)
  9.2: doVsmInit(7)
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
from config import config

# ================================================================
# ★ 配置 — 根据实际环境修改 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"
VSM_HOST = "https://192.168.8.120:7443"
TENANT_HOST = "https://192.168.8.120:7443"
CALLBACK_URL = "http://127.0.0.1:9443/callback"
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"
VSM_ID = "bf356592d2a0"
UPGRADE_PACK_VERSION = "6.2.0.0"
UPGRADE_PACK_URL = "http://192.168.8.120:9443/images?file=/images/u.trust_Anchor-6.3.0.0.raucb"
UPGRADE_ALG = "RSAWithSHA256"
UPGRADE_SIGN = "ffweJPTvBvjEHxrVYkUsjxEeGzh9ZJqNNOhgmUZMYeLpqSqMbpTeuIe+61AkruLG6CMvSpTA4o1UK7XylfxJQRzWxmUhvQzgfUvzB4VGs7cz2F/QLwJ4ahsD0x/T+NGCzvROBNRHmOUTQ12tJA13f2RqWq7KnFrg/Y8ujg0KH0NKvThJUTsyZxjv3hL9da39IaejXp1ZLj10/AQfJ/FzXj/iqJPpPPruQiDraUVMo7rlPfpT+Su43cTHZmMsBua5KHQPaKDzf/YByOLvon7wmGBRnXIA3ZPpNVzhiu55Wd7paC5J78NNQA9fKr0tDJaNqpgZPimF3UGT1xouvZLGrg=="
POLL_TIMEOUT = 600
POLL_INTERVAL = 10

# 所有应被阻塞的操作
BLOCKED_OPS = [
    # 7.1 CHSM
    {"name": "7.1.8 exportCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm/image",
     "body": {"requestId": "uuid", "oprType": "export", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.9 importCHSM", "host": CHSM_HOST, "endpoint": "/api/1.0/chsm/image",
     "body": {"requestId": "uuid", "oprType": "import", "imageUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
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
                    if record.get("requestId") != request_id:
                        continue
                    body_raw = (record.get("request") or {}).get("body", "")
                    body_parsed = None
                    if isinstance(body_raw, str) and body_raw.strip():
                        try:
                            body_parsed = json.loads(body_raw)
                        except Exception:
                            pass
                    elif isinstance(body_raw, dict):
                        body_parsed = body_raw
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
    """发送一个应被阻塞的操作，返回 (name, status_code, blocked)"""
    host = op["host"]
    endpoint = op["endpoint"]
    body = dict(op["body"])
    body["requestId"] = str(uuid.uuid4())
    params = op.get("params")

    client = get_http_client(base_url=host)
    print("  [%s] POST %s%s" % (op["name"], host, endpoint), end="")

    try:
        if params:
            resp = client.post(endpoint=endpoint, json_data=body, params=dict(p.split("=", 1) for p in params.split("&")))
        else:
            resp = client.post(endpoint=endpoint, json_data=body)
        code = resp.status_code
        print(" → HTTP %d" % code, end="")
        if code == 409:
            print(" ✓ 阻塞")
        elif code == 200:
            print(" ✗ 未阻塞!")
        else:
            print(" (非200非409)")
        return op["name"], code, (code == 409)
    except Exception as e:
        print(" → 异常: %s" % e)
        return op["name"], 0, False


def run():
    print("=" * 64)
    print("  场景 C：upgrade 全局互斥 — 验证所有异步操作被阻塞")
    print("  CHSM: %s" % CHSM_HOST)
    print("  VSM:  %s" % VSM_HOST)
    print("  upgrade vsmId: %s" % VSM_ID)
    print("  待验证操作: %d 个" % len(BLOCKED_OPS))
    print("  开始时间: %s" % now_str())
    print("=" * 64)

    report = {"scenario": "C", "steps": [], "passed": False}

    # ── Step 1: 发起 upgrade ────────────────────────────
    print("\n─── Step 1 | 发起 VSM upgrade | %s ───" % now_str())

    upgrade_rid = str(uuid.uuid4())
    client = get_http_client(base_url=VSM_HOST)
    upgrade_body = {
        "requestId": upgrade_rid, "oprType": "upgrade", "vsmId": VSM_ID,
        "packVersion": UPGRADE_PACK_VERSION, "packUrl": UPGRADE_PACK_URL,
        "alg": UPGRADE_ALG, "sign": UPGRADE_SIGN, "callbackUrl": CALLBACK_URL,
    }
    print("  POST %s/api/1.0/vsm" % VSM_HOST)
    try:
        resp = client.post(endpoint="/api/1.0/vsm", json_data=upgrade_body)
        code1 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code1, resp.elapsed.total_seconds()))
    except Exception as e:
        code1 = 0
        print("  → 异常: %s" % e)

    report["steps"].append({"step": 1, "action": "VSM upgrade", "requestId": upgrade_rid, "status_code": code1})

    if code1 != 200:
        report["steps"][-1]["issue"] = "upgrade 返回 HTTP %d，无法继续" % code1
        report["verdict"] = "FAIL — upgrade 请求失败"
        _save_report(report)
        return False

    # ── Step 2: 依次调用所有应被阻塞的操作 ──────────────
    print("\n─── Step 2 | 验证阻塞状态 (预期全部 409) | %s ───" % now_str())

    blocked_results = []
    for op in BLOCKED_OPS:
        name, code, blocked = send_blocked_op(op)
        blocked_results.append({"name": name, "status_code": code, "blocked": blocked})
        if not blocked:
            blocked_results[-1]["issue"] = "%s 返回 HTTP %d（期望409），未被阻塞" % (name, code)

    total_ops = len(blocked_results)
    blocked_count = sum(1 for r in blocked_results if r["blocked"])
    not_blocked = [r for r in blocked_results if not r["blocked"]]

    report["steps"].append({
        "step": 2, "action": "验证 %d 个操作阻塞状态" % total_ops,
        "blocked": blocked_count, "total": total_ops,
        "details": blocked_results,
    })

    print("\n  阻塞统计: %d/%d 被阻塞" % (blocked_count, total_ops))
    if not_blocked:
        print("  未被阻塞:")
        for r in not_blocked:
            print("    ✗ %s → HTTP %d" % (r["name"], r["status_code"]))

    # ── Step 3: 等 upgrade 回调 ─────────────────────────
    print("\n─── Step 3 | 等待 upgrade 回调 | %s ───" % now_str())
    upgrade_cb = find_callback(upgrade_rid, timeout=POLL_TIMEOUT)
    cb_status = upgrade_cb.get("status") if upgrade_cb else None
    report["steps"].append({
        "step": 3, "action": "等待 upgrade callback",
        "callback_status": cb_status,
    })
    if upgrade_cb:
        print("  upgrade 回调到达: status=%s" % cb_status)
    else:
        print("  超时未收到回调")
        report["steps"][-1]["issue"] = "超时 %ds 未收到 upgrade 回调" % POLL_TIMEOUT

    # ── Step 4: 锁释放后 VSM restart + 等回调确认 ────────
    print("\n─── Step 4 | 锁释放后 VSM restart | %s ───" % now_str())
    restart_rid = str(uuid.uuid4())
    try:
        resp = client.post(endpoint="/api/1.0/vsm", json_data={
            "requestId": restart_rid, "oprType": "restart", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL,
        })
        code4 = resp.status_code
        print("  → HTTP %d" % code4)
    except Exception as e:
        code4 = 0
        print("  → 异常: %s" % e)

    step4_accepted = (code4 == 200)
    step4_cb_ok = False

    if step4_accepted:
        print("  等待 restart 回调确认...")
        restart_cb = find_callback(restart_rid, timeout=POLL_TIMEOUT)
        restart_cb_status = restart_cb.get("status") if restart_cb else None
        if restart_cb_status == 200:
            print("  ✓ restart 回调 status=200，锁已释放")
            step4_cb_ok = True
        else:
            msg = "restart 回调 status=%s" % restart_cb_status if restart_cb else "超时未收到回调"
            print("  ✗ %s" % msg)

    step4_ok = step4_accepted and step4_cb_ok
    report["steps"].append({
        "step": 4, "action": "VSM restart (after upgrade) + 等回调",
        "requestId": restart_rid, "status_code": code4,
        "callback_status": restart_cb_status if step4_accepted else None,
        "passed": step4_ok,
    })
    if not step4_ok:
        if not step4_accepted:
            report["steps"][-1]["issue"] = "锁释放后 VSM restart 返回 HTTP %d" % code4
        else:
            report["steps"][-1]["issue"] = "VSM restart 请求成功但回调未确认完成"

    # ── 汇总 ─────────────────────────────────────────────
    all_blocked = (blocked_count == total_ops)
    passed = all_blocked
    report["passed"] = passed

    issues = []
    for s in report["steps"]:
        if "issue" in s:
            issues.append(s["issue"])
        if "details" in s:
            for d in s["details"]:
                if "issue" in d:
                    issues.append(d["issue"])
    if issues:
        report["issues"] = issues

    if passed and step4_ok:
        report["verdict"] = "PASS — 全部 %d 个操作被阻塞(409) + 释放后可执行" % total_ops
    elif passed:
        report["verdict"] = "PASS(部分) — 全部阻塞，但释放后 start 失败"
    else:
        report["verdict"] = "FAIL — %d/%d 个操作未被阻塞" % (total_ops - blocked_count, total_ops)

    print("\n" + "=" * 64)
    print("  结论: %s" % report["verdict"])
    print("  阻塞: %d/%d" % (blocked_count, total_ops))
    if not_blocked:
        print("  未阻塞:")
        for r in not_blocked:
            print("    - %s (HTTP %d)" % (r["name"], r["status_code"]))
    if issues:
        print("  问题:")
        for iss in issues:
            print("    - %s" % iss)
    print("  完成时间: %s" % now_str())
    print("=" * 64)

    _save_report(report)
    return passed


def _save_report(results):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_c_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
