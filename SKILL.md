---
name: make-your-qq-ai-group-member
description: 一键部署免费 QQ AI 群聊机器人全链路（AstrBot + NapCatQQ + 读空气插件 group_chat_plus + 预置"大肥鱼"人格卡）。当用户想要搭建/部署/安装 QQ 机器人、QQ AI bot、群聊 AI、读空气机器人、QQ 机器人的 Agent 端时使用。覆盖下载、配置、启动、扫码登录、全链路验收。
---

# QQ AI 群聊机器人一键部署（Windows）

把一个 QQ 小号变成有"人设"、会读空气的 AI 群聊机器人。全组件免费开源。

## 版本检查（开工第一步，失败不阻塞）

skill 会持续迭代修坑，**开工前先确认用的是最新版**（10 秒）：

1. 读本 skill 根目录 `version.json` 的 `version`（本地版本）。
2. 拉远端版本号对比（按序试，第一个成功即用；都带超时，如 `curl -s --max-time 10`）：
   ```
   curl -s https://cdn.jsdelivr.net/gh/mtshang/make-your-qq-ai-group-member@main/version.json
   curl -s https://raw.githubusercontent.com/mtshang/make-your-qq-ai-group-member/main/version.json
   curl -s https://ghfast.top/https://raw.githubusercontent.com/mtshang/make-your-qq-ai-group-member/main/version.json
   ```
   仓库地址以 `version.json` 的 `repo_url` 字段为准；jsdelivr 对国内网络最友好，放第一位。
3. 对比结果二选一：
   - **一致**（或三个源都拉不到/仓库私有 404/超时）→ **直接跳过继续正常流程，不许卡在这一步**；
   - **远端更新** → 告知用户「skill 有新版本 vX.Y.Z，是否更新到最新版？」，同意则更新（**优先 clone**——拿到本 skill 的多数方式不是 git clone，目录里没有 `.git`，就地 pull 大概率用不上；clone 到新目录旧目录保留，可随时回退）：
     - **首选：带镜像重新 clone**：`git clone --depth 1 https://ghfast.top/https://github.com/mtshang/make-your-qq-ai-group-member.git <新目录>`（镜像前缀轮换候选：`ghfast.top`、`gh-proxy.com`——即 `https://gh-proxy.com/https://github.com/<repo>.git`；直连也值得试一发）。clone 完**用新目录里的 skill 继续**，并告知用户新位置；
     - 备选：本 skill 目录本身是 git 仓库（有 `.git`）→ 就地 `git -C <skill目录> pull --ff-only`（更省事；失败回到上面 clone）；
     - 用户选择不更新 → 用当前版本继续。
   - **更新成功后重新读本 SKILL.md**（内容可能已变化），再继续。

> **维护者纪律**：每次改动 skill 内容，同步更新 `version.json` 的 `version`（语义化：修坑 +1 patch / 新能力 +1 minor）、`updated` 日期和 `notes` 一句话要点，随 commit 一起 push——版本检查只认这个文件。

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
   - 「NapCat 安装器窗口弹出来了，它启动后自动安装，你不用点任何东西；卡住或报错告诉我」
   - 「扫码窗口出现了，请用**小号**扫码，扫完说一声」
   - 「这一步我自己修不了，需要你把 AstrBot 窗口最后 20 行日志发给我」
3. **自己修好的也要报备**：自动重试成功、自动修正了路径之类，补一句「刚才 X 失败，已自动 Y，你无需操作」——保持信息透明，不许装作没发生。
4. **等待用户时明确说在等什么**：不要用模糊的"稍等"，要说清在等哪个动作完成（如「等你扫码」vs「等 WebUI 端口起来，约 1 分钟」）。
5. **一切状态落进 `deploy_state.json`**：开工确认后立刻在 `$INSTALL` 创建它（模板 `templates/deploy_state.json`），此后：
   - **每完成一个 Phase**，把 `progress` 里对应字段改成 `done`，并把新获得的路径/QQ 号写进对应字段；
   - **判读结果优先读这个文件**（文件读写对所有 agent 都可靠），读终端回显/扫日志只作兜底——GUI 型 agent 读屏易错，命令式 agent 也省得翻历史输出；
   - 中断恢复时**先读它**：progress 里第一个非 `done` 的 Phase 就是断点，从那里继续，已完成步骤不要重做。
6. **窗口管理透明化**：每开一个新的终端窗口 / 安装器 / 扫码窗口，必须**同时**告诉用户三件事——这是什么窗口、要**保留**还是**可以关**、用户需要**看什么或做什么**。示例话术：
   - 「NapCat 安装器窗口弹出来了，**启动即自动安装 QQ 内核，全程无需你操作**；窗口保留别关（关窗=中断安装），装完我自动检测到并继续」
   - 「扫码窗口出现了，请用**小号**扫码；**登录成功前千万别关**这个窗口」
   - 「AstrBot 服务窗口已开并在滚日志，保留别动，你不用操作」
   不许默默开窗口，也不许默默关窗口。全程窗口处置对照见「终端窗口一览」表。
7. **长期使用必须用拷贝，不直接依赖 skill 目录**：skill 内的脚本/模板只服务部署期。交付后要长期运行或引用的东西（bot_manager、启动脚本等）一律**用拷贝到部署目录的副本**——bot_manager 任意命令运行时自动把自身拷为 `$INSTALL\.bot_runtime\bot_manager.py`（运行时副本），`机器人启动.bat` 用相对路径（`%~dp0`）调它，skill 目录日后移动/更新/删除都不影响已交付的机器人。agent 给用户写自启动/快捷方式/文档时**只准引用部署目录内的路径，禁止引用 skill 目录内的路径**；确需长期使用 skill 里其他文件时同样先拷贝再用。

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
| `$ADMIN` | **管理员 QQ 号 = 用户自己的大号**（向用户解释：bot 得有个"主人"，管理指令、插件重置、权限豁免都认这个号；只收集号码本身，**不会用它登录任何东西**，大号不碰协议端零风险）。用户不想现在给 → 允许"稍后提供"，Phase 7 跑通后的 DIY 环节再问一次，届时填入并重启 AstrBot | cmd_config.json 的 `admins_id` |

**bot 的 QQ 号不收集**——NapCat 扫码登录后从它生成的配置文件名里读实际登录号（Phase 6 步骤 4），杜绝填错号/文件名对不上的问题。管理员不是 bot 自己，而是用户的大号（见上表 `$ADMIN`）。

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
| 管理员 QQ | <填入>（你的大号，bot 的"主人"；暂不想给可写"稍后提供"） |
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
- setx 持久化仍做一次（给用户以后手动用 astrbot 命令行工具（如 `init`/升级）的场景兜底，对当前会话无效只影响新进程；**注意这只解决 PATH，AstrBot 服务的启动/停止依旧一律走 bot_manager，见行为约定与 Phase 5**）：
  cmd：`setx ASTRBOT_ROOT "<INSTALL>\astrbot"`（安全策略拦 reg/setx 时用 Python winreg 等效写入用户环境变量）
- **防呆验证**：`verify.py file "$INSTALL\astrbot\data"` 目录已生成即成功。若 data 出现在**别处**（agent 工作区/用户主目录），说明 cwd 或变量没带上——删掉错误目录（确认无数据），用上面的单条命令重来。
- **`-y` 必须带**：跳过交互式确认（不带的话 init 卡在提问，agent 场景直接挂起）。
- v4.28.2 实测：`init` **不生成** `cmd_config.json`（属正常，Phase 3 直接铺模板），只生成 `data\` 骨架。

## Phase 3：铺配置模板 + 替换变量

模板在本 skill 的 `templates\`：

| 模板 | 铺到 | 待替换 |
|---|---|---|
| `cmd_config.json` | `$INSTALL\astrbot\data\cmd_config.json`（覆盖 init 生成的） | `<YOUR_API_KEY>` → `$KEY`；`<YOUR_QQ_NUMBER>` → `$ADMIN`（管理员=用户大号；开工时用户没给就保留占位符，Phase 7 后 DIY 环节补填） |
| `astrbot_plugin_group_chat_plus_config.json` | `$INSTALL\astrbot\data\config\astrbot_plugin_group_chat_plus_config.json`（目录不存在则创建） | 无占位符 |
| `napcat_onebot11.json` | Phase 6 登录后作注入源（合并进 NapCat 生成的配置） | 无需改 |

**替换脚本**（保持 BOM 编码， pitfalls B2）：

```python
import json, io
p = r"<data>\cmd_config.json"
d = json.load(io.open(p, encoding="utf-8-sig"))
d["provider_sources"][0]["key"] = ["<KEY>"]
d["admins_id"] = ["<ADMIN_QQ>"]   # 管理员=用户大号；开工时未提供则此行跳过，占位符留给 Phase 7 后补填
io.open(p, "w", encoding="utf-8-sig").write(
    json.dumps(d, ensure_ascii=False, indent=2))
```

验证：`verify.py json` 两个文件均可解析；`verify.py jsonkey cmd_config.json platform_settings` 等抽查。

**立刻验证 API key 可用**（推荐，30 秒防翻车——别等 Phase 7 验收才发现 401）：

```python
import urllib.request, json
req = urllib.request.Request("https://api.deepseek.com/models",
    headers={"Authorization": "Bearer <KEY>"})
data = json.load(urllib.request.urlopen(req, timeout=15))
models = [m["id"] for m in data["data"]]
print("key 有效，可用模型:", models)
print("模板模型名核对:", "deepseek-flash" in models)
```

- key 抄错/未生效/未充值 → 401，**立刻停下问用户**（行为约定第 2 条）；其他服务商把 URL 换成 `provider_sources[0].api_base + /models`。
- **顺带核对模型名**（上游退役是实测踩过的坑）：打印出的列表里若没有模板用的模型名，按上方快照警告换成列表里的现名再铺配置。

**创建部署状态文件**（Phase 5 的启动全靠它；这也是全程的断点记录）：把 `templates/deploy_state.json` 复制到 `$INSTALL\deploy_state.json`，填以下字段：
- `install_root` → `$INSTALL`；`astrbot_root` → `$INSTALL\astrbot`；`astrbot_exe` → astrbot.exe 实际路径（uv 默认 `%USERPROFILE%\.local\bin\astrbot.exe`）
- `admin_qq` → `$ADMIN`（用户开工时没提供就留空字符串，DIY 环节补）；`api_key_set` → `true`（只记布尔，不存明文）
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
python <skill目录>\scripts\download.py https://github.com/Him666233/astrbot_plugin_group_chat_plus/archive/refs/heads/main.zip $INSTALL\downloads\plugin.zip
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
| AstrBot 服务窗口（标题 `qqaibot-AstrBot`） | Phase 5 两次启动、验收期 | agent 拉起 | **保留**（服务本体）：「AstrBot 窗口已开并在滚日志，保留别动，你不用操作」 |
| AstrBot 窗口（stop 后残留） | Phase 5 写库/改配置前 | agent | 服务被 stop 后窗口停在"请按任意键继续"——**属正常残留**，用户随手关掉即可，agent 不必处理 |
| NapCat 安装器窗口 | Phase 6 步骤 2 | agent 拉起 | **启动即自动安装，用户无需点任何东西**；**窗口保留等装完**（关窗=中断安装进程）；agent 自己轮询 `NapCat.*.Shell` 目录出现 + 安装器进程退出 = 装完，不等用户回报 |
| NapCat 扫码窗口 | Phase 6 步骤 3 | **用户** | **用小号扫码**；**登录成功前千万别关**；成功后窗口保留（协议端服务本体） |
| NapCat 常驻窗口（标题 `qqaibot-NapCat`） | Phase 6 步骤 5 重启后 | agent 拉起 | **保留**（协议端服务本体） |
| bot 的 QQ 客户端窗口（标题 `qqaibot-QQ-<QQ号>`） | NapCat 启动登录后 | 自动改名 | **保留**。启动时后台自动改名（防与主号 QQ 混淆，尽力而为——QQ 可能自己改回标题，改名失败不影响功能）；`kill_napcat` 会连这个窗口的进程一起定位杀掉 |

**交付后日常（关机器人关哪些窗口，必须原话告知用户）**（bot_manager 从 Phase 5 起全程在用，用户日常面对的就是最多 3 个窗口）：职责各不同——
- `qqaibot-AstrBot`、`qqaibot-NapCat`：两个**服务本体**窗口。**关闭机器人 = 控制台按 `[2]`（推荐，反序杀干净）**；或者直接手关这两个窗口（等效强停对应组件，可行但非首选）。**不要只关其一**（会留半停状态，Bot 不响应却占着端口）。
- `qqaibot 机器人启动`（控制台窗口）：只是操作面板，**随时可关，不影响机器人运行**。
`stop`/`kill`/关窗口后，服务窗口若停在按键提示，随手关掉即可（再次 `start` 时也会自动清掉）。

## Phase 5：启动 AstrBot（两次启动法）

**第一次启动**（建立数据库 + 自动装插件依赖）——**bot_manager 从当前工作目录读 deploy_state.json，所以一律在 `$INSTALL` 下跑**（单条自包含命令，与 B1 同哲学，不依赖 shell 状态）：
```powershell
Set-Location '<INSTALL>'; python '<skill目录>\scripts\bot_manager.py' start
```
- **必须用 bot_manager 启动，禁止裸跑 `astrbot run`**——它是前台常驻进程，命令式 agent 会挂死（pitfalls B7）。bot_manager 开新窗口跑服务、轮询 `6185` 就绪后自己退出，agent 零风险；NapCat 未配置时自动只启动 AstrBot，正好符合当前阶段。**bot_manager 从本 Phase 起全程使用**（启动/扫码/停止/清理全是它的子命令，Phase 8 是命令总览与交付配置），不要脱离它手动管理任何进程。
- 启动完成标志：bot_manager 输出 `WebUI 已监听`（或 `status` 显示 AstrBot RUNNING）。**首次启动要装插件依赖，1~3 分钟属正常**——bot_manager 最多等 120 秒，超时警告≠失败：窗口还在滚日志就继续等（`status` 复查），窗口消失/停在 pause 才是启动失败。
- 然后 **停止**（写数据库必须先停，避免锁库）：`python bot_manager.py stop`。人类用户手动跑的话在 AstrBot 窗口按 Ctrl+C。

**写人格卡**（data_v4.db 此时已生成）：按 pitfalls B5 的 SQL 脚本，把 `templates/persona_dafeiyu.md` 写入 personas 表，`persona_id` 必须是 `大肥鱼DeepSeek`（与 cmd_config 绑定逐字符一致）。写库前先备份 `data_v4.db`。

**第二次启动**（正式运行）：
- 先想好 WebUI 密码（≥8 位含大小写+数字，如 `Astrbot123`），在当前 shell 设预设变量：
  PowerShell：`$env:ASTRBOT_DASHBOARD_INITIAL_PASSWORD = "<密码>"`
  （bot_manager 的子窗口会继承它；不设则 AstrBot 自动生成随机密码，从 AstrBot 窗口日志 `Initial password:` 行抄给用户。模板刻意不预存密码，空 hash 别试 astrbot/astrbot）
- 再启动：
```powershell
Set-Location '<INSTALL>'; python '<skill目录>\scripts\bot_manager.py' start
```
验证：
- `verify.py port 6185` → WebUI 监听中
- **WebUI 首次登录**：用户名默认 `astrbot`（模板 dashboard.username 可改），密码用上面预设值或日志随机密码；首登后 WebUI 会引导改密
- 浏览器开 `http://localhost:6185` 能看到控制台
- 日志无 ERROR（人格缺失/插件加载失败会在日志里报）

## Phase 6：NapCat 安装与扫码

1. **下载解压**：
   ```powershell
   python <skill目录>\scripts\download.py https://github.com/NapNeko/NapCatQQ/releases/latest/download/NapCat.Shell.Windows.OneKey.zip $INSTALL\napcat\OneKey.zip
   ```
   解压到 `$INSTALL\napcat\`。

2. **运行安装器（agent 自己启动，用户不用点任何东西）**：NapCatInstaller.exe **启动后自动下载并安装 QQ 内核（约 200MB，走腾讯 CDN，几分钟），全程无交互**。启动方式：**后台任务拉起**——GUI 安装器同样逃不掉沙箱回收，普通前台命令拉起后命令一结束安装进程就被收走（pitfalls B8，实测）；无后台任务能力按 B8 分层兜底。启动后**自己轮询** `$INSTALL\napcat` 下出现 `NapCat.*.Shell` 目录且安装器进程退出 = 装完（实测 Shell 目录名构建号随版本变，见下一步），**不要等用户回报**。卡住超 5 分钟/报错 → pitfalls A2（重试/换网络）。话术：「安装器窗口弹出来了，自动安装，你不用操作；卡住或报错告诉我」。
   **装完后必须实测 Shell 目录名，启动 NapCat 前再三强调**：安装器装出的运行目录形如 `NapCat.52230.Shell`，**中间的数字是构建号，每次安装可能不同——文档/示例里的 52230 只是本机样例，绝不许照抄**。列出实际目录：
   ```powershell
   Get-ChildItem $INSTALL\napcat -Directory -Filter "NapCat.*.Shell" | Select-Object -ExpandProperty FullName
   ```
   只有一个就用它；出现多个则取修改时间最新的那个。
   **装完立刻回填 deploy_state.json**：`napcat_shell_dir` → 上面实测到的完整路径、`napcat_root` → `$INSTALL\napcat`——**此后的 NapCat 启动/扫码/停止/清理全走 bot_manager**（scan/start/stop/kill_napcat），agent 不要再手动 cd + 跑 napcat.bat（手动路径事故 pitfalls C8）。若 `napcat_shell_dir` 填错（照抄了示例构建号/路径不存在），scan 会明确报"目录不存在"，此时回到本步骤重新实测再回填。

> **NapCat 启动 = 全流程最高频事故点**（启动失败 / 旧进程杀不干净，agent 在这里翻车最多）。四条铁律：
> 1. 启动/扫码/重启**一律走 bot_manager**（`scan` / `start`，自带"先杀残留再启动"）——**绝不手动跑 napcat.bat / napcat.quick.bat**（路径事故 pitfalls C8）。
> 2. **默认上一次实例还活着**：不要自己判断"应该已经停了"，bot_manager 每次启动前自动杀（同号多开必互踢，C5），杀完自己会复查并报残留 PID。
> 3. 启动失败按序对号：窗口秒死+日志戛然而止 → B8（沙箱回收，agent 环境特有）；报 Error Code 2 → C1（bootmain 陷阱）；不出二维码 → C4（qrcode.png 落盘兜底）；报目录不存在 → 回步骤 2 重新实测 Shell 目录名。
> 4. 状态存疑用双通道验证：`status` 的 QQ 探测靠 PowerShell（agent 沙箱里可能失灵、**假阴性 STOPPED**），bot_manager 已内置 6199 WS 连接兜底（有 ESTABLISHED 连接就是活的）；自己排查用 `netstat -ano | findstr :6199` 交叉验证——**别被假阴性骗去重复启动**（重复启动 → 同号互踢 C5）。
> 5. **AstrBot 同理**：启动/重启一律 `bot_manager.py start`，**绝不裸跑 `astrbot run` / `astrbot.exe run`**（前台常驻进程会挂死 agent，B7）；bot_manager 未配置 NapCat 时自动只启动 AstrBot，正好覆盖 Phase 5。

3. **启动并扫码**：
   ```powershell
   Set-Location '<INSTALL>'; python '<skill目录>\scripts\bot_manager.py' scan
   ```
   scan 按 deploy_state 里的 `napcat_shell_dir`（步骤 2 **实测**回填；`NapCat.<构建号>.Shell` 的数字随版本变）定位 `napcat.bat` 开窗口——bootmain 陷阱（pitfalls C1）与路径错误由它规避，**不要自己手动 start napcat.bat**。
   - 开窗后**原话告知用户**：「二维码窗口出现了，请盯着看；**如果等了约一分钟还没出二维码，直接告诉我**，我会重启一次（第二次必出码）」——**不许让用户干等**。
   - 用户报告没出码 → 按序处理：① 找 Shell 目录下落盘的 `qrcode.png`（`*.png`），有就把图发给用户扫（pitfalls C4）；② 没有就**重跑一次 `scan`**（自带先杀再启，第二次终端必出码，实测）——别反复杀重试（C5 规矩）。
   - 出二维码后让用户用**手机 QQ（bot 小号）**扫码登录——**扫码前再问一遍确认是小号**，扫错成大号就立刻下线重扫。
   - 屏幕上有停在 `Press any key` 的旧窗口不用管——那是已死进程的残留，scan/start/kill_napcat 都会自动清掉。

4. **读取实际 QQ 号**（不问用户，扫码自动获得）：登录成功后 NapCat 会在
   ```
   NapCat.*.Shell\versions\*\resources\app\napcat\config\
   ```
   下生成 `onebot11_<QQ号>.json` / `napcat_<QQ号>.json`——从文件名直接读出 QQ 号（记为 `$QQ`）。**立刻写进 deploy_state.json** 的 `qq` 字段（`napcat_shell_dir`/`napcat_root` 已在步骤 2 回填，确认无误即可）。
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
   然后重启 NapCat：`python <skill目录>\scripts\bot_manager.py start`（自带先杀后启，内部走 quick.bat 免扫码）——**不要手动跑 napcat.quick.bat**。
   备选：也可在 NapCat WebUI「网络配置」页手动加反向 WS（`ws://127.0.0.1:6199/ws`），效果相同。

6. **管理员确认**：`admins_id` 在 Phase 3 已填入**用户大号**（不是 bot 号）——确认占位符已替换；若用户开工时选了"稍后提供"，此处**必须**问一次大号 QQ 并补填，**重启 AstrBot**（`bot_manager.py stop` → `start`）。没有管理员时部分管理指令无人可用，且交付话术里"管理权限"一项不成立。完成后把 `progress.phase6_link_up` 改 `done`。

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
| 7 | 查 `$INSTALL\astrbot\data\logs\astrbot.log` 日志（v4.28.x 在 data\logs\ 下） | 有读空气概率判定/决策相关日志行（决策推理块默认关闭，无推理输出属正常） |

全部通过 → 进入「交付前 DIY 询问」。任何一步失败 → 按 `references/pitfalls.md` 对应章节排查。

## 交付前 DIY 询问（Phase 7 通过后必须执行）

验收通过后，**主动**把下面这张表发给用户，问一句「以上有没有想调整的？没有就直接交付」：

| DIY 项 | 当前默认 | 想改就说 | 改完效果 |
|---|---|---|---|
| 人格卡 | "大肥鱼"DeepSeek 小鲸鱼 | 重写人格卡文本（pitfalls B5） | 换成任何人设：管家/东北大哥/猫娘… |
| 管理员 | `$ADMIN` 未提供时此处**必问** | 提供`$ADMIN`（大号）填入 `admins_id` | 你用大号发管理指令/重置指令（pitfalls D4） |
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

## Phase 8：一键启动器 bot_manager（命令总览与交付）

bot_manager 从 Phase 5 起就是**全程骨架**（启动/扫码/停止/清理全部走它，agent 不手动管理任何进程）——本 Phase 把它配置成用户的日常工具并交付。六个命令：

```
python bot_manager.py start          先清残留再全新启动：AstrBot 先（等 WebUI 就绪）→ NapCat 后（各开独立窗口）
python bot_manager.py scan           扫码模式：用 napcat.bat 出二维码（部署期 Phase 6 用）
python bot_manager.py stop           全停：NapCat(QQ.exe) 先，AstrBot 后
python bot_manager.py status         只读探测两服务状态
python bot_manager.py kill_astrbot   只杀 AstrBot（含残留启动窗口）
python bot_manager.py kill_napcat    只杀 NapCat（含残留启动窗口）
```

- **start = 先杀对应组件的全部残留再启动**（防同号多开互踢，pitfalls C5）。重复跑 start = 重启服务（NapCat 免扫码自动重连，AstrBot 中断约 1 分钟）——不是"已运行就跳过"。
- **进程定位按端口/命令行/可执行路径，绝不按窗口标题**（标题匹配范围广会误杀，pitfalls C6）；窗口标题带 `qqaibot-` 前缀（`qqaibot-AstrBot` / `qqaibot-NapCat`）仅供任务栏辨识。

**双击入口（交付给用户的主入口）**：bot_manager 任意命令运行时，先把自身拷贝为 `$INSTALL\.bot_runtime\bot_manager.py`（**运行时副本**），再生成/刷新 **`机器人启动.bat`**——bat 用**相对路径**（`%~dp0`）调副本，**双击即自动执行一轮启动（先清残留再启动）**，随后进入菜单（可再次启动 / 停止 / 看状态），不用记任何命令。因此 **skill 目录日后移动/更新/删除都不影响已交付的机器人**（行为约定第 7 条），部署目录整体挪动/拷到别的盘也照样能跑。内部启动 bat 同样收在 `.bot_runtime\`，用户不需要碰。

1. **补全配置**：`$INSTALL\deploy_state.json` 在 Phase 3 已创建，把两个空字段填上：`napcat_shell_dir` → Phase 6 装出的实际目录（形如 `D:\qqaibot\napcat\NapCat.52230.Shell`——**52230 只是示例构建号，每次安装不同，必须实测，见 Phase 6 步骤 2**）；`napcat_root` → `$INSTALL\napcat`。同时把 `qq` 字段填上（Phase 6 已读到）。填完 `status` 应能探测 NapCat（STOPPED 属正常）。
2. **验证**：先跑 `status` 看状态——AstrBot 应 STOPPED；**NapCat 若仍是 RUNNING（Phase 6 留下的登录态）不要硬 stop**（杀登录实例 = 重新扫码，pitfalls C5/C6）。直接跑 `start` 完整验证即可：它自带"先杀再启"（NapCat 免扫码重启，pitfalls C7），跑完 `status` 两项应 RUNNING，并确认 `$INSTALL\.bot_runtime\bot_manager.py` 已生成（运行时副本，双击 bat 的依赖——没有就重跑任意 bot_manager 命令）。**stop/kill 会真杀进程，只能在部署完成、确认无其他业务共用时执行**。
3. **交付话术**：日常双击 `$INSTALL\机器人启动.bat`（双击即启动，菜单里可停止/看状态），并**原话告知关闭方法**："关机器人 = 控制台按 [2]，或者关掉 `qqaibot-AstrBot` 和 `qqaibot-NapCat` 两个窗口；控制台窗口本身随时可关、不影响机器人"；首次扫码/调试走 `bot_manager.py scan`（Phase 6 原方式就是它）。`start` 自动生成的内部启动 bat 在 `$INSTALL\.bot_runtime\` 下——**告诉用户不需要、也不要手动运行任何 bat**，双击控制台就是全部操作。
4. **交付前必须停掉 agent 自己的保活后台任务**（沙箱 agent 部署期用来撑进程的，pitfalls B8）——它是"进程死了就重新拉起"的循环，交付后若还在运行，用户跑 `start` 杀掉的实例会被它再次拉起，两套实例叠加 → 同号互踢（C5）复发。**判别特征：某实例被杀后带着新 PID 复活**（实测：杀 PID 6464 → 复活成 41956）。停掉保活后用户再跑 start，才算真正接管。

以上全部完成 → `progress.phase8_launcher` 改为 `done`，交付。

> 设计边界：刻意不做"单窗口聚合两进程日志"——NapCat 首次登录要交互、两进程输出编码不同、Windows 下 Ctrl+C 信号转发不可靠。独立窗口 + 一键启停是可靠性最优解。

## 日常使用（交付时告知用户）

- **日常启动/停止**：**双击 `$INSTALL\机器人启动.bat`**（双击即启动，菜单可停止/看状态）——这是给用户的主入口。**关闭机器人**：控制台按 `[2]`，或手关 `qqaibot-AstrBot` 与 `qqaibot-NapCat` 两个窗口（控制台窗口不影响机器人，随意关）；命令行等价 `python <skill目录>\scripts\bot_manager.py start` / `stop`（或部署目录副本 `$INSTALL\.bot_runtime\bot_manager.py`），杀单个组件 `kill_astrbot` / `kill_napcat`（`start` 本身自带"先杀残留再启动"）。**没有"手动方式"——AstrBot 禁止裸跑 `astrbot run`（前台常驻会挂死，B7），NapCat 禁止手动跑 napcat.bat / napcat.quick.bat（路径事故 C8），一切启动/停止/重启都走 bot_manager**。关机重开后双击启动即可。
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
| taskkill /F 报参数错误（F:/ 字样） | pitfalls B9（Git Bash 路径转换） |
| napcat.bat 报 Error Code 2 | pitfalls C1（bootmain 陷阱） |
| NapCat 连不上 AstrBot | pitfalls C2（/ws 后缀） |
| NapCat 启动终端不出二维码 | pitfalls C4（qrcode.png 兜底/重跑必出） |
| bot 掉线且开过多个实例 | pitfalls C5（同号互踢连锁） |
| 杀进程误伤别的窗口 | pitfalls C6（禁按窗口标题杀） |
| 每次重启都要重新扫码 | pitfalls C7（quick.bat 占位号没改） |
| 手动跑 napcat.bat 报"找不到文件"/旧扫码窗口越积越多 | pitfalls C8（扫码一律走 bot_manager scan，旧窗口自动清） |
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
