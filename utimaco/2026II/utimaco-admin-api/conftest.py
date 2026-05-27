"""
pytest 全局 conftest — 报告钩子和公共 fixture。

签名配置在 config/config.yaml 中:
  auth.enabled:    true/false 签名开关
  auth.algorithm:  RSAWithSHA256 | SM2WithSM3
"""

import os
import pytest
import allure

import config as _cfg


def pytest_configure(config):
    results_dir = os.path.join(
        _cfg.config.root_dir,
        _cfg.config.get("paths.allure_results", "reports/allure-results"),
    )
    os.makedirs(results_dir, exist_ok=True)
    os.environ["ALLURE_RESULTS_PATH"] = results_dir

    print(f"\n  签名: {'开启' if _cfg.config.auth_enabled else '关闭'}"
          f"  算法: {_cfg.config.auth_algorithm}"
          f"  环境: {_cfg.config.base_url}\n")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        allure.attach(
            f"用例失败: {rep.longreprtext[:1000]}",
            name="失败详情",
            attachment_type=allure.attachment_type.TEXT,
        )


def pytest_sessionfinish(session, exitstatus):
    from common.issue_collector import issue_collector
    from common.result_collector import result_collector

    if result_collector.results:
        path = result_collector.save()
        print(f"\n  测试结果已保存: {path} ({len(result_collector.results)} 条)")

    if issue_collector.has_issues:
        path = issue_collector.save()
        print(f"\n{'='*60}")
        print(f"  发现 {len(issue_collector.issues)} 个问题，清单已保存: {path}")
        print(f"{'='*60}")


@pytest.fixture(scope="session")
def base_url():
    return _cfg.config.base_url
