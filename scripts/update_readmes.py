#!/usr/bin/env python3
"""
update_readmes.py — 更新 references/ 下三个仓库的 README

用法:
    python update_readmes.py            # 更新全部三个
    python update_readmes.py astrbot    # 只更新指定仓库（astrbot/napcat/plugin）

特性:
    - 每个仓库尝试 master/main 分支 × raw 两种 URL 形式
    - 套用与 download.py 相同的国内镜像轮换，直连兜底
    - 校验内容非 HTML、长度合理，防止把 404 页面存成 README
    - 标准库实现，无第三方依赖
"""

import os
import sys
import urllib.request

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(SKILL_DIR, "references")

# (仓库全名, 输出文件名)
REPOS = [
    ("AstrBotDevs/AstrBot", "AstrBot-readme.md"),
    ("NapNeko/NapCatQQ", "NapCatQQ-readme.md"),
    ("Him666233/astrbot_plugin_group_chat_plus", "astrbot_plugin_group_chat_plus-readme.md"),
]

# 镜像候选（与 download.py 保持一致），空字符串 = 直连
MIRRORS = [
    "https://ghfast.top/",
    "https://gh-proxy.com/",
    "https://ghproxy.net/",
    "",
]

TIMEOUT = 30
MIN_SIZE = 500  # 小于该字节数视为异常内容（404 文本等）


def candidate_urls(repo: str):
    """生成一个仓库的所有候选 URL（分支 × raw 形式）。"""
    paths = []
    for branch in ("master", "main"):
        paths.append(f"https://raw.githubusercontent.com/{repo}/{branch}/README.md")
        paths.append(f"https://github.com/{repo}/raw/{branch}/README.md")
    return paths


def looks_valid(data: bytes) -> bool:
    if len(data) < MIN_SIZE:
        return False
    head = data[:200].lstrip()
    low = head.lower()
    # 只拦截真正的 HTML 页面；markdown 里的 <img>/<div> 等标签是合法内容
    if low.startswith(b"<!doctype") or low.startswith(b"<html"):
        return False
    if head.startswith(b"404") or b"Not Found" in data[:100]:
        return False
    return True


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def update_one(repo: str, out_name: str) -> bool:
    out_path = os.path.join(REF_DIR, out_name)
    old_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"[{out_name}] 来源 https://github.com/{repo}")

    for base in candidate_urls(repo):
        for i, mirror in enumerate(MIRRORS, 1):
            url = mirror + base
            label = "直连 GitHub" if not mirror else mirror.split("//")[1].split("/")[0]
            try:
                data = fetch(url)
                if not looks_valid(data):
                    print(f"  [{i}/{len(MIRRORS)}] {label}: 内容异常，跳过")
                    continue
                with open(out_path, "wb") as f:
                    f.write(data)
                new_size = len(data)
                delta = new_size - old_size
                arrow = "+" if delta >= 0 else ""
                print(f"  [完成] {label} | {old_size}B -> {new_size}B ({arrow}{delta}B)")
                return True
            except Exception as e:
                print(f"  [{i}/{len(MIRRORS)}] {label}: {type(e).__name__}")
    print(f"  [失败] 所有来源均不可用，保留原文件")
    return False


def main():
    os.makedirs(REF_DIR, exist_ok=True)
    key = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    targets = []
    for repo, out_name in REPOS:
        if key and key not in (repo.lower() + out_name.lower()):
            continue
        targets.append((repo, out_name))
    if not targets:
        print(__doc__)
        sys.exit(2)

    ok = 0
    for repo, out_name in targets:
        if update_one(repo, out_name):
            ok += 1
    print(f"\n完成: {ok}/{len(targets)} 个 README 已更新")
    sys.exit(0 if ok == len(targets) else 1)


if __name__ == "__main__":
    main()
