#!/usr/bin/env python3
"""
7.1+7.2 锁定接口验证 — 在持锁操作（export/upgrade等）进行中运行此脚本

用法:
  1. 先手动触发一个持锁操作（如 CHSM export / VSM upgrade）
  2. 运行此脚本，验证以下接口是否被阻塞（预期非200或callback FAILED）
  3. 可反复运行

被验证的接口:
  7.1: export(8), import(9), upgrade(10), restart(11), backup(12), restore(13)
  7.2: export(5), import(6), start(7), stop(8), restart(9), reset(10), upgrade(11)
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.http_client import get_http_client
from common.logger import logger

# ================================================================
# ★ 配置 ★
# ================================================================
CHSM_HOST = "https://192.168.8.120:7443"
VSM_HOST = "https://192.168.8.120:7443"
VSM_ID = "bf356592d2a0"
CALLBACK_URL = "http://127.0.0.1:9443/callback"

BLOCKED_OPS = [
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


def now_str():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def run():
    print("=" * 64)
    print("  7.1+7.2 锁定接口验证")
    print("  提示: 请先触发一个持锁操作再运行此脚本")
    print("  %s" % now_str())
    print("=" * 64)

    results = []
    blocked = 0
    not_blocked = 0

    for op in BLOCKED_OPS:
        body = dict(op["body"])
        body["requestId"] = str(uuid.uuid4())
        client = get_http_client(base_url=op["host"])

        try:
            resp = client.post(endpoint=op["endpoint"], json_data=body)
            code = resp.status_code
            elapsed = resp.elapsed.total_seconds()
        except Exception as e:
            code = 0
            elapsed = 0

        is_blocked = (code != 200)
        icon = "BLOCKED" if is_blocked else "NOT BLOCKED!"
        print("  %s  HTTP %3d  %.3fs  %s" % (icon, code, elapsed, op["name"]))

        if is_blocked:
            blocked += 1
        else:
            not_blocked += 1
        results.append({"name": op["name"], "code": code, "blocked": is_blocked})

    print("\n" + "─" * 64)
    print("  结果: %d/%d 被阻塞" % (blocked, len(results)))
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
