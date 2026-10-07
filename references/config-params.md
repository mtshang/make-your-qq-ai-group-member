# 配置参数参考（config-params）

> 四个模板文件的参数说明。标注含义：
> 🔧 **常改**（用户大概率要动）｜⚙️ **可改**（按需求调）｜🚫 **别动**（动了容易炸，改前先读 pitfalls）

---

## 1. `templates/cmd_config.json`（AstrBot 主配置）

### 1.1 部署必改（占位符）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `provider_sources[0].key` | `<YOUR_API_KEY>` | 🔧 DeepSeek API key，数组形式 |
| `admins_id` | `<YOUR_QQ_NUMBER>` | 🔧 管理员 QQ 号（bot 小号自身）。**Phase 6 扫码登录后从 NapCat 生成的文件名读号回填**（SKILL.md Phase 6 步骤 6），改完重启 AstrBot |

### 1.2 常改项

| 参数 | 当前值 | 说明 |
|---|---|---|
| `provider_settings.wake_prefix` | `""` | ⚙️ 群聊唤醒前缀（如 `"$bot"`）；空=不要求前缀，靠 @ 或插件概率触发 |
| `platform_settings.friend_message_needs_wake_prefix` | `false` | 🔧 私聊是否要求唤醒前缀。**必须 false**，否则私聊装死（pitfalls D1） |
| `platform_settings.reply_with_mention` | `false` | 🔧 每条回复都 @ 提问者。默认 false=纯文本回复（预期行为，不是故障）；想概率性 @ 需自装装饰插件，见 pitfalls D8 |
| `platform_settings.reply_with_quote` | `false` | 🔧 每条回复都引用原消息。默认 false=纯文本回复，同上 |
| `platform_settings.segmented_reply.enable` | `true` | 🔧 分段回复（像真人连发多条）。关掉则整段发送、无空行（pitfalls D3） |
| `platform_settings.segmented_reply.interval` | `"1.5,3.5"` | ⚙️ 分段间隔随机区间（秒），调小回复更急促、调大更从容 |
| `platform_settings.segmented_reply.words_count_threshold` | `150` | ⚙️ 超过该字数不拆分（长文整段发） |
| `dashboard.username` / 密码 | `astrbot` / 空 | 🔧 WebUI 登录。模板不预存密码：启动时自动生成随机密码（打印在日志），或提前设环境变量 `ASTRBOT_DASHBOARD_INITIAL_PASSWORD` 预设（需 ≥8 位含大小写+数字，pitfalls B6） |
| `dashboard.host` | `127.0.0.1` | ⚙️ WebUI 监听地址。默认仅本机可访问（安全）；想用手机/局域网访问 WebUI 改 `0.0.0.0`，**务必同时设强密码** |
| `dashboard.port` | `6185` | ⚙️ WebUI 端口，被占用时改 |
| `platform[0].ws_reverse_host` | `127.0.0.1` | ⚙️ 反向 WS 监听地址。默认仅本机（NapCat 同机部署够用，且不触发防火墙弹窗）；NapCat 装到别的机器才改 `0.0.0.0` |
| `platform[0].ws_reverse_port` | `6199` | ⚙️ 反向 WS 监听端口。**改了必须同步改 NapCat 侧 URL**（`ws://127.0.0.1:端口/ws`） |
| `log_level` | `INFO` | ⚙️ 排查问题时可改 `DEBUG`，平时别开（日志量巨大） |
| `timezone` | `Asia/Shanghai` | ⚙️ 影响时段概率计算，一般不动 |

### 1.3 LLM 相关

| 参数 | 当前值 | 说明 |
|---|---|---|
| `provider_sources[0].api_base` | `https://api.deepseek.com` | ⚙️ API 地址，换其他 OpenAI 兼容服务商时改这里+model |
| `provider[0].model` | `deepseek-flash` | ⚙️ 主对话模型（文本+工具），**不声明 image**（收图会 400，图片由 caption/vision 链路处理）。模型名以部署时 DeepSeek 官方文档为准 |
| `provider[1].model` | `deepseek-v4-flash-vision-exp` | ⚙️ 视觉模型，**只有它能收图**（pitfalls D5） |
| `provider_settings.default_image_caption_provider_id` | `deepseek/deepseek-vision` | ⚙️ AstrBot 原生链路的图片转述模型（引用带图等场景），**必须指向能收图的 vision provider** |
| `agent_runner.config.model.provider_id` | `deepseek/deepseek-flash` | 🚫 agent 运行器主模型，与主对话模型保持一致即可 |
| `agent_runner.config.persona.persona_id` | `大肥鱼DeepSeek` | 🚫 默认人格绑定，**必须与 personas 表里的 persona_id 逐字符一致**（pitfalls B5） |
| `provider[n].max_context_tokens` | `1000000` | 🚫 模型上下文上限（在 `provider[]` 各项里，不在 provider_settings 下），DeepSeek 支持百万级，不动 |
| `provider_settings.streaming_response` | `false` | ⚙️ 流式输出。QQ 场景意义不大（分段回复代替），保持关闭 |
| `provider_settings.datetime_system_prompt` | `true` | 🚫 注入当前时间，时段概率依赖它，别关 |
| `pypi_index_url` | `https://mirrors.aliyun.com/pypi/simple/` | 🚫 插件依赖安装源，国内镜像加速，别动 |
| `http_proxy` | `""` | ⚙️ 全局 HTTP 代理。**默认空**；有梯子且 DeepSeek 直连慢才填（如 `http://127.0.0.1:7890`） |

### 1.4 一般不动（保留默认即可）

`platform_settings.rate_limit`（平台级 60s/30 条限流）、`enable_id_white_list`（空白名单=放行）、`content_safety`（内容安全，默认内部词库已启用）、`provider_stt/tts_settings`（语音，未启用）、`provider_ltm_settings`（长期记忆）、`t2i`（文生图）、`subagent_orchestrator`、`sandbox`、`platform_specific`、`wake_prefix: ["/"]`（指令前缀，`/help` 靠它）、`disable_builtin_commands`（**保持 false**，true 会导致 /help 无效，pitfalls D2）、`plugin_set: ["*"]`（加载全部插件）。

---

## 2. `templates/astrbot_plugin_group_chat_plus_config.json`（读空气插件）

> 插件核心逻辑链：收到群消息 → **触发词/命令过滤** → **概率判定**（基础概率 × 时段系数 × 注意力/情绪/疲劳/质量加成）→ 决策 AI 判断 → 回复 AI 生成。想调"话多话少"就动 2.1/2.2/2.4 三组。

### 2.1 概率与触发（最常改）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `initial_probability` | `0.1` | 🔧 **基础回复概率**（每条非 @ 群消息触发回复的总概率根）。嫌冷调 0.15~0.2，嫌吵调 0.05 |
| `after_reply_probability` | `1.0` | 🔧 bot 回复后，紧接着下一条消息继续回复的概率（1.0=连续对话必接） |
| `probability_duration` | `120` | ⚙️ 上一条回复后的"热聊窗口"（秒），窗口内沿用已激活的判定 |
| `trigger_keywords` | `[DeepSeek, deepseek, 大肥鱼, 肥鱼, 吃白饭]` | 🔧 **命中必回**的触发词，用户自己改（bot 的名字/外号加进来） |
| `keyword_smart_mode` | `true` | 🚫 触发词智能匹配（模糊/分词），保持开 |
| `blacklist_keywords` | `[]` | ⚙️ 命中绝不回的词（如 `[广告, 招商]`） |
| `enable_ignore_at_all` | `true` | 🚫 忽略 @全体成员 消息，保持开（防活动刷屏骚扰） |
| `enabled_groups` | `[]` | ⚙️ 空=全部群生效；填群号列表则白名单制 |

### 2.2 密度限制（话多话少硬手段）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `reply_density_window_seconds` | `60` | 🔧 密度窗口（秒） |
| `reply_density_max_replies` | `6` | 🔧 **硬限**：窗口内最多回 6 条，超了直接停 |
| `reply_density_soft_limit_ratio` | `0.6` | 🔧 **软限**：0.6×6≈第 4 条起向 AI 注入"少说话"提示自然收敛 |
| `reply_density_ai_hint` | `true` | 🚫 软限提示注入开关，保持开 |
| `enable_probability_hard_limit` | `false` | ⚙️ 概率钳制开关（`probability_min/max_limit` 0.05~0.8），默认关——各项加成可自由叠加 |

### 2.3 时段概率（六时段 JSON）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_dynamic_reply_probability` | `true` | 🔧 时段系数总开关 |
| `reply_time_periods` | 6 段 JSON | 🔧 每段 `{"name","start","end","factor"}`，基础概率 × factor。当前：深夜 0.15 / 上午 0.9 / 午间 0.6 / 下午 1.0 / **晚间 1.25** / 23:30 后 0.45 |
| `reply_time_transition_minutes` | `30` | ⚙️ 时段切换平滑过渡分钟数 |
| `reply_time_max_factor` | `2.0` | 🚫 系数上限，不动 |

改法示例：想让 bot 半夜彻底闭嘴 → 把深夜段的 `factor` 改 `0`。

### 2.4 注意力 / 情绪（感知谁在重视 bot）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_attention_mechanism` | `true` | 🚫 总开关，保持开 |
| `attention_increased_probability` / `decreased` | `0.9` / `0.1` | ⚙️ 互动加成/冷落惩罚的触发概率阈值 |
| `attention_boost_step` | `0.7` | ⚙️ 被 @ 或触发词时注意力直接拉到 0.7 |
| `attention_decrease_step` | `0.08` | ⚙️ 每次冷落递减幅度 |
| `attention_duration` | `120` | ⚙️ 注意力生效窗口（秒） |
| `emotion_boost_step` | `0.1` | ⚙️ 夸 bot 时情绪加成 |
| `attention_emotion_keywords` | JSON | ⚙️ 正面/负面词表（谢谢/牛/傻/滚…），可自己加词 |
| `enable_attention_spillover` | `true` | ⚙️ A 互动热了，bot 对旁边人也热一点（外溢 0.35） |

### 2.5 疲劳系统（连续聊天自然变淡）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_conversation_fatigue` | `true` | 🚫 保持开 |
| `fatigue_reset_threshold` | `300` | ⚙️ 300 秒不聊重置疲劳 |
| `fatigue_threshold_light/medium/heavy` | `4/6/8` | ⚙️ 连聊 4/6/8 轮进入轻/中/重度疲劳 |
| `fatigue_probability_decrease_*` | `0.08/0.18/0.3` | ⚙️ 对应扣减概率 |
| `fatigue_closing_probability` | `0.4` | ⚙️ 重度疲劳时说"结束语"收尾的概率 |

### 2.6 决策 AI（判定"该不该回"）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `decision_ai_provider_id` | `""` | ⚙️ 空=用默认对话模型做决策；想给决策单独配更便宜的模型时填一个真实存在的 provider_id（注意别填收不了图的） |
| `enable_decision_ai_reasoning` | `false` | 🔧 **默认已关**（省 token 大头）。开启后每条过筛消息都输出推理块，质量更高但费 token；排查决策质量时临时开 |
| `decision_ai_reasoning_log` | `false` | ⚙️ 决策推理写日志，与上项同步开关 |
| `decision_ai_timeout` | `30` | 🚫 决策超时 |
| `concurrent_mode` | `smart` | 🚫 并发抢答模式，smart=多人同时说话智能合并 |
| `concurrent_wait_max_loops` / `interval` | `15` / `5.0` | 🚫 等待窗口轮次/间隔 |

### 2.7 图片识别

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_image_processing` | `true` | 🔧 读空气识图总开关。**用户的 API 不支持视觉模型时必须改 `false`**（否则群里发图报错） |
| `image_to_text_scope` | `all` | ⚙️ 识图范围：all=任何消息带图都识别 |
| `image_to_text_provider_id` | `deepseek/deepseek-vision` | 🚫 **必须指向视觉 provider**，填错成普通模型会 400（pitfalls D5） |
| `enable_image_description_cache` | `true` | 🚫 同图不重复调 API，保持开 |

### 2.8 拟人细节（体验向）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_typo_generator` | `true` | ⚙️ 偶尔打错别字（同音字），更像真人 |
| `typo_error_rate` | `0.02` | ⚙️ 错字概率 2% |
| `enable_typing_simulator` | `true` | ⚙️ 按字数模拟打字延迟 |
| `typing_speed` / `typing_max_delay` | `15.0` / `3.0` | ⚙️ 字/秒 与延迟上限 |
| `enable_mood_system` | `true` | ⚙️ 群氛围情绪系统（开心/无语/兴奋…影响语气） |
| `enable_emoji_filter` | `true` | ⚙️ 表情包消息衰减判定（`emoji_probability_decay` 0.7） |
| `enable_message_quality_scoring` | `true` | 🚫 水群消息（"哈哈哈""6"）降概率、提问加概率，保持开 |
| `enable_group_wait_window` | `true` | 🚫 群聊等待窗口（5000ms 攒多条合并回），保持开 |
| `enable_duplicate_filter` | `true` | 🚫 重复内容拦截（近 5 条内查重 + 30 分钟时限） |
| `enable_humanize_mode` | `true` | ⚙️ 拟人静默模式（连回太多后主动沉寂） |

### 2.9 主动对话（当前关闭）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_proactive_chat` | `false` | 🔧 **当前关闭**。开启后 bot 会冷场时主动找话题；开启前建议先跑熟读空气 |
| `proactive_*`（约 40 项） | — | 开启后再调：沉默阈值 600s、活跃时段系数、安静时间 23:00-07:00 等 |

### 2.10 指令与重置权限

| 参数 | 当前值 | 说明 |
|---|---|---|
| `plugin_gcp_reset_allowed_user_ids` | `["disabled"]` | 🚫 gcp_reset 指令白名单。**必须非空占位**（空=全员可用，pitfalls D4） |
| `plugin_gcp_reset_here_allowed_user_ids` | `["disabled"]` | 🚫 同上（重置当前会话版） |
| `gcp_clear_image_cache_allowed_user_ids` | `["disabled"]` | 🚫 清识图缓存指令，同上禁用 |
| `enable_command_filter` | `true` | 🚫 以 `/ ! #` 开头的消息不进读空气（避免把指令当聊天），保持开 |
| `command_prefixes` | `["/", "!", "#"]` | ⚙️ 与 AstrBot 指令前缀 `/` 对齐即可 |

### 2.11 私聊（当前关闭）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `enable_private_chat` | `false` | 🔧 **当前关闭**——插件不管私聊，私聊走 AstrBot 原生人格回复。想开启读空气式私聊再改 true |
| `private_*`（约 30 项） | — | 开启后再调：用户黑名单、消息聚合器、私聊识图 |

### 2.12 上下文与缓存

| 参数 | 当前值 | 说明 |
|---|---|---|
| `max_context_messages` | `50` | ⚙️ 读空气能看到的群聊历史条数（token 相关，越大越费） |
| `pending_cache_max_count` | `20` | 🚫 概率筛掉的消息暂存条数（供决策参考），不动 |
| `pending_cache_ttl_seconds` | `1800` | 🚫 暂存 30 分钟过期 |
| `enable_idle_cache_flush` | `true` | 🚫 冷群暂存消息转正给决策 AI 看 |

---

## 3. `templates/napcat_onebot11.json`（NapCat 反连配置）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `network.websocketClients[0].enable` | `true` | 🚫 反向 WS 客户端开关 |
| `network.websocketClients[0].url` | `ws://127.0.0.1:6199/ws` | 🔧 **必须带 `/ws` 后缀**（pitfalls C2）；改过 AstrBot 端口时同步改这里 |
| `network.websocketClients[0].messagePostFormat` | `array` | 🚫 消息段格式，AstrBot aiocqhttp 适配 array，别改 segment |
| `network.websocketClients[0].token` | `""` | ⚙️ 双向鉴权 token；若在 cmd_config `platform[0].ws_reverse_token` 填了值，两边必须一致 |

## 4. `templates/persona_dafeiyu.md`（人格卡）

直接编辑文本即可（5012 字符的"大肥鱼"人设）。**改名要同步两处**：personas 表的 `persona_id` 和 cmd_config.json 的 `agent_runner.config.persona.persona_id`（pitfalls B5）。改人格文本则只需重写库里 system_prompt 字段后重启。
