#!/usr/bin/env python3
"""
9.2.5/9.2.6 导出导入场景测试

流程:
  1. 调用 9.2.5 exportBackupKeys 导出（返回二进制流，保存到本地文件）
  2. 调用 9.2.6 importBackupKeys 导入（multipart 上传导出的文件，backupKey 一致）
  3. 验证导入结果

注意:
  - 导出返回二进制文件流（Content-Type: application/octet-stream）
  - 导入用 multipart/form-data，file 不参与签名
  - backupKey 导出导入必须一致
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime

import requests as req

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.http_client import get_http_client
from common.signer import get_signer
from common.logger import logger
from config import config

# ================================================================
# ★ 配置 ★
# ================================================================
VSM_HOST = "https://192.168.8.201:7443"
BACKUP_KEY = "VXnJ514jUDnAHhNqdypZkFVkn5DZBYBaXpH/GMmmDLc="
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")

# 指纹覆盖: 9.2 的指纹和 7.1 不同，填 VSM 系统的指纹值，为空则用 signer 计算的
AUTH_PK_OVERRIDE = ""


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _sign_json(body_dict):
    """对 JSON body 签名，返回认证头"""
    signer = get_signer()
    headers = signer.sign(json.dumps(body_dict))
    if AUTH_PK_OVERRIDE:
        headers["CHSM-AuthPK"] = AUTH_PK_OVERRIDE
    return headers


def _sign_form(form_data):
    """对表单字段签名（file 不参与），返回认证头"""
    sign_str = "&".join("%s=%s" % (k, v) for k, v in sorted(form_data.items()))
    signer = get_signer()
    headers = signer.sign(sign_str)
    if AUTH_PK_OVERRIDE:
        headers["CHSM-AuthPK"] = AUTH_PK_OVERRIDE
    return headers


# ================================================================
# 主流程
# ================================================================

def run():
    report = {"scenario": "9.2_export_import", "steps": [], "passed": False}

    print("=" * 64)
    print("  9.2.5/9.2.6 导出导入场景测试")
    print("  VSM HOST: %s" % VSM_HOST)
    print("  backupKey: %s" % BACKUP_KEY)
    print("  导出目录: %s" % EXPORT_DIR)
    print("  开始时间: %s" % now_str())
    print("=" * 64)

    os.makedirs(EXPORT_DIR, exist_ok=True)

    # ── Step 1: 导出 ────────────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 1 | 9.2.5 exportBackupKeys 导出 | %s" % now_str())
    print("─" * 64)

    export_rid = str(uuid.uuid4())
    export_body = {"requestId": export_rid, "backupKey": BACKUP_KEY}

    print("  POST %s/platformServlet?method=exportBackupKeys" % VSM_HOST)
    print("  requestId: %s" % export_rid)

    headers = {"Content-Type": "application/json", "User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_json(export_body))

    export_file = None
    try:
        url = "%s/platformServlet?method=exportBackupKeys" % VSM_HOST
        t0 = time.time()
        resp = req.post(url, json=export_body, headers=headers, verify=False, timeout=120)
        elapsed = time.time() - t0
        code1 = resp.status_code

        print("  → HTTP %d (%.3fs)" % (code1, elapsed))
        print("  → Content-Type: %s" % resp.headers.get("Content-Type", "?"))
        print("  → Content-Length: %s bytes" % len(resp.content))

        if code1 == 200 and len(resp.content) > 100:
            filename = "backup_%s_%s.dat" % (export_rid[:8], datetime.now().strftime("%Y%m%d%H%M%S"))
            export_file = os.path.join(EXPORT_DIR, filename)
            with open(export_file, "wb") as f:
                f.write(resp.content)
            print("  → 已保存: %s (%d bytes)" % (export_file, len(resp.content)))
        elif code1 == 200:
            try:
                print("  → 响应: %s" % json.dumps(resp.json(), ensure_ascii=False)[:300])
            except Exception:
                print("  → 响应体太小(%d bytes)，可能不是二进制文件" % len(resp.content))
        else:
            try:
                print("  → 响应: %s" % json.dumps(resp.json(), ensure_ascii=False)[:300])
            except Exception:
                print("  → 响应: %s" % resp.text[:300])
    except Exception as e:
        code1 = 0
        elapsed = 0
        print("  → 异常: %s" % e)

    step1_ok = (code1 == 200 and export_file is not None)
    report["steps"].append({
        "step": 1, "action": "9.2.5 exportBackupKeys",
        "requestId": export_rid, "status_code": code1,
        "export_file": export_file, "file_size": os.path.getsize(export_file) if export_file else 0,
        "passed": step1_ok,
    })
    if not step1_ok:
        report["steps"][-1]["issue"] = "导出失败 HTTP %d" % code1 if code1 != 200 else "HTTP 200 但未返回有效文件"
        report["verdict"] = "FAIL — 导出失败"
        _print_summary(report)
        _save_report(report)
        return False

    print("  ✓ 导出成功")

    # ── Step 2: 导入 ────────────────────────────────────
    print("\n" + "─" * 64)
    print("  Step 2 | 9.2.6 importBackupKeys 导入 | %s" % now_str())
    print("─" * 64)

    import_rid = str(uuid.uuid4())
    form_data = {"requestId": import_rid, "backupKey": BACKUP_KEY}

    print("  POST %s/platformServlet?method=importBackupKeys" % VSM_HOST)
    print("  requestId: %s" % import_rid)
    print("  backupKey: %s" % BACKUP_KEY)
    print("  file: %s" % export_file)

    headers2 = {"User-Agent": "CHSM-Test/2.0"}
    headers2.update(_sign_form(form_data))

    try:
        url = "%s/platformServlet?method=importBackupKeys" % VSM_HOST
        with open(export_file, "rb") as f:
            files = {"file": (os.path.basename(export_file), f, "application/octet-stream")}
            t0 = time.time()
            resp = req.post(url, data=form_data, files=files, headers=headers2, verify=False, timeout=120)
            elapsed2 = time.time() - t0

        code2 = resp.status_code
        print("  → HTTP %d (%.3fs)" % (code2, elapsed2))
        try:
            body2 = resp.json()
            print("  → 响应: %s" % json.dumps(body2, ensure_ascii=False)[:300])
        except Exception:
            print("  → 响应: %s" % resp.text[:300])
    except Exception as e:
        code2 = 0
        elapsed2 = 0
        print("  → 异常: %s" % e)

    step2_ok = (code2 == 200)
    report["steps"].append({
        "step": 2, "action": "9.2.6 importBackupKeys",
        "requestId": import_rid, "status_code": code2,
        "passed": step2_ok,
    })
    if step2_ok:
        print("  ✓ 导入成功")
    else:
        report["steps"][-1]["issue"] = "导入失败 HTTP %d" % code2

    # ── 汇总 ─────────────────────────────────────────────
    passed = step1_ok and step2_ok
    report["passed"] = passed

    issues = [s["issue"] for s in report["steps"] if "issue" in s]
    if issues:
        report["issues"] = issues

    report["verdict"] = "PASS — 导出+导入全流程成功" if passed else "FAIL — %s" % (issues[0] if issues else "未知")

    _print_summary(report)
    _save_report(report)
    return passed


def _print_summary(report):
    print("\n" + "=" * 64)
    print("  9.2 导出导入测试结论")
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
    path = "output/scenario_9_2_export_import_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
