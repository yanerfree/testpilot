"""
pytest 全局 conftest — 报告钩子和公共 fixture。

签名配置在 config/config.yaml 中:
  auth.enabled:    true/false 签名开关
  auth.algorithm:  RSAWithSHA256 | SM2WithSM3
"""

import os
import time

import pytest
import allure

import config as _cfg
from common.logger import logger


_session_start = 0
_passed = 0
_failed = 0
_error = 0


def pytest_configure(config):
    results_dir = os.path.join(
        _cfg.config.root_dir,
        _cfg.config.get("paths.allure_results", "reports/allure-results"),
    )
    os.makedirs(results_dir, exist_ok=True)
    os.environ["ALLURE_RESULTS_PATH"] = results_dir

    env_info = (
        f"签名: {'开启' if _cfg.config.auth_enabled else '关闭'}"
        f"  算法: {_cfg.config.auth_algorithm}"
        f"  环境: {_cfg.config.base_url}"
        f"  Excel: {_cfg.config.get('paths.excel_data')}"
    )
    print(f"\n  {env_info}\n")
    logger.info("=" * 60)
    logger.info("测试开始")
    logger.info(env_info)
    logger.info("=" * 60)


def pytest_sessionstart(session):
    global _session_start
    _session_start = time.time()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    global _passed, _failed, _error
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        if rep.passed:
            _passed += 1
        elif rep.failed:
            _failed += 1
            allure.attach(
                f"用例失败: {rep.longreprtext[:1000]}",
                name="失败详情",
                attachment_type=allure.attachment_type.TEXT,
            )
    elif rep.when == "setup" and rep.failed:
        _error += 1


def pytest_sessionfinish(session, exitstatus):
    from common.issue_collector import issue_collector
    from common.result_collector import result_collector

    duration = time.time() - _session_start
    total = _passed + _failed + _error

    logger.info("=" * 60)
    logger.info("测试结束 — 耗时 %.1f 秒", duration)
    logger.info("总计: %d | 通过: %d | 失败: %d | 错误: %d", total, _passed, _failed, _error)
    if total > 0:
        logger.info("通过率: %.1f%%", _passed / total * 100)
    logger.info("=" * 60)

    summary = (
        f"\n{'=' * 60}\n"
        f"  测试摘要\n"
        f"  总计: {total} | 通过: {_passed} | 失败: {_failed} | 错误: {_error}\n"
        f"  耗时: {duration:.1f} 秒"
    )
    if total > 0:
        summary += f" | 通过率: {_passed / total * 100:.1f}%"
    summary += f"\n{'=' * 60}"
    print(summary)

    if result_collector.results:
        path = result_collector.save()
        msg = f"  测试结果已保存: {path} ({len(result_collector.results)} 条)"
        print(msg)
        logger.info(msg.strip())

    if issue_collector.has_issues:
        path = issue_collector.save()
        msg = f"  发现 {len(issue_collector.issues)} 个问题，清单已保存: {path}"
        print(f"\n{msg}")
        logger.info(msg.strip())

    logger.info("日志文件: logs/test.log")
    print(f"  日志文件: logs/test.log")


@pytest.fixture(scope="session")
def base_url():
    return _cfg.config.base_url
