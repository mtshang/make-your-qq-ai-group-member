---
name: make-your-qq-ai-group-member
description: 一键部署免费 QQ AI 群聊机器人全链路（AstrBot + NapCatQQ + 读空气插件 group_chat_plus + 预置"大肥鱼"人格卡）。当用户想要搭建/部署/安装 QQ 机器人、QQ AI bot、群聊 AI、读空气机器人、QQ 机器人的 Agent 端时使用。覆盖下载、配置、启动、扫码登录、全链路验收。
---

# QQ AI 群聊机器人一键部署（Windows）

把一个 QQ 小号变成有"人设"、会读空气的 AI 群聊机器人。全组件免费开源。

## 最终架构

```
QQ 好友/群聊
   │ (消息)
   ▼
手机/PC QQ 客户端 ←──登录── NapCatQQ（协议端，模拟 QQ 客户端）
                                │
                                │ 反向 WebSocket: ws://127.0.0.1:6199/ws
                                ▼
                           AstrBot（LLM 管家，含 WebUI :6185）
                                ├── 插件: group_chat_plus（读空气/概率回复/注意力）
                                ├── 人格卡: 大肥鱼DeepSeek（已内置）
                                └── HTTPS → DeepSeek API（文本 + 视觉双模型）
```

## 组件与来源（三大组件运行时动态下载；配置模板与人格卡预存在本 skill 内）

| 组件 | 来源 | 版本策略 |
|---|---|---|
| AstrBot | PyPI（`uv tool install astrbot`） | 最新稳定版，Python 3.12 |
| NapCatQQ | GitHub release 最新版 OneKey | `releases/latest/download/NapCat.Shell.Windows.OneKey.zip` |
| 读空气插件 | GitHub main 分支 | `archive/refs/heads/main.zip` |
| DeepSeek | 用户已有 API key | 双模型：deepseek-flash（文本）+ deepseek-v4-flash-vision-exp（视觉） |

**仓库参考**（含完整 README，遇字段疑问先查）：
- `references/AstrBot-readme.md`、`references/NapCatQQ-readme.md`、`references/astrbot_plugin_group_chat_plus-readme.md`
- `references/pitfalls.md` ← **血泪踩坑手册，开工前通读一遍，出问题先查它**
- `references/config-params.md` ← 两个配置文件的全参数说明（用户想调参数时看这个）
- README 会过时：运行 `python scripts/update_readmes.py` 可从三个仓库重新抓取最新版（参数 astrbot / napcat / plugin 只更新单个）

**脚本调用约定**：下文出现的 `verify.py`、`download.py` 一律指 `python <本skill目录>\scripts\verify.py`（无系统 Python 时按 Phase 0 换成 `uv run python`）。

## 前置条件（Phase 0 检查）

- Windows 10/11 x64（NapCat OneKey 仅支持 Windows）
- 磁盘 ≥ 2GB 空间
- 一个用作 bot 的 QQ 小号（**不要用大号**，协议端有风控风险）
- 一个聊天模型的 API key（**任何 OpenAI 兼容 API 均可**，见下节；没有的话先引导用户创建）
- 网络能访问 GitHub（脚本自动镜像轮换，无需代理也可）

## API key 与模型（用户没有 key 时先看这里）

**任何 OpenAI 兼容的聊天 API key 都能用**（DeepSeek / 通义千问 / Kimi / OpenRouter 等），模板为了开箱即用预置了 DeepSeek。用其他服务商时改 `cmd_config.json` 三处：`provider_sources[0].api_base`（API 地址）、`provider_sources[0].key`（key）、`provider[].model`（模型名）。

**推荐 DeepSeek**（便宜 + 国内直连不需要代理），官方网址：**https://platform.deepseek.com/usage**

**用户没有 API key 时的创建引导**：
1. 打开 https://platform.deepseek.com/usage 注册/登录（手机号即可）
2. 左侧菜单「API keys」→「创建 API key」→ 复制保存（**密钥只显示这一次**，关掉就看不到了）
3. 左侧「充值」→ 充值金额（最低档即可，10 元能用很久，量入充值）
4. 把 sk- 开头的 key 交给 agent 填入配置

**⚠️ 视觉模型兼容性**：模板预置了双模型（文本 + 视觉识图），其中**识图依赖视觉模型**（DeepSeek 的 `deepseek-v4-flash-vision-exp`）。如果用户提供的 API **不支持 vision 模型**，必须把识图功能关闭：插件配置 `astrbot_plugin_group_chat_plus_config.json` 中 `enable_image_processing` 改为 `false`（可顺手把 cmd_config 里的 vision provider 删掉或 `enable: false`），否则群里发图会报错。

## 代理检测（Phase 0 顺带做）

GitHub 下载脚本已内置镜像轮换，**不需要代理**；DeepSeek API 国内直连也通常没问题。代理是**可选兜底**——某些网络环境下直连 LLM API 慢/失败时才用。

1. 先问用户：**"本机有没有开代理（Clash / V2Ray 之类）？HTTP 代理端口是多少？"**
2. 用户不清楚时可以探测：
   - 常见端口试探：`verify.py port 7890`（Clash 默认）、`7897`（Clash Verge Rev）、`10809`（v2rayN HTTP）、`1080`（通用 SOCKS）——能连通即可能有代理
   - 查 Windows 系统代理：`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer`（配合 `ProxyEnable` 是否为 1）
   - 查环境变量：`echo $env:HTTP_PROXY` / `echo $env:HTTPS_PROXY`
3. 探测到代理且 LLM API 直连不稳时，填入 `cmd_config.json` 的 `http_proxy` 字段（如 `http://127.0.0.1:7890`）。**默认留空**，别画蛇添足。

## 需要向用户收集的变量

开工前**一次性**问齐，之后全部代入：

| 变量 | 说明 | 代入处 |
|---|---|---|
| `$QQ` | 用作 bot 的 QQ 号 | NapCat 配置文件名、cmd_config.json 管理员 |
| `$KEY` | 聊天模型 API key（任何 OpenAI 兼容 API，推荐 DeepSeek，见上节） | cmd_config.json |
| `$INSTALL` | 安装根目录 | 一切下载与安装的根。**默认 `D:\qqaibot`**（无 D 盘用 `C:\qqaibot`）；问用户时直接给这个默认值，用户没意见就用。路径不要含中文和空格 |

变量替换一律用 Python 脚本做（保持 BOM、避免 shell 转义事故），参考 Phase 3。

---

## Phase 0：环境检测

1. 建目录：
   ```
   $INSTALL\downloads      下载缓存
   $INSTALL\astrbot        AstrBot 数据目录（ASTRBOT_ROOT 指向这里）
   $INSTALL\napcat         NapCat 安装目录
   ```
2. 检测 Python（跑脚本用）：
   ```
   python --version
   ```
   - 有（3.10+）→ 后续命令用 `python`。
   - 没有 → 先完成 Phase 1 装 uv，然后**所有 `python` 换成 `uv run python`**（uv 自动下载托管 Python，无需手装）。

## Phase 1：安装 uv（Python 环境管理器）

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

- 安装位置 `%USERPROFILE%\.local\bin\uv.exe`。**新开 shell** 让 PATH 生效；找不到命令就用完整路径。
- uv 会自动下载 Python 3.12，**不需要**手动装 Python，也**不需要** .venv——uv tool 自动隔离环境。

## Phase 2：安装 AstrBot 并钉死数据目录

```powershell
uv tool install astrbot --python 3.12
```

**设置 `ASTRBOT_ROOT`（在 `astrbot init` 之前！**，详见 pitfalls B1，这是最容易踩的坑）：

- PowerShell：
  ```powershell
  $env:ASTRBOT_ROOT = "$INSTALL\astrbot"
  [Environment]::SetEnvironmentVariable("ASTRBOT_ROOT", "$INSTALL\astrbot", "User")
  ```
- cmd：`set ASTRBOT_ROOT=$INSTALL\astrbot` 且 `setx ASTRBOT_ROOT "$INSTALL\astrbot"`

```powershell
astrbot init
```

- `astrbot` 命令找不到 → 新开 shell，或用 `%USERPROFILE%\.local\bin\astrbot.exe`。
- 验证：`verify.py file "$INSTALL\astrbot\data"` 目录已生成。

## Phase 3：铺配置模板 + 替换变量

模板在本 skill 的 `templates\`：

| 模板 | 铺到 | 待替换 |
|---|---|---|
| `cmd_config.json` | `$INSTALL\astrbot\data\cmd_config.json`（覆盖 init 生成的） | `<YOUR_API_KEY>` → `$KEY`；`<YOUR_QQ_NUMBER>` → `$QQ` |
| `astrbot_plugin_group_chat_plus_config.json` | `$INSTALL\astrbot\data\config\astrbot_plugin_group_chat_plus_config.json`（目录不存在则创建） | 无占位符 |
| `napcat_onebot11.json` | Phase 6 再铺（NapCat 装完后） | 文件名加 QQ 号 |

**替换脚本**（保持 BOM 编码， pitfalls B2）：

```python
import json, io
p = r"<data>\cmd_config.json"
d = json.load(io.open(p, encoding="utf-8-sig"))
d["provider_sources"][0]["key"] = ["<KEY>"]
d["admins_id"] = ["<QQ>"]
io.open(p, "w", encoding="utf-8-sig").write(
    json.dumps(d, ensure_ascii=False, indent=2))
```

验证：`verify.py json` 两个文件均可解析；`verify.py jsonkey cmd_config.json platform` 等抽查。

模板已预置的关键配置（**不要乱动**）：
- 平台：仅 `qq-napcat`（aiocqhttp，反向 WS 监听 `0.0.0.0:6199`）
- 私聊免唤醒：`friend_message_needs_wake_prefix=false`（否则私聊装死，pitfalls D1）
- 分段回复：开启（interval 1.5~3.5s，段间空行是正常行为，pitfalls D3）
- 默认人格：`大肥鱼DeepSeek`（人格卡在 Phase 5 写库）
- 双 provider：deepseek-flash + deepseek-vision

## Phase 4：安装读空气插件

```powershell
python scripts/download.py https://github.com/Him666233/astrbot_plugin_group_chat_plus/archive/refs/heads/main.zip $INSTALL\downloads\plugin.zip
```

解压到 `$INSTALL\astrbot\data\plugins\astrbot_plugin_group_chat_plus\`：
- **注意 zip 内层目录名**（通常带 `-main` 后缀），解压后重命名为 `astrbot_plugin_group_chat_plus`（去掉后缀）。
- 验证：`verify.py file <插件目录>\main.py` 存在。
- **依赖不用手动装**——AstrBot 启动时自动安装 requirements.txt（pitfalls B4）。

## Phase 5：启动 AstrBot（两次启动法）

**第一次启动**（建立数据库 + 自动装插件依赖）：
```powershell
astrbot run
```
- 看到 WebUI 地址（`http://localhost:6185`）与"启动完成"日志即可。插件依赖安装可能需要 1~2 分钟。
- 然后 **Ctrl+C 停止**（要写数据库，必须先停，避免锁库）。

**写人格卡**（data_v4.db 此时已生成）：按 pitfalls B5 的 SQL 脚本，把 `templates/persona_dafeiyu.md` 写入 personas 表，`persona_id` 必须是 `大肥鱼DeepSeek`（与 cmd_config 绑定逐字符一致）。写库前先备份 `data_v4.db`。

**第二次启动**（正式运行，窗口保持开着）：
```powershell
astrbot run
```
验证：
- `verify.py port 6185` → WebUI 监听中
- **WebUI 首次登录**（用户名默认 `astrbot`，模板 dashboard.username 可改）：
  - **推荐**：启动前设环境变量预设密码（当前会话生效即可，随 `astrbot run` 启动的 shell）：
    PowerShell：`$env:ASTRBOT_DASHBOARD_INITIAL_PASSWORD = "<用户想用的密码>"`
    ⚠ 密码必须 **≥8 位且同时含大写字母、小写字母、数字**（如 `Astrbot123`），不合规会**启动直接报错**——设之前先检查
  - 或者不设变量：AstrBot 会自动生成 24 位随机密码，从启动日志 `Initial password:` 行抄给用户
  - 模板刻意不预存任何密码（空 hash 登不上，也别试 astrbot/astrbot）；首登后 WebUI 会引导改密
- 浏览器开 `http://localhost:6185` 能看到控制台
- 日志无 ERROR（人格缺失/插件加载失败会在日志里报）

## Phase 6：NapCat 安装与扫码

1. **下载解压**：
   ```powershell
   python scripts/download.py https://github.com/NapNeko/NapCatQQ/releases/latest/download/NapCat.Shell.Windows.OneKey.zip $INSTALL\napcat\OneKey.zip
   ```
   解压到 `$INSTALL\napcat\`。

2. **运行安装器**：启动 `$INSTALL\napcat\NapCatInstaller.exe`（GUI，需要用户配合点击），等待它下载 QQ 内核。失败 → pitfalls A2（重试/换网络）。装完目录里出现 `NapCat.*.Shell\`。

3. **铺反连配置**（登录前做，pitfalls C3）：
   把 `templates\napcat_onebot11.json` 复制为：
   ```
   $INSTALL\napcat\NapCat.*.Shell\versions\*\resources\app\napcat\config\onebot11_$QQ.json
   ```
   （版本号目录用通配定位，**不要写死**；文件名必须带 QQ 号。）

4. **启动并扫码**：进 `NapCat.*.Shell\` 目录跑 `napcat.bat`。
   - ⚠ **绝对不要用 `bootmain\` 里的同名 bat**（pitfalls C1，Error Code 2 元凶）。
   - 出二维码后让用户用**手机 QQ（bot 小号）**扫码登录。

5. **验证打通**：
   - NapCat 窗口显示登录成功；
   - AstrBot 日志出现 WebSocket 连接成功行（ NapCat → `ws://127.0.0.1:6199/ws`，必须带 `/ws`，pitfalls C2）；
   - `verify.py port 6199` 在 AstrBot 侧监听中；
   - WebUI「平台适配器」→ 消息平台在线。

## Phase 7：全链路验收（人工 + 日志）

| # | 测试 | 预期 |
|---|---|---|
| 1 | 私聊 bot 发 `/help` | 返回指令菜单（无响应查 pitfalls D2） |
| 2 | 私聊闲聊一句 | "大肥鱼"人设口语化回复 |
| 3 | 群里 @bot 说话 | 回复；@/引用行为按概率（非每次必 @） |
| 4 | 群里不 @ 说闲话 | 概率触发（0.1），60s 内最多 6 条 |
| 5 | 群里发一张图 | 视觉模型识图并吐槽 |
| 6 | 查 `$INSTALL\astrbot\logs\` 日志 | 有读空气概率判定/决策相关日志行（决策推理块默认关闭，无推理输出属正常） |

全部通过 → 部署完成。任何一步失败 → 按 `references/pitfalls.md` 对应章节排查。

## 日常使用（交付时告知用户）

- **日常启动顺序**：先 `astrbot run`（窗口保持开）→ 再 NapCat 的 `napcat.quick.bat`（免扫码）。关机重开后按此顺序。
- **改配置**：改文件 → **重启 AstrBot 后**才能动 WebUI（pitfalls B3 铁律，顺序反了修改全丢）。
- **WebUI 密码**：首登用预设密码（环境变量）或日志里的随机密码，登录后立即在 WebUI 改掉（pitfalls B6）。
- **省 token**：决策 AI 推理（`enable_decision_ai_reasoning`）**默认已关闭**；若决策质量不满意可开启观察日志，确认后记得关回（它对每条过筛消息都输出推理块，token 大头）。
- **风控提醒**：bot 小号避免频繁群发/加好友，首次在常用设备+常用 IP 登录降低风控概率。

## 故障速查索引

| 症状 | 查 |
|---|---|
| 下载失败/假文件 | pitfalls A1 |
| NapCat 装 QQ 内核失败 | pitfalls A2 |
| 配置改了没生效 | pitfalls B1（ASTRBOT_ROOT）/ B3（WebUI 覆盖） |
| JSON 报 BOM 错 | pitfalls B2 |
| 人格挂不上 | pitfalls B5（persona_id 不一致） |
| WebUI 登不上 | pitfalls B6（密码机制） |
| napcat.bat 报 Error Code 2 | pitfalls C1（bootmain 陷阱） |
| NapCat 连不上 AstrBot | pitfalls C2（/ws 后缀） |
| 私聊没反应 | pitfalls D1 |
| /help 不触发 | pitfalls D2 |
| 回复有空行 | pitfalls D3 |
| gcp_reset 禁不掉 | pitfalls D4 |
| 图片报 400 | pitfalls D5 |
| token 消耗高 | pitfalls D6 |
| 群里话太多/太冷 | pitfalls D7 |
| @/引用行为不对 | pitfalls D8 |
