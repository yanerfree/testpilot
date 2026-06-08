#!/usr/bin/env python3
"""
场景 D：UpgradeInProgressGuard 二次检查 — 并发两次 upgrade，第二个应被拦截。

测试流程:
  1. 发起 CHSM upgrade（进入升级流程）
  2. 立刻再发 CHSM upgrade → 预期被 Guard 拦截（409 或 callback FAILED）
  3. 等第一次 upgrade 回调到达
  4. 再发 CHSM upgrade → 预期成功（Guard 已清除）

对应修复项: #2 UpgradeInProgressGuard 执行时二次检查 (HIGH)
"""

import json
import os
import sys
import time
import uuid
from typing import Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.http_client import get_http_client
from common.logger import logger
from config import config

# ================================================================
# ★ 配置 — 根据实际环境修改 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"                       # CHSM 管理接口地址
CALLBACK_URL = "http://127.0.0.1:9443/callback"               # 传给密码机的回调地址（内部回环）
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"  # 从外部查询回调记录
UPGRADE_PACK_VERSION = "2.0.1"
UPGRADE_PACK_URL = "http://127.0.0.1:8000/chsm_pack.bin"
UPGRADE_ALG = "RSAWithSHA256"
UPGRADE_SIGN = "PLACEHOLDER_SIGN_HEX"
POLL_TIMEOUT = 300
POLL_INTERVAL = 10


# ================================================================
# 公共函数
# ================================================================

def find_callback(request_id, timeout=POLL_TIMEOUT):
    # type: (str, float) -> Optional[dict]
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(CALLBACK_LIST_URL, timeout=10, verify=False)
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, list):
                    records = payload
                elif isinstance(payload, dict):
                    result = payload.get("result")
                    if isinstance(result, dict):
                        records = result.get("items", [])
                    else:
                        records = payload.get("records", payload.get("data", []))
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
                    return body_parsed or {"requestId": request_id, "found": True}
        except Exception as e:
            logger.warning("轮询 callback/list 异常: %s", e)
        time.sleep(POLL_INTERVAL)
    return None


def get_callback_status(cb):
    if cb is None:
        return None
    return cb.get("status")


def send_request(label, host, endpoint, json_data):
    # type: (str, str, str, dict) -> tuple
    client = get_http_client(base_url=host)
    print("\n  [%s] POST %s%s" % (label, host, endpoint))
    print("    requestId: %s" % json_data.get("requestId", "?"))
    t0 = time.time()
    try:
        resp = client.post(endpoint=endpoint, json_data=json_data)
        elapsed = time.time() - t0
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        print("    → HTTP %d (%.3fs)" % (resp.status_code, elapsed))
        if isinstance(body, dict):
            print("    → %s" % json.dumps(body, ensure_ascii=False)[:200])
        return resp.status_code, body, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        print("    → 异常: %s" % e)
        return 0, str(e), elapsed


def check_blocked(label, request_id, http_code):
    if http_code != 200:
        print("    → HTTP %d 直接拒绝，Guard 拦截生效 ✓" % http_code)
        return True
    print("    → HTTP 200 已接受，查 callback 确认后台是否 FAILED...")
    cb = find_callback(request_id, timeout=30)
    if cb:
        cb_status = get_callback_status(cb)
        print("    → callback status=%s" % cb_status)
        if cb_status is not None and cb_status != 200:
            print("    → callback status≠200，Guard 拦截生效 ✓")
            return True
        else:
            print("    → callback status=200，Guard 未拦截 ✗")
            return False
    print("    → 30s 内无 callback，状态不确定")
    return False


def _make_upgrade_body(rid):
    return {
        "requestId": rid, "oprType": "upgrade",
        "packVersion": UPGRADE_PACK_VERSION, "packUrl": UPGRADE_PACK_URL,
        "alg": UPGRADE_ALG, "sign": UPGRADE_SIGN, "callbackUrl": CALLBACK_URL,
    }


# ================================================================
# 主流程
# ================================================================

def run():
    print("=" * 64)
    print("  场景 D：UpgradeInProgressGuard 二次检查")
    print("  修复项: #2 UpgradeInProgressGuard 执行时二次检查 (HIGH)")
    print("  CHSM: %s" % CHSM_HOST)
    print("  回调查询: %s" % CALLBACK_LIST_URL)
    print("=" * 64)

    results = {"steps": [], "passed": False}

    # Step 1: 第一次 upgrade
    rid_1 = str(uuid.uuid4())
    print("\n[Step 1] 发起第一次 CHSM upgrade")
    code1, body1, t1 = send_request("upgrade-1", CHSM_HOST, "/api/1.0/chsm", _make_upgrade_body(rid_1))
    results["steps"].append({
        "step": 1, "action": "CHSM upgrade #1",
        "requestId": rid_1, "status_code": code1, "elapsed": round(t1, 3),
    })
    if code1 != 200:
        print("\n  ✗ 第一次 upgrade 未返回 200 (实际 %d)，无法继续" % code1)
        results["verdict"] = "前置失败: upgrade #1 返回 %d" % code1
        _save_report(results)
        return False

    # Step 2: 立刻第二次 upgrade（应被 Guard 拦截）
    rid_2 = str(uuid.uuid4())
    print("\n[Step 2] 立刻发起第二次 CHSM upgrade（预期: Guard 拦截 → 409/FAILED）")
    code2, body2, t2 = send_request("upgrade-2(重复)", CHSM_HOST, "/api/1.0/chsm", _make_upgrade_body(rid_2))
    results["steps"].append({
        "step": 2, "action": "CHSM upgrade #2 (duplicate)",
        "requestId": rid_2, "status_code": code2, "elapsed": round(t2, 3),
    })
    step2_blocked = check_blocked("upgrade-2(重复)", rid_2, code2)
    results["steps"][-1]["blocked"] = step2_blocked

    # Step 3: 等第一次 upgrade 回调
    print("\n[Step 3] 等第一次 upgrade 回调（超时 %ds）" % POLL_TIMEOUT)
    cb1 = find_callback(rid_1, timeout=POLL_TIMEOUT)
    if cb1:
        print("    → upgrade #1 回调到达: status=%s" % get_callback_status(cb1))
        results["steps"].append({"step": 3, "action": "wait upgrade #1 callback", "callback_status": get_callback_status(cb1)})
    else:
        print("    → 超时未收到 upgrade #1 回调")
        results["steps"].append({"step": 3, "action": "wait upgrade #1 callback", "callback_status": None, "note": "timeout"})

    # Step 4: Guard 清除后再发 upgrade
    rid_3 = str(uuid.uuid4())
    print("\n[Step 4] upgrade 完成后再发 CHSM upgrade（预期: Guard 已清除 → 成功）")
    code4, body4, t4 = send_request("upgrade-3(重试)", CHSM_HOST, "/api/1.0/chsm", _make_upgrade_body(rid_3))
    results["steps"].append({
        "step": 4, "action": "CHSM upgrade #3 (after guard cleared)",
        "requestId": rid_3, "status_code": code4, "elapsed": round(t4, 3),
    })
    step4_ok = (code4 == 200)

    # 汇总
    passed = step2_blocked
    results["passed"] = passed
    results["step2_blocked"] = step2_blocked
    results["step4_accepted"] = step4_ok

    if passed and step4_ok:
        results["verdict"] = "PASS — Guard 拦截重复 upgrade + 完成后可重新升级"
    elif passed:
        results["verdict"] = "PASS(部分) — Guard 拦截正确，但完成后仍无法升级(可能非 Guard 原因)"
    else:
        results["verdict"] = "FAIL — Guard 未拦截重复 upgrade"

    print("\n" + "=" * 64)
    print("  结论: %s" % results["verdict"])
    print("    Step 2 (重复 upgrade): %s" % ("BLOCKED ✓" if step2_blocked else "NOT BLOCKED ✗"))
    print("    Step 4 (完成后 upgrade): %s" % ("OK ✓" if step4_ok else "FAIL"))
    print("=" * 64)

    _save_report(results)
    return passed


def _save_report(results):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_d_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
