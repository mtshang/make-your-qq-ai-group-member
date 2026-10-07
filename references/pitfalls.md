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

### C3. onebot11 配置文件名必须带 QQ 号
- **规则**：文件名是 `onebot11_<QQ号>.json`，NapCat 按"协议端登录的 QQ 号"找配置。模板内容不含 QQ 号，部署时复制为 `onebot11_<你的QQ号>.json`。
- **时机**：首次扫码登录**之前**放好，登录后直接生效，省得登录完再改再重启。

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
- **原因**：DeepSeek 只有视觉模型收图。普通 `deepseek-flash` 收到图片消息直接 400。
- **解决**：保持模板里的双 provider 结构：`deepseek/deepseek-vision`（模型 `deepseek-v4-flash-vision-exp`）专收图，插件配置 `图片识别 provider` 指向它。别把视觉模型下的 provider 删了。

### D6. token 消耗比预期高
- **原因**：读空气的"决策 AI"对每条**通过概率筛**的群消息都要调一次小模型做决策。概率 `initial_probability=0.1` 已经把 90% 消息挡在 AI 调用之前（这部分零 token）。
- **当前配置**：`enable_decision_ai_reasoning` **默认已关闭**（决策直接出结论，不带推理块，省 token 大头）；`decision_ai_reasoning_log` 同步关闭。
- **如需排查决策质量**：临时打开这两项跑一天，日志里能看到决策推理块，看完关回。

### D7. 群里回复"太吵"/"太冷"
- **密度限制两层**：
  - **硬限**：`max_replies`（时间窗内最多回复条数，超了直接停）。
  - **软限**：`soft_limit_ratio`（0.6 × 硬限起，向 AI 注入"少说话"提示，让它自然收敛）。
- **当前配置**：60 秒窗口 / 硬限 6 条 / 软限比例 0.6。嫌吵调小 `max_replies`，嫌冷调大或调高 `initial_probability`。

### D8. 概率性 @ 和引用不生效 / 每次都 @
- **原因**：AstrBot 主配置 `reply_with_mention` / `reply_with_quote` 是**无条件装饰**（开启则 100% @ 或引用）。
- **当前方案**：主配置里两项为 `false`，由自研概率插件（`astrbot_plugin_prob_mention`，若部署）在装饰钩子里按概率决定。排查顺序：先确认主配置两项为 false，再查插件是否加载。

### D9. 空白名单"放行"是上游行为，不是配置约定
- **依赖**：模板里 `platform_settings.enable_id_white_list: true` 且 `id_whitelist: []`，依赖 AstrBot 白名单校验"空名单=放行"的源码行为（`whitelist_check/stage.py`，当前版本已实证）。
- **风险**：上游若把语义改成"空名单=全拦"，部署完机器人会全员沉默（群里私聊都没反应）。
- **症状**：升级 AstrBot 后所有消息无响应，日志停在白名单检查阶段。
- **解决**：先查 `id_whitelist` 是否仍为空 + 语义是否反转；稳妥做法是把你的账号填进 `id_whitelist` 或直接 `enable_id_white_list: false`。
