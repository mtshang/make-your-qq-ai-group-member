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
| DeepSeek | 用户已有 API key | 双 provider 均为 deepseek-flash（已原生支持视觉，须关思考模式 pitfalls D10） |

**仓库参考**（含完整 README，遇字段疑问先查）：
- `references/AstrBot-readme.md`、`references/NapCatQQ-readme.md`、`references/astrbot_plugin_group_chat_plus-readme.md`
- `references/pitfalls.md` ← **血泪踩坑手册，开工前通读一遍，出问题先查它**
- `references/config-params.md` ← 两个配置文件的全参数说明（用户想调参数时看这个）
- README 会过时：运行 `python scripts/update_readmes.py` 可从三个仓库重新抓取最新版（参数 astrbot / napcat / plugin 只更新单个）

**脚本调用约定**：下文出现的 `verify.py`、`download.py` 一律指 `python <本skill目录>\scripts\verify.py`（无系统 Python 时按 Phase 0 换成 `uv run python`）。

**行为约定（全程生效，最重要的一条）**：遇到**任何**问题——报错、卡住、需要等待、需要决策——必须立刻让用户知道现状，并明确说出**这一步需要用户做什么**。具体要求：

1. **不许静默失败**：重试失败、下载失败、命令卡死，都不能自己吞掉或无上限重试。最多自动重试 2 次，仍失败就停下向用户报告。
2. **每条消息带行动项**：告诉用户现状（一句话）之后，必须给出具体的下一步，例如：
   - 「凭据授权窗口弹在你屏幕上了，请完成 GitHub 登录后回复我"好了"」
   - 「NapCat 安装器需要你点击，装完后告诉我」
   - 「扫码窗口出现了，请用**小号**扫码，扫完说一声」
   - 「这一步我自己修不了，需要你把 AstrBot 窗口最后 20 行日志发给我」
3. **自己修好的也要报备**：自动重试成功、自动修正了路径之类，补一句「刚才 X 失败，已自动 Y，你无需操作」——保持信息透明，不许装作没发生。
4. **等待用户时明确说在等什么**：不要用模糊的"稍等"，要说清在等哪个动作完成（如「等你扫码」vs「等 WebUI 端口起来，约 1 分钟」）。
5. **一切状态落进 `deploy_state.json`**：开工确认后立刻在 `$INSTALL` 创建它（模板 `templates/deploy_state.json`），此后：
   - **每完成一个 Phase**，把 `progress` 里对应字段改成 `done`，并把新获得的路径/QQ 号写进对应字段；
   - **判读结果优先读这个文件**（文件读写对所有 agent 都可靠），读终端回显/扫日志只作兜底——GUI 型 agent 读屏易错，命令式 agent 也省得翻历史输出；
   - 中断恢复时**先读它**：progress 里第一个非 `done` 的 Phase 就是断点，从那里继续，已完成步骤不要重做。
6. **窗口管理透明化**：每开一个新的终端窗口 / 安装器 / 扫码窗口，必须**同时**告诉用户三件事——这是什么窗口、要**保留**还是**可以关**、用户需要**看什么或做什么**。示例话术：
   - 「NapCat 安装器窗口弹出来了，请点击安装；装完（napcat 目录出现 NapCat.数字.Shell 文件夹）回我"装好了"，窗口关掉没关系」
   - 「扫码窗口出现了，请用**小号**扫码；**登录成功前千万别关**这个窗口」
   - 「AstrBot 服务窗口已开并在滚日志，保留别动，你不用操作」
   不许默默开窗口，也不许默默关窗口。全程窗口处置对照见「终端窗口一览」表。

## 前置条件（Phase 0 检查）

- Windows 10/11 x64（NapCat OneKey 仅支持 Windows）
- 磁盘 ≥ 2GB 空间
- **本地电脑部署**（不要云电脑/云手机：QQ 风控看常用设备+IP，机房 IP 大概率触发风控）
- 一个用作 bot 的 QQ 小号（**不要用大号**，协议端有风控风险）
- 一个聊天模型的 API key（**任何 OpenAI 兼容 API 均可**，见下节；没有的话先引导用户创建）
- 网络能访问 GitHub（脚本自动镜像轮换，无需代理也可）

## API key 与模型（用户没有 key 时先看这里）

**任何 OpenAI 兼容的聊天 API key 都能用**（DeepSeek / 通义千问 / Kimi / OpenRouter 等），模板为了开箱即用预置了 DeepSeek。用其他服务商时改 `cmd_config.json` 三处：`provider_sources[0].api_base`（API 地址）、`provider_sources[0].key`（key）、`provider[].model`（模型名）。

**推荐 DeepSeek**（便宜 + 国内直连不需要代理），官方网址：**https://platform.deepseek.com/usage**

> ⚠ 模型名快照警告（2026-10 实测更新）：`deepseek-flash`（= V4.1-Flash）**已原生支持视觉**，旧视觉模型 `deepseek-v4-flash-vision-exp` 已退役（仍被接受但别再填）；`deepseek-flash` **默认开启思考模式**（白烧 reasoning token + 拖慢回复），模板已通过 `custom_extra_body` 关闭（pitfalls D10）。部署时仍应去官网核对最新模型名，上游改名按实际替换 `provider[].model`。

**用户没有 API key 时的创建引导**：
1. 打开 https://platform.deepseek.com/usage 注册/登录（手机号即可）
2. 左侧菜单「API keys」→「创建 API key」→ 复制保存（**密钥只显示这一次**，关掉就看不到了）
3. 左侧「充值」→ 充值金额（最低档即可，10 元能用很久，量入充值）
4. 把创建好的 key 完整复制交给 agent 填入配置（前缀因服务商而异，如 sk- / sk-or- / AIza- 等）

**⚠️ 视觉模型兼容性**：模板预置了双 provider 结构，其中**识图依赖视觉模型**（`deepseek/deepseek-vision`，当前指向 `deepseek-flash`——该模型已原生支持视觉）。如果用户提供的 API **不支持 vision 模型**，必须把识图功能关闭：插件配置 `astrbot_plugin_group_chat_plus_config.json` 中 `enable_image_processing` 改为 `false`（可顺手把 cmd_config 里的 vision provider 删掉或 `enable: false`），否则群里发图会报错。

## 代理检测（Phase 0 顺带做）

GitHub 下载脚本已内置镜像轮换，**不需要代理**；DeepSeek API 国内直连也通常没问题。代理是**可选兜底**——某些网络环境下直连 LLM API 慢/失败时才用。

1. 先问用户：**"本机有没有开代理（Clash / V2Ray 之类）？HTTP 代理端口是多少？"**
2. 用户不清楚时可以探测：
   - 常见端口试探：`verify.py port 7890`（Clash 默认）、`7897`（Clash Verge Rev）、`10809`（v2rayN HTTP）、`1080`（通用 SOCKS）——能连通即可能有代理
   - 查 Windows 系统代理：`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer`（配合 `ProxyEnable` 是否为 1）
   - 查环境变量：`echo $env:HTTP_PROXY` / `echo $env:HTTPS_PROXY`
3. 探测到代理且 LLM API 直连不稳时，填入 `cmd_config.json` 的 `http_proxy` 字段（如 `http://127.0.0.1:7890`）。**默认留空**，别画蛇添足。
4. ⚠ 本机设了系统代理时，用 curl/wget 探测**本地端口**（6185/6199）会被代理截胡返回 502/504——探测本地一律用 `verify.py port`（socket 直连不走代理），或给 curl 加 `--noproxy 127.0.0.1`。

## 需要向用户收集的变量

开工前**一次性**问齐，之后全部代入：

| 变量 | 说明 | 代入处 |
|---|---|---|
| `$KEY` | 聊天模型 API key（任何 OpenAI 兼容 API，推荐 DeepSeek，见上节） | cmd_config.json |
| `$INSTALL` | 安装根目录 | 一切下载与安装的根。**默认 `D:\qqaibot`**（无 D 盘用 `C:\qqaibot`）；问用户时直接给这个默认值，用户没意见就用。路径不要含中文和空格 |

**bot 的 QQ 号不收集**——NapCat 扫码登录后从它生成的配置文件名里读实际登录号（Phase 6 步骤 4），杜绝填错号/文件名对不上的问题。管理员（admins_id）届时回填。

**但 QQ 小号本身要在开工前确认**——明确问用户："用作 bot 的 QQ 小号准备好了吗？"并讲清危害：
> NapCat 是第三方协议端，模拟 QQ 客户端行为，**账号存在被风控/冻结/封禁的风险**。大号里绑着支付、社交关系、游戏资产，被封的损失不可逆；小号被封只是换个号重来。所以**必须用小号**，且最好是注册过一段时间、有过正常使用的号（全新号风控概率更高）。

代理端口顺带问一句（可选，见「代理检测」节）。

变量替换一律用 Python 脚本做（保持 BOM、避免 shell 转义事故），参考 Phase 3。

### 开工确认（必须，不得跳过）

问齐后，把结果整理成表格发给用户**过目确认**：

```
| 确认项 | 值 |
|---|---|
| bot QQ 小号 | 已准备 ✓（已知悉风控风险，不用大号） |
| API key | ****<尾 4 位>（已隐藏，前缀因服务商而异） |
| 安装目录 | <填入>（默认 D:\qqaibot） |
| 代理 | 无 / 127.0.0.1:<端口>（备用） |
```

- **必须等用户明确回复确认**（如"确认/没问题/开工"）才能进入 Phase 0。
- 用户纠正任何一项 → 更新表格 → 再次请求确认。
- key 只显示尾 4 位，**不要在对话里完整回显**。

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

**设置 `ASTRBOT_ROOT` 并在目标目录执行 init**（详见 pitfalls B1，两个坑都要防）：

- **推荐：单条自包含命令**——变量、工作目录、init 绑在同一条命令里，子进程必然继承，**完全不依赖 shell 会话状态**（GUI 型/命令式 agent 通吃）：
  ```powershell
  powershell -Command "$env:ASTRBOT_ROOT='<INSTALL>\astrbot'; Set-Location '<INSTALL>\astrbot'; & '<astrbot_exe>' init -y"
  ```
  （`<astrbot_exe>` 用完整路径，如 `%USERPROFILE%\.local\bin\astrbot.exe`，连 PATH 问题一起绕开；`Set-Location` 不能省——v4.28.2 实测 `init` 是 **cwd 语义**，无视 ASTRBOT_ROOT 把 data 建到当前目录，pitfalls B1 变种）
- setx 持久化仍做一次（给用户以后手动跑 astrbot 的场景兜底，对当前会话无效只影响新进程）：
  cmd：`setx ASTRBOT_ROOT "<INSTALL>\astrbot"`（安全策略拦 reg/setx 时用 Python winreg 等效写入用户环境变量）
- **防呆验证**：`verify.py file "$INSTALL\astrbot\data"` 目录已生成即成功。若 data 出现在**别处**（agent 工作区/用户主目录），说明 cwd 或变量没带上——删掉错误目录（确认无数据），用上面的单条命令重来。
- **`-y` 必须带**：跳过交互式确认（不带的话 init 卡在提问，agent 场景直接挂起）。
- v4.28.2 实测：`init` **不生成** `cmd_config.json`（属正常，Phase 3 直接铺模板），只生成 `data\` 骨架。

## Phase 3：铺配置模板 + 替换变量

模板在本 skill 的 `templates\`：

| 模板 | 铺到 | 待替换 |
|---|---|---|
| `cmd_config.json` | `$INSTALL\astrbot\data\cmd_config.json`（覆盖 init 生成的） | `<YOUR_API_KEY>` → `$KEY`；`<YOUR_QQ_NUMBER>` **此时不填**，Phase 6 扫码后回填 |
| `astrbot_plugin_group_chat_plus_config.json` | `$INSTALL\astrbot\data\config\astrbot_plugin_group_chat_plus_config.json`（目录不存在则创建） | 无占位符 |
| `napcat_onebot11.json` | Phase 6 登录后作注入源（合并进 NapCat 生成的配置） | 无需改 |

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

**立刻验证 API key 可用**（推荐，30 秒防翻车——别等 Phase 7 验收才发现 401）：

```python
import urllib.request
req = urllib.request.Request("https://api.deepseek.com/models",
    headers={"Authorization": "Bearer <KEY>"})
print(urllib.request.urlopen(req, timeout=15).status)   # 200 = key 有效
```

- 200 → key 有效，继续；401 → key 抄错/未生效/未充值，**立刻停下问用户**（行为约定第 2 条）；其他服务商把 URL 换成 `provider_sources[0].api_base + /models`。
- 注意：这步只验鉴权不验模型。若后面聊天报"模型不存在"，回看上方模型名快照警告。

**创建部署状态文件**（Phase 5 的启动全靠它；这也是全程的断点记录）：把 `templates/deploy_state.json` 复制到 `$INSTALL\deploy_state.json`，填两个字段：
- `astrbot_root` → `$INSTALL\astrbot`；`astrbot_exe` → astrbot.exe 实际路径（uv 默认 `%USERPROFILE%\.local\bin\astrbot.exe`）
- `napcat_shell_dir` / `napcat_root` → **暂留空字符串**（Phase 6 装完 NapCat 回填），bot_manager 会自动只启动 AstrBot
- 把 `progress.phase3_config` 改为 `done`。此后每完成一步都更新对应进度字段（行为约定第 5 条）

模板已预置的关键配置（**不要乱动**）：
- 平台：仅 `qq-napcat`（aiocqhttp，反向 WS 监听 `127.0.0.1:6199`，仅本机可连，无防火墙弹窗）
- 私聊免唤醒：`friend_message_needs_wake_prefix=false`（否则私聊装死，pitfalls D1）
- 分段回复：开启（interval 1.5~3.5s，段间空行是正常行为，pitfalls D3）
- 默认人格：`大肥鱼DeepSeek`（人格卡在 Phase 5 写库）
- 双 provider 分工：`deepseek/deepseek-flash` 只管文本/工具；`deepseek/deepseek-vision`（同模型、带 image modality）专收图
- 思考模式：两个 provider 的 `custom_extra_body` 已注入 `{"thinking": {"type": "disabled"}}`——deepseek-flash 默认开思考，群聊场景白烧 reasoning token（pitfalls D10），换其他模型/服务商时核对此项

## Phase 4：安装读空气插件

```powershell
python scripts/download.py https://github.com/Him666233/astrbot_plugin_group_chat_plus/archive/refs/heads/main.zip $INSTALL\downloads\plugin.zip
```

解压到 `$INSTALL\astrbot\data\plugins\astrbot_plugin_group_chat_plus\`：
- **注意 zip 内层目录名**（通常带 `-main` 后缀），解压后重命名为 `astrbot_plugin_group_chat_plus`（去掉后缀）。
- 验证：`verify.py file <插件目录>\main.py` 存在。
- **依赖不用手动装**——AstrBot 启动时自动安装 requirements.txt（pitfalls B4）。

## 终端窗口一览（部署期，agent 必须照此向用户说明）

部署全程会产生多个窗口，**每开一个都按行为约定第 6 条告知用户处置方式**，对照表：

| 窗口 | 出现于 | 谁操作 | 处置 + 话术要点 |
|---|---|---|---|
| agent 的命令窗口 | 全程 | agent | 用户无需理会 |
| AstrBot 服务窗口 | Phase 5 两次启动、验收期 | agent 拉起 | **保留**（服务本体）：「AstrBot 窗口已开并在滚日志，保留别动，你不用操作」 |
| AstrBot 窗口（stop 后残留） | Phase 5 写库/改配置前 | agent | 服务被 stop 后窗口停在"请按任意键继续"——**属正常残留**，用户随手关掉即可，agent 不必处理 |
| NapCat 安装器窗口 | Phase 6 步骤 2 | **用户** | **用户点安装**；装完回"装好了"；**窗口可关** |
| NapCat 扫码窗口 | Phase 6 步骤 3 | **用户** | **用小号扫码**；**登录成功前千万别关**；成功后窗口保留（协议端服务本体） |
| NapCat 常驻窗口 | Phase 6 步骤 5 重启后 | agent 拉起 | **保留**（协议端服务本体） |

**交付后日常**（Phase 8 配好 bot_manager 后）：`start` 开出的 AstrBot + NapCat 两个窗口就是服务本体，**别手点右上角 X**（等于直接拔电源）；要停就走 `stop`，`stop` 后窗口停在按键提示，随手关掉即可。

## Phase 5：启动 AstrBot（两次启动法）

**第一次启动**（建立数据库 + 自动装插件依赖）：
```powershell
python <skill目录>\scripts\bot_manager.py start
```
- **必须用 bot_manager 启动，禁止裸跑 `astrbot run`**——它是前台常驻进程，命令式 agent 会挂死（pitfalls B7）。bot_manager 开新窗口跑服务、轮询 `6185` 就绪后自己退出，agent 零风险；NapCat 未配置时自动只启动 AstrBot，正好符合当前阶段。
- 启动完成标志：bot_manager 输出 `WebUI 已监听`（或 `status` 显示 AstrBot RUNNING）。**首次启动要装插件依赖，1~3 分钟属正常**——bot_manager 最多等 120 秒，超时警告≠失败：窗口还在滚日志就继续等（`status` 复查），窗口消失/停在 pause 才是启动失败。
- 然后 **停止**（写数据库必须先停，避免锁库）：`python bot_manager.py stop`。人类用户手动跑的话在 AstrBot 窗口按 Ctrl+C。

**写人格卡**（data_v4.db 此时已生成）：按 pitfalls B5 的 SQL 脚本，把 `templates/persona_dafeiyu.md` 写入 personas 表，`persona_id` 必须是 `大肥鱼DeepSeek`（与 cmd_config 绑定逐字符一致）。写库前先备份 `data_v4.db`。

**第二次启动**（正式运行）：
- 先想好 WebUI 密码（≥8 位含大小写+数字，如 `Astrbot123`），在当前 shell 设预设变量：
  PowerShell：`$env:ASTRBOT_DASHBOARD_INITIAL_PASSWORD = "<密码>"`
  （bot_manager 的子窗口会继承它；不设则 AstrBot 自动生成随机密码，从 AstrBot 窗口日志 `Initial password:` 行抄给用户。模板刻意不预存密码，空 hash 别试 astrbot/astrbot）
- 再启动：
```powershell
python <skill目录>\scripts\bot_manager.py start
```
验证：
- `verify.py port 6185` → WebUI 监听中
- **WebUI 首次登录**：用户名默认 `astrbot`（模板 dashboard.username 可改），密码用上面预设值或日志随机密码；首登后 WebUI 会引导改密
- 浏览器开 `http://localhost:6185` 能看到控制台
- 日志无 ERROR（人格缺失/插件加载失败会在日志里报）

## Phase 6：NapCat 安装与扫码

1. **下载解压**：
   ```powershell
   python scripts/download.py https://github.com/NapNeko/NapCatQQ/releases/latest/download/NapCat.Shell.Windows.OneKey.zip $INSTALL\napcat\OneKey.zip
   ```
   解压到 `$INSTALL\napcat\`。

2. **运行安装器**：启动 `$INSTALL\napcat\NapCatInstaller.exe`（GUI，需要用户配合点击），等待它下载 QQ 内核。失败 → pitfalls A2（重试/换网络）。装完目录里出现 `NapCat.*.Shell\`。

3. **启动并扫码**：进 `NapCat.*.Shell\` 目录跑 `napcat.bat`。
   - ⚠ **绝对不要用 `bootmain\` 里的同名 bat**（pitfalls C1，Error Code 2 元凶）。
   - 出二维码后让用户用**手机 QQ（bot 小号）**扫码登录——**扫码前再问一遍确认是小号**，扫错成大号就立刻下线重扫。

4. **读取实际 QQ 号**（不问用户，扫码自动获得）：登录成功后 NapCat 会在
   ```
   NapCat.*.Shell\versions\*\resources\app\napcat\config\
   ```
   下生成 `onebot11_<QQ号>.json` / `napcat_<QQ号>.json`——从文件名直接读出 QQ 号（记为 `$QQ`）。**立刻写进 deploy_state.json**：`qq` 填号、`napcat_shell_dir`/`napcat_root` 填实际路径。
   **读号后立刻改 `napcat.quick.bat` 的占位账号**：OneKey 硬编码 `-q 10086`，把占位号替换为 `$QQ`（Python/编辑器均可）——不改则交付后用户每次重启都要重新扫码（pitfalls C7）。

5. **注入反连配置**：NapCat 生成的配置里没有反向 WS 设置。用脚本把模板的 `network.websocketClients` 合并进生成的 `onebot11_$QQ.json`（其余字段保持原样）：
   ```python
   import json, io
   src = json.load(io.open(r"<skill目录>\templates\napcat_onebot11.json", encoding="utf-8-sig"))
   p = r"<config目录>\onebot11_<QQ>.json"     # 从步骤 4 的文件名来
   d = json.load(io.open(p, encoding="utf-8-sig"))
   d["network"]["websocketClients"] = src["network"]["websocketClients"]
   io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
   ```
   然后重启 NapCat：关掉旧窗口，重新跑 `napcat.quick.bat`（已登录免扫码）。
   备选：也可在 NapCat WebUI「网络配置」页手动加反向 WS（`ws://127.0.0.1:6199/ws`），效果相同。

6. **回填管理员**：把 `$INSTALL\astrbot\data\cmd_config.json` 的 `<YOUR_QQ_NUMBER>` 替换为 `$QQ`（Python 脚本，utf-8-sig），**重启 AstrBot**（`bot_manager.py stop` → `start`）。完成后把 `progress.phase6_link_up` 改 `done`。

7. **验证打通**：
   - NapCat 窗口显示登录成功；
   - AstrBot 日志出现 WebSocket 连接成功行（ NapCat → `ws://127.0.0.1:6199/ws`，必须带 `/ws`，pitfalls C2）；
   - `verify.py port 6199` 在 AstrBot 侧监听中；
   - WebUI「平台适配器」→ 消息平台在线。

## Phase 7：全链路验收（人工 + 日志）

| # | 测试 | 预期 |
|---|---|---|
| 1 | 私聊 bot 发 `/help` | 返回指令菜单（无响应查 pitfalls D2） |
| 2 | 私聊闲聊一句 | "大肥鱼"人设口语化回复 |
| 3 | 群里 @bot 说话 | 正常回复（默认纯文本、不 @ 不引用属预期行为；想要 @ 见 pitfalls D8） |
| 4 | 群里不 @ 说闲话 | 概率触发（0.1），60s 内最多 6 条 |
| 5 | 群里发一张图 | 视觉模型识图并吐槽 |
| 6 | 群里**引用一条带图的消息**提问 | 走 caption/vision 链路正常回复，不报 400（验证 flash 模型不接图） |
| 7 | 查 `$INSTALL\astrbot\logs\` 日志 | 有读空气概率判定/决策相关日志行（决策推理块默认关闭，无推理输出属正常） |

全部通过 → 进入「交付前 DIY 询问」。任何一步失败 → 按 `references/pitfalls.md` 对应章节排查。

## 交付前 DIY 询问（Phase 7 通过后必须执行）

验收通过后，**主动**把下面这张表发给用户，问一句「以上有没有想调整的？没有就直接交付」：

| DIY 项 | 当前默认 | 想改就说 | 改完效果 |
|---|---|---|---|
| 人格卡 | "大肥鱼"DeepSeek 小鲸鱼 | 重写人格卡文本（pitfalls B5） | 换成任何人设：管家/东北大哥/猫娘… |
| 话多话少 | 基础概率 0.1，60 秒最多 6 条 | `initial_probability` / `reply_density_max_replies` | 更粘人 ↔ 更高冷 |
| 时段活跃度 | 晚间最活跃(1.25)、深夜几乎沉默(0.15) | `reply_time_periods` | 让它半夜彻底闭嘴 / 通宵话痨 |
| 触发词 | DeepSeek / 大肥鱼 / 吃白饭 | `trigger_keywords` | 给 bot 起新外号，喊了必回 |
| 真人感细节 | 2% 打错字 + 模拟打字延迟 + 拟人静默 | `typo_error_rate` / `typing_*` | 更像真人 ↔ 更正经 |
| @ 与引用 | 关（纯文本回复） | pitfalls D8 | 每次必 @ / 想要概率性 @ |
| 主动开话题 | 关 | `enable_proactive_chat` | 群里冷场时主动水群（建议先跑稳几天再开） |
| 私聊 | 插件不管，AstrBot 原生人格回复 | `enable_private_chat` | 私聊也走读空气 |
| 识图 | 开（走视觉模型） | `enable_image_processing` | API 不支持视觉时的关闭开关 |

执行规则：
- 用户点名任意项 → 按 `references/config-params.md` 对应章节修改 → **涉及配置文件的改完必须重启 AstrBot**（pitfalls B3）→ 让用户群里复测效果。
- 用户说"不用/都行" → 直接进入 Phase 8 / 交付。
- 这张表只问**一次**，别反复推销。

## Phase 8（可选）：一键启动器 bot_manager

验收通过后给用户配置日常启停工具（免记启动顺序、一键全停）。脚本 `scripts/bot_manager.py`，三个命令：

```
python bot_manager.py start    按序启动：AstrBot 先（等 WebUI 就绪）→ NapCat 后（各开独立窗口，已启动的自动跳过）
python bot_manager.py stop     反序停止：NapCat(QQ.exe) 先，AstrBot 后
python bot_manager.py status   只读探测两服务状态
```

1. **补全配置**：`$INSTALL\deploy_state.json` 在 Phase 3 已创建，把两个空字段填上：`napcat_shell_dir` → Phase 6 装出的实际目录（如 `D:\qqaibot\napcat\NapCat.52230.Shell`）；`napcat_root` → `$INSTALL\napcat`。同时把 `qq` 字段填上（Phase 6 已读到）。填完 `status` 应能探测 NapCat（STOPPED 属正常）。
2. **验证**：先跑 `status` 看状态——AstrBot 应 STOPPED；**NapCat 若仍是 RUNNING（Phase 6 留下的登录态）不要硬 stop**（杀登录实例 = 重新扫码，pitfalls C5/C6），`start` 会自动跳过在跑的、只补起 AstrBot。确认 AstrBot 正常后可再 `stop` → `start` 完整走一遍（此时 quick.bat 已是真实 QQ，NapCat 免扫码重启）。**stop 会真杀进程，只能在部署完成、确认无其他业务共用时执行**。
3. **交付话术**：日常开机用 `start`，关机/维护用 `stop`；**首次扫码和调试仍按 Phase 5/6 原方式**（napcat.bat 扫码需要 NapCat 自己的窗口交互）。

> 设计边界：刻意不做"单窗口聚合两进程日志"——NapCat 首次登录要交互、两进程输出编码不同、Windows 下 Ctrl+C 信号转发不可靠。独立窗口 + 一键启停是可靠性最优解。

## 日常使用（交付时告知用户）

- **日常启动/停止**：一键 `python bot_manager.py start` / `stop`（配置好 Phase 8 后）；手动方式：先 `astrbot run`（窗口保持开）→ 再 NapCat 的 `napcat.quick.bat`（免扫码）。关机重开后按此顺序。
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
| agent 卡在启动命令 | pitfalls B7（常驻进程） |
| 窗口启动成功秒死/日志戛然而止 | pitfalls B8（沙箱回收服务窗口） |
| napcat.bat 报 Error Code 2 | pitfalls C1（bootmain 陷阱） |
| NapCat 连不上 AstrBot | pitfalls C2（/ws 后缀） |
| NapCat 启动终端不出二维码 | pitfalls C4（qrcode.png 兜底/重跑必出） |
| bot 掉线且开过多个实例 | pitfalls C5（同号互踢连锁） |
| 杀进程误伤别的窗口 | pitfalls C6（禁按窗口标题杀） |
| 每次重启都要重新扫码 | pitfalls C7（quick.bat 占位号没改） |
| 私聊没反应 | pitfalls D1 |
| /help 不触发 | pitfalls D2 |
| 回复有空行 | pitfalls D3 |
| gcp_reset 禁不掉 | pitfalls D4 |
| 图片报 400 | pitfalls D5 |
| token 消耗高 | pitfalls D6 |
| 回复慢/token 高但 D6 已排除 | pitfalls D10（思考模式没关） |
| 群里话太多/太冷 | pitfalls D7 |
| @/引用行为不对 | pitfalls D8 |
| 升级后全员沉默 | pitfalls D9（空白名单语义依赖） |
