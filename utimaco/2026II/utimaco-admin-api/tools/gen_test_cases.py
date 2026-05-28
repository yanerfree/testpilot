"""
补齐测试用例 Excel — 根据 test_data.xlsx 中的测试数据行，
生成缺失的测试用例到 华为云密码机二期-接口测试用例.xlsx
"""

import json
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ── 文件路径 ──────────────────────────────────────────
TC_FILE = "/home/dreamer/utimaco/2026II/华为云密码机二期-接口测试用例.xlsx"
TD_FILE = "/home/dreamer/utimaco/2026II/utimaco-admin-api/data/test_data.xlsx"
TC_SHEET = "管理接口"

# ── 测试用例列 ────────────────────────────────────────
TC_COLS = [
    "用例ID", "测试模块", "接口名称", "接口路径", "请求方法",
    "测试场景", "测试类型", "优先级", "前置条件",
    "请求头(Headers)", "请求参数(Query/Body)/步骤",
    "预期响应状态码", "预期响应", "预期结果描述",
    "测试状态", "执行人", "执行时间", "缺陷ID", "备注",
]

# ── 认证头模板 ────────────────────────────────────────
AUTH_HEADER_TRUSTED = """{
  "CHSM-AuthPK": "<公钥指纹>",
  "CHSM-SignatureAlg": "SHA256withRSA",
  "CHSM-Signature": "<签名值>"
}"""
AUTH_HEADER_GUEST = "无需认证头（guest接口）"
AUTH_HEADER_NONE = "无认证头"
AUTH_HEADER_TENANT = """{
  "CHSM-AuthPK": "<公钥指纹>",
  "CHSM-SignatureAlg": "SHA256withRSA",
  "CHSM-Signature": "<签名值>"
}"""

# ── 模块映射 ──────────────────────────────────────────
MODULE_MAP = {
    "CHSM": "CHSM配置管理",
    "VSM": "VSM配置管理",
    "GUEST": "Guest接口(无认证)",
    "PK_RSA": "授权配置(RSA)",
    "PK_SM2": "授权配置(SM2)",
    "FS": "FileServer文件服务",
    "TENANT": "租户密评",
}

# ── 接口名称映射(从 description 中的英文函数名到完整名称) ──
INTERFACE_NAME_MAP = {
    "getCHSMInfo": "getCHSMInfo-获取CHSM详细信息",
    "getCHSMStatus": "getCHSMStatus-获取CHSM运行状态",
    "getCHSMAllStatus": "getCHSMAllStatus-获取CHSM所有状态",
    "configCHSMNet": "configCHSMNet-配置CHSM网络",
    "configCHSMNtp": "configCHSMNtp-配置NTP服务器",
    "configCHSMUploadAddress": "configCHSMUploadAddress-配置影像上传地址",
    "configSyslogAddr": "configSyslogAddr-配置日志上传地址",
    "configCHSMAlarmAddress": "configCHSMAlarmAddress-配置告警上传地址",
    "configCHSMToken": "configCHSMToken-配置云平台Token",
    "configCHSMMOOCAddress": "configCHSMMOOCAddress-配置MO OC对接信息",
    "exportCHSM": "exportCHSM-导出CHSM影像",
    "importCHSM": "importCHSM-导入CHSM影像",
    "upgradeCHSM": "upgradeCHSM-升级CHSM",
    "restartCHSM": "restartCHSM-重启CHSM",
    "backupCHSM": "backupCHSM-备份CHSM",
    "restoreCHSM": "restoreCHSM-恢复CHSM",
    "getCHSMDebugInfo": "getCHSMDebugInfo-获取调试信息",
    "getCHSMDeviceInfo": "getCHSMDeviceInfo-获取设备信息",
    "getVSMInfo": "getVSMInfo-获取VSM详细信息",
    "getVSMStatus": "getVSMStatus-获取VSM运行状态",
    "configVSMNet": "configVSMNet-配置VSM网络",
    "configVSMToken": "configVSMToken-配置VSM Token",
    "exportVSM": "exportVSM-导出VSM影像",
    "importVSM": "importVSM-导入VSM影像",
    "startVSM": "startVSM-启动VSM",
    "stopVSM": "stopVSM-停止VSM",
    "restartVSM": "restartVSM-重启VSM",
    "resetVSM": "resetVSM-重置VSM",
    "upgradeVSM": "upgradeVSM-升级VSM",
    "configCHSMPk": "configCHSMPk-配置认证公钥",
    "getCHSMPk": "getCHSMPk-获取认证公钥指纹",
    "clearCHSMPk": "clearCHSMPk-清空认证公钥",
    # Section 9 租户密评
    "authPK": "authPK-配置公钥指纹",
    "getAuthPKFingerprints": "getAuthPKFingerprints-获取公钥指纹",
    "cleanPK": "cleanPK-清除公钥指纹",
    "initKey": "initKey-初始化本地主密钥",
    "exportBackupKeys": "exportBackupKeys-导出数据影像",
    "importBackupKeys": "importBackupKeys-导入数据影像",
    "doVsmInit": "doVsmInit-初始化VSM",
    "getStatus": "getStatus-获取VSM运行状态",
    # Section 8
    "上传镜像文件": "uploadImage-上传镜像文件",
    "获取镜像描述": "getImageInfo-获取镜像文件描述信息",
    "下载文件": "downloadFile-下载文件",
    "删除镜像文件": "deleteImage-删除镜像文件",
}

# ── VSM 场景步骤: case_id -> 接口名称 覆盖 ─────────────
# 部分 VSM 测试数据在 SCN_VSM 场景内, case_id 前缀无法直接映射接口
VSM_SETUP_MAP = {
    "VSM_SETUP_001": "getVSMInfo-获取VSM详细信息",
}


def get_module(case_id: str) -> str:
    for prefix, mod in MODULE_MAP.items():
        if case_id.startswith(prefix + "_"):
            return mod
    if case_id.startswith("PK_RSA"):
        return MODULE_MAP["PK_RSA"]
    if case_id.startswith("PK_SM2"):
        return MODULE_MAP["PK_SM2"]
    return "未分类"


def extract_interface_name(desc: str, case_id: str, method: str = "POST") -> str:
    """从 description 中提取接口名称"""
    # 先匹配英文函数名
    m = re.match(r"^([a-zA-Z]+)", desc)
    if m:
        fn = m.group(1)
        if fn in INTERFACE_NAME_MAP:
            return INTERFACE_NAME_MAP[fn]

    # 中文前缀匹配 (Section 8)
    for cn_key in ["上传镜像文件", "获取镜像描述", "下载文件", "删除镜像文件"]:
        if desc.startswith(cn_key):
            return INTERFACE_NAME_MAP[cn_key]

    # VSM_SETUP 特殊
    if case_id in VSM_SETUP_MAP:
        return VSM_SETUP_MAP[case_id]

    # PK_RSA/PK_SM2 场景步骤 — 从 description + method 推断
    if case_id.startswith("PK_RSA") or case_id.startswith("PK_SM2"):
        return _pk_interface_from_desc(desc, method)

    return desc.split(" ")[0] if " " in desc else desc


def _pk_interface_from_desc(desc: str, method: str = "POST") -> str:
    """PK 场景: 从描述推断接口名称"""
    d = desc.lower()
    if "trusted" in d or "getCHSMInfo" in desc or "403" in desc:
        return "getCHSMInfo-获取CHSM详细信息"
    if ("清空" in d or "清除" in d) and "后" not in d:
        return "clearCHSMPk-清空认证公钥"
    if "查询" in d or "验证" in d or "指纹" in d or "确认" in d:
        return "getCHSMPk-获取认证公钥指纹"
    if "配置" in d or "追加" in d or "公钥" in d or "去重" in d or "恢复" in d or "覆盖" in d:
        return "configCHSMPk-配置认证公钥"
    # _E 系列根据 method 判断
    if method == "GET":
        return "getCHSMPk-获取认证公钥指纹"
    if method == "DELETE":
        return "clearCHSMPk-清空认证公钥"
    return "configCHSMPk-配置认证公钥"


def get_auth_type(case_id: str, sheet: str) -> str:
    if sheet == "guest":
        return "guest"
    if sheet in ("pk_rsa", "pk_sm2"):
        return "pk"
    if sheet == "section8_9":
        if case_id.startswith("FS_"):
            return "fileserver"
        return "tenant"
    return "trusted"


def get_headers(auth_type: str, desc: str, method: str, case_id: str) -> str:
    if auth_type == "guest":
        if "不带认证" in desc or "trusted" in desc.lower():
            return AUTH_HEADER_NONE
        return AUTH_HEADER_GUEST
    if auth_type == "trusted":
        return AUTH_HEADER_TRUSTED
    if auth_type == "pk":
        d = desc.lower()
        if "首次" in d:
            return "首次无需认证头（guest）"
        if "查询" in d or "验证" in d or "确认" in d or "指纹" in d:
            return AUTH_HEADER_GUEST
        if "清空" in d or "清除" in d:
            if method == "DELETE":
                return AUTH_HEADER_TRUSTED
            return AUTH_HEADER_GUEST
        if "trusted" in d or "403" in desc:
            return AUTH_HEADER_NONE
        return AUTH_HEADER_TRUSTED
    if auth_type == "fileserver":
        return "token认证"
    if auth_type == "tenant":
        return AUTH_HEADER_TENANT
    return AUTH_HEADER_TRUSTED


def get_precondition(auth_type: str, desc: str, case_id: str,
                     scenario_id: Optional[str], step: Optional[str]) -> str:
    scenario_id = _clean(scenario_id)
    step = _clean(step)
    if auth_type == "guest":
        if "VSM" in case_id and "vsmId" in desc:
            return "CHSM已运行"
        return "CHSM已正常运行"
    if auth_type == "trusted":
        base = "CHSM已正常运行，已配置公钥"
        if "VSM" in case_id:
            base = "CHSM已运行，至少有1个VSM，已配置公钥"
        if scenario_id:
            base += f"\n场景 {scenario_id} step {step or '?'}"
        return base
    if auth_type == "pk":
        if scenario_id:
            return f"场景 {scenario_id} 按步骤顺序执行"
        return "密码机上已配置公钥"
    if auth_type == "fileserver":
        return "FileServer 服务可达"
    if auth_type == "tenant":
        if scenario_id:
            return f"场景 {scenario_id} step {step or '?'} 按步骤执行"
        return "VSM 已初始化"
    return "CHSM已正常运行"


def format_request_params(json_data, params, method: str) -> str:
    """格式化请求参数"""
    if json_data:
        if isinstance(json_data, str):
            try:
                obj = json.loads(json_data)
                return json.dumps(obj, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                return json_data
        elif isinstance(json_data, dict):
            return json.dumps(json_data, ensure_ascii=False, indent=2)
    if params:
        if isinstance(params, str):
            return params
        elif isinstance(params, dict):
            return "&".join(f"{k}={v}" for k, v in params.items())
    return ""


def build_expected_response(status: int) -> str:
    if status == 200:
        return '{\n  "status": 200,\n  "message": "success",\n  "timestamp": "<ISO8601>",\n  "requestId": "<echo-back>",\n  "costMillis": "<int>"\n}'
    elif status == 400:
        return '{\n  "status": 400,\n  "message": "<参数错误描述>",\n  "timestamp": "<ISO8601>",\n  "requestId": "<echo-back>"\n}'
    elif status == 403:
        return '{\n  "status": 403,\n  "message": "认证失败",\n  "timestamp": "<ISO8601>"\n}'
    else:
        return f'{{\n  "status": {status}\n}}'


def build_expected_desc(status: int, desc: str) -> str:
    if status == 200:
        if "查询" in desc or "验证" in desc or "获取" in desc:
            return "返回200，结果符合预期"
        return "返回200，操作成功"
    elif status == 400:
        detail = ""
        if "缺" in desc:
            m = re.search(r"缺少?(\w+)", desc)
            if m:
                detail = f"，缺少{m.group(1)}参数"
        elif "空" in desc:
            detail = "，参数为空"
        elif "非法" in desc or "无效" in desc:
            detail = "，参数格式非法"
        elif "超限" in desc:
            detail = "，超出限制"
        return f"返回400，参数校验失败{detail}"
    elif status == 403:
        return "返回403，认证失败"
    return f"返回{status}"


def get_test_type(status: int, desc: str, step_type: Optional[str]) -> str:
    step_type = _clean(step_type)
    if step_type in ("setup", "teardown", "verify"):
        return "场景步骤"
    if status != 200:
        return "异常测试"
    if any(kw in desc for kw in ["超限", "失败", "非法", "无效", "错误"]):
        return "异常测试"
    return "功能测试"


def get_priority(status: int, step_type: Optional[str]) -> str:
    step_type = _clean(step_type)
    if step_type in ("setup", "teardown", "verify"):
        return "P0"
    if status == 200:
        return "P0"
    return "P1"


def _clean(val) -> Optional[str]:
    """将 None/nan/'nan'/'' 统一为 None"""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "nan", "None"):
        return None
    return s


def get_remark(enabled: str, scenario_id: Optional[str],
               step: Optional[str], step_type: Optional[str],
               ref_case_id: Optional[str]) -> str:
    parts = []
    enabled = _clean(enabled)
    if enabled and enabled.lower() in ("no", "false", "0"):
        parts.append("enabled=no(自动化暂不执行)")
    scenario_id = _clean(scenario_id)
    step = _clean(step)
    step_type = _clean(step_type)
    ref_case_id = _clean(ref_case_id)
    if scenario_id:
        parts.append(f"场景:{scenario_id}")
    if step:
        parts.append(f"step:{step}")
    if step_type:
        parts.append(f"type:{step_type}")
    if ref_case_id:
        parts.append(f"关联:{ref_case_id}")
    return "；".join(parts) if parts else None


def main():
    # 1. 读取现有测试用例
    tc_df = pd.read_excel(TC_FILE, sheet_name=TC_SHEET, dtype=str)
    tc_df = tc_df.replace({np.nan: None})
    existing_ids = set(tc_df["用例ID"].dropna().tolist())
    print(f"现有测试用例: {len(existing_ids)} 条")

    # 2. 读取现有用例建立 prefix → 接口信息 映射
    prefix_map = {}
    for _, r in tc_df.iterrows():
        cid = r["用例ID"]
        if not cid:
            continue
        prefix = re.sub(r"_\d+[A-Z]?$", "", cid)
        if prefix not in prefix_map:
            prefix_map[prefix] = {
                "接口名称": r["接口名称"],
                "接口路径": r["接口路径"],
                "请求方法": r["请求方法"],
                "测试模块": r["测试模块"],
            }

    # 3. 遍历所有测试数据 sheet，生成缺失的测试用例
    new_rows = []
    for sheet in ["trusted", "guest", "pk_rsa", "pk_sm2", "section8_9"]:
        td_df = pd.read_excel(TD_FILE, sheet_name=sheet, dtype=str)
        td_df = td_df.replace({np.nan: None})

        for _, r in td_df.iterrows():
            case_id = r.get("case_id")
            if not case_id or case_id in existing_ids:
                continue

            desc = str(r.get("description", "") or "")
            endpoint = str(r.get("endpoint", "") or "")
            method = str(r.get("method", "") or "")
            json_data = r.get("json_data")
            params = r.get("params")
            expected_status = int(r.get("expected_status", 0) or 0)
            enabled = r.get("enabled")
            scenario_id = r.get("scenario_id")
            step = r.get("step")
            step_type = r.get("step_type")
            ref_case_id = r.get("ref_case_id")

            auth_type = get_auth_type(case_id, sheet)
            module = get_module(case_id)

            # 接口名称: 优先从 description 提取，其次从 prefix_map 查找
            iface_name = extract_interface_name(desc, case_id, method)
            td_prefix = re.sub(r"_T\d+$", "", re.sub(r"_E\d+$", "", re.sub(r"_\d+[A-Z]?$", "", case_id)))
            if td_prefix in prefix_map and iface_name == desc.split(" ")[0]:
                iface_name = prefix_map[td_prefix]["接口名称"]

            headers = get_headers(auth_type, desc, method, case_id)
            precondition = get_precondition(auth_type, desc, case_id, scenario_id, step)
            req_params = format_request_params(json_data, params, method)
            expected_resp = build_expected_response(expected_status)
            expected_desc = build_expected_desc(expected_status, desc)
            test_type = get_test_type(expected_status, desc, step_type)
            priority = get_priority(expected_status, step_type)
            remark = get_remark(enabled, scenario_id, step, step_type, ref_case_id)

            row = {
                "用例ID": case_id,
                "测试模块": module,
                "接口名称": iface_name,
                "接口路径": endpoint,
                "请求方法": method,
                "测试场景": desc,
                "测试类型": test_type,
                "优先级": priority,
                "前置条件": precondition,
                "请求头(Headers)": headers,
                "请求参数(Query/Body)/步骤": req_params,
                "预期响应状态码": str(expected_status),
                "预期响应": expected_resp,
                "预期结果描述": expected_desc,
                "测试状态": None,
                "执行人": None,
                "执行时间": None,
                "缺陷ID": None,
                "备注": remark,
            }
            new_rows.append(row)

    print(f"新增测试用例: {len(new_rows)} 条")

    if not new_rows:
        print("无需补充")
        return

    # 4. 合并并写入
    new_df = pd.DataFrame(new_rows, columns=TC_COLS)
    merged = pd.concat([tc_df[TC_COLS], new_df], ignore_index=True)

    # 按模块和用例ID排序
    module_order = {
        "授权配置": 0, "授权配置(RSA)": 1, "授权配置(SM2)": 2,
        "CHSM配置管理": 3, "VSM配置管理": 4,
        "Guest接口(无认证)": 5,
        "FileServer文件服务": 6, "租户密评": 7,
    }
    merged["_sort_mod"] = merged["测试模块"].map(lambda x: module_order.get(x, 99))
    merged = merged.sort_values(["_sort_mod", "用例ID"]).drop(columns=["_sort_mod"])
    merged = merged.reset_index(drop=True)

    with pd.ExcelWriter(TC_FILE, engine="openpyxl") as writer:
        merged.to_excel(writer, sheet_name=TC_SHEET, index=False)

    total = len(merged)
    print(f"\n已保存: {TC_FILE}")
    print(f"总计: {total} 条测试用例 (原 {len(existing_ids)} + 新 {len(new_rows)})")

    # 5. 统计
    print("\n=== 按模块统计 ===")
    for mod in sorted(merged["测试模块"].unique(), key=lambda x: module_order.get(x, 99)):
        cnt = len(merged[merged["测试模块"] == mod])
        print(f"  {mod:25s}: {cnt} 条")

    print("\n=== 按测试类型统计 ===")
    for tt in merged["测试类型"].unique():
        cnt = len(merged[merged["测试类型"] == tt])
        print(f"  {tt:15s}: {cnt} 条")


if __name__ == "__main__":
    main()
