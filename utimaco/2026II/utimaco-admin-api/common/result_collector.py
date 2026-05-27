"""
测试结果收集器 — 收集所有用例的通过/失败/异常结果，输出 test_results.json。

与 issue_collector 互补：issue_collector 只记失败，这里记全量结果，
用于后续 backfill_results.py 回填到测试用例 Excel。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from common.logger import logger
from config import config


class ResultCollector:

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add(
        self,
        case_id: str,
        ref_case_id: Optional[str],
        status: str,
        endpoint: str,
        method: str,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        scenario_id: Optional[str] = None,
        step: Optional[int] = None,
    ):
        record = {
            "case_id": case_id,
            "ref_case_id": ref_case_id,
            "status": status,
            "endpoint": endpoint,
            "method": method.upper(),
            "response_time_ms": response_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
        if error_message:
            record["error_message"] = error_message[:500]
        if scenario_id:
            record["scenario_id"] = scenario_id
            record["step"] = step
        self.results.append(record)
        logger.debug("[ResultCollector] %s %s → %s", case_id, ref_case_id or "", status)

    def save(self, file_path: str = None) -> str:
        if not file_path:
            out_dir = os.path.join(config.root_dir, "output")
            os.makedirs(out_dir, exist_ok=True)
            file_path = os.path.join(out_dir, "test_results.json")

        merged = self._merge_existing(file_path)

        passed = sum(1 for r in merged if r["status"] == "passed")
        failed = sum(1 for r in merged if r["status"] == "failed")
        error = sum(1 for r in merged if r["status"] == "error")

        report = {
            "generated_at": datetime.now().isoformat(),
            "total": len(merged),
            "passed": passed,
            "failed": failed,
            "error": error,
            "results": merged,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info("测试结果已保存: %s (%d 条: %d通过/%d失败/%d异常)",
                     file_path, len(merged), passed, failed, error)
        return file_path

    def _merge_existing(self, file_path: str) -> List[Dict[str, Any]]:
        """合并已有结果：按 ref_case_id 更新，无 ref_case_id 的按 case_id 更新"""
        old = {}
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data.get("results", []):
                    key = r.get("ref_case_id") or r.get("case_id", "")
                    if key:
                        old[key] = r
            except (json.JSONDecodeError, KeyError):
                pass

        for r in self.results:
            key = r.get("ref_case_id") or r.get("case_id", "")
            if key:
                old[key] = r

        return list(old.values())


result_collector = ResultCollector()
