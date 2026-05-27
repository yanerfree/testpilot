#!/usr/bin/env python3
"""
签名演示脚本 — 展示两种签名算法的完整签名流程。

运行: python3 demo_sign.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.signer import get_signer, _signer_cache


def demo():
    # 清除缓存
    _signer_cache.clear()

    # 模拟几种典型请求体
    test_cases = [
        {
            "name": "1. getCHSMInfo (POST JSON body)",
            "body": json.dumps({"requestId": "d0b78b46-c4bc-44c1-96e6-2e8130eabad7", "oprType": "getinfo"}),
        },
        {
            "name": "2. getCHSMStatus (GET query params)",
            "body": "requestId=d0b78b46-c4bc-44c1-96e6-2e8130eabad7",
        },
        {
            "name": "3. configCHSMPk (POST JSON body)",
            "body": json.dumps({"requestId": "uuid-test", "algorithm": "rsa", "pks": ["MIIBIjANBgkq..."]}),
        },
        {
            "name": "4. 空 body (某些 GET 接口)",
            "body": "",
        },
    ]

    for alg_name in ["RSAWithSHA256", "SM2WithSM3"]:
        print("=" * 70)
        print(f"  签名算法: {alg_name}")
        print("=" * 70)

        signer = get_signer(alg_name)
        print(f"  算法标识:   {signer.algorithm_name()}")
        print(f"  公钥指纹:   {signer.fingerprint()}")
        print()

        for tc in test_cases:
            print(f"  --- {tc['name']} ---")
            print(f"  待签名串: {tc['body'][:80]}{'...' if len(tc['body']) > 80 else ''}")

            headers = signer.sign(tc["body"])
            print(f"  请求头:")
            print(f"    CHSM-AuthPK:      {headers['CHSM-AuthPK']}")
            print(f"    CHSM-SignatureAlg: {headers['CHSM-SignatureAlg']}")
            print(f"    CHSM-Signature:   {headers['CHSM-Signature'][:60]}...")
            print(f"    签名长度:          {len(headers['CHSM-Signature'])} chars")
            print()

        print()

    # ------------------------------------------------------------------
    # 验证: 同一数据，两种算法签名不同
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  交叉验证")
    print("=" * 70)
    body = json.dumps({"requestId": "test", "oprType": "getinfo"})

    rsa_sig = get_signer("RSAWithSHA256").sign(body)["CHSM-Signature"]
    sm2_sig = get_signer("SM2WithSM3").sign(body)["CHSM-Signature"]

    print(f"  RSA 签名: {rsa_sig[:50]}...")
    print(f"  SM2 签名: {sm2_sig[:50]}...")
    print(f"  两者不同: {rsa_sig != sm2_sig}")
    print()

    # ------------------------------------------------------------------
    # 密钥来源说明
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  密钥来源说明")
    print("=" * 70)
    print("  RSA 密钥: 与一期 SHA256withRSA.py 中硬编码的密钥完全相同")
    print("           私钥: PKCS8 DER 格式, BASE64 编码, 2048 bit")
    print("           公钥: SubjectPublicKeyInfo DER 格式, BASE64 编码")
    print(f"           指纹: /WiF31yZx0q9nF0fQBudD7xSeivFBfdEhG8hl/KQo1c=")
    print()
    print("  SM2 密钥: 当前为 gmssl 标准测试密钥 (来自国密规范示例)")
    print("           私钥: 256 bit, HEX 格式")
    print("           公钥: 512 bit (x+y), HEX 格式")
    print(f"           指纹: {get_signer('SM2WithSM3').fingerprint()}")
    print()
    print("  密钥替换方式:")
    print("    方式1: 修改 config.yaml 中的 key_path, 放入 PEM/HEX 文件")
    print("           auth.rsa.private_key_path / auth.rsa.public_key_path")
    print("           auth.sm2.private_key_path / auth.sm2.public_key_path")
    print("    方式2: 修改 signer.py 底部的 _RSA_PRIVATE_KEY_B64 等常量")
    print()


if __name__ == "__main__":
    demo()
