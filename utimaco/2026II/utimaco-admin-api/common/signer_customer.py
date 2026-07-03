"""
签名认证模块 — 同时支持 RSAWithSHA256 和 SM2WithSM3 两种算法。

密钥加载优先级:
  1. config.yaml 中配置的 PEM/HEX 文件路径 → 文件存在则读文件
  2. 文件不存在 → 用下方写死的字符串

testdata 中引用公钥用 ${keys.xxx}，从 data/keys.json 读取（见 excel_handler.py）。

使用方式:
    signer = get_signer()            # 按 config.yaml 中 auth.algorithm 自动选择
    headers = signer.sign("body")    # 返回 CHSM-AuthPK / CHSM-SignatureAlg / CHSM-Signature
"""

import abc
import base64
import hashlib
import json
import os
from typing import Any, Dict

from common.logger import logger
from config import config


# ================================================================
# 默认密钥 — cert/sm2_private_key.pem 等文件不存在时，用下方硬编码值
# 与 cert/keys.json 无关，keys.json 仅供测试用例引用
# ================================================================

RSA_PRIVATE_KEY = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDbl8f5IBYs3b0uFONsSwUax3SQkmixYuyR1hSJnxRXQEXi47yTyWHTsddg0gakZGlPak6CeoV9YE2lceT0JOmNxwMila2+6DUgWmpazYj1LM/CBjFQzkFsdJquMUoZRxKzIbhy6rez2mCqoJR57Daaj6XV1Z1k6piDExqRYen3X/2TyVKtUl1myXbiteuI/rka14bLBgE+PDnWGgGycpRrK4x1BY6/a35D+cEhuYsoGgp4OTEz1o7LYZZMRDr0pizrwzSJmI+6N4OOIQ2JvkFcTQz4ZQ+8+g/DFuu7vthP8yA+HIIJa+zOBCQl1N5v1Qztnm+vJNfcB+yPBls8R5wBAgMBAAECggEAHgDqk1j1frLbZuD2w/SqIWMQQ7KleFs+XJzGGJmyQ0umYN5iBUVWRwD9Hx8DRlHr66xoRr6r35oZcdoSgONMQBFplb+iyjtbCu0frAF6TZmOV4HWGibcXI/AFL3qVHLYFL6uP5FfgUT8wUOIlfIW8d5ft8xkoYXGSd6B2kxpFeH4TPFarEIHe5CLQbKjCszTny8VChgoY/wp/n4sKk1+10P4oHQXZc0/Tb/CR23t7gVJPGthNgrY37vgXaVRH2P0JR8O/k2sq+bpfdAv2RNgFbWcWeaZqWV0utf5UkW6JSqf2q8CsamsBxSWHxRgvgkBGTtTMVa372R5t/yolRrWawKBgQDeeXgOKfbhbpqSQqQpyfMX1bQP1ChmslnHVVI3XOx+kx8+wyGgG9ILeyLM6D20R9QQ642X4cmtVZtPwVpLV3kMk4XyT7l5duFgp4KUoQRMe6/u+MNu/8vreAnzrJdf0lY0M5VRJsMtGPxxyJPaMIVkbtg8EgP1rR6OiqbZ0/TyTwKBgQD8ryWx2TRL0qx2AfJfoXWnh9+o2NdxdcFQMRkiwq+p9Lpp18dgRN2do7cP7ABsvaysYciVmy3jmhbzZ76AbO4hKEaEq7jkjxSgs0D7UxItc9sNsC8ZQYPntF3bVaOQQEvULMDCJBppxphASh0ZgXWBlDCGs/WT46AE4LKRnCSIrwKBgHRMBTFKSI9RtSWuBoj908Dq6sS3gCMnKn1kIaVlQw9rsxKpCKPcxzFPPkLlSJQ8VCRALnVuB3I/5P+NMLlf0Zx8ZbHkcS2IsopHJqCxh0DAC5kdm3Qj7aJ6zqD94OerWXrSWETiwXaKsDR+yKNvZ9u3gfvs4vsDc4zJ+Cy4ezxLAoGBAPFjJGBs/b99Z5FoNLFUnf/IFkrHs7DI7D5+WOPTFlsG1losb2OxBgEFF+lW6+T1oZIf6623y7PFTS2DqwImjaoRPqSZI4z8fpkyBN7SsefH6Lh/2c6HvsnHjW3tts4kDgyIIDCWqsDnniS0aG4oNSfveBgGrJB2ADUIrq3ZezEzAoGABujH4cusjpp2H2IzYjSh5vSEih3o9kCQPkQqL2eFJFenrVONhXcaemcGIr3CJtSECDIFJfY8OdB3BlIvhQW7UQusEzS7T0Ztw/J09K5IkV5K554XjWDGk7yfi3h0+fuWvatvW0nrfy3Ls4BCXO6GlK4+BeD2dD2LgHdK7uExVTc="

RSA_PUBLIC_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA25fH+SAWLN29LhTjbEsFGsd0kJJosWLskdYUiZ8UV0BF4uO8k8lh07HXYNIGpGRpT2pOgnqFfWBNpXHk9CTpjccDIpWtvug1IFpqWs2I9SzPwgYxUM5BbHSarjFKGUcSsyG4cuq3s9pgqqCUeew2mo+l1dWdZOqYgxMakWHp91/9k8lSrVJdZsl24rXriP65GteGywYBPjw51hoBsnKUayuMdQWOv2t+Q/nBIbmLKBoKeDkxM9aOy2GWTEQ69KYs68M0iZiPujeDjiENib5BXE0M+GUPvPoPwxbru77YT/MgPhyCCWvszgQkJdTeb9UM7Z5vryTX3AfsjwZbPEecAQIDAQAB"

SM2_PRIVATE_KEY = "b62JyzmdxSk40Vne2zKhILnAZT2N9ZpkWmBvjus/cNA="

SM2_PUBLIC_KEY = "BA0Nf6CqmrtHGEJWjjqZGwwe9LKKyl8/KlrLdDhUQ7j3T1OzxWRfFJRXq5ihp4wiyWzvRi5G1n/JU8dgawxEhgg="


# ================================================================
# 密钥加载工具
# ================================================================

def _load_pem_key(cfg_path: str, fallback: str) -> str:
    """从 PEM 文件读取密钥（去掉头尾行，合并为单行 BASE64）。文件不存在则返回 fallback。"""
    rel_path = config.get(cfg_path, "")
    if rel_path:
        abs_path = os.path.join(config.root_dir, rel_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r") as f:
                lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("-----")]
            key = "".join(lines)
            logger.info("从文件加载密钥: %s", abs_path)
            return key
    return fallback


def _load_hex_key(cfg_path: str, fallback: str) -> str:
    """从文件读取 HEX 密钥。文件不存在则返回 fallback。"""
    rel_path = config.get(cfg_path, "")
    if rel_path:
        abs_path = os.path.join(config.root_dir, rel_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r") as f:
                key = f.read().strip()
            logger.info("从文件加载密钥: %s", abs_path)
            return key
    return fallback


def _normalize_sm2_private(raw: str) -> str:
    """SM2 私钥归一化为 hex。自动识别 hex / base64 两种输入格式。"""
    raw = raw.strip()
    try:
        b = bytes.fromhex(raw)
        if len(b) == 32:
            return raw.upper()
    except ValueError:
        pass
    b = base64.b64decode(raw)
    if len(b) != 32:
        raise ValueError(f"SM2 私钥长度异常: {len(b)} 字节 (期望 32)")
    return b.hex().upper()


def _normalize_sm2_public(raw: str) -> str:
    """SM2 公钥归一化为 64 字节 hex（无 04 前缀）。自动识别 hex / base64 两种输入格式。"""
    raw = raw.strip()
    try:
        b = bytes.fromhex(raw)
        if len(b) == 64:
            return raw
        if len(b) == 65 and b[0] == 0x04:
            return b[1:].hex()
    except ValueError:
        pass
    b = base64.b64decode(raw)
    if len(b) == 65 and b[0] == 0x04:
        return b[1:].hex()
    if len(b) == 64:
        return b.hex()
    raise ValueError(f"SM2 公钥长度异常: {len(b)} 字节 (期望 64 或 65)")


# ================================================================
# keys.json 读取（供 testdata 中 ${keys.xxx} 引用，不用于签名）
# ================================================================

_keys_cache = None


def load_keys() -> Dict[str, Any]:
    """加载 data/keys.json"""
    global _keys_cache
    if _keys_cache is not None:
        return _keys_cache
    keys_path = os.path.join(config.root_dir, "data", "keys.json")
    with open(keys_path, "r", encoding="utf-8") as f:
        _keys_cache = json.load(f)
    return _keys_cache


def get_key_value(path: str) -> str:
    """按点号路径取值: get_key_value("rsa.key1.public_key")"""
    keys = load_keys()
    node = keys
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise KeyError(f"keys.json 中路径不存在: {path}")
    return node


# ================================================================
# 抽象基类
# ================================================================

class BaseSigner(abc.ABC):

    @abc.abstractmethod
    def algorithm_name(self) -> str:
        ...

    @abc.abstractmethod
    def sign(self, data: str) -> Dict[str, str]:
        ...

    @abc.abstractmethod
    def fingerprint(self) -> str:
        ...


# ================================================================
# RSA SHA256withRSA 签名器
# ================================================================

class RSASigner(BaseSigner):

    def __init__(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        private_b64 = _load_pem_key("auth.rsa.private_key_path", RSA_PRIVATE_KEY)
        public_b64 = _load_pem_key("auth.rsa.public_key_path", RSA_PUBLIC_KEY)

        self._private_key = serialization.load_der_private_key(
            base64.b64decode(private_b64), password=None, backend=default_backend()
        )
        self._fingerprint = self._calc_fingerprint(public_b64)

    def algorithm_name(self) -> str:
        return "SHA256withRSA"

    def fingerprint(self) -> str:
        return self._fingerprint

    def sign(self, data: str) -> Dict[str, str]:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        sig = self._private_key.sign(
            data.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "CHSM-AuthPK": "QvbCUYXy/f6fWvJTv1gP3mBwS2zPc7C5Y7pffO+htB4=", # "70CdAfIy2L3wccIUM9Lk9MWnB+pFBPENSQc88q7+BQ0="#,#, ,self._fingerprint,
            "CHSM-SignatureAlg": self.algorithm_name(),
            "CHSM-Signature": base64.b64encode(sig).decode("utf-8"),
        }

    @staticmethod
    def _calc_fingerprint(pub_b64: str) -> str:
        digest = hashlib.sha256(pub_b64.encode("utf-8")).digest()
        return base64.b64encode(digest).decode("ascii")


# ================================================================
# SM2WithSM3 签名器
# ================================================================

class SM2Signer(BaseSigner):

    def __init__(self):
        try:
            from gmssl import sm2 as _sm2
        except ImportError:
            raise ImportError("SM2WithSM3 需要 gmssl 库: pip install gmssl")

        raw_priv = _load_hex_key("auth.sm2.private_key_path", SM2_PRIVATE_KEY)
        raw_pub = _load_hex_key("auth.sm2.public_key_path", SM2_PUBLIC_KEY)
        private_hex = _normalize_sm2_private(raw_priv)
        public_hex = _normalize_sm2_public(raw_pub)

        self._sm2_crypt = _sm2.CryptSM2(
            private_key=private_hex,
            public_key=public_hex,
        )
        self._fingerprint = self._calc_fingerprint(public_hex)

    def algorithm_name(self) -> str:
        return "SM2WithSM3"

    def fingerprint(self) -> str:
        return self._fingerprint

    def sign(self, data: str) -> Dict[str, str]:
        sig_hex = self._sm2_crypt.sign_with_sm3(data.encode("utf-8"))
        return {
            "CHSM-AuthPK": "T098X6uAFR1HqLee5uQy+QuVhCWfZCLCs8/h208HOfA=",#"USo1RSNfpigzeKT16urRd8qViV8Zld+GbbJ+3GlF5DQ=",#self._fingerprint,
            "CHSM-SignatureAlg": self.algorithm_name(),
            "CHSM-Signature": base64.b64encode(bytes.fromhex(sig_hex)).decode("utf-8"),
        }

    @staticmethod
    def _calc_fingerprint(pub_hex: str) -> str:
        try:
            from gmssl import sm3, func as _func
            pub_bytes = bytes.fromhex(pub_hex)
            digest = sm3.sm3_hash(_func.bytes_to_list(pub_bytes))
            return base64.b64encode(bytes.fromhex(digest)).decode("ascii")
        except ImportError:
            digest = hashlib.sha256(pub_hex.encode("utf-8")).digest()
            return base64.b64encode(digest).decode("ascii")


# ================================================================
# 工厂函数
# ================================================================

_signer_cache: Dict[str, BaseSigner] = {}


def get_signer(algorithm: str = None) -> BaseSigner:
    alg = (algorithm or config.auth_algorithm).upper()
    if alg in _signer_cache:
        return _signer_cache[alg]

    if "RSA" in alg or "SHA256" in alg:
        signer = RSASigner()
    elif "SM2" in alg or "SM3" in alg:
        signer = SM2Signer()
    else:
        raise ValueError(f"不支持的签名算法: {alg}")

    _signer_cache[alg] = signer
    logger.info("初始化签名器: %s (fingerprint=%s)", signer.algorithm_name(), signer.fingerprint())
    return signer
