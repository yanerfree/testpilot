#!/usr/bin/env python3
"""
签名工具 — 修改下方参数后直接运行: python3 tools/sign.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.signer import get_signer

# ========== 在这里填写 ==========

# 签名算法: RSAWithSHA256 | SM2WithSM3
ALGORITHM = "RSAWithSHA256"

# 请求类型: POST | GET
METHOD = "POST"

# POST 时填 JSON body（字典）
JSON_BODY = {
    "requestId": "d0b78b46-c4bc-44c1-96e6-2e8130eabad7",
    "oprType": "getinfo",
}

# GET 时填 query params（字典），按 key 排序后拼成 k1=v1&k2=v2 再签名
QUERY_PARAMS = {
    "requestId": "d0b78b46-c4bc-44c1-96e6-2e8130eabad7",
}

# ================================


def build_sign_string():
    if METHOD.upper() == "POST":
        return json.dumps(JSON_BODY)
    elif METHOD.upper() == "GET":
        return "&".join(f"{k}={v}" for k, v in sorted(QUERY_PARAMS.items()) if v is not None)
    else:
        return ""


sign_str = build_sign_string()
signer = get_signer(ALGORITHM)
headers = signer.sign(sign_str)

print(f"请求类型:   {METHOD.upper()}")
print(f"待签名串:   {sign_str}")
print(f"算法:       {headers['CHSM-SignatureAlg']}")
print(f"指纹:       {headers['CHSM-AuthPK']}")
print(f"签名:       {headers['CHSM-Signature']}")
