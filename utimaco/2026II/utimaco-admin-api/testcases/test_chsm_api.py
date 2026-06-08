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
from config import config

# ================================================================
# 数据加载 & 场景分组
# ================================================================
handler = ExcelHandler()
ALL_DATA = handler.get_test_cases(sheet_name="chsm", process_data=True)
SCENARIOS = group_scenarios(ALL_DATA)

for _i, _steps in enumerate(SCENARIOS, 1):
    _steps[0]["_order"] = _i


def _scenario_id(idx, steps):
    """生成用于 pytest 参数化 ID 的字符串（带执行序号）"""
    first = steps[0]
    sid = first.get("scenario_id", "")
    cid = first.get("case_id", "unknown")
    if sid:
        return f"{idx:04d}_{sid}({len(steps)}steps)"
    return f"{idx:04d}_{cid}"


# ================================================================
# 测试类
# ================================================================
@allure.feature("华为云密码机二期接口测试")
class TestCHSMAPI:

    @pytest.mark.parametrize("steps", SCENARIOS, ids=[_scenario_id(i, s) for i, s in enumerate(SCENARIOS, 1)])
    def test_scenario(self, steps: list):
        """执行一个场景（可能包含多个步骤）"""
        first = steps[0]
        scenario_id = first.get("scenario_id", first.get("case_id", ""))
        is_multi = len(steps) > 1
        order = first.get("_order", 0)

        if is_multi:
            allure.dynamic.title(f"[{order:04d}] 场景: {scenario_id} ({len(steps)} 步)")
            desc_lines = [
                f"  step {s.get('step','?')}: [{s.get('step_type','test')}] "
                f"{s.get('case_id','')} {s.get('description','')}"
                for s in steps
            ]
            allure.dynamic.description("\n".join(desc_lines))
        else:
            allure.dynamic.title(f"[{order:04d}] {first['case_id']}: {first['description']}")

        ctx = ScenarioContext()
        all_passed = True
        failed_steps = []

        for i, step in enumerate(steps):
            try:
                passed = self._run_step(step, ctx, scenario_id if is_multi else None)
            except (AssertionError, Exception):
                passed = False
            if not passed:
                all_passed = False
                _cid = step.get('case_id', '')
                _desc = step.get('description', '')
                failed_steps.append(
                    f"step {step.get('step', '?')}: {_cid} - {_desc}"
                )
                if step.get("step_type") == "setup":
                    for remaining in steps[i + 1:]:
                        with allure.step(f"跳过: {remaining.get('case_id', '')} (前置失败)"):
                            allure.attach("前置步骤失败，跳过", name="跳过原因",
                                          attachment_type=allure.attachment_type.TEXT)
                    break

        if not all_passed:
            n_fail = len(failed_steps)
            n_total = len(steps)
            if is_multi:
                allure.dynamic.title(
                    f"[{order:04d}] FAIL [{n_fail}/{n_total}] {scenario_id}"
                )
            else:
                allure.dynamic.title(
                    f"[{order:04d}] FAIL {first['case_id']}: {first['description']}"
                )
            allure.dynamic.severity(allure.severity_level.CRITICAL)
            detail = "\n".join(f"  - {s}" for s in failed_steps)
            allure.dynamic.description(f"失败 {n_fail}/{n_total} 步:\n{detail}")
            allure.attach(detail, name="失败步骤汇总",
                          attachment_type=allure.attachment_type.TEXT)
            pytest.fail(f"场景 {scenario_id} 失败 {n_fail}/{n_total}")

    def _run_step(self, step: dict, ctx: ScenarioContext, scenario_id: str = None) -> bool:
        """执行单个步骤，返回是否通过"""
        case_id = step.get("case_id", "")
        desc = step.get("description", "")
        endpoint = ctx.substitute(step.get("endpoint", "")) or ""
        method = step.get("method", "POST").lower()
        step_type = step.get("step_type", "test")
        step_num = step.get("step", "?")
        ref_case_id = step.get("ref_case_id")
        expected_status = int(step.get("expected_status", 200))
        assert_rules = step.get("assert_rules")
        should_collect = bool(ref_case_id)
        excel_row = step.get("excel_row", "?")

        section = step.get("section", "")

        if scenario_id:
            step_label = f"[{section}] [step {step_num} {step_type}] {case_id}: {desc}"
        else:
            step_label = f"[{section}] {case_id}: {desc}"

        logger.info("=" * 60)
        logger.info("用例: %s | Excel行: %s | 期望: %d", case_id, excel_row, expected_status)
        if scenario_id:
            logger.info("场景: %s | 步骤: %s (%s)", scenario_id, step_num, step_type)

        with allure.step(step_label):
            # 变量替换
            params = ctx.substitute(step.get("params"))
            json_data = ctx.substitute(step.get("json_data"))

            if ctx.vars:
                logger.info("当前变量: %s", json.dumps(ctx.vars, ensure_ascii=False, default=str))

            # 选择 host 和认证
            host = step.get("host") or None
            if host:
                logger.info("使用 host: %s", host)
            auth_val = str(step.get("auth") or "").strip().lower()
            auth_enabled = False if auth_val == "no" else True
            section = step.get("section", "")

            # 根据 section 选择指纹: 9.2 用 vsm_fingerprint，其他用 chsm_fingerprint
            fp_override = None
            if str(section).startswith("9.2"):
                vsm_fp = config.get("auth.vsm_fingerprint", "")
                if vsm_fp:
                    fp_override = vsm_fp
            else:
                chsm_fp = config.get("auth.chsm_fingerprint", "")
                if chsm_fp:
                    fp_override = chsm_fp

            client = get_http_client(base_url=host, auth_enabled=auth_enabled, fingerprint_override=fp_override)

            # 发送请求
            try:
                fn = getattr(client, method)
                kwargs = {}
                if params and isinstance(params, dict):
                    kwargs["params"] = params

                # 文件上传: file_path 列指定文件路径时用 multipart
                file_path = step.get("file_path")
                if file_path and isinstance(file_path, str) and file_path.strip():
                    import os
                    fp = os.path.join(config.root_dir, file_path.strip())
                    if os.path.isfile(fp):
                        kwargs["files"] = {"file": open(fp, "rb")}
                        if json_data and isinstance(json_data, dict):
                            kwargs["data"] = json_data
                    else:
                        logger.warning("文件不存在: %s", fp)
                        if json_data and isinstance(json_data, (dict, list)):
                            kwargs["json_data"] = json_data
                elif json_data and isinstance(json_data, (dict, list)):
                    kwargs["json_data"] = json_data

                response = fn(endpoint=endpoint, **kwargs)
            except Exception as e:
                error_msg = f"请求异常: {e}"
                logger.error("请求失败 [%s] Excel行%s: %s", case_id, excel_row, error_msg)
                allure.attach(error_msg, name=f"FAIL: {error_msg[:80]}",
                              attachment_type=allure.attachment_type.TEXT)
                issue_collector.add(
                    case_id=case_id, endpoint=endpoint, method=method,
                    error_message=error_msg, severity="high", issue_type="request_error",
                    request_body=json_data or params,
                    scenario_id=scenario_id, step=step_num, step_type=step_type,
                    description=desc, section=step.get("section", ""),
                )
                if should_collect:
                    result_collector.add(
                        case_id=case_id, ref_case_id=ref_case_id, status="error",
                        endpoint=endpoint, method=method, error_message=error_msg,
                        scenario_id=scenario_id, step=step_num,
                    )
                raise
            allure.attach(
                f"请求URL: {response.request.url}\n"
                f"请求方法: {response.request.method}\n"
                f"请求头: {dict(response.request.headers)}\n"
                f"请求体: {response.request.body if response.request.body else '无'}",
                name="请求详情",
                attachment_type=allure.attachment_type.TEXT
            )

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
                    logger.info("变量提取成功: %s → %s", save_vars,
                                json.dumps(ctx.vars, ensure_ascii=False, default=str))
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
                logger.info("通过 ✓ [%s]", case_id)
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
                logger.error("断言失败 [%s] Excel行%s: %s", case_id, excel_row, error_msg)
                logger.error("  请求: %s %s", method.upper(), endpoint)
                if json_data:
                    logger.error("  请求体: %s", json.dumps(json_data, ensure_ascii=False) if isinstance(json_data, (dict, list)) else json_data)
                logger.error("  响应码: %d | 期望: %d", response.status_code, expected_status)
                try:
                    logger.error("  响应体: %s", json.dumps(response.json(), ensure_ascii=False))
                except Exception:
                    logger.error("  响应体: %s", response.text[:500])
                short_err = error_msg.split(". body=")[0]
                allure.attach(error_msg, name=f"FAIL: {short_err}",
                              attachment_type=allure.attachment_type.TEXT)
                issue_collector.add(
                    case_id=case_id, endpoint=endpoint, method=method,
                    error_message=error_msg,
                    severity="high" if step_type == "test" else "medium",
                    issue_type="assertion_failed",
                    request_body=json_data or params,
                    response=response,
                    scenario_id=scenario_id, step=step_num, step_type=step_type,
                    description=desc, section=step.get("section", ""),
                )
                if should_collect:
                    result_collector.add(
                        case_id=case_id, ref_case_id=ref_case_id, status="failed",
                        endpoint=endpoint, method=method, error_message=error_msg,
                        response_time_ms=response.elapsed.total_seconds() * 1000,
                        scenario_id=scenario_id, step=step_num,
                    )
                raise
