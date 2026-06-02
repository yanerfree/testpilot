#!/usr/bin/env python3
"""
并发测试脚本 — 独立运行，不修改现有测试代码。

用法:
  python run_concurrency.py

json_data 中支持 {i} 占位符，每个并发请求自动替换为序号 1,2,3...
跑完后会打印最后完成的那个请求发了什么数据，方便对比最终状态。

并发用例定义在 CONCURRENT_CASES 列表中，enabled 控制开关。
"""

import json
import operator
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

sys.path.insert(0, ".")
from common.http_client import get_http_client
from common.logger import logger


# ================================================================
# 数据准备 — {i} 占位符替换 + requestId 刷新
# ================================================================
def _substitute(data: Any, idx: int) -> Any:
    """递归替换 {i} 占位符，并刷新 requestId"""
    if isinstance(data, str):
        return data.replace("{i}", str(idx))
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if k == "requestId":
                out[k] = str(uuid.uuid4())
            else:
                out[k] = _substitute(v, idx)
        return out
    if isinstance(data, list):
        return [_substitute(item, idx) for item in data]
    return data


# ================================================================
# 单次请求记录
# ================================================================
@dataclass
class RequestRecord:
    idx: int
    finish_order: int
    json_data: Any
    status_code: int = 0
    response_time: float = 0.0
    response_body: Any = None
    error: str = ""
    success: bool = False


# ================================================================
# 统计结果
# ================================================================
@dataclass
class ConcurrencyResult:
    total: int = 0
    success: int = 0
    fail: int = 0
    error_count: int = 0
    response_times: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    records: List[RequestRecord] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success / self.total if self.total else 0.0

    @property
    def avg_rt(self) -> float:
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0

    @property
    def p95_rt(self) -> float:
        return self._percentile(0.95)

    @property
    def p99_rt(self) -> float:
        return self._percentile(0.99)

    @property
    def max_rt(self) -> float:
        return max(self.response_times) if self.response_times else 0.0

    @property
    def min_rt(self) -> float:
        return min(self.response_times) if self.response_times else 0.0

    def _percentile(self, pct: float) -> float:
        if not self.response_times:
            return 0.0
        s = sorted(self.response_times)
        idx = int(len(s) * pct)
        return s[min(idx, len(s) - 1)]

    def last_success(self) -> Optional[RequestRecord]:
        """按完成顺序，返回最后一个成功的请求"""
        ok = [r for r in self.records if r.success]
        return max(ok, key=lambda r: r.finish_order) if ok else None

    def summary(self) -> dict:
        return {
            "total": self.total,
            "success": self.success,
            "fail": self.fail,
            "error_count": self.error_count,
            "success_rate": round(self.success_rate, 4),
            "avg_rt": round(self.avg_rt, 4),
            "p95_rt": round(self.p95_rt, 4),
            "p99_rt": round(self.p99_rt, 4),
            "max_rt": round(self.max_rt, 4),
            "min_rt": round(self.min_rt, 4),
            "status_codes": dict(sorted(self.status_codes.items())),
            "errors": self.errors[:10],
        }


# ================================================================
# 并发执行器
# ================================================================
def run_concurrent(
    concurrency: int,
    method: str,
    endpoint: str,
    expected_status: int = 200,
    json_data: Any = None,
    params: Optional[Dict] = None,
    auth_enabled: bool = True,
) -> ConcurrencyResult:
    result = ConcurrencyResult()
    finish_counter = [0]

    def _single(idx: int):
        client = get_http_client(auth_enabled=auth_enabled)
        req_data = _substitute(json_data, idx) if json_data else None
        fn = getattr(client, method.lower())
        kwargs = {}
        if params and isinstance(params, dict):
            kwargs["params"] = params
        if req_data is not None:
            kwargs["json_data"] = req_data
        resp = fn(endpoint=endpoint, **kwargs)
        return req_data, resp

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_single, i): i for i in range(1, concurrency + 1)}
        for future in as_completed(futures):
            idx = futures[future]
            finish_counter[0] += 1
            order = finish_counter[0]
            result.total += 1

            try:
                req_data, resp = future.result()
                rt = resp.elapsed.total_seconds()
                result.response_times.append(rt)
                code = resp.status_code
                result.status_codes[code] = result.status_codes.get(code, 0) + 1

                try:
                    body = resp.json()
                except Exception:
                    body = resp.text[:200]

                is_ok = code == expected_status
                if is_ok:
                    result.success += 1
                else:
                    result.fail += 1
                    result.errors.append(f"HTTP {code}: {body}")

                result.records.append(RequestRecord(
                    idx=idx, finish_order=order, json_data=req_data,
                    status_code=code, response_time=rt,
                    response_body=body, success=is_ok,
                ))
            except Exception as e:
                result.error_count += 1
                result.errors.append(str(e))
                result.records.append(RequestRecord(
                    idx=idx, finish_order=order, json_data=None, error=str(e),
                ))

    return result


# ================================================================
# 断言
# ================================================================
_OPS = {
    ">=": operator.ge, "<=": operator.le,
    ">": operator.gt, "<": operator.lt,
    "==": operator.eq, "!=": operator.ne,
}


def check_assertions(result: ConcurrencyResult, rules: str) -> List[str]:
    if not rules:
        return []
    failures = []
    for rule in rules.split(";"):
        rule = rule.strip()
        if not rule:
            continue
        for op_str, op_fn in sorted(_OPS.items(), key=lambda x: -len(x[0])):
            if op_str in rule:
                metric, threshold_str = rule.split(op_str, 1)
                metric = metric.strip()
                threshold = float(threshold_str.strip())
                actual = getattr(result, metric, None)
                if actual is None:
                    failures.append(f"未知指标: {metric}")
                elif not op_fn(actual, threshold):
                    failures.append(f"{metric} = {actual:.4f}, 期望 {op_str} {threshold}")
                break
    return failures


# ================================================================
# 并发用例定义 — json_data 中 {i} 会被替换为 1,2,3...
# ================================================================
CONCURRENT_CASES = [
    {
        "enabled": True,                                          # ← 改 False 跳过
        "case_id": "CC_NET_01",
        "description": "7.1.4 configCHSMNet 10路并发配置网络",
        "endpoint": "/api/1.0/chsm/network",
        "method": "POST",
        "json_data": {
            "requestId": "uuid",
            "dnsList": ["8.8.8.{i}", "114.114.114.{i}"],
            "netAddrs": [{
                "name": "eth0",
                "ip": "192.168.{i}.100",
                "mask": "255.255.255.0",
                "gateway": "192.168.{i}.1",
            }],
        },
        "expected_status": 200,
        "concurrency": 10,
        "assert_rules": "success_rate>=1.0;avg_rt<=5.0",
    },
    {
        "enabled": True,                                          # ← 改 False 跳过
        "case_id": "CC_NTP_01",
        "description": "7.1.5 configCHSMNtp 10路并发配置NTP",
        "endpoint": "/api/1.0/chsm/ntp",
        "method": "POST",
        "json_data": {
            "requestId": "uuid",
            "addr": "10.10.{i}.1",
            "syncPeriod": "{i}0",
        },
        "expected_status": 200,
        "concurrency": 10,
        "assert_rules": "success_rate>=1.0;avg_rt<=5.0",
    },
    {
        "enabled": True,                                          # ← 改 False 跳过
        "case_id": "CC_RESTART_01",
        "description": "7.1.11 restartCHSM 5路并发重启",
        "endpoint": "/api/1.0/chsm",
        "method": "POST",
        "json_data": {
            "requestId": "uuid",
            "oprType": "restart",
            "callbackUrl": "http://192.168.1.1:8080/callback",
        },
        "expected_status": 200,
        "concurrency": 5,
        "assert_rules": "success_rate>=0.8;avg_rt<=10.0",
    },
]


# ================================================================
# 主流程
# ================================================================
def run_all(cases):
    results = []
    total_pass = 0
    total_fail = 0

    for case in cases:
        cc = case["concurrency"]
        case_id = case["case_id"]
        desc = case["description"]

        print(f"\n{'=' * 60}")
        print(f"  {case_id}: {desc}")
        print(f"  并发数: {cc} | 期望状态码: {case['expected_status']}")
        print(f"{'=' * 60}")

        cr = run_concurrent(
            concurrency=cc,
            method=case["method"],
            endpoint=case["endpoint"],
            expected_status=case["expected_status"],
            json_data=case.get("json_data"),
            params=case.get("params"),
        )

        summary = cr.summary()
        print(f"\n  结果统计:")
        print(f"    总请求: {summary['total']}")
        print(f"    成功:   {summary['success']}  失败: {summary['fail']}  异常: {summary['error_count']}")
        print(f"    成功率: {summary['success_rate'] * 100:.1f}%")
        print(f"    响应时间: avg={summary['avg_rt']:.3f}s  p95={summary['p95_rt']:.3f}s  "
              f"p99={summary['p99_rt']:.3f}s  max={summary['max_rt']:.3f}s")
        print(f"    状态码分布: {summary['status_codes']}")

        # 完成顺序明细
        print(f"\n  完成顺序:")
        for r in sorted(cr.records, key=lambda x: x.finish_order):
            status = "ok" if r.success else f"FAIL({r.status_code})" if r.status_code else "ERR"
            print(f"    #{r.finish_order} 请求{r.idx} [{status}] {r.response_time:.3f}s")

        # 最后完成的成功请求
        last = cr.last_success()
        if last:
            print(f"\n  最后成功的请求: 请求{last.idx} (第{last.finish_order}个完成)")
            print(f"    发送数据: {json.dumps(last.json_data, ensure_ascii=False)}")

        failures = check_assertions(cr, case.get("assert_rules", ""))
        if failures:
            total_fail += 1
            print(f"\n  ✗ 断言失败:")
            for f in failures:
                print(f"    - {f}")
        else:
            total_pass += 1
            print(f"\n  ✓ 通过")

        if summary["errors"]:
            print(f"\n  错误详情 (前10条):")
            for err in summary["errors"]:
                print(f"    - {str(err)[:120]}")

        results.append({
            "case_id": case_id,
            "description": desc,
            "concurrency": cc,
            "passed": len(failures) == 0,
            "last_success_idx": last.idx if last else None,
            "last_success_data": last.json_data if last else None,
            **summary,
        })

    print(f"\n{'=' * 60}")
    print(f"  并发测试汇总: {total_pass} 通过, {total_fail} 失败, 共 {len(cases)} 条")
    print(f"{'=' * 60}")

    os.makedirs("output", exist_ok=True)
    report_path = "output/concurrency_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {report_path}")

    return total_fail == 0


if __name__ == "__main__":
    cases = [c for c in CONCURRENT_CASES if c.get("enabled", True)]
    if not cases:
        print("没有启用的并发用例，请检查 CONCURRENT_CASES 中的 enabled 字段")
        sys.exit(0)
    ok = run_all(cases)
    sys.exit(0 if ok else 1)
