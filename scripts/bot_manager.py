#!/usr/bin/env python3
"""
bot_manager.py — 一键启动/停止 AstrBot + NapCat（QQ AI 群聊机器人）

用法（在部署完成的机器上）:
    python bot_manager.py start          先清残留再全新启动：AstrBot 先，NapCat 后（各开独立窗口）
    python bot_manager.py stop           全部停止：NapCat(QQ) 先，AstrBot 后
    python bot_manager.py status         查看两个服务当前状态
    python bot_manager.py kill_astrbot   只杀 AstrBot（含残留启动窗口）
    python bot_manager.py kill_napcat    只杀 NapCat（含残留启动窗口）

行为约定:
    - start 每次都会**先杀掉对应组件的现有实例再启动**（防同号多开互踢，pitfalls C5）。
      重复跑 start = 重启服务（NapCat 免扫码会自动重连，AstrBot 中断约 1 分钟）。
    - 进程定位一律按端口/命令行/可执行路径，**绝不按窗口标题**（标题匹配范围广会误杀，C6）。
    - 窗口标题带 qqaibot- 前缀（qqaibot-AstrBot / qqaibot-NapCat），任务栏好认；
      但杀进程不依赖标题。

配置: 同目录/工作目录的 deploy_state.json（优先）或 bot_manager.json（部署时由 agent 生成）:
    {
      "astrbot_root":      "D:\\qqaibot\\astrbot",     <- ASTRBOT_ROOT 指向的数据目录
      "astrbot_exe":       "C:\\Users\\xx\\.local\\bin\\astrbot.exe",
      "napcat_shell_dir":  "D:\\qqaibot\\napcat\\NapCat.52230.Shell",
      "napcat_root":       "D:\\qqaibot\\napcat"       <- 用于识别该目录下的 QQ.exe（避免误杀主号 QQ）
    }

设计说明:
    - 刻意不做"单窗口聚合日志"：NapCat 首次登录需交互（扫码）、两个进程输出编码不同、
      Ctrl+C 信号传递在 Windows 上不可靠。独立窗口 + 一键启停是可靠性最优解。
    - 首次部署/扫码请按 SKILL.md Phase 5/6 原方式操作；本脚本用于日常启停。
    - 标准库实现，无第三方依赖。
"""

import json
import os
import subprocess
import sys
import time

CFG_NAMES = ("deploy_state.json", "bot_manager.json")
BAT_ASTRBOT = "start_astrbot.bat"
BAT_NAPCAT = "start_napcat.bat"
RUNTIME_DIR = ".bot_runtime"   # 启动 bat 的存放目录（内部产物，用户不需要碰）
CONSOLE_BAT = "机器人启动.bat"   # 用户双击入口：双击即启动，然后进菜单
CONSOLE_BAT_OLD = ("机器人控制台.bat",)   # 历史命名，生成时顺手清掉

DASH_PORT = "6185"   # AstrBot WebUI
WS_PORT = "6199"     # AstrBot 反向 WS（NapCat 连这里）


def log(msg):
    print(msg, flush=True)


def load_config():
    # 依次找: 脚本同目录 -> 当前目录；deploy_state.json 优先，bot_manager.json 兼容旧部署
    for base in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        for name in CFG_NAMES:
            p = os.path.join(base, name)
            if os.path.exists(p):
                with open(p, encoding="utf-8-sig") as f:
                    return json.load(f), base
    log(f"[错误] 找不到 {' 或 '.join(CFG_NAMES)}（部署时由 agent 在 $INSTALL 下生成）")
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
    """找命令行/可执行路径中含 napcat 安装目录的 QQ.exe（区别于用户主号 QQ）。"""
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


def bat_window_pids(where):
    """按 Where-Object 条件找 cmd.exe 的 PID（清理残留 bat 窗口用）。

    按 cmd.exe 的命令行内容匹配，比按窗口标题 taskkill /FI 精确得多（C6 误杀教训）。
    """
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | "
          "Where-Object { %s } | Select-Object -ExpandProperty ProcessId" % where)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, errors="replace", timeout=20
        ).stdout
    except Exception:
        return []
    return [l.strip() for l in out.splitlines() if l.strip().isdigit()]


def kill_tree(pid):
    # errors="replace" 必须带：taskkill 成功时输出中文（GBK），strict 解码会把读线程炸掉
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                   capture_output=True, text=True, errors="replace")


def runtime_dir(base):
    """启动 bat 的运行时目录：收进 .bot_runtime\\，避免与用户文件混在安装根目录。"""
    d = os.path.join(base, RUNTIME_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def clean_legacy_bat(base, name):
    """清理旧版本直接生成在安装根目录的同名 bat（可能被运行中的 cmd 锁住，忽略失败）。"""
    legacy = os.path.join(base, name)
    try:
        if os.path.exists(legacy):
            os.remove(legacy)
            log(f"[清理] 移除根目录旧启动脚本: {name}")
    except OSError:
        pass


def ensure_console_bat(base):
    """生成/刷新双击式启动 bat：**双击即先执行一轮启动（清残留+启动）**，完事进菜单。

    防呆：用户双击的意图就是"让机器人跑起来"，所以默认动作就是启动，不用再按 1。
    任意 bot_manager 命令运行时都会刷新——挪动 skill 目录后重跑一次即可修正路径。
    """
    for old in CONSOLE_BAT_OLD:
        try:
            legacy = os.path.join(base, old)
            if os.path.exists(legacy):
                os.remove(legacy)
        except OSError:
            pass
    try:
        manager = os.path.abspath(__file__)
        # 注意：bat 里满是 %~dp0 / %choice% 这类字面 %，绝不能用 % 格式化，用 f-string
        content = (
            '@echo off\r\n'
            'chcp 936 >nul\r\n'
            'title qqaibot 机器人启动\r\n'
            'cd /d "%~dp0"\r\n'
            'echo [双击默认动作] 正在启动机器人（自动清理残留）...\r\n'
            f'python "{manager}" start\r\n'
            'echo.\r\n'
            ':menu\r\n'
            'echo.\r\n'
            'echo   ========= QQ AI 机器人控制台 =========\r\n'
            'echo     [1] 再次启动（清理残留后重启）\r\n'
            'echo     [2] 停止机器人\r\n'
            'echo     [3] 查看运行状态\r\n'
            'echo     [0] 退出（不影响机器人运行）\r\n'
            'echo   ======================================\r\n'
            'set "choice="\r\n'
            'set /p choice=请输入数字后回车: \r\n'
            f'if "%choice%"=="1" python "{manager}" start\r\n'
            f'if "%choice%"=="2" python "{manager}" stop\r\n'
            f'if "%choice%"=="3" python "{manager}" status\r\n'
            'if "%choice%"=="0" exit\r\n'
            'goto menu\r\n'
        )
        with open(os.path.join(base, CONSOLE_BAT), "w", encoding="gbk", errors="replace") as f:
            f.write(content)
    except Exception as e:
        log(f"[提示] 启动 bat 生成失败（不影响命令行使用）: {e}")


def cmd_status(cfg, base=None):
    dash = listening_pids(DASH_PORT)
    ws = listening_pids(WS_PORT)
    nc_root = cfg.get("napcat_root", "").strip()
    if nc_root:
        qq = napcat_qq_pids(nc_root)
        qq_line = f"QQ.exe PID {','.join(qq) or '-'}"
        qq_state = "RUNNING" if qq else "STOPPED"
    else:
        qq, qq_line, qq_state = [], "未配置（Phase 6 后回填）", "N/A"
    log(f"AstrBot : {'RUNNING' if dash else 'STOPPED'}"
        f"  (WebUI:{DASH_PORT} {'监听中' if dash else '无'}, 反向WS:{WS_PORT} {'监听中' if ws else '无'}, PID {','.join(dash) or '-'})")
    log(f"NapCat  : {qq_state}  ({qq_line})")
    log("整体状态: " + ("正常运行" if dash and qq else ("部分未启动" if (dash or qq) else "全部未启动")))
    return 0 if (dash and qq) else 1


def cmd_kill_astrbot(cfg, base=None):
    """只杀 AstrBot：监听 6185/6199 的进程 + start_astrbot.bat 残留窗口。"""
    dash = listening_pids(DASH_PORT)
    ws = [p for p in listening_pids(WS_PORT) if p not in dash]
    for pid in dash + ws:
        kill_tree(pid)
    log(f"[清理] AstrBot: {'已杀 ' + str(len(dash) + len(ws)) + ' 个进程' if dash or ws else '未在运行'}")

    bats = bat_window_pids("$_.CommandLine -like '*%s*'" % BAT_ASTRBOT)
    for pid in bats:
        kill_tree(pid)
    log(f"[清理] 残留启动窗口: {'已杀 ' + str(len(bats)) + ' 个' if bats else '无'}")

    left = listening_pids(DASH_PORT)
    log("[复查] AstrBot 端口 " + ("仍被占用（PID %s）" % ",".join(left) if left else "已清空"))
    return 0 if not left else 1


def cmd_kill_napcat(cfg, base=None):
    """只杀 NapCat：napcat 目录下的 QQ.exe + napcat 相关 bat 残留窗口。"""
    nc_root = (cfg.get("napcat_root") or "").strip()
    if nc_root:
        qq = napcat_qq_pids(nc_root)
        for pid in qq:
            kill_tree(pid)
        log(f"[清理] NapCat(QQ.exe): {'已杀 ' + str(len(qq)) + ' 个进程' if qq else '未在运行'}")
        # napcat 目录下一切 .bat 的 cmd 窗口（napcat.bat / napcat.quick.bat / 我们的启动 bat）
        root = nc_root.rstrip("\\").replace("'", "''")
        where = "$_.CommandLine -like '*%s*' -and $_.CommandLine -like '*.bat*'" % root
    else:
        log("[清理] NapCat 未配置（napcat_root 为空）——只清理本脚本自己的启动窗口")
        where = "$_.CommandLine -like '*%s*'" % BAT_NAPCAT

    bats = bat_window_pids(where)
    for pid in bats:
        kill_tree(pid)
    log(f"[清理] NapCat 相关 bat 窗口: {'已杀 ' + str(len(bats)) + ' 个' if bats else '无'}")

    left = napcat_qq_pids(nc_root) if nc_root else []
    log("[复查] NapCat 进程 " + ("仍有残留（PID %s）" % ",".join(left) if left else "已清空"))
    return 0 if not left else 1


def cmd_start(cfg, base):
    root = cfg["astrbot_root"]
    exe = cfg["astrbot_exe"]
    shell_dir = cfg["napcat_shell_dir"]

    # 启动前先杀一次残留（用户约定 + pitfalls C5：永远单实例全新启动）
    cmd_kill_astrbot(cfg, base)
    time.sleep(2)
    clean_legacy_bat(base, BAT_ASTRBOT)
    bat = os.path.join(runtime_dir(base), BAT_ASTRBOT)
    with open(bat, "w", encoding="gbk", errors="replace") as f:
        f.write(f'@echo off\r\ntitle qqaibot-AstrBot\r\nset "ASTRBOT_ROOT={root}"\r\n'
                f'cd /d "{root}"\r\n"{exe}" run\r\npause\r\n')
    # start 的第一个参数必须带引号才被当窗口标题；list 形式下裸写 "AstrBot"
    # 会被 start 当成程序名去找 →「系统找不到文件 AstrBot」（实测踩坑）。
    # 空标题 "" + 窗口名由 bat 里的 title 设置，引号全部由 bat 文件承担。
    subprocess.run(["cmd", "/c", "start", "", bat], check=False)
    log("[启动] AstrBot 新窗口已打开，等待 WebUI 就绪 ...")
    for _ in range(60):
        time.sleep(2)
        if listening_pids(DASH_PORT):
            log("[就绪] AstrBot WebUI 已监听")
            break
    else:
        log("[警告] 120 秒未检测到 WebUI。首次启动要装插件依赖可能就是慢——"
            "窗口还在滚动日志就继续等（用 status 复查）；"
            "窗口消失或停在 pause 才是启动失败，把窗口报错发出来")

    nc_root = (cfg.get("napcat_root") or "").strip()
    shell_dir = (cfg.get("napcat_shell_dir") or "").strip()
    if not nc_root or not shell_dir:
        log("[跳过] NapCat 未配置（napcat_root/napcat_shell_dir 为空，Phase 6 装完回填）——本次只启动 AstrBot")
    else:
        # 同样先杀一次再启动（同号多开必互踢，C5）
        cmd_kill_napcat(cfg, base)
        time.sleep(3)
        if not os.path.isdir(shell_dir):
            log(f"[错误] NapCat Shell 目录不存在: {shell_dir}")
            return 1
        clean_legacy_bat(base, BAT_NAPCAT)
        bat = os.path.join(runtime_dir(base), BAT_NAPCAT)
        with open(bat, "w", encoding="gbk", errors="replace") as f:
            f.write(f'@echo off\r\ntitle qqaibot-NapCat\r\ncd /d "{shell_dir}"\r\n'
                    f'call napcat.quick.bat\r\npause\r\n')
        subprocess.run(["cmd", "/c", "start", "", bat], check=False)  # 空标题，同 AstrBot 处的坑
        log("[启动] NapCat 新窗口已打开（quick 免扫码登录；首次部署请按 SKILL.md Phase 6 用 napcat.bat 扫码）")
    log("[完成] 启动流程已执行。停止请用: python bot_manager.py stop")
    return 0


def cmd_stop(cfg, base=None):
    cmd_kill_napcat(cfg, base)
    time.sleep(1)
    cmd_kill_astrbot(cfg, base)
    time.sleep(1)
    return cmd_status(cfg)


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if cmd not in ("start", "stop", "status", "kill_astrbot", "kill_napcat"):
        print(__doc__)
        sys.exit(2)
    cfg, base = load_config()
    ensure_console_bat(base)   # 任意命令都刷新双击入口（含挪目录后的路径修正）
    return {"start": cmd_start, "stop": cmd_stop, "status": cmd_status,
            "kill_astrbot": cmd_kill_astrbot, "kill_napcat": cmd_kill_napcat}[cmd](cfg, base)


if __name__ == "__main__":
    sys.exit(main())
