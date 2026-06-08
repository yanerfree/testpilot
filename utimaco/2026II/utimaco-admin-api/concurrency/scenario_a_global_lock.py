#!/usr/bin/env python3
"""
场景 A：全局锁互斥 — CHSM 异步操作持锁期间，VSM 操作应被阻塞。

测试流程:
  1. 发起 CHSM export（全局 write lock）
  2. 立刻发起 VSM start → 预期 FAILED（被锁阻塞）
  3. 轮询 callback/list，等待 export 回调到达（锁释放）
  4. 再次发起 VSM start → 预期成功（锁已释放）

对应修复项: #1 DeviceOperationLockRegistry 两级锁 (CRITICAL)
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
CHSM_HOST = "https://192.168.8.120:7443"                       # CHSM 管理接口地址
VSM_HOST = "https://192.168.8.120:7443"                         # VSM 管理接口地址（如不同请改）
CALLBACK_URL = "http://127.0.0.1:9443/callback"               # 传给密码机的回调地址（内部回环）
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"  # 从外部查询回调记录
VSM_ID = "bf356592d2a0"                                           # 实际存在的 vsmId
POLL_TIMEOUT = 300                                              # callback 轮询超时(秒)
POLL_INTERVAL = 10                                               # 轮询间隔(秒)


# ================================================================
# 格式化输出
# ================================================================

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def print_step_header(step_no, title):
    print("\n" + "─" * 64)
    print("  Step %s | %s | %s" % (step_no, title, now_str()))
    print("─" * 64)


def print_request(method, host, endpoint, body):
    print("  请求: %s %s%s" % (method, host, endpoint))
    print("  Body: %s" % json.dumps(body, ensure_ascii=False))


def print_response(code, body, elapsed):
    print("  响应: HTTP %s  (%.3fs)" % (code, elapsed))
    if isinstance(body, dict):
        print("  Body: %s" % json.dumps(body, ensure_ascii=False)[:300])
    elif body:
        print("  Body: %s" % str(body)[:300])


def print_expect_actual(expected, actual, passed):
    icon = "✓ PASS" if passed else "✗ FAIL"
    print("  预期: %s" % expected)
    print("  实际: %s" % actual)
    print("  判定: %s" % icon)


# ================================================================
# 回调查询
# ================================================================

def find_callback(request_id, timeout=POLL_TIMEOUT):
    # type: (str, float) -> Optional[dict]
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
                # 支持多种响应结构: 顶层数组 / result.items / records / data
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
                    rid = record.get("requestId")
                    # body 在 record.request.body (JSON字符串)
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
            logger.warning("轮询 callback/list 异常: %s", e)
        time.sleep(POLL_INTERVAL)
    return None


def get_callback_status(cb):
    if cb is None:
        return None
    return cb.get("status")


# ================================================================
# 请求发送
# ================================================================

def send_request(host, endpoint, json_data):
    # type: (str, str, dict) -> tuple
    client = get_http_client(base_url=host)
    print_request("POST", host, endpoint, json_data)
    t0 = time.time()
    try:
        resp = client.post(endpoint=endpoint, json_data=json_data)
        elapsed = time.time() - t0
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        print_response(resp.status_code, body, elapsed)
        return resp.status_code, body, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        print_response("异常", str(e), elapsed)
        return 0, str(e), elapsed


# ================================================================
# 场景 A 主流程
# ================================================================

def run():
    print("=" * 64)
    print("  场景 A：全局锁互斥 (CHSM export vs VSM start)")
    print("  修复项: #1 DeviceOperationLockRegistry 两级锁 (CRITICAL)")
    print("  CHSM: %s" % CHSM_HOST)
    print("  VSM:  %s" % VSM_HOST)
    print("  回调查询: %s" % CALLBACK_LIST_URL)
    print("  VSM ID: %s" % VSM_ID)
    print("  开始时间: %s" % now_str())
    print("=" * 64)

    report = {"scenario": "A", "steps": [], "passed": False}

    # ── Step 1 ────────────────────────────────────────────
    print_step_header(1, "发起 CHSM export（异步操作，将持有全局 write lock）")

    export_rid = str(uuid.uuid4())
    export_body = {"requestId": export_rid, "oprType": "export", "callbackUrl": CALLBACK_URL}
    code1, body1, t1 = send_request(CHSM_HOST, "/api/1.0/chsm/image", export_body)

    step1_ok = (code1 == 200)
    print_expect_actual(
        "HTTP 200（任务入队，开始持有全局 write lock）",
        "HTTP %d" % code1,
        step1_ok,
    )
    report["steps"].append({
        "step": 1, "time": now_str(),
        "action": "CHSM export (获取全局 write lock)",
        "request": {"host": CHSM_HOST, "endpoint": "/api/1.0/chsm/image", "body": export_body},
        "response": {"status_code": code1, "elapsed": round(t1, 3)},
        "expected": "HTTP 200", "actual": "HTTP %d" % code1, "passed": step1_ok,
    })

    if not step1_ok:
        report["steps"][-1]["issue"] = "CHSM export 返回 HTTP %d（期望200），可能原因：认证失败/callbackUrl不可达/设备异常" % code1
        report["verdict"] = "中止 — CHSM export 未返回 200，无法继续测试"
        _print_summary(report)
        _save_report(report)
        return False

    # ── Step 2 ────────────────────────────────────────────
    print_step_header(2, "立刻发起 VSM start（此时 export 正在执行，全局锁被持有）")

    start_rid_1 = str(uuid.uuid4())
    start_body_1 = {"requestId": start_rid_1, "oprType": "start", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}
    code2, body2, t2 = send_request(VSM_HOST, "/api/1.0/vsm", start_body_1)

    step2_blocked = False
    actual_desc = ""

    if code2 != 200:
        step2_blocked = True
        actual_desc = "HTTP %d — 请求被直接拒绝（锁阻塞生效）" % code2
    else:
        # HTTP 200 但后台可能 FAILED，查 callback
        print("  查询 callback 确认后台任务最终状态...")
        cb = find_callback(start_rid_1, timeout=30)
        if cb:
            cb_status = get_callback_status(cb)
            print("  callback 到达: %s" % json.dumps(cb, ensure_ascii=False)[:200])
            if cb_status is not None and cb_status != 200:
                step2_blocked = True
                actual_desc = "HTTP 200 但 callback status=%s — 后台任务失败（锁阻塞生效）" % cb_status
            else:
                actual_desc = "HTTP 200 且 callback status=%s — 任务成功执行（锁未阻塞）" % cb_status
        else:
            actual_desc = "HTTP 200 且 30s 内无 callback — 任务可能仍在排队或已执行"

    print_expect_actual(
        "请求被拒绝(非200) 或 callback status≠200（因全局锁被 export 持有）",
        actual_desc,
        step2_blocked,
    )
    report["steps"].append({
        "step": 2, "time": now_str(),
        "action": "VSM start (export 持锁期间)",
        "request": {"host": VSM_HOST, "endpoint": "/api/1.0/vsm", "body": start_body_1},
        "response": {"status_code": code2, "elapsed": round(t2, 3)},
        "expected": "被锁阻塞（非200 或 callback FAILED）",
        "actual": actual_desc, "passed": step2_blocked,
    })
    if not step2_blocked:
        report["steps"][-1]["issue"] = "VSM start在CHSM export持锁期间未被阻塞，全局锁互斥机制未生效"

    # ── Step 3 ────────────────────────────────────────────
    print_step_header(3, "等待 CHSM export 回调到达（锁释放）")

    print("  轮询: GET %s" % CALLBACK_LIST_URL)
    print("  查找: requestId=%s" % export_rid)
    print("  超时: %ds" % POLL_TIMEOUT)

    export_cb = find_callback(export_rid, timeout=POLL_TIMEOUT)
    if export_cb:
        export_status = get_callback_status(export_cb)
        print("  callback 到达: %s" % json.dumps(export_cb, ensure_ascii=False)[:200])
        print_expect_actual(
            "export 回调到达（操作完成，全局锁释放）",
            "callback status=%s — 回调已到达" % export_status,
            True,
        )
        report["steps"].append({
            "step": 3, "time": now_str(),
            "action": "等待 export callback（锁释放）",
            "expected": "callback 到达", "actual": "status=%s" % export_status, "passed": True,
        })
    else:
        print_expect_actual(
            "export 回调到达",
            "超时 %ds 未收到回调" % POLL_TIMEOUT,
            False,
        )
        report["steps"].append({
            "step": 3, "time": now_str(),
            "action": "等待 export callback（锁释放）",
            "expected": "callback 到达", "actual": "超时", "passed": False,
            "issue": "等待export回调超时%ds，export可能执行异常或callbackUrl不可达" % POLL_TIMEOUT,
        })

    # ── Step 4 ────────────────────────────────────────────
    print_step_header(4, "export 完成后再次发起 VSM start（全局锁应已释放）")

    start_rid_2 = str(uuid.uuid4())
    start_body_2 = {"requestId": start_rid_2, "oprType": "start", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}
    code4, body4, t4 = send_request(VSM_HOST, "/api/1.0/vsm", start_body_2)

    step4_ok = (code4 == 200)
    print_expect_actual(
        "HTTP 200（全局锁已释放，VSM 操作应可执行）",
        "HTTP %d" % code4,
        step4_ok,
    )
    report["steps"].append({
        "step": 4, "time": now_str(),
        "action": "VSM start (export 完成后)",
        "request": {"host": VSM_HOST, "endpoint": "/api/1.0/vsm", "body": start_body_2},
        "response": {"status_code": code4, "elapsed": round(t4, 3)},
        "expected": "HTTP 200", "actual": "HTTP %d" % code4, "passed": step4_ok,
    })
    if not step4_ok:
        report["steps"][-1]["issue"] = "export完成后VSM start仍返回HTTP %d，锁可能未正确释放或设备状态异常" % code4

    # ── 汇总 ─────────────────────────────────────────────
    issues = [s["issue"] for s in report["steps"] if "issue" in s]
    if issues:
        report["issues"] = issues

    passed = step2_blocked
    report["passed"] = passed

    if passed and step4_ok:
        report["verdict"] = "PASS — Step2 锁阻塞生效 + Step4 释放后可执行"
    elif passed and not step4_ok:
        report["verdict"] = "PASS(部分) — Step2 锁阻塞生效，但 Step4 释放后仍失败(可能非锁原因)"
    else:
        report["verdict"] = "FAIL — Step2 锁期间 VSM start 未被阻塞"

    _print_summary(report)
    _save_report(report)
    return passed


def _print_summary(report):
    print("\n" + "=" * 64)
    print("  场景 A 测试结论")
    print("=" * 64)
    for s in report["steps"]:
        icon = "✓" if s["passed"] else "✗"
        print("  %s Step %s: %s" % (icon, s["step"], s["action"]))
        print("       预期: %s" % s["expected"])
        print("       实际: %s" % s["actual"])
    print("─" * 64)
    print("  最终结论: %s" % report.get("verdict", "未知"))
    print("  完成时间: %s" % now_str())
    print("=" * 64)


def _save_report(report):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_a_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  报告已保存: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
