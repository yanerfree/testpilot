#!/usr/bin/env python3
"""
场景 B：per-vsmId 互斥 — 同一 vsmId 的 VSM 操作互斥，不同 vsmId 可并行。

测试流程:
  Part 1 — 同 vsmId 互斥:
    1. 对 vsmId=A 发起 VSM start（持 per-vsmId lock）
    2. 立刻对同一 vsmId=A 发起 VSM restart → 预期 FAILED
    3. 等 start 回调到达（锁释放）
    4. 再对 vsmId=A 发起 VSM restart → 预期成功

  Part 2 — 不同 vsmId 不互斥（对照组）:
    5. 对 vsmId=A 发起 VSM start
    6. 立刻对 vsmId=B 发起 VSM start → 预期成功（不同设备不互斥）

对应修复项: #1 DeviceOperationLockRegistry 两级锁 (CRITICAL)
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
VSM_HOST = "https://192.168.8.120:7443"                         # VSM 管理接口地址
CALLBACK_URL = "http://127.0.0.1:9443/callback"               # 传给密码机的回调地址（内部回环）
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"  # 从外部查询回调记录
VSM_ID_A = "bf356592d2a0"                                         # 实际存在的 vsmId A
VSM_ID_B = "020a06db41a2"                                         # 实际存在的 vsmId B（不同设备）
POLL_TIMEOUT = 300                                              # callback 轮询超时(秒)
POLL_INTERVAL = 10                                               # 轮询间隔(秒)


# ================================================================
# 回调查询
# ================================================================

def find_callback(request_id, timeout=POLL_TIMEOUT):
    # type: (str, float) -> Optional[dict]
    """轮询 callback/list，查找指定 requestId 的回调，返回 callback body。"""
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
    # type: (Optional[dict]) -> Optional[int]
    if cb is None:
        return None
    return cb.get("status")


# ================================================================
# 请求发送
# ================================================================

def send_request(label, host, endpoint, json_data):
    # type: (str, str, str, dict) -> tuple
    """发送请求到指定 host，返回 (status_code, response_body, elapsed)"""
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
    # type: (str, str, int) -> bool
    """检查请求是否被锁阻塞：先看 HTTP 状态码，再查 callback"""
    if http_code != 200:
        print("    → HTTP %d 直接拒绝，锁阻塞生效 ✓" % http_code)
        return True
    print("    → HTTP 200 已接受，查 callback 确认后台是否 FAILED...")
    cb = find_callback(request_id, timeout=30)
    if cb:
        cb_status = get_callback_status(cb)
        print("    → callback status=%s" % cb_status)
        if cb_status is not None and cb_status != 200:
            print("    → callback status≠200，锁阻塞生效 ✓")
            return True
        else:
            print("    → callback status=200，锁未阻塞 ✗")
            return False
    print("    → 30s 内无 callback，状态不确定")
    return False


# ================================================================
# Part 1：同 vsmId 互斥
# ================================================================

def run_part1(results):
    print("\n" + "-" * 64)
    print("  Part 1：同 vsmId 互斥 (vsmId=%s)" % VSM_ID_A)
    print("-" * 64)

    # Step 1: VSM start for vsmId=A
    start_rid = str(uuid.uuid4())
    print("\n[Step 1] 对 vsmId=A 发起 VSM start（持 per-vsmId lock）")
    code1, body1, t1 = send_request(
        "VSM-start-A", VSM_HOST, "/api/1.0/vsm",
        {"requestId": start_rid, "oprType": "start", "vsmId": VSM_ID_A, "callbackUrl": CALLBACK_URL},
    )
    results["steps"].append({
        "step": "1.1", "action": "VSM start vsmId=A",
        "requestId": start_rid, "status_code": code1, "elapsed": round(t1, 3),
    })
    if code1 != 200:
        msg = "VSM start vsmId=A 返回 HTTP %d（期望200），无法继续。可能原因：认证失败/vsmId不存在/设备异常" % code1
        print("\n  ✗ %s" % msg)
        results["steps"][-1]["issue"] = msg
        return False, False

    # Step 2: 立刻对同一 vsmId=A 发起 VSM restart（应被阻塞）
    restart_rid_1 = str(uuid.uuid4())
    print("\n[Step 2] 立刻对同一 vsmId=A 发起 VSM restart（预期: 被阻塞 → FAILED）")
    code2, body2, t2 = send_request(
        "VSM-restart-A(锁中)", VSM_HOST, "/api/1.0/vsm",
        {"requestId": restart_rid_1, "oprType": "restart", "vsmId": VSM_ID_A, "callbackUrl": CALLBACK_URL},
    )
    results["steps"].append({
        "step": "1.2", "action": "VSM restart vsmId=A (during lock)",
        "expected": "被锁阻塞(HTTP≠200 或 callback status≠200)",
        "requestId": restart_rid_1, "status_code": code2, "elapsed": round(t2, 3),
    })

    step2_blocked = check_blocked("VSM-restart-A(锁中)", restart_rid_1, code2)
    results["steps"][-1]["blocked"] = step2_blocked
    if not step2_blocked:
        results["steps"][-1]["issue"] = "同vsmId操作未被互斥锁阻塞，restart在start执行期间仍返回成功"

    # Step 3: 等 start 回调（锁释放）
    print("\n[Step 3] 等 VSM start 回调到达（超时 %ds）" % POLL_TIMEOUT)
    start_cb = find_callback(start_rid, timeout=POLL_TIMEOUT)
    if start_cb:
        print("    → start 回调到达: status=%s" % get_callback_status(start_cb))
        results["steps"].append({"step": "1.3", "action": "wait start callback", "callback_status": get_callback_status(start_cb)})
    else:
        print("    → 超时未收到 start 回调")
        results["steps"].append({"step": "1.3", "action": "wait start callback", "callback_status": None, "note": "timeout"})

    # Step 4: 锁释放后再发 VSM restart（应成功）
    restart_rid_2 = str(uuid.uuid4())
    print("\n[Step 4] 锁释放后再对 vsmId=A 发起 VSM restart（预期: 成功）")
    code4, body4, t4 = send_request(
        "VSM-restart-A(锁后)", VSM_HOST, "/api/1.0/vsm",
        {"requestId": restart_rid_2, "oprType": "restart", "vsmId": VSM_ID_A, "callbackUrl": CALLBACK_URL},
    )
    results["steps"].append({
        "step": "1.4", "action": "VSM restart vsmId=A (after lock)",
        "requestId": restart_rid_2, "status_code": code4, "elapsed": round(t4, 3),
    })
    step4_ok = (code4 == 200)
    if step4_ok:
        print("    → HTTP 200，锁释放后可执行 ✓")
        # 等 restart 回调完成，确保锁完全释放后再跑 Part 2
        print("\n[Step 4.1] 等 restart 回调完成（确保锁释放）")
        restart_cb = find_callback(restart_rid_2, timeout=POLL_TIMEOUT)
        if restart_cb:
            print("    → restart 回调到达: status=%s" % get_callback_status(restart_cb))
        else:
            print("    → 超时未收到 restart 回调")
    else:
        msg = "锁释放后VSM restart仍返回HTTP %d，可能锁未正确释放或设备状态异常" % code4
        print("    → %s" % msg)
        results["steps"][-1]["issue"] = msg

    return step2_blocked, step4_ok


# ================================================================
# Part 2：不同 vsmId 不互斥（对照组）
# ================================================================

def run_part2(results):
    print("\n" + "-" * 64)
    print("  Part 2：不同 vsmId 不互斥 (A=%s, B=%s)" % (VSM_ID_A, VSM_ID_B))
    print("-" * 64)

    # 等前面操作的锁完全释放
    time.sleep(3)

    # Step 5: 对 vsmId=A 发起 VSM start
    start_a_rid = str(uuid.uuid4())
    print("\n[Step 5] 对 vsmId=A 发起 VSM start")
    code5, body5, t5 = send_request(
        "VSM-start-A", VSM_HOST, "/api/1.0/vsm",
        {"requestId": start_a_rid, "oprType": "start", "vsmId": VSM_ID_A, "callbackUrl": CALLBACK_URL},
    )
    results["steps"].append({
        "step": "2.1", "action": "VSM start vsmId=A",
        "requestId": start_a_rid, "status_code": code5, "elapsed": round(t5, 3),
    })
    if code5 != 200:
        msg = "VSM start vsmId=A 返回 HTTP %d，Part 2 前置失败" % code5
        print("\n  ✗ %s" % msg)
        results["steps"][-1]["issue"] = msg
        return None

    # Step 6: 立刻对 vsmId=B 发起 VSM start（应不受影响）
    start_b_rid = str(uuid.uuid4())
    print("\n[Step 6] 立刻对 vsmId=B 发起 VSM start（预期: 不同设备不互斥 → 成功）")
    code6, body6, t6 = send_request(
        "VSM-start-B", VSM_HOST, "/api/1.0/vsm",
        {"requestId": start_b_rid, "oprType": "start", "vsmId": VSM_ID_B, "callbackUrl": CALLBACK_URL},
    )
    results["steps"].append({
        "step": "2.2", "action": "VSM start vsmId=B (different device)",
        "requestId": start_b_rid, "status_code": code6, "elapsed": round(t6, 3),
    })

    if code6 == 200:
        print("    → HTTP 200，不同 vsmId 不互斥 ✓")
        return True
    else:
        msg = "不同vsmId(A=%s,B=%s)操作被误互斥，vsmId=B返回HTTP %d，预期200" % (VSM_ID_A, VSM_ID_B, code6)
        print("    → %s" % msg)
        results["steps"][-1]["issue"] = msg
        return False


# ================================================================
# 主流程
# ================================================================

def run():
    print("=" * 64)
    print("  场景 B：per-vsmId 互斥 (同设备互斥 + 不同设备不互斥)")
    print("  修复项: #1 DeviceOperationLockRegistry 两级锁 (CRITICAL)")
    print("  VSM:  %s" % VSM_HOST)
    print("  回调查询: %s" % CALLBACK_LIST_URL)
    print("  vsmId A: %s" % VSM_ID_A)
    print("  vsmId B: %s" % VSM_ID_B)
    print("=" * 64)

    results = {"steps": [], "passed": False}

    # Part 1
    step2_blocked, step4_ok = run_part1(results)

    # Part 2
    step6_ok = run_part2(results)

    # ── 汇总 ─────────────────────────────────────────────
    part1_pass = step2_blocked
    part2_pass = step6_ok if step6_ok is not None else False
    passed = part1_pass and part2_pass

    results["passed"] = passed
    results["part1_same_vsmid_blocked"] = step2_blocked
    results["part1_after_release_ok"] = step4_ok
    results["part2_diff_vsmid_ok"] = step6_ok

    if passed:
        results["verdict"] = "PASS — 同 vsmId 互斥 + 不同 vsmId 不互斥"
    elif part1_pass and not part2_pass:
        results["verdict"] = "FAIL(部分) — 同 vsmId 互斥正确，但不同 vsmId 被误伤"
    elif not part1_pass and part2_pass:
        results["verdict"] = "FAIL(部分) — 不同 vsmId 不互斥正确，但同 vsmId 未互斥"
    else:
        results["verdict"] = "FAIL — 同 vsmId 未互斥 且 不同 vsmId 也失败"

    # 收集所有问题
    issues = [s["issue"] for s in results["steps"] if "issue" in s]
    if issues:
        results["issues"] = issues
        print("\n  发现问题:")
        for iss in issues:
            print("    - %s" % iss)

    print("\n" + "=" * 64)
    print("  结论: %s" % results["verdict"])
    print("    Part 1 同 vsmId 互斥:    %s" % ("BLOCKED ✓" if step2_blocked else "NOT BLOCKED ✗"))
    print("    Part 1 释放后可执行:      %s" % ("OK ✓" if step4_ok else "FAIL ✗"))
    if step6_ok is not None:
        print("    Part 2 不同 vsmId 不互斥: %s" % ("OK ✓" if step6_ok else "BLOCKED ✗ (误伤)"))
    else:
        print("    Part 2 不同 vsmId 不互斥: SKIP (前置失败)")
    print("=" * 64)

    _save_report(results)
    return passed


def _save_report(results):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_b_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
