"""
Excel 测试数据驱动 — 读取 test_data.xlsx，自动处理字段类型转换。

Excel 列约定:
  基础列 (必填):
    case_id | description | endpoint | method | params | json_data | expected_status | assert_rules

  可选列:
    host         — 覆盖 base_url（不填使用 config.yaml 的环境配置）
    enabled      — yes/no，控制是否执行该行（不填默认 yes）
    section      — 文档章节编号（如 7.1.1），用于按章节筛选，不参与脚本逻辑
    ref_case_id  — 关联测试用例ID，用于结果收集和回填

  场景编排列 (可选，用于多步骤测试):
    scenario_id | step | step_type | save_vars
"""

import json
import os
import re
import uuid
import random
import string
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl

import numpy as np
import pandas as pd

from common.logger import logger
from config import config


class ExcelHandler:
    def __init__(self, file_path: str = None):
        root = config.root_dir
        if file_path:
            self.file_path = os.path.join(root, file_path) if not os.path.isabs(file_path) else file_path
        else:
            self.file_path = os.path.join(root, config.get("paths.excel_data"))
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"Excel 文件不存在: {self.file_path}")
        logger.info("Excel 路径: %s", self.file_path)
        self._config_vars = self._load_config_vars()

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def get_test_cases(self, sheet_name: str, process_data: bool = True) -> List[Dict[str, Any]]:
        """读取指定 sheet 并返回处理后的测试用例列表"""
        df = pd.read_excel(self.file_path, sheet_name=sheet_name, dtype=str)
        df = df.replace({np.nan: None})
        df["excel_row"] = range(2, len(df) + 2)
        records = df.to_dict("records")

        for rec in records:
            self._process_record(rec, process_data)

        required = ("case_id", "description", "endpoint", "method")
        records = [r for r in records if all(r.get(f) for f in required)]

        # enabled 列过滤: 只保留 enabled 为空、yes、true 的行
        total_before = len(records)
        records = [r for r in records if self._is_enabled(r)]
        skipped = total_before - len(records)

        records.sort(key=lambda r: r.get("excel_row", 0))
        logger.info("读取 [%s] 共 %d 条用例 (跳过 %d 条 enabled=no)", sheet_name, len(records), skipped)
        return records

    # ------------------------------------------------------------------
    # 字段处理
    # ------------------------------------------------------------------
    def _process_record(self, rec: Dict, process: bool):
        for key in list(rec.keys()):
            val = rec[key]
            if val is None:
                continue
            if isinstance(val, str):
                val = val.strip()
                val = self._replace_config_refs(val)
                val = self._replace_keys_refs(val)
                rec[key] = val

            if key == "json_data":
                self._parse_json_field(rec, val, process)
            elif key == "params":
                self._parse_params_field(rec, val, process)
            elif key == "assert_rules":
                self._parse_assert_rules(rec, val)
            elif key == "expected_status" and isinstance(val, str) and val.isdigit():
                rec[key] = int(val)
            elif key == "step" and isinstance(val, str) and val.isdigit():
                rec[key] = int(val)

    # ---------- json_data ----------
    def _parse_json_field(self, rec: Dict, raw: str, process: bool):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            parsed = self._try_fix_json(raw)
        if parsed is None:
            return
        if process and isinstance(parsed, dict):
            parsed = self._auto_fill(parsed)
        rec["json_data"] = parsed

    # ---------- params ----------
    def _parse_params_field(self, rec: Dict, raw: str, process: bool):
        if not raw:
            rec["params"] = None
            return
        try:
            if raw.startswith("{"):
                d = json.loads(raw)
            elif "=" in raw:
                d = dict(parse_qsl(raw, keep_blank_values=True))
            else:
                rec["params"] = None
                return
        except Exception:
            rec["params"] = None
            return

        if process and isinstance(d, dict):
            d = self._auto_fill(d)
        rec["params"] = d

    # ---------- assert_rules ----------
    @staticmethod
    def _parse_assert_rules(rec: Dict, raw: str):
        try:
            rec["assert_rules"] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            try:
                fixed = raw.replace("'", '"').replace("True", "true").replace("False", "false").replace("None", "null")
                rec["assert_rules"] = json.loads(fixed)
            except Exception:
                rec["assert_rules"] = None

    # ------------------------------------------------------------------
    # 自动填充 requestId / label
    # ------------------------------------------------------------------
    def _auto_fill(self, data: Dict) -> Dict:
        out = data.copy()
        if "requestId" in out:
            rid = str(out["requestId"]).strip()
            if rid.lower() == "uuid" or self._is_uuid(rid):
                out["requestId"] = str(uuid.uuid4())
        if "label" in out and str(out["label"]).strip() == "label":
            out["label"] = "RM_" + "".join(random.choices(string.ascii_letters + string.digits, k=8))
        # 递归
        for k, v in out.items():
            if isinstance(v, dict):
                out[k] = self._auto_fill(v)
        return out

    def _load_config_vars(self) -> dict:
        """读取 config sheet 的 key/value 列，返回 {key: value} 映射"""
        try:
            df = pd.read_excel(self.file_path, sheet_name="config", dtype=str)
            df = df.replace({np.nan: None})
            result = {}
            for _, r in df.iterrows():
                k = r.get("key")
                v = r.get("value")
                if k and v:
                    result[k.strip()] = v.strip()
            if result:
                logger.info("config sheet 加载 %d 个变量: %s", len(result), list(result.keys()))
            return result
        except (ValueError, KeyError):
            logger.debug("config sheet 不存在或为空，跳过")
            return {}

    def _replace_config_refs(self, val: str) -> str:
        """替换 ${env.xxx} 为 config sheet 中的值"""
        if "${env." not in val or not self._config_vars:
            return val

        def _repl(m):
            key = m.group(1)
            v = self._config_vars.get(key)
            if v is None:
                logger.warning("config sheet 变量不存在: %s", key)
                return m.group(0)
            return v

        return re.sub(r"\$\{env\.([^}]+)}", _repl, val)

    @staticmethod
    def _is_enabled(rec: Dict) -> bool:
        """判断该行是否启用。enabled 列为空、yes、true 时启用，no/false 时跳过"""
        val = rec.get("enabled")
        if val is None:
            return True
        return str(val).strip().lower() in ("yes", "true", "1", "")

    @staticmethod
    def _replace_keys_refs(val: str) -> str:
        """替换 ${keys.rsa.key1.public_key} 为 data/keys.json 中的实际值"""
        if "${keys." not in val:
            return val

        from common.signer import get_key_value

        def _repl(m):
            path = m.group(1)
            try:
                value = get_key_value(path)
                if isinstance(value, str) and any(c in value for c in '\n\r\t"\\'):
                    value = json.dumps(value)[1:-1]
                return value
            except KeyError:
                logger.warning("keys.json 路径不存在: %s", path)
                return m.group(0)

        return re.sub(r"\$\{keys\.([^}]+)}", _repl, val)

    @staticmethod
    def _is_uuid(s: str) -> bool:
        try:
            return str(uuid.UUID(s)) == s
        except ValueError:
            return False

    @staticmethod
    def _try_fix_json(raw: str) -> Optional[Any]:
        try:
            fixed = raw.replace("'", '"').replace("True", "true").replace("False", "false").replace("None", "null")
            return json.loads(fixed)
        except Exception:
            return None
