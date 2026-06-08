#!/usr/bin/env python3
"""
场景 F：9.2.5 导出期间 9.2.6 导入应被阻塞(409)

接口说明:
  9.2.5 exportBackupKeys — POST /platformServlet?method=exportBackupKeys
    请求: JSON {"requestId", "backupKey"}，需认证签名
    响应: 二进制文件流(application/octet-stream)，保存到本地
  9.2.6 importBackupKeys — POST /platformServlet?method=importBackupKeys
    请求: multipart/form-data {requestId, backupKey, file}，file不参与签名
    响应: JSON {"status", "message", ...}

测试流程:
  1. 发起 exportBackupKeys（同步，返回二进制流）
  2. export 未完成时发起 importBackupKeys → 预期 409
  3. export 完成后发起 importBackupKeys → 预期 200

对应修复项: #5 ExportImagesLockRegistry TTL 超时释放 (MEDIUM)
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from glob import glob

import requests as req

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.signer import get_signer
from common.logger import logger

# ================================================================
# ★ 配置 ★
# ================================================================
VSM_HOST = "https://192.168.8.201:7443"
BACKUP_KEY = "VXnJ514jUDnAHhNqdypZkFVkn5DZBYBaXpH/GMmmDLc="
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")

# 指纹覆盖: 9.2 的指纹和 7.1 不同，填 VSM 系统的指纹值，为空则用 signer 计算的
AUTH_PK_OVERRIDE = ""


def now_str():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _sign_json(body):
    signer = get_signer()
    headers = signer.sign(json.dumps(body))
    if AUTH_PK_OVERRIDE:
        headers["CHSM-AuthPK"] = AUTH_PK_OVERRIDE
    return headers


def _sign_form(form_data):
    sign_str = "&".join("%s=%s" % (k, v) for k, v in sorted(form_data.items()))
    signer = get_signer()
    headers = signer.sign(sign_str)
    if AUTH_PK_OVERRIDE:
        headers["CHSM-AuthPK"] = AUTH_PK_OVERRIDE
    return headers


def do_export(rid):
    """发起 exportBackupKeys，返回 (status_code, file_path, elapsed)"""
    body = {"requestId": rid, "backupKey": BACKUP_KEY}
    headers = {"Content-Type": "application/json", "User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_json(body))
    url = "%s/platformServlet?method=exportBackupKeys" % VSM_HOST

    t0 = time.time()
    try:
        resp = req.post(url, json=body, headers=headers, verify=False, timeout=300)
        elapsed = time.time() - t0
        code = resp.status_code

        if code == 200 and len(resp.content) > 100:
            os.makedirs(EXPORT_DIR, exist_ok=True)
            filename = "backup_%s_%s.dat" % (rid[:8], datetime.now().strftime("%Y%m%d%H%M%S"))
            filepath = os.path.join(EXPORT_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return code, filepath, elapsed
        return code, None, elapsed
    except Exception as e:
        return 0, None, time.time() - t0


def do_import(rid, filepath):
    """发起 importBackupKeys，返回 (status_code, body, elapsed)"""
    form_data = {"requestId": rid, "backupKey": BACKUP_KEY}
    headers = {"User-Agent": "CHSM-Test/2.0"}
    headers.update(_sign_form(form_data))
    url = "%s/platformServlet?method=importBackupKeys" % VSM_HOST

    t0 = time.time()
    try:
        with open(filepath, "rb") as f:
            files = {"file": (os.path.basename(filepath), f, "application/octet-stream")}
            resp = req.post(url, data=form_data, files=files, headers=headers, verify=False, timeout=120)
        elapsed = time.time() - t0
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        return resp.status_code, body, elapsed
    except Exception as e:
        return 0, str(e), time.time() - t0


def _get_latest_export_file():
    if not os.path.isdir(EXPORT_DIR):
        return None
    files = sorted(glob(os.path.join(EXPORT_DIR, "*.dat")), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


# ================================================================
# 主流程
# ================================================================

def run():
    report = {"scenario": "F", "steps": [], "passed": False}

    print("=" * 64)
    print("  场景 F：9.2.5 导出期间 9.2.6 导入应被阻塞(409)")
    print("  VSM: %s" % VSM_HOST)
    print("  backupKey: %s" % BACKUP_KEY)
    print("  %s" % now_str())
    print("=" * 64)

    # 先确认有可用的导出文件（用于 import）
    existing_file = _get_latest_export_file()
    if not existing_file:
        print("\n  无已有导出文件，先执行一次导出...")
        rid0 = str(uuid.uuid4())
        code0, filepath0, t0 = do_export(rid0)
        if filepath0:
            existing_file = filepath0
            print("  预导出完成: %s" % filepath0)
        else:
            print("  预导出失败 HTTP %d，无法继续" % code0)
            report["verdict"] = "中止 — 无可用导出文件"
            _save_report(report)
            return False

    # ── Step 1+2: 并发 export + import ───────────────────
    print("\n" + "─" * 64)
    print("  Step 1 | 发起 export，同时尝试 import | %s" % now_str())
    print("─" * 64)

    export_rid = str(uuid.uuid4())
    import_rid_blocked = str(uuid.uuid4())

    print("  export requestId: %s" % export_rid)
    print("  import requestId: %s" % import_rid_blocked)
    print("  import file: %s" % existing_file)

    # 用线程池并发：export 是同步长操作，import 在 export 发出后立刻发
    with ThreadPoolExecutor(max_workers=2) as pool:
        export_future = pool.submit(do_export, export_rid)
        time.sleep(1)  # 等 export 请求发出
        import_future = pool.submit(do_import, import_rid_blocked, existing_file)

        # 先拿 import 结果（应该很快返回 409）
        import_code, import_body, import_elapsed = import_future.result(timeout=60)
        print("\n  [import 锁中] HTTP %d (%.3fs)" % (import_code, import_elapsed))
        if isinstance(import_body, dict):
            print("    %s" % json.dumps(import_body, ensure_ascii=False)[:200])

        step2_blocked = (import_code == 409)
        if step2_blocked:
            print("    → 409 被阻塞 ✓")
        elif import_code >= 500:
            print("    → 500 错误 ✗")
        else:
            print("    → HTTP %d 未被阻塞 ✗" % import_code)

        report["steps"].append({
            "step": 2, "action": "import during export (应被阻塞)",
            "status_code": import_code, "blocked": step2_blocked,
            "passed": step2_blocked,
        })
        if not step2_blocked:
            report["steps"][-1]["issue"] = "导出期间导入未返回409，实际HTTP %d" % import_code

        # 等 export 完成
        print("\n  等待 export 完成...")
        export_code, export_file, export_elapsed = export_future.result(timeout=300)
        print("  [export] HTTP %d (%.3fs)" % (export_code, export_elapsed))
        if export_file:
            print("    保存: %s" % export_file)

    step1_ok = (export_code == 200 and export_file is not None)
    report["steps"].insert(0, {
        "step": 1, "action": "exportBackupKeys",
        "status_code": export_code, "export_file": export_file,
        "passed": step1_ok,
    })
    if not step1_ok:
        report["steps"][0]["issue"] = "导出失败 HTTP %d" % export_code

    # ── Step 3: 锁释放后 import ──────────────────────────
    print("\n" + "─" * 64)
    print("  Step 3 | 导出完成后再次 import（预期成功）| %s" % now_str())
    print("─" * 64)

    use_file = export_file or existing_file
    import_rid_ok = str(uuid.uuid4())
    import_code2, import_body2, import_elapsed2 = do_import(import_rid_ok, use_file)
    print("  [import 锁后] HTTP %d (%.3fs)" % (import_code2, import_elapsed2))
    if isinstance(import_body2, dict):
        print("    %s" % json.dumps(import_body2, ensure_ascii=False)[:200])

    step3_ok = (import_code2 == 200)
    report["steps"].append({
        "step": 3, "action": "import after export (应成功)",
        "status_code": import_code2, "passed": step3_ok,
    })
    if step3_ok:
        print("    → 200 导入成功 ✓")
    else:
        report["steps"][-1]["issue"] = "锁释放后导入仍失败 HTTP %d" % import_code2
        print("    → HTTP %d ✗" % import_code2)

    # ── 汇总 ─────────────────────────────────────────────
    passed = step1_ok and step2_blocked and step3_ok
    report["passed"] = passed
    issues = [s["issue"] for s in report["steps"] if "issue" in s]
    if issues:
        report["issues"] = issues

    if passed:
        report["verdict"] = "PASS — 导出期间导入被阻塞(409) + 导出后导入成功"
    elif step2_blocked and not step3_ok:
        report["verdict"] = "PASS(部分) — 阻塞正确但释放后导入失败"
    elif not step2_blocked:
        report["verdict"] = "FAIL — 导出期间导入未被阻塞"
    else:
        report["verdict"] = "FAIL — %s" % (issues[0] if issues else "未知")

    print("\n" + "=" * 64)
    print("  结论: %s" % report["verdict"])
    if issues:
        print("  问题:")
        for iss in issues:
            print("    - %s" % iss)
    print("  %s" % now_str())
    print("=" * 64)

    _save_report(report)
    return passed


def _save_report(report):
    os.makedirs("output", exist_ok=True)
    path = "output/scenario_f_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  报告: %s" % path)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
