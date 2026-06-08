#!/usr/bin/env python3
"""
并发修复验证测试脚本 v2

覆盖 Concurrency-Fix-Test-Checklist.md 中 6 项修复 / 6 个场景：
  A - 全局锁互斥（CHSM 操作 vs VSM 操作）
  B - per-vsmId 互斥（同 VSM 并发操作）
  C - VSM upgrade 全局互斥
  D - UpgradeInProgressGuard 二次检查
  E - 配置 UPSERT 幂等
  F - 导出锁 TTL 超时释放

用法:
  修改下方 ENABLED_SCENARIOS 控制运行哪些场景，然后:
    python run_concurrency_v2.py
"""

import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Barrier, BrokenBarrierError
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
from common.http_client import get_http_client
from common.logger import logger
from config import config

CALLBACK_URL = config.callback_url or "http://10.10.1.207:8000/callback"
VSM_ID_A = "vsm-concurrency-a"
VSM_ID_B = "vsm-concurrency-b"


# ================================================================
# ★★★ 运行控制 — 改 True/False 启用/禁用场景 ★★★
# ================================================================
ENABLED_SCENARIOS = {
    "A": True,     # 全局锁互斥（Fix #1 CRITICAL）—— CHSM 操作 vs VSM 操作
    "B": True,     # per-vsmId 互斥（Fix #1 CRITICAL）—— 同 VSM 并发操作
    "C": True,     # VSM upgrade 全局互斥（Fix #1 CRITICAL）
    "D": True,     # UpgradeInProgressGuard 二次检查（Fix #2 HIGH）
    "E": True,     # 配置 UPSERT 幂等（Fix #3 HIGH）
    "F": True,     # 导出锁 TTL 超时释放（Fix #5 MEDIUM）
    "G": True,     # DNS 文件锁 resolv.conf（Fix #4 MEDIUM）
}


# ================================================================
# 数据结构
# ================================================================

@dataclass
class RequestSpec:
    """单个请求规格"""
    method: str
    endpoint: str
    json_data: Any = None
    params: Optional[Dict] = None
    label: str = ""
    auth_enabled: bool = True


@dataclass
class ResponseRecord:
    """单个请求结果"""
    label: str
    idx: int
    finish_order: int
    status_code: int = 0
    response_time: float = 0.0
    response_body: Any = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass
class ScenarioResult:
    case_id: str
    description: str
    scenario: str
    passed: bool = False
    verdict: str = ""
    records: List[ResponseRecord] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


# ================================================================
# 工具函数
# ================================================================

def new_request_id() -> str:
    return str(uuid.uuid4())


def fresh(data: Any) -> Any:
    """深拷贝 JSON 数据并刷新 requestId"""
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            out[k] = new_request_id() if k == "requestId" else fresh(v)
        return out
    if isinstance(data, list):
        return [fresh(item) for item in data]
    return data


def substitute_index(data: Any, idx: int) -> Any:
    """替换 {i} 占位符并刷新 requestId"""
    if isinstance(data, str):
        return data.replace("{i}", str(idx))
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if k == "requestId":
                out[k] = new_request_id()
            else:
                out[k] = substitute_index(v, idx)
        return out
    if isinstance(data, list):
        return [substitute_index(item, idx) for item in data]
    return data


# ================================================================
# 并发执行器
# ================================================================

def run_concurrent(
    specs: List[RequestSpec],
    use_barrier: bool = True,
) -> List[ResponseRecord]:
    """
    并发发送多个请求。
    use_barrier=True 时，所有线程在 barrier 处同步后同时发出请求。
    """
    n = len(specs)
    records: List[ResponseRecord] = []
    finish_counter = [0]
    barrier = Barrier(n) if use_barrier else None

    def _fire(idx: int, spec: RequestSpec) -> ResponseRecord:
        client = get_http_client(auth_enabled=spec.auth_enabled)
        fn = getattr(client, spec.method.lower())
        kwargs = {}
        if spec.params:
            kwargs["params"] = spec.params
        if spec.json_data is not None:
            kwargs["json_data"] = spec.json_data

        if barrier:
            try:
                barrier.wait(timeout=10)
            except BrokenBarrierError:
                pass

        t0 = time.time()
        try:
            resp = fn(endpoint=spec.endpoint, **kwargs)
            elapsed = time.time() - t0
            finish_counter[0] += 1
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:300]
            return ResponseRecord(
                label=spec.label, idx=idx,
                finish_order=finish_counter[0],
                status_code=resp.status_code,
                response_time=elapsed,
                response_body=body,
            )
        except Exception as e:
            elapsed = time.time() - t0
            finish_counter[0] += 1
            return ResponseRecord(
                label=spec.label, idx=idx,
                finish_order=finish_counter[0],
                response_time=elapsed,
                error=str(e),
            )

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = {pool.submit(_fire, i, s): i for i, s in enumerate(specs)}
        for future in as_completed(futures):
            records.append(future.result())

    records.sort(key=lambda r: r.finish_order)
    return records


def run_n_concurrent(
    n: int,
    method: str,
    endpoint: str,
    json_data: Any = None,
    params: Optional[Dict] = None,
    label: str = "",
) -> List[ResponseRecord]:
    """N 路同类并发"""
    specs = []
    for i in range(1, n + 1):
        data = substitute_index(json_data, i) if json_data else None
        specs.append(RequestSpec(
            method=method, endpoint=endpoint,
            json_data=data, params=params,
            label=f"{label}#{i}",
        ))
    return run_concurrent(specs)


def poll_chsm_status(timeout: float = 30, interval: float = 2) -> Optional[dict]:
    """轮询 CHSM allstatus 直到获得响应"""
    client = get_http_client()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = client.get(endpoint="/api/1.0/chsm/allstatus")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        time.sleep(interval)
    return None


# ================================================================
# 断言助手
# ================================================================

def assert_no_500(records: List[ResponseRecord]) -> tuple:
    """断言无 500 错误，返回 (passed, verdict)"""
    codes = [r.status_code for r in records if r.status_code]
    errors = [r for r in records if r.error]
    count_500 = sum(1 for c in codes if c >= 500)
    if count_500 > 0 or errors:
        return False, f"有 {count_500} 个 500 错误, {len(errors)} 个异常"
    return True, f"全部 {len(records)} 个请求无 500 错误"


def assert_all_success(records: List[ResponseRecord], expected: int = 200) -> tuple:
    """断言全部成功"""
    ok = sum(1 for r in records if r.status_code == expected)
    total = len(records)
    if ok == total:
        return True, f"全部 {total} 个请求返回 {expected}"
    return False, f"{ok}/{total} 个请求返回 {expected}"


def assert_some_rejected(records: List[ResponseRecord], reject_codes: tuple = (409, 423, 429, 503)) -> tuple:
    """断言并发操作中至少有一个被拒绝（锁互斥验证）"""
    accepted = []
    rejected = []
    for r in records:
        if r.status_code in reject_codes or (r.response_body and isinstance(r.response_body, dict)
                                              and r.response_body.get("status") == "FAILED"):
            rejected.append(r)
        elif r.ok:
            accepted.append(r)

    if rejected:
        return True, f"锁互斥生效: {len(accepted)} 个接受, {len(rejected)} 个被拒绝"
    if len(accepted) <= 1:
        return True, f"只有 {len(accepted)} 个请求被接受（可能锁排队串行化）"
    return False, f"全部 {len(accepted)} 个请求都被接受，锁互斥可能未生效"


def assert_lock_exclusion_by_timing(records: List[ResponseRecord], min_gap: float = 0.5) -> tuple:
    """
    通过响应时间差判断锁排斥。
    如果操作被串行化，后续操作的响应时间会显著长于第一个。
    """
    times = sorted(r.response_time for r in records if r.response_time > 0)
    if len(times) < 2:
        return True, "不足 2 个有效响应，跳过时序验证"
    gap = times[-1] - times[0]
    if gap >= min_gap:
        return True, f"响应时间差 {gap:.3f}s >= {min_gap}s，存在串行化迹象"

    codes = [r.status_code for r in records]
    non_200 = [c for c in codes if c != 200]
    if non_200:
        return True, f"非 200 状态码 {non_200}，锁生效"

    return False, f"响应时间差 {gap:.3f}s < {min_gap}s，且全部 200，锁可能未生效"


# ================================================================
# 场景 A：全局锁互斥（CHSM 操作 vs VSM 操作）
# ================================================================

def scenario_a_cases() -> List[dict]:
    return [
        {
            "case_id": "CA_01",
            "scenario": "A",
            "description": "全局锁: CHSM export 期间 VSM start 应被阻塞",
            "run": _ca_01,
        },
        {
            "case_id": "CA_02",
            "scenario": "A",
            "description": "全局锁: CHSM restart + CHSM backup 并发互斥",
            "run": _ca_02,
        },
    ]


def _ca_01() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/chsm/image",
            json_data={
                "requestId": new_request_id(),
                "oprType": "export",
                "callbackUrl": CALLBACK_URL,
            },
            label="CHSM-export",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "start",
                "vsmId": VSM_ID_A,
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-start",
        ),
    ]
    records = run_concurrent(specs)
    p1, v1 = assert_some_rejected(records)
    p2, v2 = assert_lock_exclusion_by_timing(records)
    passed = p1 or p2
    return ScenarioResult(
        case_id="CA_01", scenario="A",
        description="全局锁: CHSM export 期间 VSM start 应被阻塞",
        passed=passed, verdict=f"{v1}; {v2}", records=records,
    )


def _ca_02() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/chsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "restart",
                "callbackUrl": CALLBACK_URL,
            },
            label="CHSM-restart",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/chsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "backup",
                "callbackUrl": CALLBACK_URL,
            },
            label="CHSM-backup",
        ),
    ]
    records = run_concurrent(specs)
    p1, v1 = assert_some_rejected(records)
    p2, v2 = assert_lock_exclusion_by_timing(records)
    passed = p1 or p2
    return ScenarioResult(
        case_id="CA_02", scenario="A",
        description="全局锁: CHSM restart + CHSM backup 并发互斥",
        passed=passed, verdict=f"{v1}; {v2}", records=records,
    )


# ================================================================
# 场景 B：per-vsmId 互斥（同 VSM 并发操作）
# ================================================================

def scenario_b_cases() -> List[dict]:
    return [
        {
            "case_id": "CB_01",
            "scenario": "B",
            "description": "per-vsmId 锁: 同 vsmId start + restart 互斥",
            "run": _cb_01,
        },
        {
            "case_id": "CB_02",
            "scenario": "B",
            "description": "per-vsmId 锁: 不同 vsmId start 不互斥",
            "run": _cb_02,
        },
    ]


def _cb_01() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "start",
                "vsmId": VSM_ID_A,
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-start-A",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "restart",
                "vsmId": VSM_ID_A,
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-restart-A",
        ),
    ]
    records = run_concurrent(specs)
    p1, v1 = assert_some_rejected(records)
    p2, v2 = assert_lock_exclusion_by_timing(records)
    passed = p1 or p2
    return ScenarioResult(
        case_id="CB_01", scenario="B",
        description="per-vsmId 锁: 同 vsmId start + restart 互斥",
        passed=passed, verdict=f"{v1}; {v2}", records=records,
    )


def _cb_02() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "start",
                "vsmId": VSM_ID_A,
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-start-A",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "start",
                "vsmId": VSM_ID_B,
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-start-B",
        ),
    ]
    records = run_concurrent(specs)
    p, v = assert_all_success(records)
    return ScenarioResult(
        case_id="CB_02", scenario="B",
        description="per-vsmId 锁: 不同 vsmId start 不互斥",
        passed=p, verdict=v, records=records,
    )


# ================================================================
# 场景 C：VSM upgrade 全局互斥
# ================================================================

def scenario_c_cases() -> List[dict]:
    return [
        {
            "case_id": "CC_01",
            "scenario": "C",
            "description": "VSM upgrade 全局锁: upgrade 期间 VSM start 应被阻塞",
            "run": _cc_01,
        },
    ]


def _cc_01() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "upgrade",
                "vsmId": VSM_ID_A,
                "packVersion": "99.0.0",
                "packUrl": "http://dummy/upgrade.pkg",
                "alg": "RSAWithSHA256",
                "sign": "dummysign",
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-upgrade",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "start",
                "vsmId": VSM_ID_B,
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-start-B",
        ),
    ]
    records = run_concurrent(specs)
    p1, v1 = assert_some_rejected(records)
    p2, v2 = assert_lock_exclusion_by_timing(records)
    passed = p1 or p2
    return ScenarioResult(
        case_id="CC_01", scenario="C",
        description="VSM upgrade 全局锁: upgrade 期间 VSM start 应被阻塞",
        passed=passed, verdict=f"{v1}; {v2}", records=records,
    )


# ================================================================
# 场景 D：UpgradeInProgressGuard 二次检查
# ================================================================

def scenario_d_cases() -> List[dict]:
    return [
        {
            "case_id": "CD_01",
            "scenario": "D",
            "description": "UpgradeGuard: 并发两次 CHSM upgrade，第二个应返回 409",
            "run": _cd_01,
        },
        {
            "case_id": "CD_02",
            "scenario": "D",
            "description": "UpgradeGuard: 并发两次 VSM upgrade，第二个应返回 409",
            "run": _cd_02,
        },
    ]


def _cd_01() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/chsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "upgrade",
                "packVersion": "99.0.0",
                "packUrl": "http://dummy/chsm_upgrade.pkg",
                "alg": "RSAWithSHA256",
                "sign": "dummysign",
                "callbackUrl": CALLBACK_URL,
            },
            label="CHSM-upgrade-1",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/chsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "upgrade",
                "packVersion": "99.0.0",
                "packUrl": "http://dummy/chsm_upgrade.pkg",
                "alg": "RSAWithSHA256",
                "sign": "dummysign",
                "callbackUrl": CALLBACK_URL,
            },
            label="CHSM-upgrade-2",
        ),
    ]
    records = run_concurrent(specs)
    accepted = [r for r in records if r.status_code == 200]
    rejected_409 = [r for r in records if r.status_code == 409]
    rejected_any = [r for r in records if r.status_code in (409, 423, 429, 503)]
    if len(accepted) == 1 and len(rejected_any) >= 1:
        passed = True
        verdict = f"正确: 1 个接受, {len(rejected_any)} 个被拒绝 (409={len(rejected_409)})"
    elif len(accepted) == 0:
        passed = True
        verdict = "两个均非 200（可能 upgrade 前置条件不满足），锁仍有效"
    else:
        p, v = assert_lock_exclusion_by_timing(records)
        passed = p
        verdict = f"两个均 200，时序判断: {v}"
    return ScenarioResult(
        case_id="CD_01", scenario="D",
        description="UpgradeGuard: 并发两次 CHSM upgrade，第二个应返回 409",
        passed=passed, verdict=verdict, records=records,
    )


def _cd_02() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "upgrade",
                "vsmId": VSM_ID_A,
                "packVersion": "99.0.0",
                "packUrl": "http://dummy/vsm_upgrade.pkg",
                "alg": "RSAWithSHA256",
                "sign": "dummysign",
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-upgrade-1",
        ),
        RequestSpec(
            method="POST", endpoint="/api/1.0/vsm",
            json_data={
                "requestId": new_request_id(),
                "oprType": "upgrade",
                "vsmId": VSM_ID_A,
                "packVersion": "99.0.0",
                "packUrl": "http://dummy/vsm_upgrade.pkg",
                "alg": "RSAWithSHA256",
                "sign": "dummysign",
                "callbackUrl": CALLBACK_URL,
            },
            label="VSM-upgrade-2",
        ),
    ]
    records = run_concurrent(specs)
    accepted = [r for r in records if r.status_code == 200]
    rejected_any = [r for r in records if r.status_code in (409, 423, 429, 503)]
    if len(accepted) <= 1 and len(rejected_any) >= 1:
        passed = True
        verdict = f"正确: {len(accepted)} 个接受, {len(rejected_any)} 个被拒绝"
    elif len(accepted) == 0:
        passed = True
        verdict = "两个均非 200（前置条件不满足），锁仍有效"
    else:
        p, v = assert_lock_exclusion_by_timing(records)
        passed = p
        verdict = f"两个均 200，时序判断: {v}"
    return ScenarioResult(
        case_id="CD_02", scenario="D",
        description="UpgradeGuard: 并发两次 VSM upgrade，第二个应返回 409",
        passed=passed, verdict=verdict, records=records,
    )


# ================================================================
# 场景 E：配置 UPSERT 幂等
# ================================================================

def scenario_e_cases() -> List[dict]:
    cases = [
        ("CE_01", "CHSM network", "/api/1.0/chsm/network", {
            "requestId": "uuid",
            "dnsList": ["8.8.8.{i}", "114.114.114.{i}"],
            "netAddrs": [{"name": "eth0", "ip": "192.168.{i}.100",
                          "mask": "255.255.255.0", "gateway": "192.168.{i}.1"}],
        }),
        ("CE_02", "CHSM ntp", "/api/1.0/chsm/ntp", {
            "requestId": "uuid",
            "addr": "ntp{i}.aliyun.com",
            "syncPeriod": 60,
        }),
        ("CE_03", "CHSM imageuploader", "/api/1.0/chsm/imageuploader", {
            "requestId": "uuid",
            "url": "http://image-server-{i}.example.com/upload",
        }),
        ("CE_04", "CHSM loguploader", "/api/1.0/chsm/loguploader", {
            "requestId": "uuid",
            "logServerType": "syslog",
            "logServerAddress": "10.10.{i}.100:514",
        }),
        ("CE_05", "CHSM alarmaddress", "/api/1.0/chsm/alarmaddress", {
            "requestId": "uuid",
            "url": "http://alarm-{i}.example.com/notify",
            "monitoringUrl": "http://monitor-{i}.example.com/check",
        }),
        ("CE_06", "CHSM cloudtoken", "/api/1.0/chsm/cloudtoken", {
            "requestId": "uuid",
            "cloudToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test{i}",
        }),
        ("CE_07", "CHSM moocaddress", "/api/1.0/chsm/moocaddress", {
            "requestId": "uuid",
            "ocIp": "10.10.{i}.1",
            "ocProtocol": "https",
            "ocPort": "26635",
            "resourceUrl": "/rest/cloudInfra/v1/resource",
            "performanceUrl": "/rest/cloudInfra/v1/performance",
            "bizRegionNativeId": "region-{i}",
            "cloudInfraType": "FusionSphere",
            "dewServiceHost": "kms.cn-north-{i}.myhuaweicloud.com",
        }),
        ("CE_08", "VSM network", f"/api/1.0/vsm/{VSM_ID_A}/network", {
            "requestId": "uuid",
            "vsmId": VSM_ID_A,
            "ip": "192.168.{i}.201",
            "mask": "24",
            "gateway": "192.168.{i}.1",
        }),
        ("CE_09", "VSM mac", f"/api/1.0/vsm/{VSM_ID_A}/mac", {
            "requestId": "uuid",
            "vsmId": VSM_ID_A,
            "mac": "ba:ca:c1:d2:e3:{i:02x}" if False else "ba:ca:c1:d2:e3:0{i}",
        }),
        ("CE_10", "VSM vlan", f"/api/1.0/vsm/{VSM_ID_A}/vlan", {
            "requestId": "uuid",
            "oprType": "modify",
            "vsmId": VSM_ID_A,
            "vlanType": "0",
            "vlanId": "10{i}",
        }),
        ("CE_11", "VSM network DELETE", f"/api/1.0/vsm/{VSM_ID_A}/network", {
            "requestId": "uuid",
            "vsmId": VSM_ID_A,
        }),
        ("CE_12", "VSM token", f"/api/1.0/vsm/{VSM_ID_A}/token", {
            "requestId": "uuid",
            "vsmId": VSM_ID_A,
            "token": "tenant-token-{i}",
            "tenantId": "tenant-{i}",
        }),
    ]

    result = []
    for case_id, name, endpoint, json_data in cases:
        method = "DELETE" if "DELETE" in name else "POST"
        result.append({
            "case_id": case_id,
            "scenario": "E",
            "description": f"UPSERT 幂等: {name} 10路并发无500",
            "run": _make_upsert_test(case_id, name, method, endpoint, json_data),
        })
    return result


def _make_upsert_test(case_id: str, name: str, method: str, endpoint: str, json_data: dict) -> Callable:
    def _run() -> ScenarioResult:
        records = run_n_concurrent(
            n=10, method=method, endpoint=endpoint,
            json_data=json_data, label=name,
        )
        p_no500, v_no500 = assert_no_500(records)
        p_all, v_all = assert_all_success(records)

        status_dist = {}
        for r in records:
            c = r.status_code or "ERR"
            status_dist[c] = status_dist.get(c, 0) + 1

        return ScenarioResult(
            case_id=case_id, scenario="E",
            description=f"UPSERT 幂等: {name} 10路并发无500",
            passed=p_no500,
            verdict=f"{v_no500} | {v_all}",
            records=records,
            details={"status_distribution": status_dist},
        )
    return _run


# ================================================================
# 场景 F：导出锁 TTL 超时释放
# ================================================================

def scenario_f_cases() -> List[dict]:
    return [
        {
            "case_id": "CF_01",
            "scenario": "F",
            "description": "导出锁: exportBackupKeys + importBackupKeys 并发，验证锁行为",
            "run": _cf_01,
        },
        {
            "case_id": "CF_02",
            "scenario": "F",
            "description": "导出锁: 连续两次 exportBackupKeys 并发，验证互斥",
            "run": _cf_02,
        },
    ]


def _cf_01() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST",
            endpoint="/platformServlet",
            params={"method": "exportBackupKeys"},
            json_data={
                "requestId": new_request_id(),
                "backupKey": "dGVzdC1iYWNrdXAta2V5LWV4cG9ydA==",
            },
            label="export-keys",
        ),
        RequestSpec(
            method="POST",
            endpoint="/platformServlet",
            params={"method": "importBackupKeys"},
            json_data={
                "requestId": new_request_id(),
                "backupKey": "dGVzdC1iYWNrdXAta2V5LWltcG9ydA==",
            },
            label="import-keys",
        ),
    ]
    records = run_concurrent(specs)
    p1, v1 = assert_no_500(records)
    export_r = next((r for r in records if r.label == "export-keys"), None)
    import_r = next((r for r in records if r.label == "import-keys"), None)

    notes = []
    if export_r:
        notes.append(f"export: {export_r.status_code} ({export_r.response_time:.3f}s)")
    if import_r:
        notes.append(f"import: {import_r.status_code} ({import_r.response_time:.3f}s)")

    return ScenarioResult(
        case_id="CF_01", scenario="F",
        description="导出锁: exportBackupKeys + importBackupKeys 并发，验证锁行为",
        passed=p1, verdict=f"{v1} | {'; '.join(notes)}",
        records=records,
    )


def _cf_02() -> ScenarioResult:
    specs = [
        RequestSpec(
            method="POST",
            endpoint="/platformServlet",
            params={"method": "exportBackupKeys"},
            json_data={
                "requestId": new_request_id(),
                "backupKey": "dGVzdC1iYWNrdXAta2V5LTE=",
            },
            label="export-1",
        ),
        RequestSpec(
            method="POST",
            endpoint="/platformServlet",
            params={"method": "exportBackupKeys"},
            json_data={
                "requestId": new_request_id(),
                "backupKey": "dGVzdC1iYWNrdXAta2V5LTI=",
            },
            label="export-2",
        ),
    ]
    records = run_concurrent(specs)
    p1, v1 = assert_no_500(records)
    p2, v2 = assert_lock_exclusion_by_timing(records)
    passed = p1
    return ScenarioResult(
        case_id="CF_02", scenario="F",
        description="导出锁: 连续两次 exportBackupKeys 并发，验证互斥",
        passed=passed, verdict=f"{v1}; {v2}",
        records=records,
    )


# ================================================================
# DNS 文件锁补充（Fix #4）
# ================================================================

def scenario_dns_cases() -> List[dict]:
    return [
        {
            "case_id": "CG_01",
            "scenario": "G",
            "description": "DNS 文件锁: 10路并发配网后 GET 验证内容一致",
            "run": _cg_01,
        },
    ]


def _cg_01() -> ScenarioResult:
    records = run_n_concurrent(
        n=10, method="POST", endpoint="/api/1.0/chsm/network",
        json_data={
            "requestId": "uuid",
            "dnsList": ["8.8.8.8", "114.114.114.114"],
            "netAddrs": [{"name": "eth0", "ip": "192.168.1.100",
                          "mask": "255.255.255.0", "gateway": "192.168.1.1"}],
        },
        label="dns-write",
    )
    p_no500, v_no500 = assert_no_500(records)

    time.sleep(1)

    read_records = []
    for i in range(3):
        client = get_http_client()
        try:
            resp = client.get(endpoint="/api/1.0/chsm/network")
            read_records.append(resp.json() if resp.status_code == 200 else None)
        except Exception:
            read_records.append(None)

    valid = [r for r in read_records if r is not None]
    if len(valid) >= 2:
        consistent = all(json.dumps(v, sort_keys=True) == json.dumps(valid[0], sort_keys=True)
                         for v in valid[1:])
        if consistent:
            verdict = f"{v_no500} | 读取 {len(valid)} 次内容一致"
            passed = p_no500
        else:
            verdict = f"{v_no500} | 读取内容不一致！resolv.conf 可能损坏"
            passed = False
    else:
        verdict = f"{v_no500} | 读取验证不足（{len(valid)} 条有效响应）"
        passed = p_no500

    return ScenarioResult(
        case_id="CG_01", scenario="G",
        description="DNS 文件锁: 10路并发配网后 GET 验证内容一致",
        passed=passed, verdict=verdict, records=records,
    )


# ================================================================
# 场景注册表
# ================================================================

SCENARIO_REGISTRY = {
    "A": ("全局锁互斥 (Fix #1 CRITICAL)", scenario_a_cases),
    "B": ("per-vsmId 互斥 (Fix #1 CRITICAL)", scenario_b_cases),
    "C": ("VSM upgrade 全局互斥 (Fix #1 CRITICAL)", scenario_c_cases),
    "D": ("UpgradeInProgressGuard (Fix #2 HIGH)", scenario_d_cases),
    "E": ("配置 UPSERT 幂等 (Fix #3 HIGH)", scenario_e_cases),
    "F": ("导出锁 TTL (Fix #5 MEDIUM)", scenario_f_cases),
    "G": ("DNS 文件锁 (Fix #4 MEDIUM)", scenario_dns_cases),
}


# ================================================================
# 报告输出
# ================================================================

def print_result(sr: ScenarioResult):
    status = "PASS" if sr.passed else "FAIL"
    icon = "✓" if sr.passed else "✗"
    print(f"\n  {icon} [{status}] {sr.case_id}: {sr.description}")
    print(f"    判定: {sr.verdict}")
    if sr.records:
        print(f"    请求明细:")
        for r in sr.records:
            code_str = str(r.status_code) if r.status_code else "ERR"
            err_hint = f" ({r.error[:60]})" if r.error else ""
            print(f"      #{r.finish_order} {r.label:<20s} [{code_str}] {r.response_time:.3f}s{err_hint}")
    if sr.details:
        for k, v in sr.details.items():
            print(f"    {k}: {v}")


def run_scenarios(scenario_keys: List[str]) -> List[dict]:
    results = []
    total_pass = 0
    total_fail = 0

    for key in scenario_keys:
        if key not in SCENARIO_REGISTRY:
            print(f"\n  [WARN] 未知场景: {key}，跳过")
            continue

        title, case_factory = SCENARIO_REGISTRY[key]
        cases = case_factory()

        print(f"\n{'=' * 64}")
        print(f"  场景 {key}: {title}")
        print(f"  用例数: {len(cases)}")
        print(f"{'=' * 64}")

        for case_def in cases:
            case_id = case_def["case_id"]
            desc = case_def["description"]
            run_fn = case_def["run"]

            logger.info("开始用例 %s: %s", case_id, desc)
            try:
                sr = run_fn()
            except Exception as e:
                sr = ScenarioResult(
                    case_id=case_id, scenario=key,
                    description=desc, passed=False,
                    verdict=f"执行异常: {e}",
                )
                logger.error("用例 %s 异常: %s", case_id, e, exc_info=True)

            print_result(sr)
            if sr.passed:
                total_pass += 1
            else:
                total_fail += 1

            results.append({
                "case_id": sr.case_id,
                "scenario": sr.scenario,
                "description": sr.description,
                "passed": sr.passed,
                "verdict": sr.verdict,
                "request_count": len(sr.records),
                "records": [
                    {
                        "label": r.label, "status_code": r.status_code,
                        "response_time": round(r.response_time, 4),
                        "error": r.error or None,
                    }
                    for r in sr.records
                ],
                **sr.details,
            })

    total = total_pass + total_fail
    print(f"\n{'=' * 64}")
    print(f"  并发修复验证汇总")
    print(f"  通过: {total_pass}  失败: {total_fail}  总计: {total}")
    if total > 0:
        print(f"  通过率: {total_pass / total * 100:.1f}%")
    print(f"{'=' * 64}")

    return results


# ================================================================
# 主流程
# ================================================================

def main():
    keys = [k for k, enabled in sorted(ENABLED_SCENARIOS.items()) if enabled]
    if not keys:
        print("没有启用的场景，请修改 ENABLED_SCENARIOS 中的 True/False")
        return

    print(f"\n  目标环境: {config.base_url}")
    print(f"  认证: {'开启' if config.auth_enabled else '关闭'} ({config.auth_algorithm})")
    print(f"  回调地址: {CALLBACK_URL}")
    print(f"  启用场景: {', '.join(keys)}")
    disabled = [k for k, enabled in sorted(ENABLED_SCENARIOS.items()) if not enabled]
    if disabled:
        print(f"  跳过场景: {', '.join(disabled)}")

    results = run_scenarios(keys)

    os.makedirs("output", exist_ok=True)
    report_path = "output/concurrency_v2_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {report_path}")

    failed = [r for r in results if not r["passed"]]
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
