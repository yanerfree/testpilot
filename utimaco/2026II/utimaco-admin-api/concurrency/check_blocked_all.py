#!/usr/bin/env python3
"""
全量锁定接口验证 — 7.1 + 7.2 + 9.2 一次跑完

用法:
  1. 先手动触发一个持锁操作（如 CHSM export / VSM upgrade）
  2. 运行此脚本，验证所有接口是否被阻塞
  3. 可反复运行

指纹配置从 config/config.yaml 读取:
  auth.chsm_fingerprint — 7.1/7.2 接口用（留空用 signer 默认）
  auth.vsm_fingerprint  — 9.2 接口用（留空用 signer 默认）
"""

import json
import os
import sys
import uuid
from datetime import datetime
from glob import glob

import requests as req

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.http_client import get_http_client
from common.signer import get_signer
from common.logger import logger
from config import config

# ================================================================
# ★ 配置 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"
VSM_HOST = "https://192.168.8.120:7443"
TENANT_HOST = "https://192.168.8.201:7443"
VSM_ID = "bf356592d2a0"
CALLBACK_URL = "http://127.0.0.1:9443/callback"
BACKUP_KEY = "VXnJ514jUDnAHhNqdypZkFVkn5DZBYBaXpH/GMmmDLc="
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")

# 从 config.yaml 读指纹
CHSM_FP = config.get("auth.chsm_fingerprint", "") or None
VSM_FP = config.get("auth.vsm_fingerprint", "") or None


def now_str():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _get_latest_export_file():
    if not os.path.isdir(EXPORT_DIR):
        return None
    files = sorted(glob(os.path.join(EXPORT_DIR, "*.dat")), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


# ================================================================
# 7.1 + 7.2 接口（用 CHSM 指纹）
# ================================================================

BLOCKED_7X = [
    {"name": "7.1.8  exportCHSM",   "host": CHSM_HOST, "endpoint": "/api/1.0/chsm/image",
     "body": {"oprType": "export", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.9  importCHSM",   "host": CHSM_HOST, "endpoint": "/api/1.0/chsm/image",
     "body": {"oprType": "import", "imageUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.11 restartCHSM",  "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"oprType": "restart", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.12 backupCHSM",   "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"oprType": "backup", "callbackUrl": CALLBACK_URL}},
    {"name": "7.1.13 restoreCHSM",  "host": CHSM_HOST, "endpoint": "/api/1.0/chsm",
     "body": {"oprType": "restore", "backupUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.5  exportVSM",    "host": VSM_HOST, "endpoint": "/api/1.0/vsm/image",
     "body": {"oprType": "export", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.6  importVSM",    "host": VSM_HOST, "endpoint": "/api/1.0/vsm/image",
     "body": {"oprType": "import", "vsmId": VSM_ID, "imageUrl": "http://127.0.0.1:9443/images",
              "alg": "RSAWithSHA256", "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.7  startVSM",     "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"oprType": "start", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.8  stopVSM",      "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"oprType": "stop", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.9  restartVSM",   "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"oprType": "restart", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.10 resetVSM",     "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"oprType": "reset", "vsmId": VSM_ID, "callbackUrl": CALLBACK_URL}},
    {"name": "7.2.11 upgradeVSM",   "host": VSM_HOST, "endpoint": "/api/1.0/vsm",
     "body": {"oprType": "upgrade", "vsmId": VSM_ID, "packVersion": "1.0",
              "packUrl": "http://127.0.0.1:9443/images", "alg": "RSAWithSHA256",
              "sign": "PLACEHOLDER", "callbackUrl": CALLBACK_URL}},
]


def check_7x():
    """检查 7.1+7.2 接口"""
    results = []
    for op in BLOCKED_7X:
        body = dict(op["body"])
        body["requestId"] = str(uuid.uuid4())
        client = get_http_client(base_url=op["host"], fingerprint_override=CHSM_FP)
        try:
            resp = client.post(endpoint=op["endpoint"], json_data=body)
            code = resp.status_code
            elapsed = resp.elapsed.total_seconds()
        except Exception:
            code = 0
            elapsed = 0
        is_blocked = (code != 200)
        icon = "BLOCKED" if is_blocked else "NOT BLOCKED!"
        print("  %-12s HTTP %3d  %.3fs  %s" % (icon, code, elapsed, op["name"]))
        results.append({"name": op["name"], "code": code, "blocked": is_blocked})
    return results


# ================================================================
# 9.2 接口（用 VSM 指纹）
# ================================================================

def _sign_json_9_2(body):
    signer = get_signer()
    headers = signer.sign(json.dumps(body))
    if VSM_FP:
        headers["CHSM-AuthPK"] = VSM_FP
    return headers


def _sign_form_9_2(form_data):
    sign_str = "&".join("%s=%s" % (k, v) for k, v in sorted(form_data.items()))
    signer = get_signer()
    headers = signer.sign(sign_str)
    if VSM_FP:
        headers["CHSM-AuthPK"] = VSM_FP
    return headers


def check_9_2_export():
    """9.2.5 exportBackupKeys"""
    body = {"requestId": str(uuid.uuid4()), "backupKey": BACKUP_KEY}
    headers = {"Content-Type": "application/json", "User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_json_9_2(body))
    url = "%s/platformServlet?method=exportBackupKeys" % TENANT_HOST
    try:
        resp = req.post(url, json=body, headers=headers, verify=False, timeout=30)
        return resp.status_code, resp.elapsed.total_seconds()
    except Exception:
        return 0, 0


def check_9_2_import():
    """9.2.6 importBackupKeys"""
    export_file = _get_latest_export_file()
    if not export_file:
        return -1, 0
    form_data = {"requestId": str(uuid.uuid4()), "backupKey": BACKUP_KEY}
    headers = {"User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_form_9_2(form_data))
    url = "%s/platformServlet?method=importBackupKeys" % TENANT_HOST
    try:
        with open(export_file, "rb") as f:
            files = {"file": (os.path.basename(export_file), f, "application/octet-stream")}
            resp = req.post(url, data=form_data, files=files, headers=headers, verify=False, timeout=30)
        return resp.status_code, resp.elapsed.total_seconds()
    except Exception:
        return 0, 0


def check_9_2_vsminit():
    """9.2.7 doVsmInit"""
    body = {"requestId": str(uuid.uuid4()), "clearPK": "false"}
    headers = {"Content-Type": "application/json", "User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_json_9_2(body))
    url = "%s/platformServlet?method=doVsmInit" % TENANT_HOST
    try:
        resp = req.post(url, json=body, headers=headers, verify=False, timeout=30)
        return resp.status_code, resp.elapsed.total_seconds()
    except Exception:
        return 0, 0


def check_9_2():
    """检查 9.2 接口"""
    checks = [
        ("9.2.5 exportBackupKeys", check_9_2_export),
        ("9.2.6 importBackupKeys", check_9_2_import),
        ("9.2.7 doVsmInit",        check_9_2_vsminit),
    ]
    results = []
    for name, fn in checks:
        code, elapsed = fn()
        if code == -1:
            print("  %-12s  ---     ---    %s (无导出文件,跳过)" % ("SKIP", name))
            continue
        is_blocked = (code != 200)
        icon = "BLOCKED" if is_blocked else "NOT BLOCKED!"
        print("  %-12s HTTP %3d  %.3fs  %s" % (icon, code, elapsed, name))
        results.append({"name": name, "code": code, "blocked": is_blocked})
    return results


# ================================================================
# 主流程
# ================================================================

def run():
    print("=" * 64)
    print("  全量锁定接口验证 (7.1 + 7.2 + 9.2)")
    print("  提示: 请先触发一个持锁操作再运行此脚本")
    print("  CHSM: %s  指纹: %s" % (CHSM_HOST, CHSM_FP or "(默认)"))
    print("  VSM:  %s  指纹: %s" % (TENANT_HOST, VSM_FP or "(默认)"))
    print("  %s" % now_str())
    print("=" * 64)

    print("\n--- 7.1 + 7.2 ---")
    results_7x = check_7x()

    print("\n--- 9.2 ---")
    results_9_2 = check_9_2()

    all_results = results_7x + results_9_2
    blocked = sum(1 for r in all_results if r["blocked"])
    not_blocked = sum(1 for r in all_results if not r["blocked"])

    print("\n" + "=" * 64)
    print("  结果: %d/%d 被阻塞" % (blocked, len(all_results)))
    if not_blocked > 0:
        print("  未阻塞:")
        for r in all_results:
            if not r["blocked"]:
                print("    ✗ %s (HTTP %d)" % (r["name"], r["code"]))
    else:
        print("  ✓ 全部被阻塞")
    print("=" * 64)

    return not_blocked == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
