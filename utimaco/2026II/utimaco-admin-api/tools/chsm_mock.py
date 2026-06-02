#!/usr/bin/env python3
"""
CHSM API Mock Server — 用于 dry-run 测试框架全链路验证。

启动: python3 tools/chsm_mock.py [--port 9443]
测试: curl http://127.0.0.1:9443/api/1.0/chsm/status?requestId=test

支持全部 44 个接口路由，有状态公钥管理，按接口必填字段校验。
不做 HTTPS、签名验证、文件上传。
"""

import hashlib
import json
import base64
import os
import re
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ================================================================
# 已知指纹（来自设计笔记，确定性值）
# ================================================================
KNOWN_FINGERPRINTS = {
    "rsa": {
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA25fH+SAWLN29LhTjbEsFGsd0kJJosWLskdYUiZ8UV0BF4uO8k8lh07HXYNIGpGRpT2pOgnqFfWBNpXHk9CTpjccDIpWtvug1IFpqWs2I9SzPwgYxUM5BbHSarjFKGUcSsyG4cuq3s9pgqqCUeew2mo+l1dWdZOqYgxMakWHp91/9k8lSrVJdZsl24rXriP65GteGywYBPjw51hoBsnKUayuMdQWOv2t+Q/nBIbmLKBoKeDkxM9aOy2GWTEQ69KYs68M0iZiPujeDjiENib5BXE0M+GUPvPoPwxbru77YT/MgPhyCCWvszgQkJdTeb9UM7Z5vryTX3AfsjwZbPEecAQIDAQAB":
            "/WiF31yZx0q9nF0fQBudD7xSeivFBfdEhG8hl/KQo1c=",
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy2bFOfTLtxfECYIpFPxYR0brRwwpJxXCGrPl0UJylvJA7vE5UqCNkn3uqRsBUDD+oxs4tbKDMRmrvFDeHJN6VL3A/PlYBvacWGIw7eN0RtbksRS334cVDL24//w6p8qVbPzrFZp8QhWBapUNRfzbtwQUzAPTLEUEwx8xSji/FVdOqWGbIzyIdjWW0+nvV7KblgPKUxPNIuYLK6Togb9WGo06bMG+9nIXYO+ElWgJ7Ytv9emjPbXx78AmQ7gMUvp2LY+k9RhXLKnvOZ4Cqst5pzvoiotVJUF+cTQdCZQva5btQtAkgeezeq19MUtCDZQRjI4dLUHrKaeUI/APXw5RVQIDAQAB":
            "8CPhhUBOk75PaceSD6UjfghIh2V0xEo+1v2nUN4k7uc=",
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2Ls1jVTf8YJ06sulG/EsrsPQguHXVE6mOi490VVmclVqmz4kpS8Ui5lFEyHQSYTEN+MlQNVwdTznytpeXDO7lG2Z/crrpumcE7lwqfWs1QTrVUJbjDMtafugwAvAzdZ40cqHBDHtXHyZ/6lcnauG5u8G5JoIDGZ9eD81X2Nie992BHBo/RjCK5meXz9SRwm7NHmGglYYpOZqEVxCZMMIGS4zp+lRIhdy93E+06svOPSX1qkOKHwCW5OjT68mC86Rz8zyP25vcS9gmMLgxS2PdAIrLKyfE0hk+/AeNDrIo5wLeomyeSKMpCYzv4Ac4W+n88cNXjx3C49OVABMQNNLDwIDAQAB":
            "EZe+Or1pc78hK6RoKjqYPGuZ7h59ohDZqJBa7xBCgb8=",
    },
    "sm2": {
        "15974d4c7d1b7de8c7c7ae5cb568bdb6672645d2801ed415d396c1ae9a57486ea3aa7fb376486c39995d7a574b18d2e17ddf0f5d0256fcefcebb7e83724f0806":
            "mdg2R+NkXUI3WidsEba3Dkg/MBx98JaXO23L9XF8xK8=",
        "318ef67a1f1ddca3425b862b0271f87a696ea03ea46a938f25336fbc86eb5097a3f9f6dd0cf180c9a7d66e9e927fa7e1ff9352d7fd919968f23ef90f2afc3760":
            "RSiUBOLEkAC8AzPRie3UiN8UPHlrLyA0SVpYGEO7tUc=",
        "d39a43278d2e63cec269c547f28e7006a52cf84675a1ac89d18cf8088a824a9358ca3abd1d4513a57f3473a2a9d2f5af5fba258a0ee96c543232c8501b3124f7":
            "gr1fZe+LtAM9IA5QhUWOj7Wm0fCavaBXn5oHLS/9UCM=",
    },
}

VALID_CHSM_OPR = {"getinfo", "getdeviceinfo", "upgrade", "restart", "backup", "restore"}
VALID_VSM_OPR = {"getinfo", "start", "stop", "restart", "reset", "upgrade"}
VALID_ALG_VALUES = {"rsawithsha256", "sm2withsm3", "rsa", "sm2"}
MOCK_VSM_ID = "vsm-mock-001"


def _normalize_alg(alg: str) -> str:
    """将 API algorithm 值归一化为内部简称: 'RSAWithSHA256' → 'rsa', 'sm2' → 'sm2'"""
    a = alg.lower().strip()
    if a in ("rsawithsha256", "sha256withrsa", "rsa"):
        return "rsa"
    if a in ("sm2withsm3", "sm2"):
        return "sm2"
    return a

# 各 oprType 的必填字段（/api/1.0/chsm 和 /api/1.0/vsm）
CHSM_OPR_REQUIRED = {
    "upgrade": ["packVersion", "packUrl", "alg", "sign", "callbackUrl"],
    "restart": ["callbackUrl"],
    "backup": ["callbackUrl"],
    "restore": ["backupUrl", "alg", "sign", "callbackUrl"],
    "export": ["callbackUrl"],
    "import": ["imageUrl", "alg", "sign", "callbackUrl"],
}

# 各 config 子路径的必填字段
CONFIG_REQUIRED = {
    "/api/1.0/chsm/network": {
        "any_of": ["dnsList", "netAddrs"],
        "validate": "_validate_network",
    },
    "/api/1.0/chsm/ntp": ["addr", "syncPeriod"],
    "/api/1.0/chsm/imageuploader": ["url"],
    "/api/1.0/chsm/loguploader": ["logServerType", "logServerAddress"],
    "/api/1.0/chsm/alarmaddress": ["url"],
    "/api/1.0/chsm/moocaddress": [
        "ocIp", "ocProtocol", "ocPort", "resourceUrl",
        "performanceUrl", "bizRegionNativeId", "cloudInfraType", "dewServiceHost",
    ],
    "/api/1.0/chsm/cloudtoken": ["cloudToken"],
    "/api/1.0/vsm/network": ["ip"],
}


def compute_fingerprint(alg, pk_value):
    raw_key = pk_value
    if pk_value.startswith("-----BEGIN"):
        raw_key = _pem_to_raw_key(alg, pk_value)
    table = KNOWN_FINGERPRINTS.get(alg, {})
    if raw_key in table:
        return table[raw_key]
    if alg == "rsa":
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    else:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.b64encode(digest).decode()


def _pem_to_raw_key(alg, pem_str):
    """从 PEM 格式提取原始密钥: RSA → base64字符串, SM2 → hex字符串"""
    lines = pem_str.strip().split("\n")
    b64_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("-----")]
    b64_content = "".join(b64_lines)
    if alg == "rsa":
        return b64_content
    # SM2: DER SubjectPublicKeyInfo → 前 27 字节是固定头，后 64 字节是 x||y
    try:
        der = base64.b64decode(b64_content)
        if len(der) == 91:
            return der[27:].hex()
    except Exception:
        pass
    return b64_content


def _is_empty(val):
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, list) and len(val) == 0:
        return True
    return False


def _check_required(body, fields, rid):
    for f in fields:
        if f not in body or _is_empty(body[f]):
            return False, f
    return True, None


# ================================================================
# 有状态存储
# ================================================================
pk_store = []
tenant_pk_store = []


def _validate_pk_format(alg, pk):
    if isinstance(pk, str) and pk.startswith("-----BEGIN"):
        return True
    if alg == "rsa":
        try:
            base64.b64decode(pk, validate=True)
            return len(pk) > 100
        except Exception:
            return False
    else:
        return bool(re.fullmatch(r"[0-9a-fA-F]+", pk)) and len(pk) > 50


def _pk_add(store, alg, pks):
    new_keys = []
    for pk in pks:
        existing = {item["pk"] for item in store}
        if pk not in existing:
            new_keys.append({"alg": alg, "pk": pk, "fp": compute_fingerprint(alg, pk)})
    if len(store) + len(new_keys) > 2:
        return False, "public key count exceeds limit (max 2)"
    store.extend(new_keys)
    return True, ""


def _pk_fingerprints(store):
    if not store:
        return {"algorithm": "", "fingerprints": []}
    algs = list({item["alg"] for item in store})
    alg_hash = "sha256" if "rsa" in algs else "sm3"
    fps = [item["fp"] for item in store]
    return {"algorithm": alg_hash, "fingerprints": fps}


def _pk_clear(store):
    store.clear()


# Guest 接口列表（不需要认证）
GUEST_PATHS = {
    ("/api/1.0/chsm/status", "GET"),
    ("/api/1.0/chsm/allstatus", "GET"),
    ("/api/1.0/vsm/status", "GET"),
}


# ================================================================
# Mock Handler
# ================================================================
class CHSMMockHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[mock] {self.client_address[0]} - {format % args}")

    def _respond(self, body_dict, http_status=200):
        body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
        self.send_response(http_status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _std(self, status=200, message="success", result=None, request_id=None):
        body = {
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
            "requestId": request_id or str(uuid.uuid4()),
            "costMillis": 50,
        }
        if result is not None:
            body["result"] = result
        http_code = 200 if status == 200 else (403 if status == 403 else 400)
        self._respond(body, http_code)

    def _err(self, status, message, request_id=None):
        self._std(status, message, request_id=request_id)

    def _parse_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _parse_url(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query, keep_blank_values=True)

    def _get_param(self, qs, key):
        vals = qs.get(key, [])
        return vals[0] if vals else None

    def _check_request_id_body(self, body):
        rid = body.get("requestId") if isinstance(body, dict) else None
        if rid is None:
            return False, None
        if isinstance(rid, str) and rid.strip() == "":
            return False, ""
        return True, str(rid)

    def _check_request_id_params(self, qs):
        rid = self._get_param(qs, "requestId")
        if rid is None:
            return False, None
        if isinstance(rid, str) and rid.strip() == "":
            return False, ""
        return True, str(rid)

    def _check_auth_header(self):
        return self.headers.get("CHSM-AuthPK") is not None

    # ================================================================
    # GET
    # ================================================================
    def do_GET(self):
        path, qs = self._parse_url()

        if path == "/api/1.0/chsm/status":
            return self._handle_chsm_status(qs)
        if path == "/api/1.0/chsm/allstatus":
            return self._handle_chsm_allstatus(qs)
        if path == "/api/1.0/vsm/status":
            return self._handle_vsm_status(qs)
        if path == "/api/1.0/chsm/authpk":
            return self._handle_authpk_get(qs)
        if path in ("/authServlet", "/platformServlet"):
            return self._handle_servlet_get(path, qs)
        self._err(404, f"not found: {path}")

    # ================================================================
    # POST
    # ================================================================
    def do_POST(self):
        path, qs = self._parse_url()
        body = self._parse_body()

        # 检查 trusted 接口是否带认证头（简化：仅检查有无 header）
        # if (path, "POST") not in GUEST_PATHS and not path.startswith("/auth") and path != "/api/1.0/chsm/authpk":
        #     if not self._check_auth_header():
        #         return self._err(403, "authentication required")

        if path == "/api/1.0/chsm":
            return self._handle_chsm(body)
        if path == "/api/1.0/chsm/image":
            return self._handle_chsm_image(body)
        if path == "/api/1.0/chsm/authpk":
            return self._handle_authpk_post(body)
        if path.startswith("/api/1.0/chsm/"):
            return self._handle_chsm_config(path, body)
        if path == "/api/1.0/vsm":
            return self._handle_vsm(body)
        if path == "/api/1.0/vsm/image":
            return self._handle_vsm_image(body)
        if path.startswith("/api/1.0/vsm/"):
            return self._handle_vsm_config(path, body)
        if path in ("/authServlet", "/platformServlet"):
            return self._handle_servlet_post(path, qs, body)
        self._err(404, f"not found: {path}")

    # ================================================================
    # DELETE
    # ================================================================
    def do_DELETE(self):
        path, qs = self._parse_url()
        body = self._parse_body()
        if path == "/api/1.0/chsm/authpk":
            ok, rid = self._check_request_id_body(body)
            if not ok:
                return self._err(400, "requestId is required", rid)
            _pk_clear(pk_store)
            return self._std(200, "success", request_id=rid)
        if path == "/api/mock/reset":
            _pk_clear(pk_store)
            _pk_clear(tenant_pk_store)
            return self._respond({"status": "reset"})
        self._err(404, f"not found: {path}")

    # ================================================================
    # 7.1 CHSM 管理 — /api/1.0/chsm (oprType 分发)
    # ================================================================
    def _handle_chsm(self, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        opr = body.get("oprType", "")
        if not opr or (isinstance(opr, str) and opr.strip() == ""):
            return self._err(400, "oprType is required", rid)
        opr_lower = opr.lower()
        if opr_lower not in VALID_CHSM_OPR:
            return self._err(400, f"invalid oprType: {opr}", rid)

        required = CHSM_OPR_REQUIRED.get(opr_lower, [])
        ok, field = _check_required(body, required, rid)
        if not ok:
            return self._err(400, f"{field} is required", rid)

        if opr_lower in ("upgrade", "import", "restore"):
            alg_val = body.get("alg", "")
            if isinstance(alg_val, str) and alg_val.lower() not in VALID_ALG_VALUES:
                return self._err(400, f"invalid alg: {alg_val}", rid)

        if opr_lower == "getinfo":
            return self._std(200, "success", result={
                "id": "chsm-mock-001", "version": "2.0.0-mock",
                "sn": "MOCK-SN-001", "status": "running",
                "vsmIds": [MOCK_VSM_ID],
            }, request_id=rid)
        if opr_lower == "getdeviceinfo":
            return self._std(200, "success", result={
                "version": "2.0.0-mock", "sn": "MOCK-SN-001", "model": "CHSM-MOCK",
            }, request_id=rid)
        return self._std(200, "success", request_id=rid)

    # ================================================================
    # 7.1 CHSM image — /api/1.0/chsm/image (export/import)
    # ================================================================
    def _handle_chsm_image(self, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        opr = body.get("oprType", "")
        if not opr:
            return self._err(400, "oprType is required", rid)

        required = CHSM_OPR_REQUIRED.get(opr.lower(), [])
        ok, field = _check_required(body, required, rid)
        if not ok:
            return self._err(400, f"{field} is required", rid)

        if opr.lower() == "import":
            alg_val = body.get("alg", "")
            if isinstance(alg_val, str) and alg_val.lower() not in VALID_ALG_VALUES:
                return self._err(400, f"invalid alg: {alg_val}", rid)

        return self._std(200, "success", request_id=rid)

    # ================================================================
    # 7.1 CHSM config — /api/1.0/chsm/{sub} (network, ntp, etc.)
    # ================================================================
    def _handle_chsm_config(self, path, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        spec = CONFIG_REQUIRED.get(path)
        if spec:
            if isinstance(spec, dict):
                err = self._validate_config_dict(spec, body, rid)
                if err:
                    return err
            elif isinstance(spec, list):
                ok, field = _check_required(body, spec, rid)
                if not ok:
                    return self._err(400, f"{field} is required", rid)

        # moocaddress: ocPort 必须是数字
        if path == "/api/1.0/chsm/moocaddress":
            port = body.get("ocPort", "")
            if isinstance(port, str) and not port.replace("-", "").isdigit():
                return self._err(400, "ocPort must be numeric", rid)

        # ntp: syncPeriod 必须 > 0, addr 必须是有效 IP
        if path == "/api/1.0/chsm/ntp":
            addr = body.get("addr", "")
            if addr and not self._is_valid_ip(addr):
                return self._err(400, f"invalid addr: {addr}", rid)
            sp = body.get("syncPeriod")
            if sp is not None:
                try:
                    if int(sp) <= 0:
                        return self._err(400, "syncPeriod must be positive", rid)
                except (ValueError, TypeError):
                    return self._err(400, "syncPeriod must be numeric", rid)

        # loguploader: logServerType 校验
        if path == "/api/1.0/chsm/loguploader":
            lt = body.get("logServerType", "")
            if lt and lt not in ("syslog", "logserver"):
                return self._err(400, f"invalid logServerType: {lt}", rid)

        # network: 内容校验
        if path == "/api/1.0/chsm/network":
            err = self._validate_chsm_network(body, rid)
            if err:
                return err

        # imageuploader: url 格式
        if path == "/api/1.0/chsm/imageuploader":
            url = body.get("url", "")
            if url and not url.startswith("http"):
                return self._err(400, "url format invalid", rid)

        return self._std(200, "success", request_id=rid)

    def _validate_config_dict(self, spec, body, rid):
        if "any_of" in spec:
            fields = spec["any_of"]
            if not any(f in body and not _is_empty(body[f]) for f in fields):
                return self._err(400, f"at least one of {fields} is required", rid)
        return None

    def _validate_chsm_network(self, body, rid):
        dns = body.get("dnsList")
        addrs = body.get("netAddrs")
        if dns is not None and isinstance(dns, list) and len(dns) == 0:
            return self._err(400, "dnsList must not be empty", rid)
        if dns is not None and isinstance(dns, list):
            for d in dns:
                if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", str(d)):
                    return self._err(400, f"invalid DNS address: {d}", rid)
        if addrs is not None and isinstance(addrs, list):
            for a in addrs:
                if isinstance(a, dict):
                    ip = a.get("ip", "")
                    if ip and not self._is_valid_ip(ip):
                        return self._err(400, f"invalid IP address: {ip}", rid)
                    if "ip" not in a:
                        return self._err(400, "ip is required in netAddrs", rid)
        if not body.get("dnsList") and not body.get("netAddrs"):
            return self._err(400, "dnsList or netAddrs is required", rid)
        return None

    @staticmethod
    def _is_valid_ip(ip):
        if ":" in ip:
            return True
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for p in parts:
            try:
                n = int(p)
                if n < 0 or n > 255:
                    return False
            except ValueError:
                return False
        return True

    # ================================================================
    # 7.2 VSM 管理 — /api/1.0/vsm (oprType 分发)
    # ================================================================
    def _handle_vsm(self, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        opr = body.get("oprType", "")
        if not opr or (isinstance(opr, str) and opr.strip() == ""):
            return self._err(400, "oprType is required", rid)
        opr_lower = opr.lower()
        if opr_lower not in VALID_VSM_OPR:
            return self._err(400, f"invalid oprType: {opr}", rid)

        vsm_id = body.get("vsmId")
        if not vsm_id:
            return self._err(400, "vsmId is required", rid)
        if vsm_id != MOCK_VSM_ID:
            return self._err(400, f"vsmId not found: {vsm_id}", rid)

        if opr_lower in ("start", "stop", "restart", "reset"):
            if "callbackUrl" not in body or _is_empty(body["callbackUrl"]):
                return self._err(400, "callbackUrl is required", rid)

        if opr_lower == "upgrade":
            for f in ["packVersion", "packUrl", "alg", "sign", "callbackUrl"]:
                if f not in body or _is_empty(body[f]):
                    return self._err(400, f"{f} is required", rid)

        if opr_lower == "getinfo":
            return self._std(200, "success", result={
                "id": MOCK_VSM_ID, "version": "1.0.0-mock", "status": "running",
            }, request_id=rid)
        return self._std(200, "success", request_id=rid)

    # ================================================================
    # 7.2 VSM image — /api/1.0/vsm/image
    # ================================================================
    def _handle_vsm_image(self, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        opr = body.get("oprType", "")
        if not opr:
            return self._err(400, "oprType is required", rid)

        vsm_id = body.get("vsmId")
        if not vsm_id:
            return self._err(400, "vsmId is required", rid)

        if opr.lower() == "export":
            if "callbackUrl" not in body or _is_empty(body["callbackUrl"]):
                return self._err(400, "callbackUrl is required", rid)
        elif opr.lower() == "import":
            for f in ["imageUrl", "alg", "sign", "callbackUrl"]:
                if f not in body or _is_empty(body[f]):
                    return self._err(400, f"{f} is required", rid)

        return self._std(200, "success", request_id=rid)

    # ================================================================
    # 7.2 VSM config — /api/1.0/vsm/{sub}
    # ================================================================
    def _handle_vsm_config(self, path, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        vsm_id = body.get("vsmId")
        if not vsm_id:
            return self._err(400, "vsmId is required", rid)

        if path == "/api/1.0/vsm/token":
            if "token" not in body:
                return self._err(400, "token is required", rid)
            token = body["token"]
            if isinstance(token, str) and token.strip() == "":
                return self._err(400, "token must not be empty", rid)

        if path == "/api/1.0/vsm/network":
            if "ip" not in body or _is_empty(body["ip"]):
                return self._err(400, "ip is required", rid)
            ip = body["ip"]
            if ":" not in ip and not CHSMMockHandler._is_valid_ip(ip):
                return self._err(400, f"invalid IP address: {ip}", rid)

        return self._std(200, "success", request_id=rid)

    # ================================================================
    # 7.3 公钥管理
    # ================================================================
    def _handle_authpk_post(self, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        alg = body.get("algorithm", "")
        if isinstance(alg, str):
            alg = _normalize_alg(alg)
        if alg not in ("rsa", "sm2"):
            return self._err(400, f"invalid algorithm: {body.get('algorithm', '')}", rid)

        pks = body.get("pks")
        if not pks or not isinstance(pks, list) or len(pks) == 0:
            return self._err(400, "pks is required and must be non-empty array", rid)

        success, err = _pk_add(pk_store, alg, pks)
        if not success:
            return self._err(400, err, rid)
        return self._std(200, "success", request_id=rid)

    def _handle_authpk_get(self, qs):
        rid = self._get_param(qs, "requestId")
        if rid is None:
            return self._err(400, "requestId is required")
        if isinstance(rid, str) and rid.strip() == "":
            return self._err(400, "requestId must not be empty")
        result = _pk_fingerprints(pk_store)
        return self._std(200, "success", result=result, request_id=rid)

    # ================================================================
    # Guest 状态接口
    # ================================================================
    def _handle_chsm_status(self, qs):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        return self._std(200, "success", result={"status": "running"}, request_id=rid)

    def _handle_chsm_allstatus(self, qs):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        return self._std(200, "success", result={
            "hsmStatus": "running",
            "vsmStatusMap": {MOCK_VSM_ID: "running"},
        }, request_id=rid)

    def _handle_vsm_status(self, qs):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        vsm_id = self._get_param(qs, "vsmId")
        if not vsm_id:
            return self._err(400, "vsmId is required")
        if vsm_id != MOCK_VSM_ID:
            return self._err(400, f"vsmId not found: {vsm_id}")
        return self._std(200, "success", result={"status": "running"}, request_id=rid)

    # ================================================================
    # Section 9 Servlet
    # ================================================================
    def _handle_servlet_get(self, path, qs):
        method_param = self._get_param(qs, "method")
        if not method_param:
            return self._err(400, "method parameter is required")

        if path == "/authServlet":
            if method_param == "getAuthPKFingerprints":
                return self._servlet_get_fingerprints(qs)
            if method_param == "cleanPK":
                return self._servlet_clean_pk(qs)

        if path == "/platformServlet":
            if method_param == "getStatus":
                return self._servlet_get_status(qs)

        return self._err(400, f"unknown servlet method: {method_param}")

    def _handle_servlet_post(self, path, qs, body):
        method_param = self._get_param(qs, "method")
        if not method_param:
            return self._err(400, "method parameter is required")

        if path == "/authServlet":
            if method_param == "authPK":
                return self._servlet_auth_pk(body)

        if path == "/platformServlet":
            if method_param == "initKey":
                return self._servlet_init_key(qs, body)
            if method_param == "exportBackupKeys":
                return self._servlet_export(qs, body)
            if method_param == "importBackupKeys":
                return self._servlet_import(qs, body)
            if method_param == "doVsmInit":
                return self._servlet_vsm_init(qs, body)

        return self._err(400, f"unknown servlet method: {method_param}")

    def _servlet_auth_pk(self, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)

        alg = body.get("alg", "")
        if isinstance(alg, str):
            alg = alg.lower().strip()
        if alg not in ("rsa", "sm2"):
            return self._err(400, f"invalid alg: {alg}", rid)

        pks = body.get("pks")
        if not pks or not isinstance(pks, list) or len(pks) == 0:
            return self._err(400, "pks is required and must be non-empty array", rid)
        if len(pks) > 2:
            return self._err(400, "too many keys in single request (max 2)", rid)

        success, err = _pk_add(tenant_pk_store, alg, pks)
        if not success:
            return self._err(400, err, rid)
        return self._std(200, "success", request_id=rid)

    def _servlet_get_fingerprints(self, qs):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        fps = _pk_fingerprints(tenant_pk_store)
        return self._respond({"status": 200, "message": "success", "data": fps})

    def _servlet_clean_pk(self, qs):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        _pk_clear(tenant_pk_store)
        return self._std(200, "success", request_id=rid)

    def _servlet_get_status(self, qs):
        return self._respond({
            "status": 200, "message": "success",
            "data": {"status": "success", "initFlag": True, "serviceStatus": "running"},
        })

    def _servlet_init_key(self, qs, body):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        return self._std(200, "success", request_id=rid)

    def _servlet_export(self, qs, body):
        ok, rid = self._check_request_id_params(qs)
        if not ok:
            return self._err(400, "requestId is required")
        backup_key = body.get("backupKey") if isinstance(body, dict) else None
        if backup_key is None or (isinstance(backup_key, str) and backup_key.strip() == ""):
            return self._err(400, "backupKey is required", rid)
        return self._std(200, "success", request_id=rid)

    def _servlet_import(self, qs, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)
        return self._std(200, "success", request_id=rid)

    def _servlet_vsm_init(self, qs, body):
        ok, rid = self._check_request_id_body(body)
        if not ok:
            return self._err(400, "requestId is required", rid)
        clear_pk = body.get("clearPK")
        if clear_pk is None:
            return self._err(400, "clearPK is required", rid)
        if isinstance(clear_pk, str) and clear_pk.lower() not in ("true", "false"):
            return self._err(400, f"invalid clearPK value: {clear_pk}", rid)
        return self._std(200, "success", request_id=rid)


# ================================================================
# 配置 — 在这里修改
# ================================================================
PORT = 9443
HOST = "0.0.0.0"
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads")


# ================================================================
# 入口
# ================================================================
def main():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    CHSMMockHandler.upload_dir = UPLOAD_DIR

    server = HTTPServer((HOST, PORT), CHSMMockHandler)
    print(f"CHSM Mock Server: http://{HOST}:{PORT}")
    print(f"  上传目录: {UPLOAD_DIR}")
    print(f"  curl http://127.0.0.1:{PORT}/api/1.0/chsm/status?requestId=test")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
        server.server_close()


if __name__ == "__main__":
    main()
