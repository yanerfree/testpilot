#!/usr/bin/env python3
"""
导出期间导入阻塞验证

流程:
  1. 查询 images/list 获取已有导出文件的 sign+token（用于正确的 import 数据）
  2. 发起 CHSM export（持全局锁）
  3. export 进行中立刻发起 import → 预期被阻塞（非200 或 callback FAILED）
  4. 等 export 回调完成（锁释放）
  5. 再次 import → 预期成功
  6. 等 import 回调完成
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
# ★ 配置 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"
CALLBACK_URL = "http://127.0.0.1:9443/callback"
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"
IMAGES_LIST_URL = "http://192.168.8.120:9443/images/list"
IMAGE_BASE_URL = "http://127.0.0.1:9443/images"
POLL_TIMEOUT = 300
POLL_INTERVAL = 10


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
                records = []
                if isinstance(payload, dict):
                    result = payload.get("result")
                    if isinstance(result, dict):
                        records = result.get("items", [])
                elif isinstance(payload, list):
                    records = payload
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
                    if not rid and body_parsed:
                        rid = body_parsed.get("requestId")
                    if rid == request_id:
                        print(" 找到!")
                        return body_parsed or {"requestId": request_id, "found": True}
                print(" 未到达")
            else:
                print(" HTTP %d" % resp.status_code)
        except Exception as e:
            print(" 异常: %s" % e)
        time.sleep(POLL_INTERVAL)
    print("  超时")
    return None


def get_latest_export_file():
    """从 images/list 获取最新的导出文件 sign+token"""
    print("  GET %s" % IMAGES_LIST_URL)
    try:
        resp = requests.get(IMAGES_LIST_URL, timeout=10, verify=False)
        if resp.status_code != 200:
            print("  HTTP %d" % resp.status_code)
            return None
        items = resp.json().get("result", {}).get("items", [])
        if not items:
            print("  文件列表为空")
            return None
        latest = sorted(items, key=lambda x: x.get("uploadTime", ""), reverse=True)[0]
        info = latest.get("info", {})
        print("  最新文件: %s" % latest.get("filename", "?"))
        print("    sign: %s..." % info.get("sign", "?")[:50])
        print("    token: %s" % info.get("token", "?"))
        print("    alg: %s" % info.get("alg", "?"))
        return info
    except Exception as e:
        print("  异常: %s" % e)
        return None


def build_import_body(file_info):
    """根据文件信息构建正确的 import 请求体"""
    alg = file_info.get("alg", "rsa")
    import_alg = "RSAWithSHA256" if alg.lower() == "rsa" else "SM2WithSM3"
    token = file_info.get("token", "")
    return {
        "requestId": str(uuid.uuid4()),
        "oprType": "import",
        "imageUrl": "%s?file=%s" % (IMAGE_BASE_URL, token),
        "alg": import_alg,
        "sign": file_info.get("sign", ""),
        "callbackUrl": CALLBACK_URL,
    }


def run():
    report = {"scenario": "export_block_import", "steps": [], "passed": False}

    print("=" * 64)
    print("  导出期间导入阻塞验证")
    print("  CHSM: %s" % CHSM_HOST)
    print("  开始时间: %s" % now_str())
    print("=" * 64)

    client = get_http_client(base_url=CHSM_HOST)

    # ── Step 1: 获取已有导出文件 ─────────────────────────
    print("\n" + "─" * 64)
    print("  Step 1 | 获取已有导出文件的 sign+token | %s" % now_str())
    print("─" * 64)

    file_info = get_latest_export_file()
    step1_ok = (file_info is not None and file_info.get("sign") and file_info.get("token"))
    report["steps"].append({"step": 1, "action": "获取导出文件信息", "passed": step1_ok})

    if not step1_ok:
        report["steps"][-1]["issue"] = "未找到可用的导出文件，请先执行一次导出"
        report["verdict"] = "中止 — 无可用导出文件"
        _save_report(report)
        return False

    # ── Step 2: 发起 export ──────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 2 | 发起 CHSM export（持全局锁）| %s" % now_str())
    print("─" * 64)

    export_rid = str(uuid.uuid4())
    export_body = {"requestId": export_rid, "oprType": "export", "callbackUrl": CALLBACK_URL}
    print("  requestId: %s" % export_rid)

    try:
        resp = client.post(endpoint="/api/1.0/chsm/image", json_data=export_body)
        code2 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code2, resp.elapsed.total_seconds()))
    except Exception as e:
        code2 = 0
        print("  → 异常: %s" % e)

    step2_ok = (code2 == 200)
    report["steps"].append({"step": 2, "action": "CHSM export", "requestId": export_rid,
                            "status_code": code2, "passed": step2_ok})
    if not step2_ok:
        report["steps"][-1]["issue"] = "export 返回 HTTP %d" % code2
        report["verdict"] = "中止 — export 请求失败"
        _save_report(report)
        return False

    # ── Step 3: export 期间立刻 import → 预期被阻塞 ───────
    print("\n" + "─" * 64)
    print("  Step 3 | export 期间发起 import（预期被阻塞）| %s" % now_str())
    print("─" * 64)

    import_body_blocked = build_import_body(file_info)
    import_rid_blocked = import_body_blocked["requestId"]
    print("  requestId: %s" % import_rid_blocked)
    print("  imageUrl: %s" % import_body_blocked["imageUrl"])

    try:
        resp = client.post(endpoint="/api/1.0/chsm/image", json_data=import_body_blocked)
        code3 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code3, resp.elapsed.total_seconds()))
    except Exception as e:
        code3 = 0
        print("  → 异常: %s" % e)

    step3_blocked = False
    if code3 != 200:
        step3_blocked = True
        detail3 = "HTTP %d — 直接拒绝（锁阻塞生效）" % code3
        print("  → %s ✓" % detail3)
    else:
        print("  → HTTP 200，查 callback 确认...")
        cb = find_callback(import_rid_blocked, timeout=30)
        if cb:
            cb_status = cb.get("status")
            if cb_status is not None and cb_status != 200:
                step3_blocked = True
                detail3 = "HTTP 200 但 callback status=%s（后台失败，锁阻塞生效）" % cb_status
                print("  → %s ✓" % detail3)
            else:
                detail3 = "HTTP 200 且 callback status=%s（未被阻塞!）" % cb_status
                print("  → %s ✗" % detail3)
        else:
            detail3 = "HTTP 200 且 30s 内无 callback（状态不确定）"
            print("  → %s" % detail3)

    report["steps"].append({"step": 3, "action": "export 期间 import（应被阻塞）",
                            "requestId": import_rid_blocked, "status_code": code3,
                            "blocked": step3_blocked, "detail": detail3, "passed": step3_blocked})
    if not step3_blocked:
        report["steps"][-1]["issue"] = "export 持锁期间 import 未被阻塞: %s" % detail3

    # ── Step 4: 等 export 回调 ────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 4 | 等待 export 回调（锁释放）| %s" % now_str())
    print("─" * 64)

    export_cb = find_callback(export_rid, timeout=POLL_TIMEOUT)
    export_status = export_cb.get("status") if export_cb else None
    step4_ok = (export_cb is not None)

    report["steps"].append({"step": 4, "action": "等待 export callback",
                            "callback_status": export_status, "passed": step4_ok})
    if export_cb:
        print("  ✓ export 回调到达, status=%s" % export_status)
        if export_status != 200:
            ext = export_cb.get("extMessage", "")
            print("  extMessage: %s" % ext)
    else:
        report["steps"][-1]["issue"] = "超时未收到 export 回调"
        print("  ✗ 超时")

    # ── Step 5: 锁释放后再次 import → 预期成功 ──────────
    print("\n" + "─" * 64)
    print("  Step 5 | 锁释放后发起 import（预期成功）| %s" % now_str())
    print("─" * 64)

    # 重新获取最新文件（可能 step2 的 export 产生了新文件）
    print("  重新获取最新导出文件...")
    file_info_new = get_latest_export_file() or file_info
    import_body_ok = build_import_body(file_info_new)
    import_rid_ok = import_body_ok["requestId"]
    print("  requestId: %s" % import_rid_ok)

    try:
        resp = client.post(endpoint="/api/1.0/chsm/image", json_data=import_body_ok)
        code5 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code5, resp.elapsed.total_seconds()))
    except Exception as e:
        code5 = 0
        print("  → 异常: %s" % e)

    step5_ok = (code5 == 200)
    report["steps"].append({"step": 5, "action": "锁释放后 import",
                            "requestId": import_rid_ok, "status_code": code5, "passed": step5_ok})
    if step5_ok:
        print("  ✓ import 请求已接受")
    else:
        report["steps"][-1]["issue"] = "锁释放后 import 返回 HTTP %d" % code5
        print("  ✗ HTTP %d" % code5)

    # ── Step 6: 等 import 回调 ────────────────────────────
    if step5_ok:
        print("\n" + "─" * 64)
        print("  Step 6 | 等待 import 回调 | %s" % now_str())
        print("─" * 64)

        import_cb = find_callback(import_rid_ok, timeout=POLL_TIMEOUT)
        import_status = import_cb.get("status") if import_cb else None
        step6_ok = (import_status == 200)

        report["steps"].append({"step": 6, "action": "等待 import callback",
                                "callback_status": import_status, "passed": step6_ok})
        if import_cb:
            print("  import 回调 status=%s" % import_status)
            if import_status != 200:
                ext = import_cb.get("extMessage", "")
                print("  extMessage: %s" % ext)
                report["steps"][-1]["issue"] = "import 回调 status=%s: %s" % (import_status, ext)
        else:
            report["steps"][-1]["issue"] = "超时未收到 import 回调"
    else:
        step6_ok = False

    # ── 汇总 ─────────────────────────────────────────────
    passed = step3_blocked and step4_ok and step5_ok and step6_ok
    report["passed"] = passed

    issues = [s["issue"] for s in report["steps"] if "issue" in s]
    if issues:
        report["issues"] = issues

    if passed:
        report["verdict"] = "PASS — export 期间 import 被阻塞 + 锁释放后 import 成功"
    elif step3_blocked and not step5_ok:
        report["verdict"] = "PASS(部分) — export 期间阻塞正确，但锁释放后 import 失败"
    elif not step3_blocked:
        report["verdict"] = "FAIL — export 期间 import 未被阻塞"
    else:
        report["verdict"] = "FAIL — %s" % (issues[0] if issues else "未知原因")

    print("\n" + "=" * 64)
    print("  结论: %s" % report["verdict"])
    if issues:
        print("  问题:")
        for iss in issues:
            print("    - %s" % iss)
    print("  完成时间: %s" % now_str())
    print("=" * 64)

    _save_report(report)
    return passed


def _save_report(report):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_export_block_import_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
