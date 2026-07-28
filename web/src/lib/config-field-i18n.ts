import type { Locale } from '@/i18n/types'

export interface ConfigFieldDisplay {
  label: string
  description: string
  optionLabels: Record<string, string>
}

interface ExactFieldTranslation {
  label: string
  description: string
  options?: Record<string, string>
}

const EXACT_FIELDS: Record<string, ExactFieldTranslation> = {
  model: {
    label: '默认模型',
    description: '新会话默认使用的模型。可填写“供应方/模型”形式的模型 ID。'
  },
  model_context_length: {
    label: '模型上下文长度',
    description: '覆盖模型元数据中的上下文窗口长度；设为 0 时自动检测。'
  },
  fallback_providers: {
    label: '备用供应方',
    description: '主供应方不可用时依次尝试的备用供应方。'
  },
  toolsets: {
    label: '已启用工具集',
    description: '默认向 Agent 提供的工具集列表。'
  },
  max_concurrent_sessions: {
    label: '最大并发会话数',
    description: 'Hermes 可同时处理的会话数量上限。'
  },
  max_live_sessions: {
    label: '最大活跃会话数',
    description: '内存中同时保持活跃的会话数量上限。'
  },
  'agent.max_turns': {
    label: '最大轮数',
    description: '单次 Agent 运行允许的最大模型调用轮数。'
  },
  'agent.service_tier': {
    label: 'API 服务等级',
    description: 'OpenAI 或 Anthropic 请求使用的服务等级。'
  },
  'agent.image_input_mode': {
    label: '图片输入模式',
    description: '控制 Agent 如何接收和处理图片输入。'
  },
  'terminal.backend': {
    label: '终端后端',
    description: '执行终端命令所使用的本地、容器或远程后端。'
  },
  'terminal.modal_mode': {
    label: 'Modal 沙箱模式',
    description: '使用 Modal 终端后端时采用的沙箱隔离模式。'
  },
  'terminal.cwd': {
    label: '终端工作目录',
    description: '终端命令的默认工作目录。'
  },
  'terminal.timeout': {
    label: '终端超时',
    description: '终端命令的默认超时时间。'
  },
  'browser.engine': {
    label: '浏览器引擎',
    description: '浏览器工具使用的自动化引擎。'
  },
  'browser.headed': {
    label: '显示浏览器窗口',
    description: '在本机显示浏览器窗口，并在多轮对话之间保持窗口。'
  },
  'browser.allow_private_urls': {
    label: '允许私有 URL',
    description: '允许浏览器访问回环地址和私有网络 URL。'
  },
  'browser.inactivity_timeout': {
    label: '浏览器空闲超时',
    description: '空闲浏览器会话被回收前的等待时间。'
  },
  'compression.enabled': {
    label: '启用上下文压缩',
    description: '上下文接近模型限制时自动压缩较早的对话内容。'
  },
  'compression.threshold': {
    label: '压缩阈值',
    description: '达到上下文容量的此比例后开始压缩。'
  },
  'memory.memory_enabled': {
    label: '启用长期记忆',
    description: '允许 Hermes 读取和维护 MEMORY.md。'
  },
  'memory.user_profile_enabled': {
    label: '启用用户档案',
    description: '允许 Hermes 读取和维护 USER.md。'
  },
  'memory.write_approval': {
    label: '记忆写入审批',
    description: '写入长期记忆前要求用户确认。'
  },
  'delegation.max_concurrent_children': {
    label: '最大并发子 Agent 数',
    description: '一个父 Agent 可同时运行的子 Agent 数量上限。'
  },
  'delegation.max_spawn_depth': {
    label: '最大委派深度',
    description: '子 Agent 继续创建下级 Agent 的最大层数。'
  },
  'approvals.mode': {
    label: '危险命令审批模式',
    description: '控制危险终端命令在执行前如何请求批准。',
    options: {
      manual: '始终手动确认',
      smart: '智能判断',
      off: '关闭审批'
    }
  },
  'security.redact_secrets': {
    label: '隐藏敏感信息',
    description: '在日志和可分享输出中隐藏检测到的密钥与令牌。'
  },
  'security.allow_private_urls': {
    label: '允许私有网络 URL',
    description: '允许网络工具访问回环地址和私有网络。'
  },
  timezone: {
    label: '时区',
    description: '定时任务和本地时间显示使用的 IANA 时区。'
  },
  'logging.level': {
    label: '日志级别',
    description: '写入 agent.log 的最低日志级别。'
  },
  'updates.pre_update_backup': {
    label: '更新前备份',
    description: 'Hermes 更新前是否自动创建本地完整备份。'
  },
  'updates.non_interactive_local_changes': {
    label: '非交互更新时的本地修改',
    description: 'Dashboard 或 Gateway 无终端提示地更新 Hermes 时，如何处理尚未提交的源码修改。',
    options: {
      stash: '暂存并在更新后重新应用',
      discard: '丢弃本地修改'
    }
  },
  'dashboard.theme': {
    label: 'Dashboard 主题',
    description: 'Web Dashboard 使用的视觉主题。',
    options: {
      'hermes-light-large': 'Hermes Light (Large)',
      default: 'Hermes Teal',
      'default-large': 'Hermes Teal (Large)',
      'nous-blue': 'Nous Blue',
      midnight: 'Midnight',
      ember: 'Ember',
      mono: 'Mono',
      cyberpunk: 'Cyberpunk',
      rose: 'Rose'
    }
  },
  'dashboard.show_token_analytics': {
    label: '显示本地 Token 分析',
    description: '显示仅供调试的本地 Token 与成本估算；该估算不等同于供应方账单。'
  },
  'backup.webdav.enabled': {
    label: '启用 WebDAV 云备份',
    description: '启用 WebDAV 原始 ZIP 上传和每日自动备份。'
  },
  'backup.webdav.url': {
    label: 'WebDAV URL',
    description: 'WebDAV 服务的 HTTPS 地址；URL 中不得包含用户名或密码。'
  },
  'backup.webdav.remote_path': {
    label: 'WebDAV 远端路径',
    description: 'WebDAV 服务中存放 Hermes 备份的目录。'
  },
  'backup.webdav.device_name': {
    label: '备份设备名称',
    description: '在远端备份列表中显示的当前设备名称。'
  },
  'backup.webdav.schedule': {
    label: '自动备份计划',
    description: '每日自动备份使用的五字段 cron 表达式。'
  },
  'backup.webdav.retention': {
    label: '备份保留数量',
    description: '当前设备在 WebDAV 中保留的最近完整备份数量。'
  }
}

// Leaf-key translations cover fields whose names cannot be composed cleanly
// from the shared segment glossary. The raw dot-path remains visible beside
// every label, so technical identity is preserved without exposing English UI
// copy as the primary field name.
const FIELD_LABELS_ZH: Record<string, string> = {
  abort_on_summary_failure: '摘要失败时中止',
  access_token_env: '访问 Token 环境变量',
  ack_enabled: '启用确认回应',
  ack_phrases: '确认短语',
  acked_advisories: '已确认的安全公告',
  adopt_existing_tab: '接管现有标签页',
  allow_any_attachment: '允许任意附件类型',
  allow_env_fallback: '允许环境变量回退',
  allow_lazy_installs: '允许按需安装',
  ambient_enabled: '启用环境音',
  ambient_gain: '环境音增益',
  ambient_path: '环境音文件路径',
  api_max_retries: 'API 最大重试次数',
  approval_mentions: '审批通知提及对象',
  archive_after_days: '归档等待天数',
  audio_tags: '音频标签',
  auto_decompose: '自动拆解任务',
  auto_decompose_per_tick: '每轮自动拆解数量',
  auto_local_for_private_urls: '私有 URL 自动使用本地浏览器',
  auto_source_bashrc: '自动加载 .bashrc',
  auto_speech_tags: '自动语音标签',
  auto_thread: '自动创建话题',
  auto_tts: '自动文字转语音',
  barge_in: '允许语音打断',
  battery: '电池状态显示',
  beep_enabled: '启用提示音',
  bell_on_complete: '完成时响铃',
  bit_rate: '比特率',
  bots_require_inline_mention: 'Bot 要求行内提及',
  buffer_threshold: '缓冲阈值',
  build_wait_timeout: '构建等待超时',
  busy_input_mode: 'Agent 忙碌时的输入模式',
  busy_steer_ack_enabled: '启用引导确认',
  cache_ttl: '缓存有效期',
  cache_ttl_seconds: '缓存有效期（秒）',
  capture_after_mode: '操作后截图模式',
  cdp_url: 'CDP URL',
  channels: '频道',
  child_timeout_seconds: '子 Agent 超时（秒）',
  clarify_timeout: '澄清请求超时',
  cli_refresh_interval: 'CLI 刷新间隔',
  codex_app_server_auto: '自动使用 Codex App Server',
  codex_gpt55_autoraise: '自动提升 Codex GPT-5.5 上下文',
  codex_gpt55_autoraise_notice: '显示 Codex GPT-5.5 自动提升提示',
  coding_context: '编码上下文',
  coding_instructions: '编码指令',
  command_allowlist: '命令允许列表',
  compact: '紧凑显示',
  compute_host_heartbeat_secs: '计算主机心跳间隔（秒）',
  compute_host_respawn_max: '计算主机最大重启次数',
  consolidate: '合并重复技能',
  container_cpu: '容器 CPU',
  container_disk: '容器磁盘',
  container_memory: '容器内存',
  container_persistent: '持久化容器',
  copy_shortcut: '复制快捷键',
  credential_source: '凭据来源',
  credits_notices: '额度提示',
  cua_telemetry: 'CUA 遥测',
  cursor: '流式输出光标',
  daemon_term_grace_seconds: '守护进程终止宽限期（秒）',
  daytona_image: 'Daytona 镜像',
  delivery_ledger: '投递账本',
  deny: '拒绝规则',
  destructive_slash_confirm: '危险斜杠命令确认',
  diarize: '说话人分离',
  dispatch_in_gateway: '由 Gateway 调度',
  dispatch_stale_timeout_seconds: '调度过期超时（秒）',
  dm_role_auth_guild: '私信角色认证服务器',
  docker_extra_args: 'Docker 额外参数',
  docker_forward_env: '转发到 Docker 的环境变量',
  docker_image: 'Docker 镜像',
  docker_mount_cwd_to_workspace: '将当前目录挂载到工作区',
  docker_network: 'Docker 网络',
  docker_run_as_host_user: '以宿主用户运行 Docker',
  docker_volumes: 'Docker 卷',
  download_timeout: '下载超时',
  duck_gain: '压低增益',
  echo_transcripts: '回显转写文本',
  edit_interval: '编辑更新间隔',
  enforce_on_docker: '对 Docker 强制执行',
  env_passthrough: '透传环境变量',
  environment_hint: '环境提示',
  environment_probe: '环境探测',
  ephemeral_system_ttl: '临时系统消息有效期',
  expected_audience: '预期受众',
  external_dirs: '外部技能目录',
  extra_allowed_hosts: '额外允许的主机',
  fields: '显示字段',
  file_mutation_verifier: '文件修改验证器',
  first_lines: '开头行数',
  fresh_final_after_seconds: '重新发送最终回复等待时间（秒）',
  freshness_minutes: '有效新鲜度（分钟）',
  fts_optimize_notice: 'FTS 优化提示',
  gateway_auto_continue_freshness: 'Gateway 自动继续有效期',
  gateway_notify_interval: 'Gateway 通知间隔',
  gateway_timeout_warning: 'Gateway 超时警告',
  guard_agent_created: '保护 Agent 创建的技能',
  guardrail_identifier: 'Guardrail 标识符',
  guardrail_version: 'Guardrail 版本',
  home_mode: 'Home 目录模式',
  hooks_auto_accept: '自动接受 Hook',
  hygiene_failure_cooldown_seconds: '上下文整理失败冷却（秒）',
  hygiene_hard_message_limit: '上下文整理消息硬上限',
  hygiene_timeout_seconds: '上下文整理超时（秒）',
  hygiene_total_ceiling_seconds: '上下文整理总时限（秒）',
  idle_compact_after_seconds: '空闲压缩等待时间（秒）',
  idle_timeout_minutes: '空闲超时（分钟）',
  ignore_other_user_mentions: '忽略对其他用户的提及',
  in_place: '原位压缩',
  inherit_mcp_toolsets: '继承 MCP 工具集',
  inline_diffs: '内联显示差异',
  inline_shell: '允许内联 Shell',
  inline_shell_timeout: '内联 Shell 超时',
  install_strategy: '安装策略',
  intent_ack_continuation: '意图确认后继续',
  interface: '界面模式',
  interim_assistant_messages: '显示中间 Assistant 消息',
  keep: '保留数量',
  last_lines: '末尾行数',
  limit: '数量上限',
  listing: '显示工具清单',
  listing_max_tokens: '工具清单最大 Token 数',
  local_stream_stale_timeout: '本地流停滞超时',
  loop_watchdog: '事件循环看门狗',
  loopback_host_alias: '回环主机别名',
  managed_persistence: '托管持久化',
  max_attachment_bytes: '附件最大字节数',
  max_concurrent_runs: '最大并发运行数',
  max_dispatches: '最大调度次数',
  max_image_dimension: '图片最大边长',
  max_in_progress_per_profile: '每个 Profile 最大进行中任务数',
  max_inbound_media_bytes: '入站媒体最大字节数',
  max_ms: '最大延迟（毫秒）',
  max_recording_seconds: '最大录音时长（秒）',
  max_restarts: '最大重启次数',
  max_search_limit: '搜索结果最大上限',
  max_stale_seconds: '最大过期容忍时间（秒）',
  max_starts: '最大启动次数',
  max_summary_chars: '摘要最大字符数',
  max_verify_nudges: '最大验证提醒次数',
  mcp_discovery_timeout: 'MCP 发现超时',
  mcp_reload_confirm: 'MCP 重载确认',
  media_delivery_allow_dirs: '媒体投递允许目录',
  memory_char_limit: 'MEMORY.md 字符上限',
  memory_notifications: '记忆通知',
  min_coding_score: '最低编码评分',
  min_idle_hours: '最短空闲时间（小时）',
  min_interval_hours: '最小间隔（小时）',
  min_ms: '最小延迟（毫秒）',
  min_secret_chars: '密钥最小字符数',
  min_tail_user_messages: '最少保留尾部用户消息数',
  mirror_delivery: '镜像投递',
  modal_image: 'Modal 镜像',
  nas_jwks_url: 'NAS JWKS URL',
  no_overlay: '禁用覆盖层',
  optimize_streaming_latency: '优化流式延迟',
  override_existing: '覆盖现有值',
  parallel_tool_call_guidance: '并行工具调用指引',
  password_hash: '密码哈希',
  paste_collapse_char_threshold: '粘贴内容折叠字符阈值',
  paste_collapse_threshold: '粘贴内容折叠行数阈值',
  paste_collapse_threshold_fallback: '粘贴内容折叠回退阈值',
  persist_prompts: '持久保存 Prompt',
  persistent_output: '持久显示输出',
  persistent_output_max_lines: '持久输出最大行数',
  persistent_shell: '持久化 Shell',
  persona_prompt_file: 'Persona Prompt 文件',
  personality: '显示个性',
  platform_connect_timeout: '平台连接超时',
  prefill_messages_file: '预填消息文件',
  proactive_prune_min_reclaim_tokens: '主动清理最少回收 Token 数',
  proactive_prune_min_result_chars: '主动清理结果最小字符数',
  proactive_prune_tokens: '主动清理 Token 阈值',
  profile_build: 'Profile 构建引导',
  prune_builtins: '清理内置技能',
  reasoning_full: '完整显示推理',
  reasoning_style: '推理显示样式',
  record_key: '录音快捷键',
  ref_audio: '参考音频',
  ref_text: '参考文本',
  refresh_interval: '刷新间隔',
  render_mode: '渲染模式',
  response_cache: '响应缓存',
  response_cache_ttl: '响应缓存有效期',
  restart_drain_timeout: '重启排空超时',
  resume_display: '恢复会话显示模式',
  resume_exchanges: '恢复时显示的对话轮数',
  resume_max_assistant_chars: '恢复时 Assistant 最大字符数',
  resume_max_assistant_lines: '恢复时 Assistant 最大行数',
  resume_max_user_chars: '恢复时用户消息最大字符数',
  resume_skip_tool_only: '恢复时跳过仅工具轮次',
  rewrite_loopback_urls: '重写回环 URL',
  rich_drafts: '富文本草稿',
  rich_messages: '富文本消息',
  sample_rate: '采样率',
  scale: '缩放比例',
  scope: '作用域',
  search_default_limit: '默认搜索结果数',
  server_actions: '服务器操作',
  service_account_token_env: '服务账户 Token 环境变量',
  session_db_timeout_seconds: '会话数据库超时（秒）',
  session_key: '会话密钥',
  session_ttl_seconds: '会话有效期（秒）',
  shell_init_files: 'Shell 初始化文件',
  show_commentary: '显示 Commentary',
  silence_duration: '静音持续时间',
  silence_threshold: '静音阈值',
  singularity_image: 'Singularity 镜像',
  slug: 'Pet 标识',
  speech_gain: '语音增益',
  speed: '语速',
  stale_after_days: '过期判定天数',
  stream_only_base_urls: '仅流式基础 URL',
  stream_processing_mode: '流式处理模式',
  strict: '严格模式',
  subagent_auto_approve: '自动批准子 Agent',
  tag_audio_events: '标注音频事件',
  task_completion_guidance: '任务完成指引',
  template_vars: '模板变量',
  tirith_enabled: '启用 Tirith',
  tirith_fail_open: 'Tirith 失败时放行',
  tirith_path: 'Tirith 程序路径',
  tirith_timeout: 'Tirith 超时',
  tool_preview_length: '工具预览长度',
  tool_use_enforcement: '强制使用工具',
  trace: '跟踪模式',
  transient_retries: '临时错误重试次数',
  trust_recent_files: '信任最近文件',
  trust_recent_files_seconds: '最近文件信任时限（秒）',
  ttl_hours: '有效期（小时）',
  tui_agents_nudge: 'TUI AGENTS.md 提醒',
  tui_auto_resume_recent: 'TUI 自动恢复最近会话',
  tui_status_indicator: 'TUI 状态指示器',
  tunnel_port: '隧道端口',
  turn_completion_explainer: '回合完成说明',
  turn_isolation: '回合隔离',
  unicode_cols: 'Unicode 列宽',
  upstream_deny_cidrs: '上游拒绝 CIDR',
  user_char_limit: 'USER.md 字符上限',
  user_id: '用户 ID',
  vacuum_after_prune: '清理后压缩数据库',
  verify_guidance: '验证指引',
  verify_on_stop: '停止前验证',
  wait_mode: '等待模式',
  wait_timeout: '等待超时',
  websocket_heartbeat_ack_max_age_seconds: 'WebSocket 心跳确认最大间隔（秒）',
  websocket_liveness_failure_threshold: 'WebSocket 存活检查失败阈值',
  websocket_liveness_interval_seconds: 'WebSocket 存活检查间隔（秒）',
  websocket_max_latency_seconds: 'WebSocket 最大延迟（秒）',
  window_seconds: '时间窗口（秒）',
  worker_log_backup_count: 'Worker 日志备份数量',
  worker_log_rotate_bytes: 'Worker 日志轮转字节数',
  wrap_response: '包装 Cron 回复'
}

const SEGMENTS: Record<string, string> = {
  general: '通用',
  agent: 'Agent',
  terminal: '终端',
  browser: '浏览器',
  web: '网页',
  memory: '记忆',
  compression: '压缩',
  security: '安全',
  delegation: '委派',
  display: '显示',
  dashboard: 'Dashboard',
  gateway: 'Gateway',
  sessions: '会话',
  checkpoints: '检查点',
  cron: '定时任务',
  skills: '技能',
  tools: '工具',
  toolsets: '工具集',
  logging: '日志',
  approvals: '审批',
  auxiliary: '辅助任务',
  curator: '技能整理器',
  kanban: '看板',
  updates: '更新',
  backup: '备份',
  webdav: 'WebDAV',
  streaming: '流式输出',
  network: '网络',
  proxy: '代理',
  desktop: '桌面应用',
  voice: '语音',
  tts: '文字转语音',
  stt: '语音转文字',
  model: '模型',
  provider: '供应方',
  backend: '后端',
  enabled: '启用',
  disabled: '停用',
  mode: '模式',
  timeout: '超时',
  timeout_seconds: '超时秒数',
  interval_hours: '间隔小时数',
  max_turns: '最大轮数',
  max_iterations: '最大迭代次数',
  max_attempts: '最大尝试次数',
  max_retries: '最大重试次数',
  retries: '重试次数',
  max_bytes: '最大字节数',
  max_lines: '最大行数',
  max_line_length: '最大行长度',
  max_tokens: '最大 Token 数',
  max_size_mb: '最大大小（MB）',
  max_file_size_mb: '最大文件大小（MB）',
  max_total_size_mb: '最大总大小（MB）',
  max_snapshots: '最大快照数',
  max_concurrent_sessions: '最大并发会话数',
  max_live_sessions: '最大活跃会话数',
  max_parallel_jobs: '最大并行任务数',
  retention: '保留数量',
  retention_days: '保留天数',
  backup_count: '备份数量',
  backup_keep: '备份保留数量',
  auto_prune: '自动清理',
  auto_archive: '自动归档',
  auto_archive_days: '自动归档天数',
  auto_install: '自动安装',
  auto_continue: '自动继续',
  auto_reload_on_config_change: '配置更改后自动重新加载',
  provider_filter: '供应方筛选',
  service_tier: '服务等级',
  reasoning_effort: '推理强度',
  api_key: 'API 密钥',
  api_mode: 'API 模式',
  base_url: '基础 URL',
  url: 'URL',
  public_url: '公开 URL',
  server_url: '服务器 URL',
  callback_url: '回调 URL',
  portal_url: 'Portal URL',
  username: '用户名',
  password: '密码',
  secret: '密钥',
  client_id: '客户端 ID',
  project_id: '项目 ID',
  account: '账户',
  region: '区域',
  language: '语言',
  language_code: '语言代码',
  model_id: '模型 ID',
  voice_id: '声音 ID',
  device: '设备',
  device_name: '设备名称',
  cwd: '工作目录',
  workdir: '工作目录',
  binary_path: '程序路径',
  trace_dir: '跟踪目录',
  remote_path: '远端路径',
  domains: '域名',
  shared_files: '共享文件',
  allowed_channels: '允许的频道',
  allowed_chats: '允许的聊天',
  allowed_rooms: '允许的房间',
  free_response_channels: '免提及回复频道',
  free_response_rooms: '免提及回复房间',
  require_mention: '要求提及',
  require_mention_channels: '要求提及的频道',
  thread_require_mention: '话题中要求提及',
  reactions: '表情回应',
  history_backfill: '历史消息补录',
  history_backfill_limit: '历史消息补录上限',
  output_retention: '输出保留数量',
  context: '上下文',
  context_file_max_chars: '上下文文件最大字符数',
  file_read_max_chars: '文件读取最大字符数',
  threshold: '阈值',
  threshold_tokens: 'Token 阈值',
  threshold_pct: '百分比阈值',
  target_ratio: '目标比例',
  protect_first_n: '保护开头消息数',
  protect_last_n: '保护末尾消息数',
  progress_notices: '进度通知',
  write_approval: '写入审批',
  warnings_enabled: '启用警告',
  hard_stop_enabled: '启用强制停止',
  warn_after: '警告阈值',
  hard_stop_after: '强制停止阈值',
  exact_failure: '完全相同的失败',
  same_tool_failure: '同一工具失败',
  idempotent_no_progress: '幂等操作无进展',
  level: '级别',
  schedule: '计划',
  theme: '主题',
  skin: '皮肤',
  transport: '传输方式',
  engine: '引擎',
  headed: '显示窗口',
  record_sessions: '记录会话',
  inactivity_timeout: '空闲超时',
  command_timeout: '命令超时',
  allow_private_urls: '允许私有 URL',
  allow_unsafe_evaluate: '允许不安全脚本求值',
  restrict_evaluate: '限制脚本求值',
  dialog_policy: '对话框策略',
  dialog_timeout_s: '对话框超时秒数',
  search_backend: '搜索后端',
  extract_backend: '内容提取后端',
  extract_char_limit: '内容提取字符上限',
  default_assignee: '默认负责人',
  orchestrator_profile: '编排配置档案',
  orchestrator_enabled: '启用编排器',
  dispatch_interval_seconds: '调度间隔秒数',
  failure_limit: '失败次数上限',
  active_preset: '当前预设',
  default_preset: '默认预设',
  reference_models: '参考模型',
  aggregator: '汇总模型',
  save_traces: '保存跟踪记录',
  privacy_filter: '隐私过滤',
  show_reasoning: '显示推理',
  show_cost: '显示成本',
  show_token_analytics: '显示 Token 分析',
  timestamps: '时间戳',
  timestamp_format: '时间戳格式',
  tool_progress_command: '工具进度命令',
  tool_progress_grouping: '工具进度分组',
  friendly_tool_labels: '易读工具名称',
  final_response_markdown: '最终回复 Markdown',
  redact_secrets: '隐藏敏感信息',
  redact_pii: '隐藏个人身份信息',
  cjk_fts: 'CJK 全文搜索',
  search_slow_ms: '慢速搜索阈值（毫秒）',
  write_json_snapshots: '写入 JSON 快照',
  write_sessions_json: '写入会话 JSON',
  force_ipv4: '强制使用 IPv4',
  pre_update_backup: '更新前备份',
  non_interactive_local_changes: '非交互更新时的本地修改',
  refresh_cua_driver: '刷新 CUA 驱动',
  repo_scan_enabled: '启用代码库扫描',
  repo_scan_roots: '代码库扫描根目录',
  repo_scan_exclude_paths: '代码库扫描排除路径',
  disable_gpu: '停用 GPU',
  electron_flags: 'Electron 参数',
  webhook: 'Webhook',
  webhooks: 'Webhook',
  tool_output: '工具输出',
  tool_loop_guardrails: '工具循环保护',
  model_catalog: '模型目录',
  x_search: 'X 搜索',
  secrets: '密钥管理'
}

const TECHNICAL_SEGMENTS = new Set([
  'api',
  'mcp',
  'oauth',
  'cli',
  'json',
  'yaml',
  'http',
  'https',
  'lsp',
  'tts',
  'stt',
  'moa',
  'cdp',
  'cua',
  'fts',
  'docker',
  'modal',
  'daytona',
  'singularity',
  'openai',
  'openrouter',
  'anthropic',
  'bedrock',
  'vertex',
  'gemini',
  'discord',
  'telegram',
  'slack',
  'matrix',
  'mattermost',
  'bitwarden',
  'onepassword'
])

const OPTION_LABELS: Record<string, string> = {
  auto: '自动',
  default: '默认',
  manual: '手动',
  off: '关闭',
  low: '低',
  medium: '中',
  high: '高',
  xhigh: '极高',
  max: '最高',
  ultra: '超高',
  minimal: '最少',
  full: '完整',
  fixed: '固定',
  flex: '灵活',
  local: '本地',
  custom: '自定义',
  smart: '智能',
  interrupt: '中断',
  queue: '排队',
  steer: '引导',
  stash: '暂存并恢复',
  discard: '丢弃',
  typing: '模拟输入',
  env: '环境变量',
  sandbox: '沙箱'
}

function englishLabel(path: string): string {
  const leaf = path.split('.').pop() ?? path
  return leaf.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
}

function zhSegment(segment: string): string {
  const direct = SEGMENTS[segment] ?? FIELD_LABELS_ZH[segment]
  if (direct) return direct
  if (TECHNICAL_SEGMENTS.has(segment.toLowerCase())) return segment.toUpperCase()

  const pieces = segment.split('_')
  const translated = pieces.map(piece => SEGMENTS[piece])
  if (translated.every(Boolean)) return translated.join('')
  return segment
}

function zhDescription(path: string, label: string, schema: Record<string, unknown>): string {
  const rawDescription = schema.description ? String(schema.description) : ''
  if (/[㐀-鿿]/.test(rawDescription)) return rawDescription

  const sectionPath = path.includes('.') ? path.slice(0, path.lastIndexOf('.')) : 'general'
  const section = zhSegment(sectionPath.split('.')[0] ?? 'general')
  const context = section ? `${section}中的` : ''
  const type = String(schema.type ?? '').toLowerCase()
  const hasOptions = Array.isArray(schema.options) && schema.options.length > 0

  if (hasOptions) {
    return `设置${context}“${label}”；界面显示中文选项，保存时仍使用原始配置值。`
  }
  if (type === 'boolean' || type === 'bool') {
    return `控制${context}“${label}”是否启用。`
  }
  if (type === 'array' || type === 'list') {
    return `设置${context}“${label}”列表。`
  }
  if (type === 'integer' || type === 'number' || type === 'float') {
    return `设置${context}“${label}”的数值。`
  }
  return `设置${context}“${label}”。`
}

export function getConfigSectionLabel(section: string, locale: Locale): string {
  return locale === 'zh' ? zhSegment(section) : englishLabel(section)
}

export function getConfigFieldDisplay(
  path: string,
  schema: Record<string, unknown>,
  locale: Locale
): ConfigFieldDisplay {
  const options = Array.isArray(schema.options) ? schema.options.map(option => String(option)) : []

  if (locale !== 'zh') {
    return {
      label: englishLabel(path),
      description: schema.description ? String(schema.description) : '',
      optionLabels: Object.fromEntries(options.map(option => [option, option]))
    }
  }

  const exact = EXACT_FIELDS[path]
  const leaf = path.split('.').pop() ?? path
  const label = exact?.label ?? zhSegment(leaf)
  return {
    label,
    description: exact?.description ?? zhDescription(path, label, schema),
    optionLabels: Object.fromEntries(
      options.map(option => [option, exact?.options?.[option] ?? OPTION_LABELS[option] ?? option])
    )
  }
}
