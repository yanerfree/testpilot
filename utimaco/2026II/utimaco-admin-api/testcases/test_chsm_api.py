"""
测试入口 — 支持两种模式:
  1. 单步用例: 没有 scenario_id 的行，每行独立执行（向后兼容）
  2. 场景编排: 有 scenario_id 的行，按场景分组、按 step 排序、步骤间传递变量

运行:
  pytest testcases/test_chsm_api.py -v --alluredir=reports/allure-results
"""

import json

import allure
import pytest

from common.assertions import assertions
from common.excel_handler import ExcelHandler
from common.http_client import get_http_client
from common.issue_collector import issue_collector
from common.logger import logger
from common.result_collector import result_collector
from common.scenario_runner import ScenarioContext, extract_vars, group_scenarios

# ================================================================
# 数据加载 & 场景分组
# ================================================================
handler = ExcelHandler()
ALL_DATA = handler.get_test_cases(sheet_name="testdata", process_data=True)
SCENARIOS = group_scenarios(ALL_DATA)


def _scenario_id(steps):
    """生成用于 pytest 参数化 ID 的字符串"""
    first = steps[0]
    sid = first.get("scenario_id", "")
    cid = first.get("case_id", "unknown")
    if sid:
        return f"{sid}({len(steps)}steps)"
    return cid


# ================================================================
# 测试类
# ================================================================
@allure.feature("华为云密码机二期接口测试")
class TestCHSMAPI:

    @pytest.mark.parametrize("steps", SCENARIOS, ids=[_scenario_id(s) for s in SCENARIOS])
    def test_scenario(self, steps: list):
        """执行一个场景（可能包含多个步骤）"""
        first = steps[0]
        scenario_id = first.get("scenario_id", first.get("case_id", ""))
        is_multi = len(steps) > 1

        if is_multi:
            allure.dynamic.title(f"场景: {scenario_id} ({len(steps)} 步)")
            desc_lines = [
                f"  step {s.get('step','?')}: [{s.get('step_type','test')}] "
                f"{s.get('case_id','')} {s.get('description','')}"
                for s in steps
            ]
            allure.dynamic.description("\n".join(desc_lines))
        else:
            row = first.get("excel_row", 0) - 1
            allure.dynamic.title(f"[{row:04d}] {first['case_id']}: {first['description']}")

        ctx = ScenarioContext()
        all_passed = True

        for i, step in enumerate(steps):
            passed = self._run_step(step, ctx, scenario_id if is_multi else None)
            if not passed:
                all_passed = False
                if step.get("step_type") == "setup":
                    for remaining in steps[i + 1:]:
                        with allure.step(f"跳过: {remaining.get('case_id', '')} (前置失败)"):
                            allure.attach("前置步骤失败，跳过", name="跳过原因",
                                          attachment_type=allure.attachment_type.TEXT)
                    break

        if not all_passed:
            pytest.fail(f"场景 {scenario_id} 存在失败步骤")

    def _run_step(self, step: dict, ctx: ScenarioContext, scenario_id: str = None) -> bool:
        """执行单个步骤，返回是否通过"""
        case_id = step.get("case_id", "")
        desc = step.get("description", "")
        endpoint = step.get("endpoint", "")
        method = step.get("method", "POST").lower()
        step_type = step.get("step_type", "test")
        step_num = step.get("step", "?")
        ref_case_id = step.get("ref_case_id")
        expected_status = int(step.get("expected_status", 200))
        assert_rules = step.get("assert_rules")
        should_collect = bool(ref_case_id)

        if scenario_id:
            step_label = f"[step {step_num} {step_type}] {case_id}: {desc}"
        else:
            step_label = f"{case_id}: {desc}"

        with allure.step(step_label):
            # 变量替换
            params = ctx.substitute(step.get("params"))
            json_data = ctx.substitute(step.get("json_data"))

            # 选择 host
            host = step.get("host") or None
            client = get_http_client(base_url=host)

            # 发送请求
            try:
                fn = getattr(client, method)
                kwargs = {}
                if params and isinstance(params, dict):
                    kwargs["params"] = params
                if json_data and isinstance(json_data, (dict, list)):
                    kwargs["json_data"] = json_data

                logger.info("[%s] %s %s", case_id, method.upper(), endpoint)
                response = fn(endpoint=endpoint, **kwargs)
            except Exception as e:
                error_msg = f"请求异常: {e}"
                allure.attach(error_msg, name="错误", attachment_type=allure.attachment_type.TEXT)
                issue_collector.add(
                    case_id=case_id, endpoint=endpoint, method=method,
                    error_message=error_msg, severity="high", issue_type="request_error",
                    request_body=json_data or params,
                    scenario_id=scenario_id, step=step_num, step_type=step_type,
                )
                if should_collect:
                    result_collector.add(
                        case_id=case_id, ref_case_id=ref_case_id, status="error",
                        endpoint=endpoint, method=method, error_message=error_msg,
                        scenario_id=scenario_id, step=step_num,
                    )
                return False

            # 记录响应
            try:
                body_str = json.dumps(response.json(), indent=2, ensure_ascii=False)
                allure.attach(body_str, name="响应JSON", attachment_type=allure.attachment_type.JSON)
            except Exception:
                allure.attach(response.text[:1000], name="响应文本", attachment_type=allure.attachment_type.TEXT)

            # 提取变量（在断言之前）
            save_vars = step.get("save_vars")
            if save_vars:
                try:
                    extract_vars(response.json(), save_vars, ctx)
                    allure.attach(
                        json.dumps(ctx.vars, ensure_ascii=False, indent=2, default=str),
                        name="变量上下文", attachment_type=allure.attachment_type.JSON,
                    )
                except Exception as e:
                    logger.warning("变量提取失败: %s", e)

            # 断言
            try:
                assertions.assert_status_code(response, expected_status)
                if assert_rules:
                    assertions.apply_assert_rules(response, assert_rules)
                if should_collect:
                    result_collector.add(
                        case_id=case_id, ref_case_id=ref_case_id, status="passed",
                        endpoint=endpoint, method=method,
                        response_time_ms=response.elapsed.total_seconds() * 1000,
                        scenario_id=scenario_id, step=step_num,
                    )
                return True
            except AssertionError as e:
                error_msg = str(e)
                allure.attach(error_msg, name="断言失败", attachment_type=allure.attachment_type.TEXT)
                issue_collector.add(
                    case_id=case_id, endpoint=endpoint, method=method,
                    error_message=error_msg,
                    severity="high" if step_type == "test" else "medium",
                    issue_type="assertion_failed",
                    request_body=json_data or params,
                    response=response,
                    scenario_id=scenario_id, step=step_num, step_type=step_type,
                )
                if should_collect:
                    result_collector.add(
                        case_id=case_id, ref_case_id=ref_case_id, status="failed",
                        endpoint=endpoint, method=method, error_message=error_msg,
                        response_time_ms=response.elapsed.total_seconds() * 1000,
                        scenario_id=scenario_id, step=step_num,
                    )
                return False
