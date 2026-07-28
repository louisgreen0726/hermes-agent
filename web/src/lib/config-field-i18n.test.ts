import { describe, expect, it } from 'vitest'

import { getConfigFieldDisplay, getConfigSectionLabel } from './config-field-i18n'

const previouslyGenericFields = [
  ['mcp_discovery_timeout', 'MCP 发现超时', 'number'],
  ['agent.restart_drain_timeout', '重启排空超时', 'number'],
  ['terminal.docker_mount_cwd_to_workspace', '将当前目录挂载到工作区', 'boolean'],
  ['display.resume_max_assistant_lines', '恢复时 Assistant 最大行数', 'number'],
  ['discord.websocket_max_latency_seconds', 'WebSocket 最大延迟（秒）', 'number'],
  ['gateway.media_delivery_allow_dirs', '媒体投递允许目录', 'array'],
  ['security.allow_lazy_installs', '允许按需安装', 'boolean'],
  ['desktop.auto_continue.freshness_minutes', '有效新鲜度（分钟）', 'number']
] as const

describe('Simplified Chinese config field labels', () => {
  it.each(previouslyGenericFields)(
    'translates %s with a contextual Chinese description',
    (path, expectedLabel, type) => {
      const display = getConfigFieldDisplay(path, { type }, 'zh')

      expect(display.label).toBe(expectedLabel)
      expect(display.label).not.toBe('配置项')
      expect(display.description).toMatch(/[\u3400-\u9fff]/)
      expect(display.description).not.toContain('配置项')
    }
  )

  it('translates backend-only config sections instead of using a placeholder', () => {
    expect(getConfigSectionLabel('general', 'zh')).toBe('通用')
    expect(getConfigSectionLabel('tool_output', 'zh')).toBe('工具输出')
    expect(getConfigSectionLabel('tool_loop_guardrails', 'zh')).toBe('工具循环保护')
    expect(getConfigSectionLabel('model_catalog', 'zh')).toBe('模型目录')
    expect(getConfigSectionLabel('x_search', 'zh')).toBe('X 搜索')
    expect(getConfigSectionLabel('secrets', 'zh')).toBe('密钥管理')
  })

  it('shows friendly theme names while preserving raw stored values', () => {
    const display = getConfigFieldDisplay(
      'dashboard.theme',
      {
        type: 'select',
        options: ['hermes-light-large', 'default', 'default-large', 'nous-blue']
      },
      'zh'
    )

    expect(display.optionLabels).toEqual({
      'hermes-light-large': 'Hermes Light (Large)',
      default: 'Hermes Teal',
      'default-large': 'Hermes Teal (Large)',
      'nous-blue': 'Nous Blue'
    })
  })

  it('keeps non-Chinese locales on the backend schema description', () => {
    const display = getConfigFieldDisplay(
      'agent.restart_drain_timeout',
      { type: 'number', description: 'Agent restart drain timeout' },
      'en'
    )

    expect(display.label).toBe('Restart Drain Timeout')
    expect(display.description).toBe('Agent restart drain timeout')
  })
})
