#!/usr/bin/env python3
"""
bot_manager.py — 一键启动/停止 AstrBot + NapCat（QQ AI 群聊机器人）

用法（在部署完成的机器上）:
    python bot_manager.py start    按序启动：AstrBot 先，NapCat 后（各开独立窗口）
    python bot_manager.py stop     按相反顺序停止：NapCat(QQ) 先，AstrBot 后
    python bot_manager.py status   查看两个服务当前状态

配置: 同目录/工作目录的 bot_manager.json（部署时由 agent 生成）:
    {
      "astrbot_root":      "D:\\qqaibot\\astrbot",     <- ASTRBOT_ROOT 指向的数据目录
      "astrbot_exe":       "C:\\Users\\xx\\.local\\bin\\astrbot.exe",
      "napcat_shell_dir":  "D:\\qqaibot\\napcat\\NapCat.52230.Shell",
      "napcat_root":       "D:\\qqaibot\\napcat"       <- 用于识别该目录下的 QQ.exe（避免误杀主号 QQ）
    }

设计说明:
    - 刻意不做"单窗口聚合日志"：NapCat 首次登录需交互（扫码）、两个进程输出编码不同、
      Ctrl+C 信号传递在 Windows 上不可靠。独立窗口 + 一键启停是可靠性最优解。
    - 首次部署/扫码请按 SKILL.md Phase 5/6 原方式操作；本脚本用于日常启动。
    - 标准库实现，无第三方依赖。
"""

import json
import os
import subprocess
import sys
import time

CFG_NAME = "bot_manager.json"
BAT_ASTRBOT = "start_astrbot.bat"
BAT_NAPCAT = "start_napcat.bat"

DASH_PORT = "6185"   # AstrBot WebUI
WS_PORT = "6199"     # AstrBot 反向 WS（NapCat 连这里）


def log(msg):
    print(msg, flush=True)


def load_config():
    # 依次找: 脚本同目录 -> 当前目录
    for base in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        p = os.path.join(base, CFG_NAME)
        if os.path.exists(p):
            with open(p, encoding="utf-8-sig") as f:
                return json.load(f), base
    log(f"[错误] 找不到 {CFG_NAME}（部署完成后由 agent 生成，含实际路径）")
    sys.exit(2)


def listening_pids(port):
    """返回监听指定端口的 PID 列表（netstat 解析，仅 LISTENING）。"""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, text=True, errors="replace", timeout=15
        ).stdout
    except Exception:
        return []
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        # 协议 本地地址 远程地址 状态 PID
        if len(parts) == 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
            if parts[4].isdigit():
                pids.add(parts[4])
    return sorted(pids)


def napcat_qq_pids(napcat_root):
    """找命令行/路径中含 napcat 安装目录的 QQ.exe（区别于用户主号 QQ）。"""
    root = napcat_root.lower().rstrip("\\")
    ps = (
        "$root='%s';"
        "Get-CimInstance Win32_Process -Filter \"Name='QQ.exe'\" | "
        "Where-Object { ($_.CommandLine -and $_.CommandLine.ToLower().Contains($root)) "
        "or ($_.ExecutablePath -and $_.ExecutablePath.ToLower().Contains($root)) } | "
        "Select-Object -ExpandProperty ProcessId" % root.replace("'", "''")
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, errors="replace", timeout=20
        ).stdout
    except Exception:
        return []
    return [l.strip() for l in out.splitlines() if l.strip().isdigit()]


def kill_tree(pid):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                   capture_output=True, text=True)


def cmd_status(cfg, base=None):
    dash = listening_pids(DASH_PORT)
    ws = listening_pids(WS_PORT)
    qq = napcat_qq_pids(cfg["napcat_root"])
    log(f"AstrBot : {'RUNNING' if dash else 'STOPPED'}"
        f"  (WebUI:{DASH_PORT} {'监听中' if dash else '无'}, 反向WS:{WS_PORT} {'监听中' if ws else '无'}, PID {','.join(dash) or '-'})")
    log(f"NapCat  : {'RUNNING' if qq else 'STOPPED'}"
        f"  (QQ.exe PID {','.join(qq) or '-'})")
    ok = bool(dash) and bool(qq)
    log("整体状态: " + ("正常运行" if ok else ("部分未启动" if (dash or qq) else "全部未启动")))
    return 0 if ok else 1


def cmd_start(cfg, base):
    root = cfg["astrbot_root"]
    exe = cfg["astrbot_exe"]
    shell_dir = cfg["napcat_shell_dir"]

    if listening_pids(DASH_PORT):
        log("[跳过] AstrBot 已在运行")
    else:
        bat = os.path.join(base, BAT_ASTRBOT)
        with open(bat, "w", encoding="gbk", errors="replace") as f:
            f.write(f'@echo off\r\ntitle AstrBot\r\nset "ASTRBOT_ROOT={root}"\r\n'
                    f'cd /d "{root}"\r\n"{exe}" run\r\npause\r\n')
        # start 新控制台窗口跑 bat（引号全部由 bat 文件承担，避免 cmd 转义地狱）
        subprocess.run(["cmd", "/c", "start", "AstrBot", bat], check=False)
        log("[启动] AstrBot 新窗口已打开，等待 WebUI 就绪 ...")
        for _ in range(30):
            time.sleep(2)
            if listening_pids(DASH_PORT):
                log("[就绪] AstrBot WebUI 已监听")
                break
        else:
            log("[警告] 60 秒内未检测到 WebUI，请看 AstrBot 窗口日志排查")

    if napcat_qq_pids(cfg["napcat_root"]):
        log("[跳过] NapCat 已在运行")
    else:
        if not os.path.isdir(shell_dir):
            log(f"[错误] NapCat Shell 目录不存在: {shell_dir}")
            return 1
        bat = os.path.join(base, BAT_NAPCAT)
        with open(bat, "w", encoding="gbk", errors="replace") as f:
            f.write(f'@echo off\r\ntitle NapCat\r\ncd /d "{shell_dir}"\r\n'
                    f'call napcat.quick.bat\r\npause\r\n')
        subprocess.run(["cmd", "/c", "start", "NapCat", bat], check=False)
        log("[启动] NapCat 新窗口已打开（quick 登录；首次部署请按 SKILL.md Phase 6 用 napcat.bat 扫码）")
    log("[完成] 日常启动顺序已执行。停止请用: python bot_manager.py stop")
    return 0


def cmd_stop(cfg):
    qq = napcat_qq_pids(cfg["napcat_root"])
    for pid in qq:
        kill_tree(pid)
    log(f"[停止] NapCat: {'已停止 ' + str(len(qq)) + ' 个进程' if qq else '未在运行'}")

    dash = listening_pids(DASH_PORT)
    for pid in dash:
        kill_tree(pid)
    log(f"[停止] AstrBot: {'已停止' if dash else '未在运行'}")

    time.sleep(1)
    return cmd_status(cfg)


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if cmd not in ("start", "stop", "status"):
        print(__doc__)
        sys.exit(2)
    cfg, base = load_config()
    return {"start": cmd_start, "stop": cmd_stop, "status": cmd_status}[cmd](cfg, base)


if __name__ == "__main__":
    sys.exit(main())
