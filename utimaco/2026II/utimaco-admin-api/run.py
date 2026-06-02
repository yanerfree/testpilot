#!/usr/bin/env python3
"""
运行测试 & 生成 Allure 报告。

用法:
  python run.py                    # 运行全部用例 + 生成报告
  python run.py --no-open          # 运行后不自动打开报告
  python run.py -k "CHSM_INFO"    # 按关键字筛选用例
"""

import argparse
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(ROOT, "reports", "allure-results")
REPORT_DIR = os.path.join(ROOT, "reports", "allure-report")


def run_tests(extra_args: list):
    cmd = [
        sys.executable, "-m", "pytest",
        "--alluredir", RESULTS_DIR,
        "--clean-alluredir",
    ] + extra_args
    print(f">>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


def generate_report():
    cmd = ["allure", "generate", RESULTS_DIR, "-o", REPORT_DIR, "--clean", "--single-file"]
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, shell=True, check=True, cwd=ROOT)


def open_report():
    cmd = ["allure", "open", REPORT_DIR]
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, shell=True, cwd=ROOT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行测试并生成 Allure 报告")
    parser.add_argument("--no-open", action="store_true", help="运行后不自动打开报告")
    parser.add_argument("pytest_args", nargs="*", default=[], help="透传给 pytest 的参数")
    args = parser.parse_args()

    rc = run_tests(args.pytest_args)
    generate_report()
    if not args.no_open:
        open_report()
    sys.exit(rc)
