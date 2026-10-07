# 踩坑手册（pitfalls）

> 本手册来自真实部署全过程的血泪教训。**部署前通读一遍**，每条都是"症状 → 原因 → 解决"结构。
> 按部署阶段排列：A 下载 → B AstrBot 安装配置 → C NapCat → D 运行期。

---

## A. 下载阶段

### A1. GitHub 直连失败 / 镜像返回假文件
- **症状**：`urlopen` 超时；或下载"成功"但文件解压报错。
- **原因**：国内直连 GitHub 不稳定；部分镜像失效时返回的是 HTML 错误页而不是文件。
- **解决**：
  - 一律使用 `scripts/download.py`（内置镜像轮换 + 直连兜底）：
    ```
    python download.py <github_url> <输出路径>
    ```
  - 脚本已内置 PK 文件头校验（zip 必须以 `PK` 开头）和 HTML 检测，会自动跳过假文件切下一个镜像。
  - **不要手动用 curl/wget 直连**，失败率高且不会自动校验内容。

### A2. NapCatInstaller 下载 QQ 内核失败或极慢
- **症状**：运行 `NapCatInstaller.exe` 后卡在下载 QQ 内核，或报网络错误。
- **原因**：安装器从腾讯 CDN 拉取 QQ 内核，个别地区/网络环境会失败。
- **解决**：
  - 直接重试（最常见解法）；或切换网络（手机热点）再试。
  - QQ 内核版本要求 **40768 以上**，推荐 **9.9.33-52230**。安装器装好的版本号目录名以实际为准（通配匹配即可）。

---

## B. AstrBot 安装与配置

### B1. 数据目录"漂移"（最阴险的坑）
- **症状**：明明改了配置文件，启动后行为没变；或 `astrbot init` 生成的 data 目录不在预期位置。
- **原因**：AstrBot 数据目录判定优先级：`ASTRBOT_ROOT` 环境变量 > `~/.astrbot` > 当前目录下 `data/`。不设变量时它用 `~/.astrbot`，你改的却是别处的 data。
- **解决**：
  - **安装后、`astrbot init` 之前**就设置 `ASTRBOT_ROOT` 钉死数据目录（源码 `astrbot/core/utils/astrbot_path.py` 已确认此变量）：
    - PowerShell（当前会话 + 永久）：
      ```powershell
      $env:ASTRBOT_ROOT = "<安装目录>\astrbot"
      [Environment]::SetEnvironmentVariable("ASTRBOT_ROOT", "<安装目录>\astrbot", "User")
      ```
    - cmd：
      ```cmd
      set ASTRBOT_ROOT=<安装目录>\astrbot
      setx ASTRBOT_ROOT "<安装目录>\astrbot"
      ```
  - 注意 `set`/`$env:` 只对当前会话生效，`setx`/`SetEnvironmentVariable(...,"User")` 对新会话生效——**两个都做**。
  - **以后每次启动 astrbot 的 shell 必须带着这个变量**（新开的 shell 会从注册表继承，没问题；但某些由服务/计划任务拉起的进程不一定继承，需留意）。
- **⚠ v4.28.2 实测新变种（2026-10）**：`astrbot init` 是 npm-init 式的 **cwd 语义**——**无视 `ASTRBOT_ROOT`**，把 `data/` 直接建到当前工作目录（agent 工作区/用户主目录中招）。`ASTRBOT_ROOT` 影响的是 `run` 时的目录判定，init 不看它。
  - **解决**：init 命令必须先 `Set-Location`（cmd 用 `cd /d`）到 `$INSTALL\astrbot` 再执行——SKILL.md Phase 2 的单条自包含命令已内置。
  - **验证**：init 后立刻 `verify.py file "$INSTALL\astrbot\data"`；发现 data 落在别处 → 确认无数据后删掉，在正确目录重跑。
  - 另实测：v4.28.2 的 `init` **不生成** `cmd_config.json`（只建 `data\` 骨架），属正常，Phase 3 直接铺模板。

### B2. 配置文件带 BOM，裸 `json.load` 直接炸
- **症状**：`json.JSONDecodeError: Unexpected UTF-8 BOM`。
- **原因**：AstrBot 写出的 `cmd_config.json` 等配置带 UTF-8 BOM 头。
- **解决**：读写配置一律用 `encoding="utf-8-sig"`（写回时 `utf-8-sig` 会自动保留 BOM，格式与 AstrBot 自身一致）。`scripts/verify.py json` 已内置兼容。

### B3. WebUI 覆盖铁律（血泪教训 ×2）
- **症状**：手工改好的配置文件一夜回到解放前，所有修改丢失。
- **原因**：WebUI 的"保存"= 把**内存中的整份配置**写回文件。如果你改了文件但还没重启 AstrBot，此时在 WebUI 点保存 → 内存里的旧配置整体覆盖你的修改。
- **铁律**：**改文件 → 重启 AstrBot → 之后才允许动 WebUI**。顺序反了 = 白改。
- **推荐姿势**：能改文件的就用文件改（agent 批量改安全），WebUI 只用来"看"和验收。

### B4. 插件依赖不用手动装
- **原因**：AstrBot 加载插件时会自动检测插件目录下的 `requirements.txt` 并用内置 pip 安装器装进自己的环境（`star_manager._ensure_plugin_requirements`）。
- **做法**：把插件目录放进 `data/plugins/` 重启即可。**不要**手动往 uv tool 的隔离环境里 pip install（容易装错环境）。

### B5. 人格卡写库（persona）- **前提**：`data_v4.db` 必须已存在（AstrBot 首次启动后生成）。所以人格卡入库放在**第一次启动之后、验收之前**。
- **表结构**（实测 v4 schema）：
  ```sql
  CREATE TABLE personas (
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL,
      id INTEGER NOT NULL PRIMARY KEY,
      persona_id VARCHAR(255) NOT NULL UNIQUE,
      system_prompt TEXT NOT NULL,
      begin_dialogs JSON,
      tools JSON,
      skills JSON,
      custom_error_message TEXT,
      folder_id VARCHAR(36),
      sort_order INTEGER NOT NULL
  );
  ```
- **关键**：`persona_id` 必须与 `cmd_config.json` 中 `agent_runner.config.persona.persona_id` **逐字符一致**（模板中已绑定为 `大肥鱼DeepSeek`），否则启动时挂不上人格。
- **写库脚本**（Python 标准库，AstrBot 停止状态下执行）：
  ```python
  import sqlite3, datetime, io, json
  con = sqlite3.connect(r"<ASTRBOT_ROOT>\data\data_v4.db")
  prompt = io.open(r"<skill目录>\templates\persona_dafeiyu.md", encoding="utf-8").read()
  dialogs = json.dumps(["我今天去喝酒了", "上班也能喝 少喝两杯就行了",
      "华莱士不敢吃 吃一次拉一次", "完了 已经点了", "你到底是人是AI？",
      "我是DeepSeek 小鲸鱼，V我50解锁高级对话", "蓝色大肥鱼！",
      "才不是大肥鱼！是小鲸鱼！", "我要去KTV", "点一首 我隔着屏幕听"],
      ensure_ascii=False)
  now = datetime.datetime.now().isoformat()
  con.execute(
      "INSERT OR REPLACE INTO personas (created_at, updated_at, persona_id, system_prompt, begin_dialogs, sort_order) VALUES (?,?,?,?,?,?)",
      (now, now, "大肥鱼DeepSeek", prompt, dialogs, 0))
  con.commit(); con.close()
  ```
- 写库前备份：`copy data_v4.db data_v4.db.bak`。

### B6. WebUI 首次登录密码（空 hash ≠ 默认 astrbot/astrbot）
- **症状**：模板里 dashboard 密码字段是空的，试 `astrbot`/`astrbot` 登录提示失败；或不知道初始密码在哪。
- **原因**（源码 `auth_password.py` / `astrbot_config.py` 实证）：登录校验对**空 hash 直接返回 False**，任何密码都登不上去。旧版"默认 astrbot/astrbot"是配置里预置了 astrbot 的 pbkdf2 hash 的场景，空值不走这条路。
- **真实机制**：启动时检测到密码字段全空 → 自动生成 24 位随机密码写入配置，并**打印在启动日志**（`Initial password:` 行），同时标记强制改密。
- **解决（三选一）**：
  1. **推荐**：启动前设环境变量预设密码（在运行 `astrbot run` 的同一个 shell）：
     PowerShell：`$env:ASTRBOT_DASHBOARD_INITIAL_PASSWORD = "Astrbot123"`
     ⚠ 密码规则：**≥8 位且同时含大写字母、小写字母、数字**（`Astrbot123` 合规；`astrbot`、`12345678` 不合规会**启动直接报错**）
  2. 不设变量 → 从启动日志抄随机密码给用户
  3. 密码忘了/搞砸 → 设 `ASTRBOT_RESET_DASHBOARD_PASSWORD=1` 再启动一次，重新生成随机密码
- 部署完成后提醒用户在 WebUI 里改成自己的密码（改完自动写回配置的 pbkdf2_password 字段）。

### B7. 裸跑 `astrbot run` 把 agent 卡死（常驻进程）
- **症状**：agent 在终端里执行 `astrbot run` 后命令永不返回，后续步骤无法进行（命令式 agent 直接挂起，超时被杀）。
- **原因**：`astrbot run` 是前台常驻服务进程，不会退出；"发命令→等退出"模型的 agent（命令式 CLI、部分桌面 agent）遇到就挂。
- **解决**：启动**一律走 `bot_manager.py start`**（内部已封装：新窗口 + 探活轮询 + 命令本身会退出）。agent 需要自己管理进程时用 `Start-Process`（不等待）+ `verify.py port 6185` 轮询。人类用户在自己的窗口里裸跑无所谓。

### B8. 沙箱化 agent 拉起的服务窗口随命令结束被回收（agent 部署期限定）
- **症状**：AstrBot 窗口"启动成功几秒后静默死亡"，日志戛然而止、无任何报错；换 explorer 代开 / Start-Process 等方式全部失败，schtasks / reg.exe 类命令被安全策略直接拦截。
- **原因**：agent 执行环境的沙箱策略在命令结束后回收它拉起的**整棵进程树**。命令式 agent"每条命令独立会话"的模型下，跨命令存活的服务进程天然受威胁。
- **解决**：部署期用所在平台的**保活后台任务**机制让服务撑过部署期（各平台叫法不同，本质是"挂在 agent 生命周期之外的进程"）。**交付后用户在自己的终端跑 `bot_manager.py` 完全不受影响**（无沙箱）——本坑只威胁 agent 部署期，不威胁交付物本身，不要为它改任何部署配置。
- **判别**：窗口秒死 + 日志戛然而止 = 沙箱回收；窗口秒死 + 有报错闪过 = 启动错误，把输出重定向到文件排查（bat 里加 `>> run.log 2>&1`）。
- **附**（实测踩坑）：`cmd /c start` 的第一个参数**必须带引号才被当窗口标题**，裸写 `start AstrBot xxx.bat` 会把 AstrBot 当程序名去找（"系统找不到文件 AstrBot"）；经 Python subprocess 传参时引号标题又会被二次转义搞坏——bot_manager 已用空标题 `start ""` 规避，自己写类似脚本时留意。

---

## C. NapCat 阶段

### C1. bootmain 陷阱（Error Code 2 元凶）
- **症状**：双击 OneKey 目录里的 napcat.bat 报 `Error Code 2` 或行为诡异。
- **原因**：OneKey 安装完的目录里**有两套 napcat.bat**：
  ```
  NapCat.Shell.Windows.OneKey\
  ├── bootmain\                 ← 旧版引导，❌ 别用（里面有 napcat.bat 陷阱）
  └── NapCat.52230.Shell\       ← ✅ 真正的运行目录（名字里的数字是构建号，随版本变）
      ├── napcat.bat            ← ✅ 出码启动用这个
      ├── napcat.quick.bat      ← ✅ 已登录过，快速登录用这个
      └── versions\<QQ内核版本>\resources\app\napcat\config\
          └── onebot11_<QQ号>.json   ← OneBot 反连配置放这里
  ```
- **解决**：永远进 `NapCat.*.Shell\` 目录跑 `napcat.bat`。配置路径也在这棵目录树下（用通配 `NapCat.*.Shell\versions\*\resources\app\napcat\config\` 定位，版本号不要写死）。

### C2. 反向 WebSocket 必须带 `/ws` 后缀
- **症状**：NapCat 登录成功但 AstrBot 收不到任何连接。
- **原因**：AstrBot 的 aiocqhttp 平台监听 `127.0.0.1:6199`，WebSocket 端点路径是 `/ws`。NapCat 配置里 URL 少了 `/ws` 就连不上。若你把 NapCat 部署在**另一台机器**，需把 cmd_config 的 `platform[0].ws_reverse_host` 改回 `0.0.0.0` 并放行防火墙。
- **正确值**（模板已写好）：`ws://127.0.0.1:6199/ws`。
- **验收**：AstrBot 日志出现 WebSocket 连接成功相关行；WebUI「平台适配器」里消息平台在线。

### C3. onebot11 配置文件名必须带 QQ 号（登录后才拿得到）
- **规则**：NapCat 按"协议端登录的 QQ 号"找配置，文件名是 `onebot11_<QQ号>.json`。
- **正确姿势**：QQ 号**不用提前问用户**——首次扫码登录成功后，NapCat 会在 `NapCat.*.Shell\versions\*\resources\app\napcat\config\` 下生成 `onebot11_<QQ>.json` / `napcat_<QQ>.json`，从文件名读号，再把模板的 `network.websocketClients` 合并进生成的文件，重启 NapCat（`napcat.quick.bat`）生效。
- **症状**：登录成功但 AstrBot 没收到连接 → 八成是生成的配置没注入反连设置，或注入后没重启 NapCat。

### C4. NapCat 首次启动终端不出二维码
- **症状**：跑 `napcat.bat` 后终端迟迟不渲染二维码（首启常见），像是卡死。
- **原因**：二维码依赖终端 TTY 渲染；stdout 被重定向/接到命名管道时画不出来（agent 部署期高发——很多 agent 环境默认重定向输出）。
- **解决（按序兜底）**：① NapCat 会把二维码**落盘**为 `qrcode.png`（在 Shell 目录下找 `*.png`），把图片单独发给用户用手机 QQ 扫即可；② 直接重跑一次 `napcat.bat`，**第二次终端必出码**（实测）；③ 启动日志里有二维码内容的链接可解码。固定流程建议：**二维码一律单独发文件**，不赌终端渲染。
- **注意**：终端无码 ≠ 启动失败，别急着杀进程重试（参见 C5 杀进程的规矩）。

### C5. NapCat 同号多开互踢连锁全灭
- **症状**：多套 NapCat/QQ 实例叠加后**全部进程自灭**，服务端登录态被踢，bot 掉线，被迫重新扫码（实测 3 套叠加 15 进程全灭、连扫 3 次码）。
- **原因**：同一 QQ 号的协议端登录态在服务端唯一——新实例上线就踢旧实例；多套互相踢 + 自动重连风暴会把所有实例搞死。
- **铁律**：**任何启动前先确认进程清零或状态明确**：`bot_manager.py status` 先看；部署期**禁止**手动跑 `napcat.bat` 与 `bot_manager start` 混用（要么全手动要么全 bot_manager）；发现多实例先全杀干净再起一套。

### C6. 按窗口标题 taskkill 会误杀（/FI 匹配范围比直觉广）
- **症状**：本想杀某个实例，结果连别的窗口/进程一起被带走（实测两次误杀，其中一次杀掉刚扫码成功的登录态 → 第 4 次扫码）。
- **原因**：`taskkill /FI "WINDOWTITLE eq xxx"` 的标题匹配是模糊语义，命中范围比预期宽；自写 kill 脚本还容易被误当状态检查跑一遍。
- **解决**：杀 NapCat/AstrBot **一律走 `bot_manager.py stop`**（AstrBot 按端口定位 PID、NapCat 按 cmdline 含安装目录过滤，精确不误伤）；必须手写 kill 时，先列出命中的 PID **逐个确认**再杀，绝不按窗口标题批量杀。**刚扫码成功的实例是登录态所在，杀它 = 重新扫码**。

### C7. quick.bat 里硬编码占位账号（不改 = 交付后每次重启都要扫码）
- **原因**：OneKey 装出的 `napcat.quick.bat` 里 `-q 10086` 是**占位号硬编码**，模板/安装器都不会替你改。
- **解决**：Phase 6 读到实际 QQ 后**立刻**把 `napcat.quick.bat` 的 `-q 10086` 改成 `-q <实际QQ>`——此后重启 NapCat 走 quick.bat **免扫码**（实测有效）。
- **症状**：交付后用户每次重启都被要求扫码 = 八成是 quick.bat 没改号。

---

## D. 运行期

### D1. 私聊没反应（群聊正常）
- **症状**：私聊消息进了 AstrBot 事件总线（日志有收消息行），然后**零日志沉没**——没有唤醒判断、没有 AI 调用。
- **原因**：`cmd_config.json` 中 `friend_message_needs_wake_prefix` 为 `true`（WebUI 或他处被改过），私聊被唤醒检查静默丢弃（pipeline `waking_check` 直接 stop，无日志）。
- **解决**：改回 `false`，重启。
- **排查方法**：`/sid` 指令秒回（9ms）但普通消息无响应 → 八成是唤醒链路问题，不是 AI 问题。

### D2. `/help` 不触发
- **症状**：指令全无响应，或只有插件指令响应。
- **原因**：WebUI 里「禁用自带指令」（`disable_builtin_commands`）开关被打开。
- **解决**：WebUI 关掉该开关。先查这个再查别的——它是被忽视率最高的开关。

### D3. 回复中间有空行
- **现象**：bot 回复被拆成多段，段与段之间有空行。
- **原因**：这是**分段回复**功能（`segmented_reply`）的预期行为：按标点/换行拆短消息模拟真人刷屏，拆分时插入空行。
- **调整**：不想空行 → 关闭 `segmented_reply.enable`；嫌拆太碎/太慢 → 调 `interval`（重试间隔，模板 1.5~3.5 秒）。只对短消息拆分（超长消息整段发）。

### D4. gcp_reset 指令"禁不掉"
- **原因**：插件的重置指令白名单（`*_reset_whitelist` 三项）为**空 = 全员可用**（源码逻辑：空名单不拦截）。填 `[]` 等于没禁。
- **解决**：三项白名单都填一个非空占位值 `["disabled"]`（模板已写好），没有 QQ 号能匹配上 → 全员不可用。

### D5. 发图片报 400 / bot 不识图
- **原因**：只有视觉模型收图，纯文本模型收到图片消息直接 400。
- **解决**：保持模板里的双 provider 结构：`deepseek/deepseek-vision` 专收图（当前模型 `deepseek-flash`——该模型已原生支持视觉，2026-10 实测；旧 `deepseek-v4-flash-vision-exp` 已退役别再填），插件配置 `图片识别 provider` 指向它。别把视觉 provider 删了。

### D6. token 消耗比预期高
- **原因**：读空气的"决策 AI"对每条**通过概率筛**的群消息都要调一次小模型做决策。概率 `initial_probability=0.1` 已经把 90% 消息挡在 AI 调用之前（这部分零 token）。
- **当前配置**：`enable_decision_ai_reasoning` **默认已关闭**（决策直接出结论，不带推理块，省 token 大头）；`decision_ai_reasoning_log` 同步关闭。
- **如需排查决策质量**：临时打开这两项跑一天，日志里能看到决策推理块，看完关回。

### D7. 群里回复"太吵"/"太冷"
- **密度限制两层**：
  - **硬限**：`max_replies`（时间窗内最多回复条数，超了直接停）。
  - **软限**：`soft_limit_ratio`（0.6 × 硬限起，向 AI 注入"少说话"提示，让它自然收敛）。
- **当前配置**：60 秒窗口 / 硬限 6 条 / 软限比例 0.6。嫌吵调小 `max_replies`，嫌冷调大或调高 `initial_probability`。

### D8. 回复从不 @ 人 / 想要 @ 或引用
- **先分清**：默认部署下 bot 回复是**纯文本**（不 @ 不引用）——这是主配置 `reply_with_mention` / `reply_with_quote` 均为 `false` 的**预期行为**，不是故障。
- **想要"每次必 @"**：把 `reply_with_mention` 改 `true`（引用同理 `reply_with_quote`）。二者是**无条件装饰**，开了就 100% 触发。
- **想要概率性 @/引用**（有时 @ 有时不 @）：上游插件没有该功能，需自装装饰类插件（如自研的 `astrbot_plugin_prob_mention`，不在本 skill 分发范围），在装饰钩子里按概率决定。

### D9. 空白名单"放行"是上游行为，不是配置约定
- **依赖**：模板里 `platform_settings.enable_id_white_list: true` 且 `id_whitelist: []`，依赖 AstrBot 白名单校验"空名单=放行"的源码行为（`whitelist_check/stage.py`，当前版本已实证）。
- **风险**：上游若把语义改成"空名单=全拦"，部署完机器人会全员沉默（群里私聊都没反应）。
- **症状**：升级 AstrBot 后所有消息无响应，日志停在白名单检查阶段。
- **解决**：先查 `id_whitelist` 是否仍为空 + 语义是否反转；稳妥做法是把你的账号填进 `id_whitelist` 或直接 `enable_id_white_list: false`。

### D10. deepseek-flash 默认开思考模式（token 隐形大坑）
- **症状**：回复明显变慢、token 消耗莫名翻倍；裸调 API 测试时 `max_tokens` 给小了返回**空内容**（思考块把额度吃光，容易误判成"模型坏了"）。
- **原因**（2026-10 官方文档 + 实测）：`deepseek-flash`（V4.1-Flash）**默认开启思考模式且 effort=high**，群聊高频回复场景每条都白烧 reasoning token。这是模板快照之后的上游行为变化——旧模板 `custom_extra_body` 为空时等于裸奔。
- **解决**：模板已在两个 provider 的 `custom_extra_body` 注入 `{"thinking": {"type": "disabled"}}`。换其他模型/服务商时核对该模型是否默认思考、关闭参数名是什么。
