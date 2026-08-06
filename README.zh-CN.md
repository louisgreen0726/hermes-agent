<p align="center">
  <img src="assets/banner.png" alt="Louis Hermes Agent" width="100%">
</p>

# Louis Hermes Agent

<p align="center">
  <strong>一个源自 Hermes Agent、现由 Louis 项目独立维护的 AI Agent 项目。</strong>
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/louisgreen0726/hermes-agent/releases"><img src="https://img.shields.io/badge/stable-Louis--0.20.0.1-2563eb" alt="稳定版本：Louis-0.20.0.1"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-16a34a" alt="MIT 许可证"></a>
  <a href="https://github.com/louisgreen0726/hermes-agent/issues"><img src="https://img.shields.io/badge/issues-Louis%20project-7c3aed" alt="Louis 项目问题反馈"></a>
</p>

> [!IMPORTANT]
> Louis Hermes Agent 是
> [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent)
> 的独立衍生项目，不是 Nous Research 的官方产品或官方发行版。原项目、原贡献者、
> 版权声明与 MIT 许可证均会被完整保留和注明。

## 这个项目是什么

Louis Hermes Agent 是一个可以运行在命令行、终端 UI、Electron 桌面端、
Web 管理面板和消息网关中的个人 AI Agent。项目保留了 Hermes 原有的工具、
记忆、技能、插件、定时任务、子代理、模型服务商、终端后端与浏览器自动化基础，
同时建立自己的产品方向、维护节奏和发布流程。

为了保留清晰的代码来源，本仓库在 GitHub 上仍处于原项目的 fork 网络中；但在
实际维护和发布层面，它已经作为独立项目运行：

- 所有 Louis 版本均从 `louisgreen0726/hermes-agent` 发布。
- Louis 安装只会自动更新到本仓库的 `origin/main`。
- 上游提交只会经过人工评估后选择性吸收，不会自动 merge 或 rebase。
- 不承诺与上游未来的每一次变更保持完全兼容。
- GitHub 显示大量“落后于上游”的提交属于预期现象，不代表 Louis 版本失效。

## 项目来源

Louis 独立维护线开始于 2026 年 7 月 27 日（UTC+8），起点为上游 Hermes Agent
提交
[`41f2196c`](https://github.com/NousResearch/hermes-agent/commit/41f2196c530b3359d9a7fc9c7bd41e9ddd7882c5)，
继承时的 Hermes Agent 版本为 `0.19.0`。

当前版本化基线选择性吸收了 Hermes Agent `0.20.0`（上游发布版本
`2026.8.3`）中经过审查的改动。这是经审计的回迁边界，不代表整体代码树同步。

Nous Research 创建了原始 Hermes Agent 架构以及本项目继承代码中的大部分实现。
Louis 在 MIT 许可证允许的范围内继续开发。源码历史、文档、资源或集成名称中保留的
Nous Research 引用用于说明代码来源或上游服务，不表示本独立项目属于 Nous Research
官方发行版。

## 当前状态

| 项目 | 当前状态 |
| --- | --- |
| 维护状态 | 活跃，独立维护 |
| 生产分支 | `main` |
| 稳定基线 | [`Louis-0.20.0.1`](docs/releases/LOUIS_0.20.0.1.md) |
| Python 包版本 | `0.20.0+Louis.1` |
| 选择性上游基线 | Hermes Agent `0.20.0` / `2026.8.3` |
| 当前 `main` | `Louis-0.20.0.1` 稳定基线 |
| 与上游的关系 | 仅选择性评估和回迁 |
| 自动更新来源 | 仅 Louis `origin/main` |

多个具名自定义服务商可以共用同一个中转 URL，同时保持各自独立的 API Key、模型、
API 模式和凭据池；这一身份隔离约束已经属于稳定基线。

版本历史和待发布内容记录在
[`LOUIS_RELEASE_NOTES.md`](LOUIS_RELEASE_NOTES.md) 与
[`docs/releases/LOUIS_UNRELEASED.md`](docs/releases/LOUIS_UNRELEASED.md) 中。

## 主要能力

从 Hermes 继承的基础能力包括：

- 交互式 CLI、基于 Ink 的 TUI、Electron 桌面端与 Web 管理面板。
- Telegram、Discord、Slack、WhatsApp、Signal 等消息平台网关。
- 持久会话、记忆、技能、插件、MCP、定时任务和子代理委派。
- 本地、Docker、SSH、Singularity、Modal 和 Daytona 终端环境。
- 多种模型服务商，以及兼容 OpenAI、Anthropic 和 Responses API 的自定义端点。

Louis 当前独立维护的能力包括：

- Telegram Native Guest Mode，以及富 Markdown 表格与中文消息投递。
- 用于管理模型、服务商、Gateway、诊断、日志、备份和安全更新的原生管理中心。
- 自定义服务商分组、API 模式保持，以及同一中转端点下具名服务商的凭据隔离。
- 由候选版本自身控制的更新验证、回归测试门禁、回滚保护和 Gateway 安全重启。
- 支持按设备保留和定时执行的 WebDAV 备份与恢复。
- 简体中文 Dashboard、本地化配置元数据与 Louis Dashboard 主题。
- 选择性吸收 0.20.0 的依赖、脱敏、daemon 审批、终端提示、patch、搜索和写入
  落盘校验加固。
- `/init`、直接 `!` shell 命令、重依赖懒加载，以及按 process home 隔离的启动
  配置缓存。
- 带证据事实核查的 Grounded Citations，以及显式启用、支持签名和有界异步投递的
  outbound webhook。
- 统一的 STT 语言选择与本地 Whisper prompt，并为 TTS 提供共享清洗、速度、
  instructions、provider、language 和 xAI normalization 控制。
- Desktop Quick Entry 复用现有提交流程投递到当前、新建或最近会话，并提供可见的
  全局快捷键错误和全部内置语言支持。

更完整的项目与发布策略请参阅 [`LOUIS.md`](LOUIS.md)。

## 安装

### Linux、macOS、WSL2 和 Termux

```bash
curl -fsSL https://raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.sh | bash
```

### Windows 原生 PowerShell

```powershell
iex (irm https://raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.ps1)
```

安装完成后：

```bash
hermes setup          # 配置模型服务商、工具和集成
hermes                # 启动交互式 Agent
hermes-manage         # 打开 Louis 管理中心
hermes gateway        # 管理消息平台
hermes doctor         # 诊断安装状态
```

## 更新

Louis 安装只从本仓库更新，不会直接同步上游：

```bash
hermes update
```

生产环境可以先验证候选版本，再执行激活：

```bash
hermes-update-louis --dry-run
hermes-update-louis
```

不要在生产检出中运行 `git pull upstream main`。上游代码只能在独立集成分支中，
经过代码审查和 Louis 回归测试后再决定是否吸收。

## 文档与支持

- [项目与发布策略](LOUIS.md)
- [Louis 版本记录](LOUIS_RELEASE_NOTES.md)
- [仓库内文档源码](website/docs)
- [Louis 问题反馈](https://github.com/louisgreen0726/hermes-agent/issues)
- [原始 Hermes Agent 项目](https://github.com/NousResearch/hermes-agent)
- [原始上游文档](https://hermes-agent.nousresearch.com/docs/)

上游文档仍可用于了解继承自 Hermes 的通用能力；当上游文档与本仓库的 Louis 特有
行为或命令不一致时，以本仓库内容为准。

## 许可证与署名

本项目按照 [MIT 许可证](LICENSE) 分发。

Hermes Agent 最初由 [Nous Research](https://nousresearch.com) 及其贡献者创建。
Louis Hermes Agent 由 Louis 项目独立维护，与 Nous Research 不存在隶属或官方背书关系。
