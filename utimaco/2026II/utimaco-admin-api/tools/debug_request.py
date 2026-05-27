#!/usr/bin/env python3
"""
手动调试工具 — 修改下方的请求信息，直接运行即可。

运行: python3 tools/debug_request.py
"""

import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.http_client import get_http_client
from config import config

# 清理框架日志
import logging
logging.getLogger("utimaco").handlers.clear()
logging.getLogger("utimaco").addHandler(logging.NullHandler())


# ============================================================
# 修改这里 ↓↓↓   （取消注释你要用的示例，注释掉其他的）
# ============================================================

# --- 示例1: POST JSON（配置公钥） ---
HOST = None
METHOD = "POST"
ENDPOINT = "/api/1.0/chsm/authpk"
AUTH = True
BODY = {
    "requestId": "uuid",
    "algorithm": "rsa",
    "pks": ["MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."]
}
PARAMS = None
FILE_PATH = None

# # --- 示例2: GET 带查询参数（获取公钥指纹） ---
# HOST = None
# METHOD = "GET"
# ENDPOINT = "/api/1.0/chsm/authpk"
# AUTH = False
# BODY = None
# PARAMS = {"requestId": "uuid"}
# FILE_PATH = None

# # --- 示例3: POST 文件上传（恢复密钥） ---
# HOST = None
# METHOD = "POST"
# ENDPOINT = "/api/1.0/chsm/image"
# AUTH = True
# BODY = {"requestId": "uuid", "oprType": "import"}  # 表单字段
# PARAMS = None
# FILE_PATH = "/path/to/image.zip"  # 文件路径，上传字段名为 data

# ============================================================
# 修改这里 ↑↑↑
# ============================================================


def auto_fill_uuid(data):
    """递归替换 "uuid" 为真实 UUID"""
    if isinstance(data, dict):
        return {k: auto_fill_uuid(v) for k, v in data.items()}
    if isinstance(data, list):
        return [auto_fill_uuid(v) for v in data]
    if isinstance(data, str) and data.strip().lower() == "uuid":
        return str(uuid.uuid4())
    return data


def main():
    client = get_http_client(base_url=HOST, auth_enabled=AUTH)
    method = METHOD.upper()

    print(f"目标:  {client.base_url}")
    print(f"请求:  {method} {ENDPOINT}")
    print(f"签名:  {'开启 (' + config.auth_algorithm + ')' if AUTH else '关闭'}")

    kwargs = {}

    # 文件上传
    if FILE_PATH:
        if not os.path.isfile(FILE_PATH):
            print(f"\n文件不存在: {FILE_PATH}")
            return
        files = {"data": (os.path.basename(FILE_PATH), open(FILE_PATH, "rb"))}
        kwargs["files"] = files
        if BODY:
            form_data = auto_fill_uuid(BODY)
            kwargs["data"] = form_data
            print(f"表单:  {form_data}")
        print(f"文件:  {FILE_PATH} ({os.path.getsize(FILE_PATH)} bytes)")
        print(f"       (文件内容不参与签名，只对表单字段签名)")
    # JSON body
    elif method in ("POST", "PUT", "DELETE") and BODY:
        body = auto_fill_uuid(BODY)
        kwargs["json_data"] = body
        print(f"Body:  {json.dumps(body, ensure_ascii=False)}")
    # Query 参数
    elif PARAMS:
        params = auto_fill_uuid(PARAMS)
        kwargs["params"] = params
        print(f"Query: {params}")

    print("=" * 60)

    fn = getattr(client, method.lower())
    try:
        resp = fn(endpoint=ENDPOINT, **kwargs)
    except Exception as e:
        print(f"\n请求失败: {e}")
        return

    print(f"\n状态码: {resp.status_code}")
    print(f"耗时:   {resp.elapsed.total_seconds():.3f}s")
    print("=" * 60)

    try:
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(resp.text[:2000])


if __name__ == "__main__":
    main()
