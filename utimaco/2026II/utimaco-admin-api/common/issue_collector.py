"""
问题清单收集器 — 测试过程中自动收集失败信息，输出结构化 issues.json。

输出格式设计为 AI 可直接解析，包含定位和修复所需的全部上下文。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from common.logger import logger
from config import config


class IssueCollector:
    """收集测试中发现的问题，运行结束后写入 JSON 文件"""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self._counter = 0

    def add(
        self,
        case_id: str,
        endpoint: str,
        method: str,
        error_message: str,
        severity: str = "medium",
        issue_type: str = "assertion_failed",
        request_body: Any = None,
        response: Optional[requests.Response] = None,
        scenario_id: str = None,
        step: int = None,
        step_type: str = None,
    ):
        self._counter += 1
        issue = {
            "id": f"ISS-{self._counter:03d}",
            "case_id": case_id,
            "severity": severity,
            "type": issue_type,
            "endpoint": endpoint,
            "method": method.upper(),
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
        }

        # 场景信息
        if scenario_id:
            issue["scenario_id"] = scenario_id
            issue["step"] = step
            issue["step_type"] = step_type

        # 请求数据
        if request_body is not None:
            try:
                issue["request_body"] = request_body if isinstance(request_body, (dict, list)) else str(request_body)[:500]
            except Exception:
                pass

        # 响应数据
        if response is not None:
            issue["actual_status"] = response.status_code
            try:
                issue["actual_body"] = response.json()
            except Exception:
                issue["actual_body"] = response.text[:500]
            issue["response_time"] = f"{response.elapsed.total_seconds():.3f}s"

        self.issues.append(issue)
        logger.info("[IssueCollector] 记录问题 %s: %s", issue["id"], error_message[:100])

    def save(self, file_path: str = None):
        """将问题清单写入 JSON 文件，按 case_id 去重合并已有记录"""
        if not file_path:
            out_dir = os.path.join(config.root_dir, "output")
            os.makedirs(out_dir, exist_ok=True)
            file_path = os.path.join(out_dir, "issues.json")

        merged = self._merge_existing(file_path)

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_issues": len(merged),
            "summary": self._summary_from(merged),
            "issues": merged,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info("问题清单已保存: %s (%d 个问题)", file_path, len(merged))
        return file_path

    def _merge_existing(self, file_path: str) -> List[Dict[str, Any]]:
        """合并已有问题：同 case_id 的用最新结果覆盖"""
        old = {}
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for iss in data.get("issues", []):
                    key = iss.get("case_id", "")
                    if key:
                        old[key] = iss
            except (json.JSONDecodeError, KeyError):
                pass

        for iss in self.issues:
            key = iss.get("case_id", "")
            if key:
                old[key] = iss

        return list(old.values())

    def _summary(self) -> Dict[str, Any]:
        return self._summary_from(self.issues)

    @staticmethod
    def _summary_from(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_severity = {}
        by_type = {}
        by_endpoint = {}
        for iss in issues:
            s = iss.get("severity", "unknown")
            by_severity[s] = by_severity.get(s, 0) + 1
            t = iss.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            e = iss.get("endpoint", "unknown")
            by_endpoint[e] = by_endpoint.get(e, 0) + 1
        return {
            "by_severity": by_severity,
            "by_type": by_type,
            "by_endpoint": by_endpoint,
        }

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0


# 全局单例
issue_collector = IssueCollector()
