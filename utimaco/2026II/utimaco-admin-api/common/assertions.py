"""
断言引擎 — 根据 Excel 中 assert_rules JSON 规则自动验证响应。

支持的规则类型 (type):
  status_code       — 验证 HTTP 状态码
  json_contains     — 验证 JSON 路径存在且值匹配 (支持点号路径、数组下标、通配符 *)
  json_not_contains — 验证 JSON 路径不存在或值不匹配
  text_contains     — 验证响应文本包含子串
  response_time     — 验证响应时间 ≤ max_time (秒)
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

import allure
import requests

from common.logger import logger


class Assertions:
    """断言执行器"""

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    def assert_status_code(self, resp: requests.Response, expected: int):
        actual = resp.status_code
        with allure.step(f"断言: 状态码 {actual} == {expected}"):
            assert actual == expected, (
                f"状态码不匹配: 期望 {expected}, 实际 {actual}. body={resp.text[:300]}"
            )
        logger.info("✓ 状态码 %d", actual)

    def apply_assert_rules(self, resp: requests.Response, rules: Union[List[Dict], None]):
        """依次执行 assert_rules 列表中的每条规则"""
        if not rules:
            return
        for idx, rule in enumerate(rules):
            rule_type = rule.get("type", "")
            try:
                if rule_type == "status_code":
                    self.assert_status_code(resp, rule["expected_code"])
                elif rule_type == "json_contains":
                    self._assert_json_contains(resp, rule)
                elif rule_type == "json_not_contains":
                    self._assert_json_not_contains(resp, rule)
                elif rule_type == "text_contains":
                    self._assert_text_contains(resp, rule)
                elif rule_type == "response_time":
                    self._assert_response_time(resp, rule)
                else:
                    logger.warning("未知断言类型: %s (规则 #%d)", rule_type, idx)
            except AssertionError:
                raise
            except Exception as e:
                raise AssertionError(f"规则 #{idx} ({rule_type}) 执行失败: {e}")

    # ------------------------------------------------------------------
    # JSON 路径解析: 支持 "data.alg", "data[0].name", "data[*].alg"
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_path(obj: Any, path: str) -> List[Any]:
        if not path:
            return [obj]

        parts = re.split(r"\.(?![^\[]*\])", path)
        current = [obj]

        for part in parts:
            next_vals: List[Any] = []
            m = re.match(r"^(\w+)\[(.+?)\]$", part)
            if m:
                key, idx = m.group(1), m.group(2)
            else:
                key, idx = part, None

            for node in current:
                if not isinstance(node, dict) or key not in node:
                    continue
                val = node[key]

                if idx is None:
                    next_vals.append(val)
                elif idx == "*":
                    if isinstance(val, list):
                        next_vals.extend(val)
                elif idx.lstrip("-").isdigit():
                    i = int(idx)
                    if isinstance(val, list) and -len(val) <= i < len(val):
                        next_vals.append(val[i])

            current = next_vals

        return current

    # ------------------------------------------------------------------
    # 各类断言实现
    # ------------------------------------------------------------------
    def _assert_json_contains(self, resp: requests.Response, rule: Dict):
        body = resp.json()
        key = rule.get("key", "")
        vals = self._resolve_path(body, key)

        if "value" in rule:
            expected = rule["value"]
            matched = any(self._value_match(v, expected) for v in vals)
            actual_str = str(vals[0]) if len(vals) == 1 else str(vals)
            with allure.step(f"断言: {key} 包含 {expected!r} → 实际: {actual_str}"):
                assert vals, f"JSON 路径 '{key}' 不存在. body={json.dumps(body, ensure_ascii=False)[:300]}"
                assert matched, (
                    f"JSON 路径 '{key}' 值不匹配: 期望 {expected!r}, 实际 {vals}"
                )
        else:
            with allure.step(f"断言: {key} 存在 → {'存在' if vals else '不存在'}"):
                assert vals, f"JSON 路径 '{key}' 不存在. body={json.dumps(body, ensure_ascii=False)[:300]}"
        logger.info("✓ json_contains: %s", key)

    def _assert_json_not_contains(self, resp: requests.Response, rule: Dict):
        body = resp.json()
        key = rule.get("key", "")
        vals = self._resolve_path(body, key)
        if "value" in rule:
            expected = rule["value"]
            matched = any(self._value_match(v, expected) for v in vals)
            with allure.step(f"断言: {key} 不包含 {expected!r} → {'不包含' if not matched else '包含!'}"):
                assert not matched, f"JSON 路径 '{key}' 不应包含值 {expected!r}"
        else:
            with allure.step(f"断言: {key} 不存在 → {'不存在' if not vals else '存在!'}"):
                assert not vals, f"JSON 路径 '{key}' 不应存在"
        logger.info("✓ json_not_contains: %s", key)

    @staticmethod
    def _assert_text_contains(resp: requests.Response, rule: Dict):
        text = rule.get("text", "")
        with allure.step(f"断言: 响应包含 '{text}'"):
            assert text in resp.text, f"响应文本不包含 '{text}'. body={resp.text[:300]}"
        logger.info("✓ text_contains: %s", text)

    @staticmethod
    def _assert_response_time(resp: requests.Response, rule: Dict):
        max_t = float(rule.get("max_time", 5.0))
        actual = resp.elapsed.total_seconds()
        with allure.step(f"断言: 响应时间 {actual:.3f}s <= {max_t}s"):
            assert actual <= max_t, f"响应时间 {actual:.3f}s 超过 {max_t}s"
        logger.info("✓ response_time: %.3fs <= %.1fs", actual, max_t)

    @staticmethod
    def _value_match(actual: Any, expected: Any) -> bool:
        if actual == expected:
            return True
        try:
            return str(actual) == str(expected)
        except Exception:
            return False


assertions = Assertions()
