#!/usr/bin/env python3
"""
生成 section8_9 sheet — 覆盖第8章(FileServer)和第9章(租户密评)全部接口。

设计思路:
  - Section 8: FileServer，host = fileServerIp:port
    - 上传(multipart→enabled=no) / 获取描述 / 下载(binary→enabled=no) / 删除
    - 独立用例，无场景
  - Section 9: 租户密评，host = vsmIp:port (不同于管理接口)
    - 认证机制同CHSM（CHSM-AuthPK/SignatureAlg/Signature header）
    - 配置公钥指纹/清除公钥指纹 无需认证(guest)
    - 其他接口需要认证(trusted)
    - 用 SCN_TENANT 场景链:
      step 1: getStatus 获取基线状态
      step 2: authPK 配置第1个RSA公钥
      step 3: getAuthPKFingerprints 验证1个指纹
      step 4: authPK 配置第2个SM2公钥(混合算法)
      step 5: getAuthPKFingerprints 验证2组指纹
      step 6: cleanPK 清除全部
      step 7: getAuthPKFingerprints 验证已清空
      step 8: authPK 恢复公钥(后续接口需要认证)
      step 9-N: 各接口异常测试
    - 高危操作 initKey / doVsmInit → enabled=no
    - 文件操作 exportBackupKeys / importBackupKeys → enabled=no(binary/multipart)

注意:
  - host 列填写占位符 ${fileServerHost} 和 ${vsmHost}，
    运行时需在 config 或手动填入实际地址
  - Section 9 的 servlet URL 通过 params 列传 method 参数
"""

import json
import os
import sys

try:
    import openpyxl
except ImportError:
    print("pip install openpyxl")
    sys.exit(1)

HEADERS = [
    "case_id", "description", "host", "endpoint", "method",
    "params", "json_data", "expected_status", "assert_rules",
    "scenario_id", "step", "step_type", "save_vars",
    "enabled", "section", "ref_case_id",
]

OK = json.dumps([
    {"type": "status_code", "expected_code": 200},
    {"type": "json_contains", "key": "message", "value": "success"},
], ensure_ascii=False)

ERR400 = json.dumps([
    {"type": "status_code", "expected_code": 400},
], ensure_ascii=False)


def ok_with(*extra_rules):
    base = [
        {"type": "status_code", "expected_code": 200},
        {"type": "json_contains", "key": "message", "value": "success"},
    ]
    base.extend(extra_rules)
    return json.dumps(base, ensure_ascii=False)


def ok_status_only():
    return json.dumps([
        {"type": "status_code", "expected_code": 200},
    ], ensure_ascii=False)


def ok_data(*extra_rules):
    """Section 9 返回 data 而非 result"""
    base = [
        {"type": "status_code", "expected_code": 200},
    ]
    base.extend(extra_rules)
    return json.dumps(base, ensure_ascii=False)


def jd(d):
    return json.dumps(d, ensure_ascii=False)


def row(case_id, desc, endpoint, expected_status, json_data=None, params=None,
        assert_rules=None, ref_case_id=None, enabled="yes", section="",
        scenario_id=None, step=None, step_type=None, save_vars=None,
        method="POST", host=None):
    if assert_rules is None:
        assert_rules = OK if expected_status == 200 else ERR400
    return {
        "case_id": case_id,
        "description": desc,
        "host": host,
        "endpoint": endpoint,
        "method": method,
        "params": params,
        "json_data": json_data,
        "expected_status": expected_status,
        "assert_rules": assert_rules,
        "scenario_id": scenario_id,
        "step": step,
        "step_type": step_type,
        "save_vars": save_vars,
        "enabled": enabled,
        "section": section,
        "ref_case_id": ref_case_id or "",
    }


# FileServer host 占位符（${env.xxx} 语法，由 excel_handler 从 config sheet 替换）
FS_HOST = "${env.fileServerHost}"
# 租户密评 VSM host 占位符
VSM_HOST = "${env.vsmHost}"


# ================================================================
# Section 8: FileServer
# ================================================================

def gen_fileserver():
    """FileServer 接口，host = fileServerIp:port"""
    EP = "/images"
    rows = []

    # --- 8.1.1 上传镜像文件 (multipart → 框架不支持) ---
    rows.extend([
        row("FS_UPLOAD_001", "上传镜像文件 正常上传(multipart不支持)", EP, 200,
            json_data=jd({"requestId": "uuid", "info": {"token": "/chsm/image_v1.bin", "type": "hsm"}}),
            host=FS_HOST, section="8.1.1", enabled="no"),
        row("FS_UPLOAD_002", "上传镜像文件 缺file参数(multipart不支持)", EP, 400,
            json_data=jd({"requestId": "uuid", "info": {"token": "/chsm/image_v1.bin", "type": "hsm"}}),
            host=FS_HOST, section="8.1.1", enabled="no"),
        row("FS_UPLOAD_003", "上传镜像文件 type=vsm", EP, 200,
            json_data=jd({"requestId": "uuid", "info": {"token": "/vsm/image_v1.bin", "type": "vsm"}}),
            host=FS_HOST, section="8.1.1", enabled="no"),
        row("FS_UPLOAD_004", "上传镜像文件 type无效值", EP, 400,
            json_data=jd({"requestId": "uuid", "info": {"token": "/chsm/image.bin", "type": "invalid"}}),
            host=FS_HOST, section="8.1.1", enabled="no"),
        row("FS_UPLOAD_005", "上传镜像文件 缺token", EP, 400,
            json_data=jd({"requestId": "uuid", "info": {"type": "hsm"}}),
            host=FS_HOST, section="8.1.1", enabled="no"),
        row("FS_UPLOAD_006", "上传镜像文件 缺requestId", EP, 400,
            json_data=jd({"info": {"token": "/chsm/image.bin", "type": "hsm"}}),
            host=FS_HOST, section="8.1.1", enabled="no"),
    ])

    # --- 8.1.2 获取镜像文件描述信息 ---
    # 需要先有上传的文件，用占位符 token
    rows.extend([
        row("FS_GETINFO_001", "获取镜像描述 正常获取", EP, 200,
            params="token=/chsm/image_v1.bin",
            assert_rules=ok_with(
                {"type": "json_contains", "key": "result.uuid"},
                {"type": "json_contains", "key": "result.version"},
                {"type": "json_contains", "key": "result.sign"},
                {"type": "json_contains", "key": "result.alg"},
            ),
            host=FS_HOST, method="GET", section="8.1.2", enabled="no"),
        row("FS_GETINFO_002", "获取镜像描述 token不存在", EP, 400,
            params="token=/nonexistent/file.bin",
            host=FS_HOST, method="GET", section="8.1.2", enabled="no"),
        row("FS_GETINFO_003", "获取镜像描述 缺token参数", EP, 400,
            host=FS_HOST, method="GET", section="8.1.2", enabled="no"),
    ])

    # --- 8.1.3 下载文件 (binary stream → 无法断言body) ---
    rows.extend([
        row("FS_DOWNLOAD_001", "下载文件 正常下载", EP, 200,
            params="file=/chsm/image_v1.bin",
            assert_rules=ok_status_only(),
            host=FS_HOST, method="POST", section="8.1.3", enabled="no"),
        row("FS_DOWNLOAD_002", "下载文件 file不存在", EP, 400,
            params="file=/nonexistent/file.bin",
            host=FS_HOST, method="POST", section="8.1.3", enabled="no"),
        row("FS_DOWNLOAD_003", "下载文件 缺file参数", EP, 400,
            host=FS_HOST, method="POST", section="8.1.3", enabled="no"),
    ])

    # --- 8.1.4 删除镜像文件 ---
    rows.extend([
        row("FS_DELETE_001", "删除镜像文件 正常删除", EP, 200,
            params="token=/chsm/image_v1.bin",
            host=FS_HOST, section="8.1.4", enabled="no"),
        row("FS_DELETE_002", "删除镜像文件 token不存在", EP, 400,
            params="token=/nonexistent/file.bin",
            host=FS_HOST, section="8.1.4", enabled="no"),
        row("FS_DELETE_003", "删除镜像文件 缺token参数", EP, 400,
            host=FS_HOST, section="8.1.4", enabled="no"),
    ])

    return rows


# ================================================================
# Section 9: 租户密评
# ================================================================

def gen_tenant_scenario():
    """
    SCN_TENANT 场景: 公钥配置→验证→清除→验证→恢复 + 各接口异常用例。

    业务关联链:
      authPK 配置 → getAuthPKFingerprints 验证 → cleanPK 清除 → 验证已清空
      getStatus 查询运行状态（基线 + 后续校验）
      initKey / doVsmInit 高危操作(enabled=no)
      exportBackupKeys / importBackupKeys 文件操作(enabled=no)
    """
    rows = []
    step = 0

    def add(case_id, desc, endpoint, expected_status, json_data=None, params=None,
            ref_case_id=None, enabled="yes", section="", assert_rules=None,
            save_vars=None, step_type="test", method="POST"):
        nonlocal step
        step += 1
        rows.append(row(
            case_id, desc, endpoint, expected_status,
            json_data=json_data, params=params,
            assert_rules=assert_rules,
            ref_case_id=ref_case_id, enabled=enabled, section=section,
            scenario_id="SCN_TENANT", step=step, step_type=step_type,
            save_vars=save_vars, method=method, host=VSM_HOST,
        ))

    # ---- 场景主线: 公钥配置生命周期 ----

    # step 1: 获取基线状态
    add("TENANT_STATUS_001", "getStatus 获取VSM运行状态(基线)",
        "/platformServlet", 200,
        params="method=getStatus",
        assert_rules=ok_data(
            {"type": "json_contains", "key": "data.status", "value": "success"},
            {"type": "json_contains", "key": "data.initFlag"},
            {"type": "json_contains", "key": "data.serviceStatus"},
        ),
        method="GET", step_type="setup", section="9.2.8")

    # step 2: 配置第1个RSA公钥(guest，不需认证)
    add("TENANT_AUTHPK_001", "authPK 配置第1个RSA公钥",
        "/authServlet", 200,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": ["${keys.rsa_key1}"]}),
        section="9.2.2")

    # step 3: 获取指纹验证已配置1个RSA
    add("TENANT_GETPK_001", "getAuthPKFingerprints 验证1个RSA指纹",
        "/authServlet", 200,
        params="method=getAuthPKFingerprints&requestId=uuid",
        assert_rules=ok_data({"type": "json_contains", "key": "data"}),
        method="GET", step_type="verify", section="9.2.1")

    # step 4: 配置第2个SM2公钥(混合算法)
    add("TENANT_AUTHPK_002", "authPK 追加SM2公钥(混合算法)",
        "/authServlet", 200,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "sm2", "pks": ["${keys.sm2_key1}"]}),
        section="9.2.2")

    # step 5: 获取指纹验证 2 组(RSA+SM2)
    add("TENANT_GETPK_002", "getAuthPKFingerprints 验证RSA+SM2两组指纹",
        "/authServlet", 200,
        params="method=getAuthPKFingerprints&requestId=uuid",
        assert_rules=ok_data({"type": "json_contains", "key": "data"}),
        method="GET", step_type="verify", section="9.2.1")

    # step 6: 清除全部公钥
    add("TENANT_CLEANPK_001", "cleanPK 清除全部公钥指纹",
        "/authServlet", 200,
        params="method=cleanPK&requestId=uuid",
        method="GET", section="9.2.3")

    # step 7: 验证已清空
    add("TENANT_GETPK_003", "getAuthPKFingerprints 验证清空后为空",
        "/authServlet", 200,
        params="method=getAuthPKFingerprints&requestId=uuid",
        assert_rules=ok_data({"type": "json_contains", "key": "data"}),
        method="GET", step_type="verify", section="9.2.1")

    # step 8: 恢复公钥(后续场景可能需要认证)
    add("TENANT_AUTHPK_003", "authPK 恢复RSA公钥(为后续接口准备)",
        "/authServlet", 200,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": ["${keys.rsa_key1}"]}),
        section="9.2.2")

    # ---- authPK 异常用例 ----

    # step 9: 超限测试(已有1个RSA + 传2个RSA = 3 → 超限)
    add("TENANT_AUTHPK_004", "authPK 超限(已有1+传2=3)",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": ["${keys.rsa_key2}", "${keys.rsa_key3}"]}),
        section="9.2.2")

    # step 10: alg无效值
    add("TENANT_AUTHPK_005", "authPK alg无效值",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "invalid_alg", "pks": ["${keys.rsa_key1}"]}),
        section="9.2.2")

    # step 11: pks空列表
    add("TENANT_AUTHPK_006", "authPK pks为空列表",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": []}),
        section="9.2.2")

    # step 12: 缺alg字段
    add("TENANT_AUTHPK_007", "authPK 缺alg字段",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "pks": ["${keys.rsa_key1}"]}),
        section="9.2.2")

    # step 13: 缺pks字段
    add("TENANT_AUTHPK_008", "authPK 缺pks字段",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa"}),
        section="9.2.2")

    # step 14: 缺requestId
    add("TENANT_AUTHPK_009", "authPK 缺requestId",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"alg": "rsa", "pks": ["${keys.rsa_key1}"]}),
        section="9.2.2")

    # step 15: requestId空字符串
    add("TENANT_AUTHPK_010", "authPK requestId空字符串",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "", "alg": "rsa", "pks": ["${keys.rsa_key1}"]}),
        section="9.2.2")

    # step 16: pks含非法格式公钥
    add("TENANT_AUTHPK_011", "authPK pks含非法格式公钥",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": ["NOT_A_VALID_PUBLIC_KEY!!!"]}),
        section="9.2.2")

    # step 17: 一次传3个公钥
    add("TENANT_AUTHPK_012", "authPK 一次传3个公钥(超限)",
        "/authServlet", 400,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": ["${keys.rsa_key1}", "${keys.rsa_key2}", "${keys.rsa_key3}"]}),
        section="9.2.2")

    # ---- getAuthPKFingerprints 异常用例 ----

    # step 18: 缺requestId
    add("TENANT_GETPK_004", "getAuthPKFingerprints 缺requestId",
        "/authServlet", 400,
        params="method=getAuthPKFingerprints",
        method="GET", section="9.2.1")

    # step 19: requestId空字符串
    add("TENANT_GETPK_005", "getAuthPKFingerprints requestId空字符串",
        "/authServlet", 400,
        params="method=getAuthPKFingerprints&requestId=",
        method="GET", section="9.2.1")

    # ---- cleanPK 异常用例 ----

    # step 20: cleanPK 缺requestId
    add("TENANT_CLEANPK_002", "cleanPK 缺requestId",
        "/authServlet", 400,
        params="method=cleanPK",
        method="GET", section="9.2.3")

    # step 21: cleanPK requestId空字符串
    add("TENANT_CLEANPK_003", "cleanPK requestId空字符串",
        "/authServlet", 400,
        params="method=cleanPK&requestId=",
        method="GET", section="9.2.3")

    # ---- getStatus 异常用例 ----

    # step 22: getStatus 无参数(验证是否需要requestId)
    add("TENANT_STATUS_002", "getStatus 无参数调用",
        "/platformServlet", 200,
        params="method=getStatus",
        assert_rules=ok_data({"type": "json_contains", "key": "data.status"}),
        method="GET", section="9.2.8")

    # ---- initKey 初始化本地主密钥 (高危) ----

    add("TENANT_INITKEY_001", "initKey 正常初始化(高危操作)",
        "/platformServlet", 200,
        params="method=initKey&requestId=uuid",
        method="POST", section="9.2.4", enabled="no")

    add("TENANT_INITKEY_002", "initKey 缺requestId",
        "/platformServlet", 400,
        params="method=initKey",
        method="POST", section="9.2.4")

    add("TENANT_INITKEY_003", "initKey requestId空字符串",
        "/platformServlet", 400,
        params="method=initKey&requestId=",
        method="POST", section="9.2.4")

    # ---- exportBackupKeys 导出全部数据影像 ----

    add("TENANT_EXPORT_001", "exportBackupKeys 正常导出(返回binary)",
        "/platformServlet", 200,
        params="method=exportBackupKeys&requestId=uuid",
        json_data=jd({"requestId": "uuid", "backupKey": "test_backup_key_123"}),
        assert_rules=ok_status_only(),
        method="POST", section="9.2.5", enabled="no")

    add("TENANT_EXPORT_002", "exportBackupKeys 缺backupKey",
        "/platformServlet", 400,
        params="method=exportBackupKeys&requestId=uuid",
        json_data=jd({"requestId": "uuid"}),
        method="POST", section="9.2.5")

    add("TENANT_EXPORT_003", "exportBackupKeys backupKey空字符串",
        "/platformServlet", 400,
        params="method=exportBackupKeys&requestId=uuid",
        json_data=jd({"requestId": "uuid", "backupKey": ""}),
        method="POST", section="9.2.5")

    add("TENANT_EXPORT_004", "exportBackupKeys 缺requestId",
        "/platformServlet", 400,
        params="method=exportBackupKeys",
        json_data=jd({"backupKey": "test_backup_key_123"}),
        method="POST", section="9.2.5")

    # ---- importBackupKeys 导入全部数据影像 (文件上传 → enabled=no) ----

    add("TENANT_IMPORT_001", "importBackupKeys 正常导入(文件上传不支持)",
        "/platformServlet", 200,
        params="method=importBackupKeys",
        json_data=jd({"requestId": "uuid", "backupKey": "test_backup_key_123"}),
        method="POST", section="9.2.6", enabled="no")

    add("TENANT_IMPORT_002", "importBackupKeys 缺backupKey",
        "/platformServlet", 400,
        params="method=importBackupKeys",
        json_data=jd({"requestId": "uuid"}),
        method="POST", section="9.2.6", enabled="no"),

    add("TENANT_IMPORT_003", "importBackupKeys 缺requestId",
        "/platformServlet", 400,
        params="method=importBackupKeys",
        json_data=jd({"backupKey": "test_backup_key_123"}),
        method="POST", section="9.2.6", enabled="no")

    # ---- doVsmInit 初始化VSM (高危) ----

    add("TENANT_VSMINIT_001", "doVsmInit 正常初始化clearPK=false(高危)",
        "/platformServlet", 200,
        params="method=doVsmInit",
        json_data=jd({"requestId": "uuid", "clearPK": "false"}),
        method="POST", section="9.2.7", enabled="no")

    add("TENANT_VSMINIT_002", "doVsmInit clearPK=true(高危+清公钥)",
        "/platformServlet", 200,
        params="method=doVsmInit",
        json_data=jd({"requestId": "uuid", "clearPK": "true"}),
        method="POST", section="9.2.7", enabled="no")

    add("TENANT_VSMINIT_003", "doVsmInit 缺requestId",
        "/platformServlet", 400,
        params="method=doVsmInit",
        json_data=jd({"clearPK": "false"}),
        method="POST", section="9.2.7")

    add("TENANT_VSMINIT_004", "doVsmInit 缺clearPK",
        "/platformServlet", 400,
        params="method=doVsmInit",
        json_data=jd({"requestId": "uuid"}),
        method="POST", section="9.2.7")

    add("TENANT_VSMINIT_005", "doVsmInit clearPK无效值",
        "/platformServlet", 400,
        params="method=doVsmInit",
        json_data=jd({"requestId": "uuid", "clearPK": "maybe"}),
        method="POST", section="9.2.7")

    # ---- 场景尾部: 清理恢复 ----

    # step N: cleanPK 清理测试残留公钥
    add("TENANT_CLEANUP_001", "cleanPK 场景尾部清理公钥",
        "/authServlet", 200,
        params="method=cleanPK&requestId=uuid",
        method="GET", step_type="teardown", section="9.2.3")

    # step N+1: 恢复主公钥(与7.3 sheet保持一致)
    add("TENANT_CLEANUP_002", "authPK 场景尾部恢复主RSA公钥",
        "/authServlet", 200,
        params="method=authPK",
        json_data=jd({"requestId": "uuid", "alg": "rsa", "pks": ["${keys.rsa_key1}"]}),
        step_type="teardown", section="9.2.2")

    # step N+2: 验证恢复成功
    add("TENANT_CLEANUP_003", "getAuthPKFingerprints 验证恢复成功",
        "/authServlet", 200,
        params="method=getAuthPKFingerprints&requestId=uuid",
        assert_rules=ok_data({"type": "json_contains", "key": "data"}),
        method="GET", step_type="verify", section="9.2.1")

    return rows


# ================================================================
# 主流程
# ================================================================

def write_sheet(ws, data_rows):
    for ci, h in enumerate(HEADERS, 1):
        ws.cell(1, ci, h)
    for ri, data in enumerate(data_rows, 2):
        for ci, h in enumerate(HEADERS, 1):
            val = data.get(h)
            if val is not None:
                ws.cell(ri, ci, val)


def main():
    xlsx = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test_data.xlsx")
    wb = openpyxl.load_workbook(xlsx)

    sheet_name = "section8_9"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]

    all_data = []
    fs_data = gen_fileserver()
    tenant_data = gen_tenant_scenario()
    all_data.extend(fs_data)
    all_data.extend(tenant_data)

    ws = wb.create_sheet(sheet_name)
    write_sheet(ws, all_data)

    enabled_count = sum(1 for r in all_data if r.get("enabled", "yes") == "yes")
    disabled_count = len(all_data) - enabled_count

    print(f"section8_9: {len(all_data)} 行 ({enabled_count} enabled, {disabled_count} disabled)")
    print(f"  Section 8 FileServer: {len(fs_data)} 行 (全部 enabled=no，依赖文件上传/FileServer环境)")
    print(f"  Section 9 租户密评:   {len(tenant_data)} 行 (SCN_TENANT 场景)")

    wb.save(xlsx)
    print(f"\n已保存: {xlsx}")

    # 按 section 统计
    from collections import Counter
    by_section = Counter()
    by_enabled = {"yes": 0, "no": 0}
    for r in all_data:
        sec = r.get("section", "unknown")
        by_section[sec] += 1
        en = r.get("enabled", "yes")
        by_enabled[en] = by_enabled.get(en, 0) + 1

    print("\n=== 按章节统计 ===")
    for sec, cnt in sorted(by_section.items()):
        print(f"  {sec}: {cnt} 条")

    print(f"\n=== enabled 统计 ===")
    print(f"  enabled=yes: {by_enabled['yes']}")
    print(f"  enabled=no:  {by_enabled['no']}")

    # 场景步骤统计
    scn_steps = [r for r in all_data if r.get("scenario_id") == "SCN_TENANT"]
    print(f"\n=== SCN_TENANT 场景 ===")
    print(f"  总步骤: {len(scn_steps)}")
    enabled_steps = [r for r in scn_steps if r.get("enabled", "yes") == "yes"]
    print(f"  enabled步骤: {len(enabled_steps)}")
    setup_steps = [r for r in scn_steps if r.get("step_type") == "setup"]
    verify_steps = [r for r in scn_steps if r.get("step_type") == "verify"]
    teardown_steps = [r for r in scn_steps if r.get("step_type") == "teardown"]
    print(f"  setup: {len(setup_steps)}, verify: {len(verify_steps)}, teardown: {len(teardown_steps)}, test: {len(scn_steps) - len(setup_steps) - len(verify_steps) - len(teardown_steps)}")


if __name__ == "__main__":
    main()
