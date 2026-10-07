#!/usr/bin/env python3
"""
download.py — GitHub 下载器（自动镜像切换 + 直连兜底）

用法:
    python download.py <github_url> <输出文件路径>

特性:
    - 依次尝试国内镜像前缀，最后直连 GitHub
    - 校验 zip 文件头（PK），防止把 HTML 错误页存成 zip
    - 流式下载，每 1MB 打印进度
    - 标准库实现，无第三方依赖
"""

import os
import sys
import time
import urllib.request

# 镜像候选：依次尝试，空字符串 = 直连 GitHub（放最后）
MIRRORS = [
    "https://ghfast.top/",
    "https://gh-proxy.com/",
    "https://ghproxy.net/",
    "",
]

TIMEOUT = 30
CHUNK = 1024 * 256


def looks_like_zip(head: bytes) -> bool:
    return head[:2] == b"PK"


def fetch(url: str, out_path: str) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        total = resp.getheader("Content-Length")
        total = int(total) if total else None
        # 先读文件头判断是不是真文件（HTML/JSON 错误页拦截；zip 场景强制 PK 头）
        head = resp.read(4)
        if head[:1] in (b"<", b"{"):
            print(f"    [跳过] 返回的是 HTML/JSON 页面而非文件（可能镜像失效/路径错误）")
            return False
        if out_path.lower().endswith(".zip") and not looks_like_zip(head):
            print(f"    [跳过] zip 响应缺少 PK 文件头（内容异常）")
            return False
        tmp_path = out_path + ".part"
        written = len(head)
        start = time.time()
        with open(tmp_path, "wb") as f:
            f.write(head)
            last_report = 0
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                f.write(chunk)
                written += len(chunk)
                if total and written - last_report > 1024 * 1024:
                    last_report = written
                    pct = written * 100 // total
                    speed = written / max(time.time() - start, 0.1) / 1024
                    print(f"\r    进度 {pct}% ({written//1024//1024}MB/{total//1024//1024}MB, {speed:.0f}KB/s)", end="", flush=True)
        print()
    if total and written != total:
        print(f"    [失败] 大小不完整: {written}/{total}")
        os.remove(tmp_path)
        return False
    os.replace(tmp_path, out_path)
    print(f"    [完成] {out_path} ({written//1024}KB, {time.time()-start:.0f}s)")
    return True


def main():
    if len(sys.argv) != 3:
        print("用法: python download.py <github_url> <输出文件路径>")
        sys.exit(2)
    original, out_path = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    for i, mirror in enumerate(MIRRORS, 1):
        url = mirror + original
        name = "直连 GitHub" if not mirror else mirror.split("//")[1].split("/")[0]
        print(f"[{i}/{len(MIRRORS)}] 尝试 {name} ...")
        try:
            if fetch(url, out_path):
                sys.exit(0)
        except Exception as e:
            print(f"    [失败] {type(e).__name__}: {str(e)[:100]}")
    print("全部镜像失败。请检查网络（代理/防火墙）后重试，或手动下载后放到目标位置。")
    sys.exit(1)


if __name__ == "__main__":
    main()
