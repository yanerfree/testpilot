#!/usr/bin/env python3
"""
导出导入场景测试脚本

流程:
  1. 调用 export 接口发起 CHSM 导出
  2. 轮询 callback/list 等待导出完成（status=200）
  3. 查询 images/list 获取导出文件的 sign 和 token
  4. 调用 import 接口发起导入（sign 和 imageUrl 从文件服务获取）
  5. 轮询 callback/list 等待导入完成
  6. 输出结果
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
CALLBACK_URL = "http://127.0.0.1:9443/callback"
CALLBACK_LIST_URL = "http://192.168.8.120:9443/callback/list"
IMAGES_LIST_URL = "http://192.168.8.120:9443/images/list"
IMAGE_BASE_URL = "http://127.0.0.1:9443/images"
POLL_TIMEOUT = 300
POLL_INTERVAL = 10


# ================================================================
# 工具函数
# ================================================================

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def find_callback(request_id, timeout=POLL_TIMEOUT):
    """轮询 callback/list 查找指定 requestId 的回调"""
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
    print("  超时 %ds 未收到回调" % timeout)
    return None


def find_export_file(request_id):
    """从 images/list 查找导出文件的 sign 和 token"""
    print("\n  查询文件列表: GET %s" % IMAGES_LIST_URL)
    try:
        resp = requests.get(IMAGES_LIST_URL, timeout=10, verify=False)
        if resp.status_code != 200:
            print("  文件列表请求失败: HTTP %d" % resp.status_code)
            return None
        payload = resp.json()
        items = payload.get("result", {}).get("items", [])
        print("  文件总数: %d" % len(items))

        # 按 requestId 匹配
        for item in items:
            if item.get("requestId") == request_id:
                info = item.get("info", {})
                print("  匹配到文件: %s" % item.get("filename", "?"))
                print("    sign: %s" % info.get("sign", "?")[:60])
                print("    token: %s" % info.get("token", "?"))
                print("    alg: %s" % info.get("alg", "?"))
                return info

        # 没有精确匹配，取最新的（按 uploadTime 倒序）
        if items:
            latest = sorted(items, key=lambda x: x.get("uploadTime", ""), reverse=True)[0]
            info = latest.get("info", {})
            print("  未精确匹配 requestId，使用最新文件: %s" % latest.get("filename", "?"))
            print("    sign: %s" % info.get("sign", "?")[:60])
            print("    token: %s" % info.get("token", "?"))
            return info

        print("  文件列表为空")
        return None
    except Exception as e:
        print("  查询文件列表异常: %s" % e)
        return None


# ================================================================
# 主流程
# ================================================================

def run():
    report = {"scenario": "export_import", "steps": [], "passed": False}

    print("=" * 64)
    print("  导出导入场景测试")
    print("  CHSM: %s" % CHSM_HOST)
    print("  回调查询: %s" % CALLBACK_LIST_URL)
    print("  文件查询: %s" % IMAGES_LIST_URL)
    print("  开始时间: %s" % now_str())
    print("=" * 64)

    client = get_http_client(base_url=CHSM_HOST)

    # ── Step 1: 导出 ────────────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 1 | 发起 CHSM export | %s" % now_str())
    print("─" * 64)

    export_rid = str(uuid.uuid4())
    export_body = {
        "requestId": export_rid,
        "oprType": "export",
        "callbackUrl": CALLBACK_URL,
    }
    print("  请求: POST %s/api/1.0/chsm/image" % CHSM_HOST)
    print("  Body: %s" % json.dumps(export_body, ensure_ascii=False))

    try:
        resp = client.post(endpoint="/api/1.0/chsm/image", json_data=export_body)
        code1 = resp.status_code
        body1 = resp.json() if resp.status_code == 200 else resp.text[:300]
        print("  响应: HTTP %d (%.3fs)" % (code1, resp.elapsed.total_seconds()))
        print("  Body: %s" % json.dumps(body1, ensure_ascii=False)[:200] if isinstance(body1, dict) else body1)
    except Exception as e:
        code1 = 0
        print("  异常: %s" % e)

    step1_ok = (code1 == 200)
    report["steps"].append({
        "step": 1, "action": "CHSM export", "requestId": export_rid,
        "status_code": code1, "passed": step1_ok,
    })

    if not step1_ok:
        report["steps"][-1]["issue"] = "export 返回 HTTP %d，无法继续" % code1
        report["verdict"] = "FAIL — export 请求失败"
        _save_report(report)
        return False

    # ── Step 2: 等待导出回调 ─────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 2 | 等待 export 回调 | %s" % now_str())
    print("─" * 64)
    print("  查找: requestId=%s" % export_rid)

    export_cb = find_callback(export_rid, timeout=POLL_TIMEOUT)
    export_status = export_cb.get("status") if export_cb else None

    step2_ok = (export_status == 200)
    report["steps"].append({
        "step": 2, "action": "等待 export callback",
        "callback_status": export_status, "passed": step2_ok,
    })

    if not step2_ok:
        msg = "export 回调 status=%s" % export_status if export_cb else "超时未收到回调"
        print("  ✗ %s" % msg)
        report["steps"][-1]["issue"] = msg
        if export_cb:
            ext = export_cb.get("extMessage", "")
            if ext:
                print("  extMessage: %s" % ext)
                report["steps"][-1]["extMessage"] = ext
        report["verdict"] = "FAIL — export 未成功完成"
        _save_report(report)
        return False

    print("  ✓ export 完成, status=200")

    # ── Step 3: 查询导出文件 ─────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 3 | 查询导出文件 | %s" % now_str())
    print("─" * 64)

    file_info = find_export_file(export_rid)
    step3_ok = (file_info is not None and file_info.get("sign") and file_info.get("token"))
    report["steps"].append({
        "step": 3, "action": "查询 images/list 获取 sign+token",
        "passed": step3_ok, "file_info": file_info,
    })

    if not step3_ok:
        report["steps"][-1]["issue"] = "未找到导出文件或缺少 sign/token"
        report["verdict"] = "FAIL — 导出文件查询失败"
        _save_report(report)
        return False

    file_sign = file_info["sign"]
    file_token = file_info["token"]
    file_alg = file_info.get("alg", "rsa")
    # alg 映射: rsa → RSAWithSHA256
    import_alg = "RSAWithSHA256" if file_alg.lower() == "rsa" else "SM2WithSM3"

    print("  ✓ 获取到文件信息")
    print("    sign: %s..." % file_sign[:60])
    print("    token: %s" % file_token)
    print("    alg: %s → %s" % (file_alg, import_alg))

    # ── Step 4: 导入 ────────────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 4 | 发起 CHSM import | %s" % now_str())
    print("─" * 64)

    import_rid = str(uuid.uuid4())
    image_url = "%s?file=%s" % (IMAGE_BASE_URL, file_token)
    import_body = {
        "requestId": import_rid,
        "oprType": "import",
        "imageUrl": image_url,
        "alg": import_alg,
        "sign": file_sign,
        "callbackUrl": CALLBACK_URL,
    }
    print("  请求: POST %s/api/1.0/chsm/image" % CHSM_HOST)
    print("  Body: %s" % json.dumps(import_body, ensure_ascii=False)[:300])

    try:
        resp = client.post(endpoint="/api/1.0/chsm/image", json_data=import_body)
        code4 = resp.status_code
        body4 = resp.json() if resp.status_code == 200 else resp.text[:300]
        print("  响应: HTTP %d (%.3fs)" % (code4, resp.elapsed.total_seconds()))
        print("  Body: %s" % json.dumps(body4, ensure_ascii=False)[:200] if isinstance(body4, dict) else body4)
    except Exception as e:
        code4 = 0
        print("  异常: %s" % e)

    step4_ok = (code4 == 200)
    report["steps"].append({
        "step": 4, "action": "CHSM import", "requestId": import_rid,
        "status_code": code4, "passed": step4_ok,
        "imageUrl": image_url, "alg": import_alg,
    })

    if not step4_ok:
        report["steps"][-1]["issue"] = "import 返回 HTTP %d" % code4
        report["verdict"] = "FAIL — import 请求失败"
        _save_report(report)
        return False

    # ── Step 5: 等待导入回调 ─────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 5 | 等待 import 回调 | %s" % now_str())
    print("─" * 64)
    print("  查找: requestId=%s" % import_rid)

    import_cb = find_callback(import_rid, timeout=POLL_TIMEOUT)
    import_status = import_cb.get("status") if import_cb else None

    step5_ok = (import_status == 200)
    report["steps"].append({
        "step": 5, "action": "等待 import callback",
        "callback_status": import_status, "passed": step5_ok,
    })

    if not step5_ok:
        msg = "import 回调 status=%s" % import_status if import_cb else "超时未收到回调"
        print("  ✗ %s" % msg)
        report["steps"][-1]["issue"] = msg
        if import_cb:
            ext = import_cb.get("extMessage", "")
            if ext:
                print("  extMessage: %s" % ext)
                report["steps"][-1]["extMessage"] = ext
    else:
        print("  ✓ import 完成, status=200")

    # ── 汇总 ─────────────────────────────────────────────
    passed = step1_ok and step2_ok and step3_ok and step4_ok and step5_ok
    report["passed"] = passed

    issues = [s["issue"] for s in report["steps"] if "issue" in s]
    if issues:
        report["issues"] = issues

    if passed:
        report["verdict"] = "PASS — 导出+导入全流程成功"
    elif not report.get("verdict"):
        report["verdict"] = "FAIL — 导入未成功完成"

    print("\n" + "=" * 64)
    print("  结论: %s" % report["verdict"])
    print("  export requestId: %s" % export_rid)
    print("  import requestId: %s" % import_rid)
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
    path = "output/scenario_export_import_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
