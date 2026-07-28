import type { Locale } from '@/i18n/types'

const INTL_LOCALES: Partial<Record<Locale, string>> = {
  zh: 'zh-CN',
  'zh-hant': 'zh-TW'
}

export function toIntlLocale(locale: Locale): string {
  return INTL_LOCALES[locale] ?? locale
}

export function formatMessage(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((result, [key, value]) => result.replaceAll(`{${key}}`, String(value)), template)
}

export function formatDateTime(
  value: string | number | Date,
  locale: Locale,
  options: Intl.DateTimeFormatOptions = {
    dateStyle: 'medium',
    timeStyle: 'short'
  }
): string {
  return new Intl.DateTimeFormat(toIntlLocale(locale), options).format(value instanceof Date ? value : new Date(value))
}

export function formatNumber(value: number, locale: Locale, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(toIntlLocale(locale), options).format(value)
}

export function formatRelativeSeconds(deltaSeconds: number, locale: Locale): string {
  const formatter = new Intl.RelativeTimeFormat(toIntlLocale(locale), {
    numeric: 'auto'
  })
  const absolute = Math.abs(deltaSeconds)
  if (absolute < 60) return formatter.format(0, 'second')
  if (absolute < 3600) return formatter.format(Math.trunc(deltaSeconds / 60), 'minute')
  if (absolute < 86400) return formatter.format(Math.trunc(deltaSeconds / 3600), 'hour')
  return formatter.format(Math.trunc(deltaSeconds / 86400), 'day')
}

export function formatUnixRelative(timestampSeconds: number, locale: Locale): string {
  return formatRelativeSeconds(timestampSeconds - Date.now() / 1000, locale)
}

export function formatIsoRelative(iso: string, locale: Locale): string {
  const timestamp = new Date(iso).getTime()
  if (Number.isNaN(timestamp)) return locale === 'zh' ? '未知' : 'unknown'
  return formatRelativeSeconds((timestamp - Date.now()) / 1000, locale)
}
