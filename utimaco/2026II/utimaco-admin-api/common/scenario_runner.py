"""
场景编排引擎 — 支持多步骤测试场景，步骤间变量传递。

Excel 新增列:
  scenario_id  — 场景分组标识，相同 ID 的行属于同一场景
  step         — 步骤序号（场景内按此排序执行）
  step_type    — setup(前置) / test(被测) / verify(验证)
  save_vars    — 从响应中提取变量，格式: varName=json.path  多个用分号分隔
  use_vars     — 标记该行使用变量替换（有 ${xx} 占位符时自动替换，无需显式填写）

单条用例（无 scenario_id）仍按原逻辑独立执行，完全向后兼容。

用法:
    runner = ScenarioRunner(client)
    results = runner.run_scenario(steps)  # steps 是同一 scenario_id 的行列表
"""

import copy
import json
import re
from typing import Any, Dict, List, Optional

import requests

from common.assertions import Assertions
from common.logger import logger

assertions = Assertions()


class ScenarioContext:
    """场景内共享的变量上下文"""

    def __init__(self):
        self.vars: Dict[str, Any] = {}

    def set(self, name: str, value: Any):
        logger.info("  [ctx] 保存变量: %s = %s", name, repr(value)[:100])
        self.vars[name] = value

    def get(self, name: str, default=None) -> Any:
        return self.vars.get(name, default)

    def substitute(self, data: Any) -> Any:
        """递归替换数据中的 ${varName} 占位符"""
        if isinstance(data, str):
            return self._sub_string(data)
        if isinstance(data, dict):
            return {k: self.substitute(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.substitute(item) for item in data]
        return data

    def _sub_string(self, s: str) -> Any:
        # 整个字符串就是一个变量引用 → 返回原始类型（不强制转 str）
        m = re.fullmatch(r"\$\{(\w+)}", s)
        if m:
            name = m.group(1)
            if name in self.vars:
                return self.vars[name]
            logger.warning("  [ctx] 变量未定义: %s", name)
            return s

        # 字符串中嵌入多个变量 → 替换为字符串
        def _repl(match):
            name = match.group(1)
            val = self.vars.get(name)
            if val is None:
                logger.warning("  [ctx] 变量未定义: %s", name)
                return match.group(0)
            return str(val)

        return re.sub(r"\$\{(\w+)}", _repl, s)


def extract_vars(response_json: Any, save_vars_str: str, ctx: ScenarioContext):
    """
    从响应 JSON 中提取变量存入上下文。
    save_vars 格式: "vsmId=result.vsmIds[0];token=result.token"
    """
    if not save_vars_str or not isinstance(save_vars_str, str):
        return

    for pair in save_vars_str.split(";"):
        pair = pair.strip()
        if "=" not in pair:
            continue
        var_name, json_path = pair.split("=", 1)
        var_name = var_name.strip()
        json_path = json_path.strip()

        values = assertions._resolve_path(response_json, json_path)
        if values:
            ctx.set(var_name, values[0])
        else:
            logger.warning("  [ctx] 提取变量失败: %s (路径 %s 无匹配)", var_name, json_path)


class StepResult:
    """单个步骤的执行结果"""

    def __init__(self, step: dict):
        self.step = step
        self.case_id: str = step.get("case_id", "")
        self.step_num: int = int(step.get("step", 0))
        self.step_type: str = step.get("step_type", "test")
        self.passed: bool = False
        self.response: Optional[requests.Response] = None
        self.error: Optional[str] = None
        self.skipped: bool = False


class ScenarioResult:
    """整个场景的执行结果"""

    def __init__(self, scenario_id: str):
        self.scenario_id = scenario_id
        self.step_results: List[StepResult] = []

    @property
    def passed(self) -> bool:
        return all(r.passed or r.skipped for r in self.step_results)

    @property
    def test_steps(self) -> List[StepResult]:
        """只返回 step_type=test 的结果（用于报告统计）"""
        return [r for r in self.step_results if r.step_type == "test"]


def run_scenario(steps: List[dict], client, ctx: ScenarioContext = None) -> ScenarioResult:
    """
    执行一个场景的所有步骤。

    Args:
        steps: 同一 scenario_id 的行列表，已按 step 排序
        client: HttpClient 实例
        ctx: 可选，外部传入的上下文（用于场景间共享变量）
    """
    if ctx is None:
        ctx = ScenarioContext()

    scenario_id = steps[0].get("scenario_id", steps[0].get("case_id", "unknown"))
    result = ScenarioResult(scenario_id)
    setup_failed = False

    for step in steps:
        sr = StepResult(step)
        result.step_results.append(sr)

        step_type = step.get("step_type", "test")
        case_id = step.get("case_id", "")
        endpoint = step.get("endpoint", "")
        method = step.get("method", "POST").lower()

        logger.info("--- [%s] step %s (%s): %s %s ---",
                     scenario_id, step.get("step", "?"), step_type, method.upper(), endpoint)

        # setup 失败后跳过后续步骤
        if setup_failed:
            sr.skipped = True
            sr.error = "前置步骤失败，跳过"
            logger.warning("  跳过: %s (前置步骤失败)", case_id)
            continue

        # 变量替换
        params = ctx.substitute(step.get("params"))
        json_data = ctx.substitute(step.get("json_data"))

        # 发送请求
        try:
            fn = getattr(client, method)
            kwargs = {}
            if params and isinstance(params, dict):
                kwargs["params"] = params
            if json_data and isinstance(json_data, (dict, list)):
                kwargs["json_data"] = json_data

            # 选择 host
            host = step.get("host")
            if host:
                from common.http_client import get_http_client
                req_client = get_http_client(base_url=host)
                fn = getattr(req_client, method)

            response = fn(endpoint=endpoint, **kwargs)
            sr.response = response
        except Exception as e:
            sr.error = f"请求异常: {e}"
            logger.error("  请求异常: %s", e)
            if step_type == "setup":
                setup_failed = True
            continue

        # 提取变量（在断言之前，确保即使断言失败也能提取到变量）
        save_vars = step.get("save_vars")
        if save_vars and response:
            try:
                extract_vars(response.json(), save_vars, ctx)
            except Exception as e:
                logger.warning("  变量提取失败: %s", e)

        # 断言
        expected_status = int(step.get("expected_status", 200))
        assert_rules = step.get("assert_rules")
        try:
            assertions.assert_status_code(response, expected_status)
            if assert_rules:
                assertions.apply_assert_rules(response, assert_rules)
            sr.passed = True
        except AssertionError as e:
            sr.error = str(e)
            logger.error("  断言失败: %s", e)
            if step_type == "setup":
                setup_failed = True

    return result


def group_scenarios(test_data: List[dict]) -> List[List[dict]]:
    """
    将测试数据按场景分组。
    - 有 scenario_id 的行按 scenario_id 分组，组内按 step 排序
    - 没有 scenario_id 的行各自成为独立场景（单步骤）
    """
    scenarios: Dict[str, List[dict]] = {}
    standalone: List[List[dict]] = []

    for row in test_data:
        sid = row.get("scenario_id")
        if sid and isinstance(sid, str) and sid.strip():
            sid = sid.strip()
            if sid not in scenarios:
                scenarios[sid] = []
            scenarios[sid].append(row)
        else:
            # 无 scenario_id → 独立单步场景，自动填充字段
            row.setdefault("step", 1)
            row.setdefault("step_type", "test")
            standalone.append([row])

    # 场景内按 step 排序
    grouped = []
    for sid, steps in scenarios.items():
        steps.sort(key=lambda r: int(r.get("step", 0)))
        grouped.append(steps)

    return grouped + standalone
