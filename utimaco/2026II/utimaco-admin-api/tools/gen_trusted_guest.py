#!/usr/bin/env python3
"""
生成 trusted / guest sheet — 覆盖全部 7.1/7.2 接口的参数校验和业务逻辑测试。

每个接口的标准测试维度:
  1. 正常调用 (happy path)
  2. requestId="" → 400
  3. requestId 缺失 → 400
  4. requestId 非UUID格式 → 200/400 (边界)
  5. oprType="" / 缺失 / 无效 (oprType 接口)
  6. 各必填字段缺失/空/非法
  7. 业务边界
"""

import json
import os
import sys

try:
    import openpyxl
except ImportError:
    print("pip install openpyxl")
    sys.exit(1)

CALLBACK_URL = "${env.callbackUrl}"
UPLOAD_URL = "${env.uploadUrl}"
ALARM_URL = "${env.alarmUrl}"
MONITORING_URL = "${env.monitoringUrl}"
LOG_SERVER_URL = "${env.logServerUrl}"
CHSM_IMAGE_URL = "${env.chsmImageUrl}"
CHSM_PACK_URL = "${env.chsmPackUrl}"
CHSM_BACKUP_URL = "${env.chsmBackupUrl}"
VSM_IMAGE_URL = "${env.vsmImageUrl}"
VSM_PACK_URL = "${env.vsmPackUrl}"
SIGN_BASE64 = "${env.signBase64}"
SIGN_HEX = "${env.signHex}"

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


def jd(d):
    return json.dumps(d, ensure_ascii=False)


def row(case_id, desc, endpoint, expected_status, json_data=None, params=None,
        assert_rules=None, ref_case_id=None, enabled="yes", section="",
        scenario_id=None, step=None, step_type=None, save_vars=None,
        method="POST"):
    if assert_rules is None:
        assert_rules = OK if expected_status == 200 else ERR400
    return {
        "case_id": case_id,
        "description": desc,
        "host": None,
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


# ================================================================
# CHSM 查询类
# ================================================================

def gen_getCHSMInfo():
    EP = "/api/1.0/chsm"
    return [
        row("CHSM_INFO_001", "getCHSMInfo 正常获取", EP, 200,
            jd({"requestId": "uuid", "oprType": "getinfo"}),
            assert_rules=ok_with({"type": "json_contains", "key": "result.id"}),
            ref_case_id="CHSM_INFO_001", section="7.1.1"),
        row("CHSM_INFO_002", "getCHSMInfo oprType空字符串", EP, 400,
            jd({"requestId": "uuid", "oprType": ""}),
            ref_case_id="CHSM_INFO_002", section="7.1.1"),
        row("CHSM_INFO_003", "getCHSMInfo oprType无效值", EP, 400,
            jd({"requestId": "uuid", "oprType": "invalid_type"}),
            ref_case_id="CHSM_INFO_003", section="7.1.1"),
        row("CHSM_INFO_004", "getCHSMInfo 缺requestId", EP, 400,
            jd({"oprType": "getinfo"}),
            ref_case_id="CHSM_INFO_004", section="7.1.1"),
        row("CHSM_INFO_007", "getCHSMInfo requestId非UUID格式", EP, 200,
            jd({"requestId": "abc123", "oprType": "getinfo"}),
            assert_rules=ok_with({"type": "json_contains", "key": "result.id"}),
            ref_case_id="CHSM_INFO_007", section="7.1.1"),
        row("CHSM_INFO_T01", "getCHSMInfo requestId空字符串", EP, 400,
            jd({"requestId": "", "oprType": "getinfo"}),
            section="7.1.1"),
        row("CHSM_INFO_T02", "getCHSMInfo oprType缺失", EP, 400,
            jd({"requestId": "uuid"}),
            section="7.1.1"),
        row("CHSM_INFO_T03", "getCHSMInfo 空body", EP, 400,
            jd({}),
            section="7.1.1"),
    ]


def gen_getCHSMDebugInfo():
    EP = "/api/1.0/chsm/debuginfo"
    return [
        row("CHSM_DEBUG_001", "getCHSMDebugInfo 正常获取", EP, 200,
            jd({"requestId": "uuid"}),
            assert_rules=ok_with({"type": "json_contains", "key": "result"}),
            ref_case_id="CHSM_DEBUG_001", section="7.1.17"),
        row("CHSM_DEBUG_T01", "getCHSMDebugInfo requestId空字符串", EP, 400,
            jd({"requestId": ""}),
            section="7.1.17"),
        row("CHSM_DEBUG_T02", "getCHSMDebugInfo 缺requestId", EP, 400,
            jd({}),
            section="7.1.17"),
        row("CHSM_DEBUG_T03", "getCHSMDebugInfo requestId非UUID", EP, 200,
            jd({"requestId": "not-a-uuid"}),
            assert_rules=ok_with({"type": "json_contains", "key": "result"}),
            section="7.1.17"),
    ]


def gen_getCHSMDeviceInfo():
    EP = "/api/1.0/chsm"
    return [
        row("CHSM_DEVICE_001", "getCHSMDeviceInfo 正常获取", EP, 200,
            jd({"requestId": "uuid", "oprType": "getDeviceInfo"}),
            assert_rules=ok_with(
                {"type": "json_contains", "key": "result.version"},
                {"type": "json_contains", "key": "result.sn"},
            ),
            ref_case_id="CHSM_DEVICE_001", section="7.1.18"),
        row("CHSM_DEVICE_T01", "getCHSMDeviceInfo requestId空字符串", EP, 400,
            jd({"requestId": "", "oprType": "getDeviceInfo"}),
            section="7.1.18"),
        row("CHSM_DEVICE_T02", "getCHSMDeviceInfo 缺requestId", EP, 400,
            jd({"oprType": "getDeviceInfo"}),
            section="7.1.18"),
        row("CHSM_DEVICE_T03", "getCHSMDeviceInfo oprType缺失", EP, 400,
            jd({"requestId": "uuid"}),
            section="7.1.18"),
    ]


# ================================================================
# CHSM 配置类
# ================================================================

def gen_configCHSMNet():
    EP = "/api/1.0/chsm/network"
    return [
        row("CHSM_NET_001", "configCHSMNet 正常配置DNS", EP, 200,
            jd({"requestId": "uuid", "dnsList": ["8.8.8.8", "114.114.114.114"]}),
            ref_case_id="CHSM_NET_001", section="7.1.4"),
        row("CHSM_NET_002", "configCHSMNet 正常配置网口", EP, 200,
            jd({"requestId": "uuid", "netAddrs": [{"name": "eth0", "ip": "192.168.1.100", "mask": "255.255.255.0", "gateway": "192.168.1.1"}]}),
            ref_case_id="CHSM_NET_002", section="7.1.4"),
        row("CHSM_NET_003", "configCHSMNet 重复配置(幂等)", EP, 200,
            jd({"requestId": "uuid", "dnsList": ["8.8.8.8", "114.114.114.114"]}),
            ref_case_id="CHSM_NET_003", section="7.1.4"),
        row("CHSM_NET_004", "configCHSMNet 无效IP", EP, 400,
            jd({"requestId": "uuid", "netAddrs": [{"name": "eth0", "ip": "999.999.999.999", "mask": "255.255.255.0", "gateway": "192.168.1.1"}]}),
            ref_case_id="CHSM_NET_004", section="7.1.4"),
        row("CHSM_NET_006", "configCHSMNet IPv6地址", EP, 200,
            jd({"requestId": "uuid", "netAddrs": [{"name": "eth0", "ip": "fd00::100", "mask": "64", "gateway": "fd00::1"}]}),
            ref_case_id="CHSM_NET_006", section="7.1.4"),
        row("CHSM_NET_T01", "configCHSMNet requestId空字符串", EP, 400,
            jd({"requestId": "", "dnsList": ["8.8.8.8"]}),
            section="7.1.4"),
        row("CHSM_NET_T02", "configCHSMNet 缺requestId", EP, 400,
            jd({"dnsList": ["8.8.8.8"]}),
            section="7.1.4"),
        row("CHSM_NET_T03", "configCHSMNet dnsList空数组", EP, 400,
            jd({"requestId": "uuid", "dnsList": []}),
            section="7.1.4"),
        row("CHSM_NET_T04", "configCHSMNet netAddrs缺ip字段", EP, 400,
            jd({"requestId": "uuid", "netAddrs": [{"name": "eth0", "mask": "255.255.255.0", "gateway": "192.168.1.1"}]}),
            section="7.1.4"),
        row("CHSM_NET_T05", "configCHSMNet netAddrs和dnsList都缺失", EP, 400,
            jd({"requestId": "uuid"}),
            section="7.1.4"),
        row("CHSM_NET_T06", "configCHSMNet dnsList含非法DNS格式", EP, 400,
            jd({"requestId": "uuid", "dnsList": ["not_an_ip"]}),
            section="7.1.4"),
    ]


def gen_configCHSMNtp():
    EP = "/api/1.0/chsm/ntp"
    return [
        row("CHSM_NTP_001", "configCHSMNtp 正常配置", EP, 200,
            jd({"requestId": "uuid", "addr": "10.10.1.1", "syncPeriod": 60}),
            ref_case_id="CHSM_NTP_001", section="7.1.5"),
        row("CHSM_NTP_002", "configCHSMNtp syncPeriod超大值", EP, 200,
            jd({"requestId": "uuid", "addr": "10.10.1.1", "syncPeriod": 99999}),
            ref_case_id="CHSM_NTP_002", section="7.1.5"),
        row("CHSM_NTP_003", "configCHSMNtp addr空字符串", EP, 400,
            jd({"requestId": "uuid", "addr": "", "syncPeriod": 60}),
            ref_case_id="CHSM_NTP_003", section="7.1.5"),
        row("CHSM_NTP_004", "configCHSMNtp syncPeriod负数", EP, 400,
            jd({"requestId": "uuid", "addr": "10.10.1.1", "syncPeriod": -1}),
            ref_case_id="CHSM_NTP_004", section="7.1.5"),
        row("CHSM_NTP_T01", "configCHSMNtp requestId空字符串", EP, 400,
            jd({"requestId": "", "addr": "10.10.1.1", "syncPeriod": 60}),
            section="7.1.5"),
        row("CHSM_NTP_T02", "configCHSMNtp 缺requestId", EP, 400,
            jd({"addr": "10.10.1.1", "syncPeriod": 60}),
            section="7.1.5"),
        row("CHSM_NTP_T03", "configCHSMNtp 缺addr", EP, 400,
            jd({"requestId": "uuid", "syncPeriod": 60}),
            section="7.1.5"),
        row("CHSM_NTP_T04", "configCHSMNtp 缺syncPeriod", EP, 400,
            jd({"requestId": "uuid", "addr": "10.10.1.1"}),
            section="7.1.5"),
        row("CHSM_NTP_T05", "configCHSMNtp syncPeriod=0", EP, 400,
            jd({"requestId": "uuid", "addr": "10.10.1.1", "syncPeriod": 0}),
            section="7.1.5"),
        row("CHSM_NTP_T06", "configCHSMNtp addr非法格式", EP, 400,
            jd({"requestId": "uuid", "addr": "not_an_ip", "syncPeriod": 60}),
            section="7.1.5"),
    ]


def gen_configCHSMUploadAddress():
    EP = "/api/1.0/chsm/imageuploader"
    return [
        row("CHSM_UPLOAD_001", "configCHSMUploadAddress 正常配置", EP, 200,
            jd({"requestId": "uuid", "url": UPLOAD_URL}),
            ref_case_id="CHSM_UPLOAD_001", section="7.1.6"),
        row("CHSM_UPLOAD_002", "configCHSMUploadAddress url空字符串", EP, 400,
            jd({"requestId": "uuid", "url": ""}),
            ref_case_id="CHSM_UPLOAD_002", section="7.1.6"),
        row("CHSM_UPLOAD_T01", "configCHSMUploadAddress requestId空字符串", EP, 400,
            jd({"requestId": "", "url": UPLOAD_URL}),
            section="7.1.6"),
        row("CHSM_UPLOAD_T02", "configCHSMUploadAddress 缺requestId", EP, 400,
            jd({"url": UPLOAD_URL}),
            section="7.1.6"),
        row("CHSM_UPLOAD_T03", "configCHSMUploadAddress 缺url", EP, 400,
            jd({"requestId": "uuid"}),
            section="7.1.6"),
        row("CHSM_UPLOAD_T04", "configCHSMUploadAddress url非法格式", EP, 400,
            jd({"requestId": "uuid", "url": "not_a_url"}),
            section="7.1.6"),
    ]


def gen_configSyslogAddr():
    EP = "/api/1.0/chsm/loguploader"
    return [
        row("CHSM_SYSLOG_001", "configSyslogAddr type=syslog", EP, 200,
            jd({"requestId": "uuid", "logServerType": "syslog", "logServerAddress": "10.10.1.100:514"}),
            ref_case_id="CHSM_SYSLOG_001", section="7.1.7"),
        row("CHSM_SYSLOG_002", "configSyslogAddr type=logserver", EP, 200,
            jd({"requestId": "uuid", "logServerType": "logserver", "logServerAddress": LOG_SERVER_URL}),
            ref_case_id="CHSM_SYSLOG_002", section="7.1.7"),
        row("CHSM_SYSLOG_003", "configSyslogAddr type无效值", EP, 400,
            jd({"requestId": "uuid", "logServerType": "invalid", "logServerAddress": "10.10.1.100:514"}),
            ref_case_id="CHSM_SYSLOG_003", section="7.1.7"),
        row("CHSM_SYSLOG_T01", "configSyslogAddr requestId空字符串", EP, 400,
            jd({"requestId": "", "logServerType": "syslog", "logServerAddress": "10.10.1.100:514"}),
            section="7.1.7"),
        row("CHSM_SYSLOG_T02", "configSyslogAddr 缺requestId", EP, 400,
            jd({"logServerType": "syslog", "logServerAddress": "10.10.1.100:514"}),
            section="7.1.7"),
        row("CHSM_SYSLOG_T03", "configSyslogAddr 缺logServerType", EP, 400,
            jd({"requestId": "uuid", "logServerAddress": "10.10.1.100:514"}),
            section="7.1.7"),
        row("CHSM_SYSLOG_T04", "configSyslogAddr 缺logServerAddress", EP, 400,
            jd({"requestId": "uuid", "logServerType": "syslog"}),
            section="7.1.7"),
        row("CHSM_SYSLOG_T05", "configSyslogAddr logServerAddress空字符串", EP, 400,
            jd({"requestId": "uuid", "logServerType": "syslog", "logServerAddress": ""}),
            section="7.1.7"),
    ]


def gen_configCHSMAlarmAddress():
    EP = "/api/1.0/chsm/alarmaddress"
    return [
        row("CHSM_ALARM_001", "configCHSMAlarmAddress url+monitoringUrl", EP, 200,
            jd({"requestId": "uuid", "url": ALARM_URL, "monitoringUrl": MONITORING_URL}),
            ref_case_id="CHSM_ALARM_001", section="7.1.14"),
        row("CHSM_ALARM_002", "configCHSMAlarmAddress 只传url", EP, 200,
            jd({"requestId": "uuid", "url": ALARM_URL}),
            ref_case_id="CHSM_ALARM_002", section="7.1.14"),
        row("CHSM_ALARM_T01", "configCHSMAlarmAddress requestId空字符串", EP, 400,
            jd({"requestId": "", "url": ALARM_URL}),
            section="7.1.14"),
        row("CHSM_ALARM_T02", "configCHSMAlarmAddress 缺requestId", EP, 400,
            jd({"url": ALARM_URL}),
            section="7.1.14"),
        row("CHSM_ALARM_T03", "configCHSMAlarmAddress 缺url", EP, 400,
            jd({"requestId": "uuid"}),
            section="7.1.14"),
        row("CHSM_ALARM_T04", "configCHSMAlarmAddress url空字符串", EP, 400,
            jd({"requestId": "uuid", "url": ""}),
            section="7.1.14"),
    ]


def gen_configCHSMToken():
    EP = "/api/1.0/chsm/cloudtoken"
    return [
        row("CHSM_TOKEN_001", "configCHSMToken 正常配置", EP, 200,
            jd({"requestId": "uuid", "cloudToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test_token_value"}),
            ref_case_id="CHSM_TOKEN_001", section="7.1.15"),
        row("CHSM_TOKEN_002", "configCHSMToken cloudToken空字符串", EP, 400,
            jd({"requestId": "uuid", "cloudToken": ""}),
            ref_case_id="CHSM_TOKEN_002", section="7.1.15"),
        row("CHSM_TOKEN_T01", "configCHSMToken requestId空字符串", EP, 400,
            jd({"requestId": "", "cloudToken": "test_token"}),
            section="7.1.15"),
        row("CHSM_TOKEN_T02", "configCHSMToken 缺requestId", EP, 400,
            jd({"cloudToken": "test_token"}),
            section="7.1.15"),
        row("CHSM_TOKEN_T03", "configCHSMToken 缺cloudToken", EP, 400,
            jd({"requestId": "uuid"}),
            section="7.1.15"),
    ]


def gen_configCHSMMOOCAddress():
    EP = "/api/1.0/chsm/moocaddress"
    FULL = {
        "requestId": "uuid", "ocIp": "10.10.10.1", "ocProtocol": "https",
        "ocPort": "26635", "resourceUrl": "/rest/cloudInfra/v1/resource",
        "performanceUrl": "/rest/cloudInfra/v1/performance",
        "bizRegionNativeId": "region-001", "cloudInfraType": "FusionSphere",
        "dewServiceHost": "kms.cn-north-1.myhuaweicloud.com",
    }
    return [
        row("CHSM_MOOC_001", "configCHSMMOOCAddress 正常配置全参数", EP, 200,
            jd(FULL),
            ref_case_id="CHSM_MOOC_001", section="7.1.16"),
        row("CHSM_MOOC_002", "configCHSMMOOCAddress 缺ocIp", EP, 400,
            jd({k: v for k, v in FULL.items() if k != "ocIp"}),
            ref_case_id="CHSM_MOOC_002", section="7.1.16"),
        row("CHSM_MOOC_T01", "configCHSMMOOCAddress requestId空字符串", EP, 400,
            jd({**FULL, "requestId": ""}),
            section="7.1.16"),
        row("CHSM_MOOC_T02", "configCHSMMOOCAddress 缺requestId", EP, 400,
            jd({k: v for k, v in FULL.items() if k != "requestId"}),
            section="7.1.16"),
        row("CHSM_MOOC_T03", "configCHSMMOOCAddress ocIp空字符串", EP, 400,
            jd({**FULL, "ocIp": ""}),
            section="7.1.16"),
        row("CHSM_MOOC_T04", "configCHSMMOOCAddress 缺ocPort", EP, 400,
            jd({k: v for k, v in FULL.items() if k != "ocPort"}),
            section="7.1.16"),
        row("CHSM_MOOC_T05", "configCHSMMOOCAddress 缺resourceUrl", EP, 400,
            jd({k: v for k, v in FULL.items() if k != "resourceUrl"}),
            section="7.1.16"),
    ]


# ================================================================
# CHSM 异步类
# ================================================================

def gen_exportCHSM():
    EP = "/api/1.0/chsm/image"
    return [
        row("CHSM_EXPORT_001", "exportCHSM 正常导出", EP, 200,
            jd({"requestId": "uuid", "oprType": "export", "callbackUrl": CALLBACK_URL}),
            ref_case_id="CHSM_EXPORT_001", section="7.1.8"),
        row("CHSM_EXPORT_002", "exportCHSM 缺callbackUrl", EP, 400,
            jd({"requestId": "uuid", "oprType": "export"}),
            ref_case_id="CHSM_EXPORT_002", section="7.1.8"),
        row("CHSM_EXPORT_T01", "exportCHSM requestId空字符串", EP, 400,
            jd({"requestId": "", "oprType": "export", "callbackUrl": CALLBACK_URL}),
            section="7.1.8"),
        row("CHSM_EXPORT_T02", "exportCHSM 缺requestId", EP, 400,
            jd({"oprType": "export", "callbackUrl": CALLBACK_URL}),
            section="7.1.8"),
        row("CHSM_EXPORT_T03", "exportCHSM oprType缺失", EP, 400,
            jd({"requestId": "uuid", "callbackUrl": CALLBACK_URL}),
            section="7.1.8"),
        row("CHSM_EXPORT_T04", "exportCHSM callbackUrl空字符串", EP, 400,
            jd({"requestId": "uuid", "oprType": "export", "callbackUrl": ""}),
            section="7.1.8"),
    ]


def gen_importCHSM():
    EP = "/api/1.0/chsm/image"
    BASE = {
        "requestId": "uuid", "oprType": "import",
        "imageUrl": CHSM_IMAGE_URL,
        "alg": "RSAWithSHA256", "sign": SIGN_BASE64,
        "callbackUrl": CALLBACK_URL,
    }
    return [
        row("CHSM_IMPORT_001", "importCHSM 正常导入", EP, 200,
            jd(BASE), ref_case_id="CHSM_IMPORT_001", section="7.1.9", enabled="no"),
        row("CHSM_IMPORT_003", "importCHSM imageUrl不可达", EP, 200,
            jd({**BASE, "imageUrl": "http://192.168.99.99/no_exist.zip"}),
            ref_case_id="CHSM_IMPORT_003", section="7.1.9", enabled="no"),
        row("CHSM_IMPORT_004", "importCHSM sign篡改", EP, 200,
            jd({**BASE, "sign": "TAMPERED_SIGN_VALUE"}),
            ref_case_id="CHSM_IMPORT_004", section="7.1.9", enabled="no"),
        row("CHSM_IMPORT_005", "importCHSM 缺alg", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "alg"}),
            ref_case_id="CHSM_IMPORT_005", section="7.1.9"),
        row("CHSM_IMPORT_T01", "importCHSM requestId空字符串", EP, 400,
            jd({**BASE, "requestId": ""}),
            section="7.1.9"),
        row("CHSM_IMPORT_T02", "importCHSM 缺requestId", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "requestId"}),
            section="7.1.9"),
        row("CHSM_IMPORT_T03", "importCHSM 缺imageUrl", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "imageUrl"}),
            section="7.1.9"),
        row("CHSM_IMPORT_T04", "importCHSM 缺sign", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "sign"}),
            section="7.1.9"),
        row("CHSM_IMPORT_T05", "importCHSM 缺callbackUrl", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "callbackUrl"}),
            section="7.1.9"),
        row("CHSM_IMPORT_T06", "importCHSM oprType缺失", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "oprType"}),
            section="7.1.9"),
    ]


def gen_upgradeCHSM():
    EP = "/api/1.0/chsm"
    BASE = {
        "requestId": "uuid", "oprType": "upgrade",
        "packVersion": "2.0.1", "packUrl": CHSM_PACK_URL,
        "alg": "RSAWithSHA256", "sign": SIGN_HEX,
        "callbackUrl": CALLBACK_URL,
    }
    return [
        row("CHSM_UPGRADE_001", "upgradeCHSM 正常升级", EP, 200,
            jd(BASE), ref_case_id="CHSM_UPGRADE_001", section="7.1.10", enabled="no"),
        row("CHSM_UPGRADE_003", "upgradeCHSM packUrl无效", EP, 200,
            jd({**BASE, "packUrl": "http://192.168.99.99/no_exist.bin"}),
            ref_case_id="CHSM_UPGRADE_003", section="7.1.10", enabled="no"),
        row("CHSM_UPGRADE_T01", "upgradeCHSM requestId空字符串", EP, 400,
            jd({**BASE, "requestId": ""}),
            section="7.1.10"),
        row("CHSM_UPGRADE_T02", "upgradeCHSM 缺requestId", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "requestId"}),
            section="7.1.10"),
        row("CHSM_UPGRADE_T03", "upgradeCHSM 缺packVersion", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "packVersion"}),
            section="7.1.10"),
        row("CHSM_UPGRADE_T04", "upgradeCHSM 缺packUrl", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "packUrl"}),
            section="7.1.10"),
        row("CHSM_UPGRADE_T05", "upgradeCHSM 缺alg", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "alg"}),
            section="7.1.10"),
        row("CHSM_UPGRADE_T06", "upgradeCHSM 缺callbackUrl", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "callbackUrl"}),
            section="7.1.10"),
    ]


def gen_restartCHSM():
    EP = "/api/1.0/chsm"
    return [
        row("CHSM_RESTART_001", "restartCHSM 正常重启", EP, 200,
            jd({"requestId": "uuid", "oprType": "restart", "callbackUrl": CALLBACK_URL}),
            ref_case_id="CHSM_RESTART_001", section="7.1.11", enabled="no"),
        row("CHSM_RESTART_T01", "restartCHSM requestId空字符串", EP, 400,
            jd({"requestId": "", "oprType": "restart", "callbackUrl": CALLBACK_URL}),
            section="7.1.11"),
        row("CHSM_RESTART_T02", "restartCHSM 缺requestId", EP, 400,
            jd({"oprType": "restart", "callbackUrl": CALLBACK_URL}),
            section="7.1.11"),
        row("CHSM_RESTART_T03", "restartCHSM 缺callbackUrl", EP, 400,
            jd({"requestId": "uuid", "oprType": "restart"}),
            section="7.1.11"),
        row("CHSM_RESTART_T04", "restartCHSM oprType缺失", EP, 400,
            jd({"requestId": "uuid", "callbackUrl": CALLBACK_URL}),
            section="7.1.11"),
    ]


def gen_backupCHSM():
    EP = "/api/1.0/chsm"
    return [
        row("CHSM_BACKUP_001", "backupCHSM 正常备份", EP, 200,
            jd({"requestId": "uuid", "oprType": "backup", "callbackUrl": CALLBACK_URL}),
            ref_case_id="CHSM_BACKUP_001", section="7.1.12"),
        row("CHSM_BACKUP_T01", "backupCHSM requestId空字符串", EP, 400,
            jd({"requestId": "", "oprType": "backup", "callbackUrl": CALLBACK_URL}),
            section="7.1.12"),
        row("CHSM_BACKUP_T02", "backupCHSM 缺requestId", EP, 400,
            jd({"oprType": "backup", "callbackUrl": CALLBACK_URL}),
            section="7.1.12"),
        row("CHSM_BACKUP_T03", "backupCHSM 缺callbackUrl", EP, 400,
            jd({"requestId": "uuid", "oprType": "backup"}),
            section="7.1.12"),
        row("CHSM_BACKUP_T04", "backupCHSM oprType缺失", EP, 400,
            jd({"requestId": "uuid", "callbackUrl": CALLBACK_URL}),
            section="7.1.12"),
    ]


def gen_restoreCHSM():
    EP = "/api/1.0/chsm"
    BASE = {
        "requestId": "uuid", "oprType": "restore",
        "backupUrl": CHSM_BACKUP_URL,
        "alg": "RSAWithSHA256", "sign": SIGN_BASE64,
        "callbackUrl": CALLBACK_URL,
    }
    return [
        row("CHSM_RESTORE_001", "restoreCHSM 正常恢复", EP, 200,
            jd(BASE), ref_case_id="CHSM_RESTORE_001", section="7.1.13", enabled="no"),
        row("CHSM_RESTORE_T01", "restoreCHSM requestId空字符串", EP, 400,
            jd({**BASE, "requestId": ""}),
            section="7.1.13"),
        row("CHSM_RESTORE_T02", "restoreCHSM 缺requestId", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "requestId"}),
            section="7.1.13"),
        row("CHSM_RESTORE_T03", "restoreCHSM 缺backupUrl", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "backupUrl"}),
            section="7.1.13"),
        row("CHSM_RESTORE_T04", "restoreCHSM 缺alg", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "alg"}),
            section="7.1.13"),
        row("CHSM_RESTORE_T05", "restoreCHSM 缺callbackUrl", EP, 400,
            jd({k: v for k, v in BASE.items() if k != "callbackUrl"}),
            section="7.1.13"),
    ]


# ================================================================
# VSM 场景类 (SCN_VSM)
# ================================================================

def gen_vsm_scenario():
    """VSM 全部接口在 SCN_VSM 场景中执行, step 1 提取 vsmId"""
    rows = []
    step = 0

    def add(case_id, desc, endpoint, expected_status, json_data,
            ref_case_id=None, enabled="yes", section="", assert_rules=None,
            save_vars=None, step_type="test"):
        nonlocal step
        step += 1
        rows.append(row(
            case_id, desc, endpoint, expected_status,
            json_data=json_data, assert_rules=assert_rules,
            ref_case_id=ref_case_id, enabled=enabled, section=section,
            scenario_id="SCN_VSM", step=step, step_type=step_type,
            save_vars=save_vars,
        ))

    # --- setup: 获取 vsmId ---
    add("VSM_SETUP_001", "SCN_VSM setup: getCHSMInfo取vsmId",
        "/api/1.0/chsm", 200,
        jd({"requestId": "uuid", "oprType": "getinfo"}),
        assert_rules=ok_with({"type": "json_contains", "key": "result.vsmIds"}),
        step_type="setup", save_vars="vsmId=result.vsmIds[0]")

    # --- getVSMInfo ---
    EP_VSM = "/api/1.0/vsm"
    add("VSM_INFO_001", "getVSMInfo 正常获取", EP_VSM, 200,
        jd({"requestId": "uuid", "oprType": "getinfo", "vsmId": "${vsmId}"}),
        assert_rules=ok_with(
            {"type": "json_contains", "key": "result.id"},
            {"type": "json_contains", "key": "result.version"},
        ),
        ref_case_id="VSM_INFO_001", section="7.2.1")
    add("VSM_INFO_002", "getVSMInfo vsmId不存在", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "getinfo", "vsmId": "non_existent_id"}),
        ref_case_id="VSM_INFO_002", section="7.2.1")
    add("VSM_INFO_003", "getVSMInfo 缺vsmId", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "getinfo"}),
        ref_case_id="VSM_INFO_003", section="7.2.1")
    add("VSM_INFO_T01", "getVSMInfo requestId空字符串", EP_VSM, 400,
        jd({"requestId": "", "oprType": "getinfo", "vsmId": "${vsmId}"}),
        section="7.2.1")
    add("VSM_INFO_T02", "getVSMInfo 缺requestId", EP_VSM, 400,
        jd({"oprType": "getinfo", "vsmId": "${vsmId}"}),
        section="7.2.1")
    add("VSM_INFO_T03", "getVSMInfo oprType缺失", EP_VSM, 400,
        jd({"requestId": "uuid", "vsmId": "${vsmId}"}),
        section="7.2.1")
    add("VSM_INFO_T04", "getVSMInfo vsmId空字符串", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "getinfo", "vsmId": ""}),
        section="7.2.1")

    # --- configVSMNet ---
    EP_VNET = "/api/1.0/vsm/network"
    add("VSM_NET_001", "configVSMNet 正常配置IPv4", EP_VNET, 200,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "ip": "192.168.10.100", "mask": "255.255.255.0", "gateway": "192.168.10.1"}),
        ref_case_id="VSM_NET_001", section="7.2.3")
    add("VSM_NET_002", "configVSMNet IPv6", EP_VNET, 200,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "ip": "fd00::100", "mask": "64", "gateway": "fd00::1"}),
        ref_case_id="VSM_NET_002", section="7.2.3")
    add("VSM_NET_T01", "configVSMNet requestId空字符串", EP_VNET, 400,
        jd({"requestId": "", "vsmId": "${vsmId}", "ip": "192.168.10.100", "mask": "255.255.255.0", "gateway": "192.168.10.1"}),
        section="7.2.3")
    add("VSM_NET_T02", "configVSMNet 缺requestId", EP_VNET, 400,
        jd({"vsmId": "${vsmId}", "ip": "192.168.10.100", "mask": "255.255.255.0", "gateway": "192.168.10.1"}),
        section="7.2.3")
    add("VSM_NET_T03", "configVSMNet 缺vsmId", EP_VNET, 400,
        jd({"requestId": "uuid", "ip": "192.168.10.100", "mask": "255.255.255.0", "gateway": "192.168.10.1"}),
        section="7.2.3")
    add("VSM_NET_T04", "configVSMNet 缺ip", EP_VNET, 400,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "mask": "255.255.255.0", "gateway": "192.168.10.1"}),
        section="7.2.3")
    add("VSM_NET_T05", "configVSMNet ip无效格式", EP_VNET, 400,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "ip": "999.999.999.999", "mask": "255.255.255.0", "gateway": "192.168.10.1"}),
        section="7.2.3")

    # --- configVSMToken ---
    EP_VTOK = "/api/1.0/vsm/token"
    add("VSM_TOKEN_001", "configVSMToken 正常配置", EP_VTOK, 200,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "token": "test_token_123", "tenantId": "tenant_001"}),
        ref_case_id="VSM_TOKEN_001", section="7.2.4")
    add("VSM_TOKEN_002", "configVSMToken token=0释放", EP_VTOK, 200,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "token": "0"}),
        ref_case_id="VSM_TOKEN_002", section="7.2.4")
    add("VSM_TOKEN_T01", "configVSMToken requestId空字符串", EP_VTOK, 400,
        jd({"requestId": "", "vsmId": "${vsmId}", "token": "test_token", "tenantId": "tenant_001"}),
        section="7.2.4")
    add("VSM_TOKEN_T02", "configVSMToken 缺requestId", EP_VTOK, 400,
        jd({"vsmId": "${vsmId}", "token": "test_token", "tenantId": "tenant_001"}),
        section="7.2.4")
    add("VSM_TOKEN_T03", "configVSMToken 缺vsmId", EP_VTOK, 400,
        jd({"requestId": "uuid", "token": "test_token", "tenantId": "tenant_001"}),
        section="7.2.4")

    # --- exportVSM ---
    EP_VIMG = "/api/1.0/vsm/image"
    add("VSM_EXPORT_001", "exportVSM 正常导出", EP_VIMG, 200,
        jd({"requestId": "uuid", "oprType": "export", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_EXPORT_001", section="7.2.5")
    add("VSM_EXPORT_T01", "exportVSM requestId空字符串", EP_VIMG, 400,
        jd({"requestId": "", "oprType": "export", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        section="7.2.5")
    add("VSM_EXPORT_T02", "exportVSM 缺vsmId", EP_VIMG, 400,
        jd({"requestId": "uuid", "oprType": "export", "callbackUrl": CALLBACK_URL}),
        section="7.2.5")
    add("VSM_EXPORT_T03", "exportVSM 缺callbackUrl", EP_VIMG, 400,
        jd({"requestId": "uuid", "oprType": "export", "vsmId": "${vsmId}"}),
        section="7.2.5")

    # --- importVSM ---
    IMP_BASE = {
        "requestId": "uuid", "oprType": "import", "vsmId": "${vsmId}",
        "imageUrl": VSM_IMAGE_URL,
        "alg": "RSAWithSHA256", "sign": SIGN_BASE64,
        "callbackUrl": CALLBACK_URL,
    }
    add("VSM_IMPORT_001", "importVSM 正常导入", EP_VIMG, 200,
        jd(IMP_BASE), ref_case_id="VSM_IMPORT_001", section="7.2.6", enabled="no")
    add("VSM_IMPORT_T01", "importVSM requestId空字符串", EP_VIMG, 400,
        jd({**IMP_BASE, "requestId": ""}),
        section="7.2.6")
    add("VSM_IMPORT_T02", "importVSM 缺vsmId", EP_VIMG, 400,
        jd({k: v for k, v in IMP_BASE.items() if k != "vsmId"}),
        section="7.2.6")
    add("VSM_IMPORT_T03", "importVSM 缺alg", EP_VIMG, 400,
        jd({k: v for k, v in IMP_BASE.items() if k != "alg"}),
        section="7.2.6")

    # --- startVSM ---
    add("VSM_START_001", "startVSM 正常启动", EP_VSM, 200,
        jd({"requestId": "uuid", "oprType": "start", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_START_001", section="7.2.7")
    add("VSM_START_002", "startVSM vsmId不存在", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "start", "vsmId": "non_existent_id", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_START_002", section="7.2.7")
    add("VSM_START_T01", "startVSM requestId空字符串", EP_VSM, 400,
        jd({"requestId": "", "oprType": "start", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        section="7.2.7")
    add("VSM_START_T02", "startVSM 缺vsmId", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "start", "callbackUrl": CALLBACK_URL}),
        section="7.2.7")
    add("VSM_START_T03", "startVSM oprType缺失", EP_VSM, 400,
        jd({"requestId": "uuid", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        section="7.2.7")

    # --- stopVSM ---
    add("VSM_STOP_001", "stopVSM 正常停止", EP_VSM, 200,
        jd({"requestId": "uuid", "oprType": "stop", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_STOP_001", section="7.2.8")
    add("VSM_STOP_002", "stopVSM vsmId不存在", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "stop", "vsmId": "non_existent_id", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_STOP_002", section="7.2.8")
    add("VSM_STOP_T01", "stopVSM requestId空字符串", EP_VSM, 400,
        jd({"requestId": "", "oprType": "stop", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        section="7.2.8")
    add("VSM_STOP_T02", "stopVSM 缺vsmId", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "stop", "callbackUrl": CALLBACK_URL}),
        section="7.2.8")

    # --- restartVSM ---
    add("VSM_RESTART_001", "restartVSM 正常重启", EP_VSM, 200,
        jd({"requestId": "uuid", "oprType": "restart", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_RESTART_001", section="7.2.9")
    add("VSM_RESTART_002", "restartVSM vsmId不存在", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "restart", "vsmId": "non_existent_id", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_RESTART_002", section="7.2.9")
    add("VSM_RESTART_T01", "restartVSM requestId空字符串", EP_VSM, 400,
        jd({"requestId": "", "oprType": "restart", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        section="7.2.9")
    add("VSM_RESTART_T02", "restartVSM 缺vsmId", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "restart", "callbackUrl": CALLBACK_URL}),
        section="7.2.9")

    # --- resetVSM ---
    add("VSM_RESET_001", "resetVSM 正常重置", EP_VSM, 200,
        jd({"requestId": "uuid", "oprType": "reset", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_RESET_001", section="7.2.10", enabled="no")
    add("VSM_RESET_002", "resetVSM vsmId不存在", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "reset", "vsmId": "non_existent_id", "callbackUrl": CALLBACK_URL}),
        ref_case_id="VSM_RESET_002", section="7.2.10")
    add("VSM_RESET_T01", "resetVSM requestId空字符串", EP_VSM, 400,
        jd({"requestId": "", "oprType": "reset", "vsmId": "${vsmId}", "callbackUrl": CALLBACK_URL}),
        section="7.2.10")
    add("VSM_RESET_T02", "resetVSM 缺vsmId", EP_VSM, 400,
        jd({"requestId": "uuid", "oprType": "reset", "callbackUrl": CALLBACK_URL}),
        section="7.2.10")

    # --- upgradeVSM ---
    UPG_BASE = {
        "requestId": "uuid", "oprType": "upgrade", "vsmId": "${vsmId}",
        "packVersion": "1.5.0", "packUrl": VSM_PACK_URL,
        "alg": "RSAWithSHA256", "sign": SIGN_HEX,
        "callbackUrl": CALLBACK_URL,
    }
    add("VSM_UPGRADE_001", "upgradeVSM 正常升级", EP_VSM, 200,
        jd(UPG_BASE), ref_case_id="VSM_UPGRADE_001", section="7.2.11", enabled="no")
    add("VSM_UPGRADE_T01", "upgradeVSM requestId空字符串", EP_VSM, 400,
        jd({**UPG_BASE, "requestId": ""}),
        section="7.2.11")
    add("VSM_UPGRADE_T02", "upgradeVSM 缺vsmId", EP_VSM, 400,
        jd({k: v for k, v in UPG_BASE.items() if k != "vsmId"}),
        section="7.2.11")
    add("VSM_UPGRADE_T03", "upgradeVSM 缺packVersion", EP_VSM, 400,
        jd({k: v for k, v in UPG_BASE.items() if k != "packVersion"}),
        section="7.2.11")
    add("VSM_UPGRADE_T04", "upgradeVSM 缺callbackUrl", EP_VSM, 400,
        jd({k: v for k, v in UPG_BASE.items() if k != "callbackUrl"}),
        section="7.2.11")

    return rows


# ================================================================
# Guest 接口
# ================================================================

def gen_guest():
    return [
        row("GUEST_STATUS_001", "getCHSMStatus 正常(无认证)", "/api/1.0/chsm/status", 200,
            params="requestId=uuid", method="GET",
            assert_rules=ok_with({"type": "json_contains", "key": "result.status"}),
            ref_case_id="CHSM_STATUS_001"),
        row("GUEST_STATUS_T01", "getCHSMStatus requestId空", "/api/1.0/chsm/status", 400,
            params="requestId=", method="GET"),
        row("GUEST_STATUS_T02", "getCHSMStatus 缺requestId", "/api/1.0/chsm/status", 400,
            method="GET"),
        row("GUEST_ALLSTATUS_001", "getCHSMAllStatus 正常(无认证)", "/api/1.0/chsm/allstatus", 200,
            params="requestId=uuid", method="GET",
            assert_rules=ok_with({"type": "json_contains", "key": "result.hsmStatus"}),
            ref_case_id="CHSM_ALLSTATUS_001"),
        row("GUEST_ALLSTATUS_T01", "getCHSMAllStatus requestId空", "/api/1.0/chsm/allstatus", 400,
            params="requestId=", method="GET"),
        row("GUEST_ALLSTATUS_T02", "getCHSMAllStatus 缺requestId", "/api/1.0/chsm/allstatus", 400,
            method="GET"),
        row("GUEST_VSM_STATUS_001", "getVSMStatus 正常(无认证)", "/api/1.0/vsm/status", 200,
            params="requestId=uuid&vsmId=待确认", method="GET",
            assert_rules=ok_with({"type": "json_contains", "key": "result.status"}),
            ref_case_id="VSM_STATUS_001", enabled="no"),
        row("GUEST_VSM_STATUS_T01", "getVSMStatus 缺requestId", "/api/1.0/vsm/status", 400,
            params="vsmId=待确认", method="GET", enabled="no"),
        row("GUEST_VSM_STATUS_T02", "getVSMStatus 缺vsmId", "/api/1.0/vsm/status", 400,
            params="requestId=uuid", method="GET"),
    ]


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

    # 删除旧 sheet
    for name in ["trusted", "guest"]:
        if name in wb.sheetnames:
            del wb[name]

    # trusted
    trusted_data = []
    for gen_fn in [
        gen_getCHSMInfo, gen_getCHSMDebugInfo, gen_getCHSMDeviceInfo,
        gen_configCHSMNet, gen_configCHSMNtp, gen_configCHSMUploadAddress,
        gen_configSyslogAddr, gen_configCHSMAlarmAddress, gen_configCHSMToken,
        gen_configCHSMMOOCAddress,
        gen_exportCHSM, gen_importCHSM, gen_upgradeCHSM,
        gen_restartCHSM, gen_backupCHSM, gen_restoreCHSM,
    ]:
        trusted_data.extend(gen_fn())
    trusted_data.extend(gen_vsm_scenario())

    ws_t = wb.create_sheet("trusted")
    write_sheet(ws_t, trusted_data)

    enabled_count = sum(1 for r in trusted_data if r.get("enabled", "yes") == "yes")
    disabled_count = len(trusted_data) - enabled_count
    print(f"trusted: {len(trusted_data)} 行 ({enabled_count} enabled, {disabled_count} disabled)")

    # guest
    guest_data = gen_guest()
    ws_g = wb.create_sheet("guest")
    write_sheet(ws_g, guest_data)

    g_enabled = sum(1 for r in guest_data if r.get("enabled", "yes") == "yes")
    g_disabled = len(guest_data) - g_enabled
    print(f"guest: {len(guest_data)} 行 ({g_enabled} enabled, {g_disabled} disabled)")

    wb.save(xlsx)
    print(f"\n已保存: {xlsx}")

    # 统计
    from collections import Counter
    ep_counter = Counter()
    for r in trusted_data:
        ep = r["endpoint"]
        jd_str = r.get("json_data", "")
        if jd_str:
            try:
                d = json.loads(jd_str)
                opr = d.get("oprType", "")
                if opr:
                    ep = f"{ep} [{opr}]"
            except Exception:
                pass
        ep_counter[ep] += 1

    print("\n=== 每接口用例数 ===")
    for ep, cnt in sorted(ep_counter.items()):
        print(f"  {ep}: {cnt} 条")


if __name__ == "__main__":
    main()
