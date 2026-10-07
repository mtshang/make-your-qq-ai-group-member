#!/usr/bin/env python3
"""
verify.py — 部署环境检测工具

用法:
    python verify.py port <端口号>          检查 TCP 端口是否在监听（如 6185 / 6199）
    python verify.py file <路径>            检查文件是否存在
    python verify.py json <路径>            检查 JSON 文件可解析
    python verify.py jsonkey <路径> <键>    检查 JSON 中指定键存在
    python verify.py http <url>             检查 HTTP 可达（返回 <400 即通过）

返回码: 0 = 通过, 1 = 不通过, 2 = 用法错误
标准库实现，无第三方依赖。
"""

import json
import socket
import sys
import urllib.request


def check_port(port: int) -> bool:
    """端口有监听返回 True。0.0.0.0 / 127.0.0.1 通吃。"""
    for host in ("127.0.0.1",):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            s.connect((host, port))
            s.close()
            return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False
        finally:
            s.close()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    action = sys.argv[1]

    if action == "port":
        port = int(sys.argv[2])
        ok = check_port(port)
        print(f"端口 {port}: {'✓ 监听中' if ok else '✗ 未监听'}")
        sys.exit(0 if ok else 1)

    elif action == "file":
        import os
        ok = os.path.exists(sys.argv[2])
        print(f"文件 {sys.argv[2]}: {'✓ 存在' if ok else '✗ 不存在'}")
        sys.exit(0 if ok else 1)

    elif action == "json":
        try:
            # utf-8-sig 兼容带 BOM 的文件（AstrBot 写回的配置带 BOM）
            json.load(open(sys.argv[2], encoding="utf-8-sig"))
            print(f"JSON {sys.argv[2]}: ✓ 可解析")
            sys.exit(0)
        except Exception as e:
            print(f"JSON {sys.argv[2]}: ✗ 解析失败 - {e}")
            sys.exit(1)

    elif action == "jsonkey" and len(sys.argv) >= 4:
        path, key = sys.argv[2], sys.argv[3]
        try:
            d = json.load(open(path, encoding="utf-8-sig"))
            ok = key in d
            print(f"JSON 键 '{key}': {'✓ 存在' if ok else '✗ 缺失'}")
            sys.exit(0 if ok else 1)
        except Exception as e:
            print(f"JSON {path}: ✗ 解析失败 - {e}")
            sys.exit(1)

    elif action == "http":
        try:
            req = urllib.request.Request(sys.argv[2], headers={"User-Agent": "Mozilla/5.0"})
            code = urllib.request.urlopen(req, timeout=8).status
            ok = code < 400
            print(f"HTTP {sys.argv[2]}: {'✓' if ok else '✗'} (status {code})")
            sys.exit(0 if ok else 1)
        except Exception as e:
            print(f"HTTP {sys.argv[2]}: ✗ {type(e).__name__}")
            sys.exit(1)

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
