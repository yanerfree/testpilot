"""
HTTP 客户端 — 自动集成签名认证。

核心逻辑:
  1. auth_enabled=True 时，自动对请求体签名并注入认证头
  2. 签名算法由 config.yaml → auth.algorithm 决定，也可运行时切换
  3. 对 JSON body 直接 json.dumps 后签名; 对 query params 按 ASCII 排序拼接后签名
"""

import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests

from common.logger import logger
from common.signer import get_signer
from config import config


class HttpClient:
    def __init__(self, base_url: str = None, auth_enabled: bool = None):
        self.base_url = base_url or config.base_url
        self.timeout = config.timeout
        self.auth_enabled = auth_enabled if auth_enabled is not None else config.auth_enabled
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CHSM-Test/2.0"

    # ------------------------------------------------------------------
    # 签名
    # ------------------------------------------------------------------
    def _build_sign_string(
        self,
        json_data: Any = None,
        data: Any = None,
        params: Dict = None,
        files: Dict = None,
    ) -> str:
        """拼接待签名字符串。
        优先级: files+data(表单) > json_data(独占) > data > params
        json_data 存在时只对 json 签名，不拼接 params。
        """
        if files and data and isinstance(data, dict):
            sig_data = {k: v for k, v in data.items() if k not in files and not hasattr(v, "read")}
            if sig_data:
                return "&".join(f"{k}={v}" for k, v in sorted(sig_data.items()) if v is not None)
            return ""

        if json_data is not None:
            return json.dumps(json_data)

        body = ""
        if data is not None:
            if isinstance(data, dict):
                body = json.dumps(data)
            else:
                body = str(data)

        if params:
            p_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
            body = f"{body}&{p_str}" if body else p_str

        return body

    def _inject_auth(
        self,
        headers: Dict,
        json_data: Any = None,
        data: Any = None,
        params: Dict = None,
        files: Dict = None,
    ):
        """在 headers 中注入签名认证头"""
        if not self.auth_enabled:
            return

        sign_str = self._build_sign_string(json_data, data, params, files)
        signer = get_signer()
        auth_headers = signer.sign(sign_str)
        headers.update(auth_headers)
        logger.info("已注入认证头: alg=%s", signer.algorithm_name())

    # ------------------------------------------------------------------
    # 底层请求
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None,
        json_data: Optional[Union[Dict, List]] = None,
        files: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs,
    ) -> requests.Response:
        url = urljoin(self.base_url, endpoint)
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        # 默认 JSON content-type（无文件时）
        if not files and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

        # 注入签名
        self._inject_auth(req_headers, json_data, data, params, files)

        # 构建 requests 参数
        req_kwargs: Dict[str, Any] = {}
        if files:
            req_kwargs["files"] = files
            if data:
                req_kwargs["data"] = data
            req_headers.pop("Content-Type", None)  # 让 requests 自动设置
        elif json_data is not None:
            req_kwargs["json"] = json_data
        elif data is not None:
            if isinstance(data, dict):
                req_kwargs["json"] = data
            else:
                req_kwargs["data"] = data

        # 对于无 body 的方法, 去掉多余 Content-Type
        if method.upper() in ("GET", "HEAD", "DELETE", "OPTIONS") and not req_kwargs:
            req_headers.pop("Content-Type", None)

        self._log_request(method, url, params, json_data or data, req_headers)

        resp = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            headers=req_headers,
            timeout=self.timeout,
            verify=False,
            **req_kwargs,
            **kwargs,
        )

        self._log_response(resp)
        return resp

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------
    def get(self, endpoint, params=None, headers=None, **kw):
        return self._request("GET", endpoint, params=params, headers=headers, **kw)

    def post(self, endpoint, data=None, json_data=None, params=None, files=None, headers=None, **kw):
        return self._request("POST", endpoint, params=params, data=data, json_data=json_data,
                             files=files, headers=headers, **kw)

    def delete(self, endpoint, params=None, json_data=None, headers=None, **kw):
        return self._request("DELETE", endpoint, params=params, json_data=json_data, headers=headers, **kw)

    def put(self, endpoint, data=None, json_data=None, params=None, headers=None, **kw):
        return self._request("PUT", endpoint, params=params, data=data, json_data=json_data,
                             headers=headers, **kw)

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    @staticmethod
    def _log_request(method, url, params, body, headers):
        logger.info(">>> %s %s", method.upper(), url)
        if params:
            logger.info("    params: %s", params)
        if body:
            logger.info("    body:   %s", json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else body)
        auth_keys = ["CHSM-AuthPK", "CHSM-SignatureAlg", "CHSM-Signature"]
        auth_hdrs = {k: headers[k] for k in auth_keys if k in headers}
        if auth_hdrs:
            logger.debug("    auth:   %s", json.dumps(auth_hdrs, ensure_ascii=False))
        logger.debug("    headers: %s", json.dumps(dict(headers), ensure_ascii=False))

    @staticmethod
    def _log_response(resp: requests.Response):
        logger.info("<<< %d  %.3fs", resp.status_code, resp.elapsed.total_seconds())
        try:
            logger.info("    body: %s", json.dumps(resp.json(), ensure_ascii=False))
        except Exception:
            logger.info("    body: %s", resp.text[:500])
        logger.debug("    resp_headers: %s", dict(resp.headers))


def get_http_client(base_url: str = None, auth_enabled: bool = None) -> HttpClient:
    """工厂函数: 创建 HttpClient 实例"""
    return HttpClient(base_url=base_url, auth_enabled=auth_enabled)
