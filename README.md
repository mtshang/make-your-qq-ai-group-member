# make-your-qq-ai-group-member

> 把一个 QQ 小号变成有"人设"、会读空气的 AI 群友。全组件免费开源。

这是一个 **Agent Skill**（智能体技能包）：把它喂给任意支持 Skill 的 AI Agent（WorkBuddy、Claude Code 等），Agent 会按 `SKILL.md` 里的流程自动完成全部部署——下载组件、铺配置、装插件、启动服务、引导扫码，最后交付一个能落地的 QQ 群聊机器人。

无需手动配置，无需写代码，全程只需提供：**一个 QQ 小号 + 一个大模型 API key + 跟着 Agent 走**。

## 最终效果

```
QQ 好友/群聊
   │ (消息)
   ▼
手机/PC QQ 客户端 ←──登录── NapCatQQ（协议端，模拟 QQ 客户端）
                                │
                                │ 反向 WebSocket: ws://127.0.0.1:6199/ws
                                ▼
                           AstrBot（LLM 管家，含 WebUI :6185）
                                ├── 插件: group_chat_plus（读空气核心）
                                ├── 人格卡: "大肥鱼"（已内置，可换成自己的）
                                └── HTTPS → 大模型 API（文本 + 视觉）
```

- 🗣️ **读空气**：群里聊天不 @ 也有概率自然接话（概率可调，默认 0.1），带时段系数、注意力/情绪感知、疲劳系统、消息质量打分，像真人一样有话多话少
- 🖼️ **识图**：群里发图能看懂并吐槽（依赖视觉模型，不支持时可一键关闭）
- 📝 **预置人格卡**："大肥鱼"人设 + 开场白开箱即用，改一段文本就能换成你自己的人设
- 🧩 **拼装开源组件**：[AstrBot](https://github.com/AstrBotDevs/AstrBot)（LLM 管家）+ [NapCatQQ](https://github.com/NapNeko/NapCatQQ)（QQ 协议端）+ [astrbot_plugin_group_chat_plus](https://github.com/Him666233/astrbot_plugin_group_chat_plus)（读空气插件），本 skill 不修改任何上游代码，只做部署编排

## 快速开始

1. **获取本仓库**（`Code` → `Download ZIP`，或 `git clone`）并解压
2. **交给你的 Agent**（按所用的 Agent 选择）：

   | Agent | 接入方式 |
   |---|---|
   | **WorkBuddy** | 直接把文件夹/zip 拖进对话 |
   | **终端类 Agent**（Claude Code / Codex 等，推荐） | 发文件夹路径或 zip，说「读 SKILL.md 按流程执行」 |
   | **其他桌面版 Agent**（有交互窗口的软件） | 把文件夹/zip 给它 + 说「读 SKILL.md 按流程执行」，**并补一句：「全程用 PowerShell/Python 命令行完成，不要模拟鼠标键盘操作 GUI，出任何报错立即停下问我」**——桌面 Agent 默认爱用"模拟人点界面"的范式，而本 skill 的坑几乎全是命令行细节坑，命令行范式能把出错率降一个量级 |
   | **Claude Code**（可选安装式） | 解压到 `~/.claude/skills/`（全局）或项目 `.claude/skills/` 下，新会话自动识别，可 `/make-your-qq-ai-group-member` 调用 |

3. Agent 会依次问你三件事：**bot 用的 QQ 小号**、**大模型 API key**（没有会给你创建引导，推荐 DeepSeek）、**安装到哪个目录**（默认 `D:\qqaibot`）
4. 剩下全自动：下载（国内镜像轮换）→ 配置 → 启动 → 出二维码扫码 → 七项全链路验收

> 部署约 10~20 分钟（视网速）。详细流程、参数说明、20 条踩坑记录都在 `SKILL.md` 和 `references/` 里，人类也能直接读懂。

## 目录结构

```
make-your-qq-ai-group-member/
├── SKILL.md                  # Agent 执行的主流程（Phase 0-7 + 验收清单）
├── references/
│   ├── pitfalls.md           # 20 条真实踩坑记录（出问题先查它）
│   ├── config-params.md      # 全部配置参数说明（想调"话多话少"看这个）
│   └── *-readme.md           # 三个上游组件的 README 存档（可脚本更新）
├── templates/                # 预置配置模板（已脱敏、含占位符）
│   ├── cmd_config.json       # AstrBot 主配置（平台/模型/人格绑定）
│   ├── astrbot_plugin_group_chat_plus_config.json  # 读空气全套参数
│   ├── napcat_onebot11.json  # NapCat 反向 WS 连接配置（Phase 6 注入源）
│   ├── persona_dafeiyu.md    # "大肥鱼"人格卡文本
│   └── deploy_state.json     # 部署状态单一来源（路径/QQ号/进度，agent 全程读写）
└── scripts/
    ├── bot_manager.py        # 日常一键启动/停止/状态（start/stop/status）
    ├── download.py           # GitHub 下载器（镜像轮换 + 直连兜底 + 假文件校验）
    ├── update_readmes.py     # 一键更新三个上游 README 到最新版
    └── verify.py             # 部署环境自检（端口/文件/JSON/HTTP）
```

## 免责声明

- 本项目是**部署编排工具**，本身不包含也不修改任何 QQ 协议实现；NapCatQQ 为第三方开源协议端，**使用非官方协议端存在账号风控/封禁风险**，请务必使用小号、避免频繁群发与加好友
- 大模型 API 调用费用由使用者自担；默认配置已按低成本取向设置（基础回复概率 0.1、决策推理关闭）
- 请遵守所在地区法律法规及腾讯软件许可协议；仅供学习交流，请勿用于骚扰、营销群发等用途
- 本项目与 AstrBot、NapCatQQ、astrbot_plugin_group_chat_plus 的作者无 affiliations，感谢上游开源作者

## License

[MIT](LICENSE)
