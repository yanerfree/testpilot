#!/usr/bin/env python3
"""
9.2.5-7 锁定接口验证 — 在持锁操作进行中运行此脚本

用法:
  1. 先手动触发一个持锁操作（如 9.2.5 exportBackupKeys）
  2. 运行此脚本，验证以下接口是否被阻塞
  3. 可反复运行

被验证的接口:
  9.2.5 exportBackupKeys
  9.2.6 importBackupKeys（需要有导出文件）
  9.2.7 doVsmInit
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from glob import glob

import requests as req

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.signer import get_signer
from common.logger import logger

# ================================================================
# ★ 配置 ★
# ================================================================
VSM_HOST = "https://192.168.8.201:7443"
BACKUP_KEY = "VXnJ514jUDnAHhNqdypZkFVkn5DZBYBaXpH/GMmmDLc="
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")

# 指纹覆盖: 9.2 的指纹和 7.1 不同，填 VSM 系统的指纹值，为空则用 signer 计算的
AUTH_PK_OVERRIDE = ""


def now_str():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _sign_json(body):
    signer = get_signer()
    headers = signer.sign(json.dumps(body))
    if AUTH_PK_OVERRIDE:
        headers["CHSM-AuthPK"] = AUTH_PK_OVERRIDE
    return headers


def _sign_form(form_data):
    sign_str = "&".join("%s=%s" % (k, v) for k, v in sorted(form_data.items()))
    signer = get_signer()
    headers = signer.sign(sign_str)
    if AUTH_PK_OVERRIDE:
        headers["CHSM-AuthPK"] = AUTH_PK_OVERRIDE
    return headers


def _get_latest_export_file():
    """获取最新的导出文件"""
    if not os.path.isdir(EXPORT_DIR):
        return None
    files = sorted(glob(os.path.join(EXPORT_DIR, "*.dat")), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def check_export():
    """9.2.5 exportBackupKeys"""
    rid = str(uuid.uuid4())
    body = {"requestId": rid, "backupKey": BACKUP_KEY}
    headers = {"Content-Type": "application/json", "User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_json(body))

    url = "%s/platformServlet?method=exportBackupKeys" % VSM_HOST
    try:
        resp = req.post(url, json=body, headers=headers, verify=False, timeout=30)
        code = resp.status_code
        return code, resp.elapsed.total_seconds()
    except Exception as e:
        return 0, 0


def check_import():
    """9.2.6 importBackupKeys"""
    export_file = _get_latest_export_file()
    if not export_file:
        print("    (无导出文件，跳过 import 验证)")
        return -1, 0

    rid = str(uuid.uuid4())
    form_data = {"requestId": rid, "backupKey": BACKUP_KEY}
    headers = {"User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_form(form_data))

    url = "%s/platformServlet?method=importBackupKeys" % VSM_HOST
    try:
        with open(export_file, "rb") as f:
            files = {"file": (os.path.basename(export_file), f, "application/octet-stream")}
            resp = req.post(url, data=form_data, files=files, headers=headers, verify=False, timeout=30)
        return resp.status_code, resp.elapsed.total_seconds()
    except Exception as e:
        return 0, 0


def check_vsm_init():
    """9.2.7 doVsmInit"""
    rid = str(uuid.uuid4())
    body = {"requestId": rid, "clearPK": "false"}
    headers = {"Content-Type": "application/json", "User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_json(body))

    url = "%s/platformServlet?method=doVsmInit" % VSM_HOST
    try:
        resp = req.post(url, json=body, headers=headers, verify=False, timeout=30)
        return resp.status_code, resp.elapsed.total_seconds()
    except Exception as e:
        return 0, 0


def run():
    print("=" * 64)
    print("  9.2.5-7 锁定接口验证")
    print("  提示: 请先触发一个持锁操作再运行此脚本")
    print("  VSM: %s" % VSM_HOST)
    print("  %s" % now_str())
    print("=" * 64)

    checks = [
        ("9.2.5 exportBackupKeys", check_export),
        ("9.2.6 importBackupKeys", check_import),
        ("9.2.7 doVsmInit",        check_vsm_init),
    ]

    results = []
    blocked = 0
    skipped = 0

    for name, fn in checks:
        code, elapsed = fn()
        if code == -1:
            print("  SKIP     ---    ---    %s" % name)
            skipped += 1
            continue
        is_blocked = (code != 200)
        icon = "BLOCKED" if is_blocked else "NOT BLOCKED!"
        print("  %s  HTTP %3d  %.3fs  %s" % (icon, code, elapsed, name))
        if is_blocked:
            blocked += 1
        results.append({"name": name, "code": code, "blocked": is_blocked})

    not_blocked = sum(1 for r in results if not r["blocked"])
    print("\n" + "─" * 64)
    print("  结果: %d/%d 被阻塞" % (blocked, len(results)))
    if skipped:
        print("  跳过: %d" % skipped)
    if not_blocked > 0:
        print("  未阻塞:")
        for r in results:
            if not r["blocked"]:
                print("    ✗ %s (HTTP %d)" % (r["name"], r["code"]))
    else:
        print("  ✓ 全部被阻塞")
    print("─" * 64)

    return not_blocked == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
