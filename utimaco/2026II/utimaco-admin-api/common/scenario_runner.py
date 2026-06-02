"""
场景编排引擎 — 支持多步骤测试场景，步骤间变量传递。

Excel 新增列:
  scenario_id  — 场景分组标识，相同 ID 的行属于同一场景
  step         — 步骤序号（场景内按此排序执行）
  step_type    — setup(前置) / test(被测) / verify(验证)
  save_vars    — 从响应中提取变量，格式: varName=json.path  多个用分号分隔

单条用例（无 scenario_id）仍按原逻辑独立执行，完全向后兼容。
"""

import re
from typing import Any, Dict, List

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
    grouped = {}
    for sid, steps in scenarios.items():
        steps.sort(key=lambda r: int(r.get("step", 0)))
        grouped[sid] = steps

    # 按 Excel 行顺序输出：每个场景/独立用例取首行的 excel_row 排序
    result: List[List[dict]] = []
    seen_scenarios = set()
    for row in test_data:
        sid = row.get("scenario_id")
        if sid and isinstance(sid, str) and sid.strip():
            sid = sid.strip()
            if sid not in seen_scenarios:
                seen_scenarios.add(sid)
                result.append(grouped[sid])
        else:
            result.append([row])

    return result
