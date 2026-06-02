#!/usr/bin/env python3
"""
Mock 服务 — 接收密码机的回调通知和文件上传，记录所有请求。

启动:
  python3 mock_server.py

记录查看:
  浏览器访问 http://<ip>:<port>/records     # 查看所有请求记录
  记录文件:  mock_data/records.json
  上传文件:  对应 UPLOAD_DIR 配置目录
"""

# ================================================================
# 配置 — 在这里修改
# ================================================================
PORT = 8000
HOST = "0.0.0.0"
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads")

import json
import os
import sys
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data")
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    upload_path = UPLOAD_DIR if os.path.isabs(UPLOAD_DIR) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), UPLOAD_DIR)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def load_records():
    if os.path.isfile(RECORDS_FILE):
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_records(records):
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


class MockHandler(BaseHTTPRequestHandler):
    upload_dir = ""

    def do_GET(self):
        # /records — 查看请求记录
        if self.path.startswith("/records"):
            self._serve_records()
            return
        # /clear — 清空记录
        if self.path.startswith("/clear"):
            self._clear_records()
            return
        # 其他 GET 请求也记录
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def _handle_request(self):
        """处理所有请求：记录信息，保存文件"""
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        record = {
            "id": len(load_records()) + 1,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": self.command,
            "path": self.path,
            "client": f"{self.client_address[0]}:{self.client_address[1]}",
            "content_type": content_type,
            "content_length": content_length,
            "headers": dict(self.headers),
        }

        saved_file = None

        if content_length > 0:
            body = self.rfile.read(content_length)

            if "multipart/form-data" in content_type:
                # 文件上传（multipart）
                saved_file = self._save_multipart(body, content_type)
                record["body_type"] = "multipart"
                record["saved_file"] = saved_file

            elif "application/json" in content_type or self._is_json(body):
                # JSON 回调
                try:
                    record["body"] = json.loads(body.decode("utf-8"))
                    record["body_type"] = "json"
                except Exception:
                    record["body"] = body.decode("utf-8", errors="replace")[:2000]
                    record["body_type"] = "text"

            elif "application/octet-stream" in content_type or content_length > 10240:
                # 二进制文件（非 multipart 直传）
                saved_file = self._save_binary(body)
                record["body_type"] = "binary"
                record["saved_file"] = saved_file

            else:
                # 其他文本
                record["body"] = body.decode("utf-8", errors="replace")[:2000]
                record["body_type"] = "text"
        else:
            record["body_type"] = "empty"

        # 保存记录（最新的插到最前面）
        records = load_records()
        records.insert(0, record)
        save_records(records)

        # 打印日志
        file_info = f" → 文件已保存: {saved_file}" if saved_file else ""
        print(f"[{record['time']}] {self.command} {self.path} "
              f"({content_type or 'no-type'}, {content_length} bytes){file_info}")

        # 响应 200
        resp = json.dumps({"success": True, "message": "recorded"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def _save_multipart(self, body, content_type):
        """解析 multipart/form-data，保存文件部分"""
        # 简单解析：找到文件内容保存
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part.split("=", 1)[1].strip('"')
                break

        if not boundary:
            return self._save_binary(body)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        saved_files = []

        parts = body.split(f"--{boundary}".encode())
        for part in parts:
            if b"filename=" not in part:
                continue

            # 提取文件名
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            header_section = part[:header_end].decode("utf-8", errors="replace")
            file_content = part[header_end + 4:]
            # 去掉末尾的 \r\n
            if file_content.endswith(b"\r\n"):
                file_content = file_content[:-2]

            # 提取原始文件名
            filename = "unknown"
            for line in header_section.split("\r\n"):
                if "filename=" in line:
                    start = line.find('filename="') + 10
                    end = line.find('"', start)
                    if start > 9 and end > start:
                        filename = line[start:end]
                    break

            # 保存
            safe_name = f"{timestamp}_{filename}"
            filepath = os.path.join(self.upload_dir, safe_name)
            with open(filepath, "wb") as f:
                f.write(file_content)
            saved_files.append(safe_name)
            print(f"  文件保存: {safe_name} ({len(file_content)} bytes)")

        return saved_files if saved_files else None

    def _save_binary(self, body):
        """直接保存二进制数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_upload.bin"
        filepath = os.path.join(self.upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(body)
        print(f"  文件保存: {filename} ({len(body)} bytes)")
        return filename

    @staticmethod
    def _is_json(body):
        try:
            json.loads(body)
            return True
        except Exception:
            return False

    def _serve_records(self):
        """返回所有请求记录"""
        records = load_records()

        # 支持 ?path=/xxx 过滤
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        filter_path = qs.get("path", [None])[0]
        if filter_path:
            records = [r for r in records if filter_path in r.get("path", "")]

        body = json.dumps({
            "total": len(records),
            "records": records,
        }, ensure_ascii=False, indent=2).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _clear_records(self):
        """清空记录"""
        save_records([])
        body = json.dumps({"success": True, "message": "records cleared"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
        print("[CLEAR] 记录已清空")

    def log_message(self, format, *args):
        pass  # 用自定义日志，不用默认的


def get_local_ip():
    """获取本机局域网 IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    upload_path = ensure_dirs()
    MockHandler.upload_dir = upload_path

    local_ip = get_local_ip()
    server = HTTPServer((HOST, PORT), MockHandler)
    print(f"Mock 服务启动: http://{local_ip}:{PORT}")
    print(f"  回调地址示例:  http://{local_ip}:{PORT}/callback")
    print(f"  上传地址示例:  http://{local_ip}:{PORT}/image/upload")
    print(f"  记录查看:      http://{local_ip}:{PORT}/records")
    print(f"  清空记录:      http://{local_ip}:{PORT}/clear")
    print(f"  数据目录:      {DATA_DIR}")
    print(f"  上传目录:      {upload_path}")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
