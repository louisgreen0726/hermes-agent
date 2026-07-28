import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Locale } from "@/i18n/types";
import { formatIsoRelative, formatUnixRelative } from "@/lib/locale-format";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Mondwest font only — use on layout shells; do not force normal-case here or `text-display` chrome (Segmented, badges) stops uppercasing. */
export const themedFont = "font-mondwest";

/** Mondwest body copy — sentence-case themed text (not uppercase chrome). */
export const themedBody = "font-mondwest normal-case";

/** Mondwest brand chrome — uppercase section headers and nav labels. */
export const themedChrome = "font-mondwest text-display";

/** Relative time from a Unix epoch timestamp (seconds). */
export function timeAgo(ts: number, locale: Locale = "en"): string {
  return formatUnixRelative(ts, locale);
}

/** Relative time from an ISO-8601 timestamp string. */
export function isoTimeAgo(iso: string, locale: Locale = "en"): string {
  return formatIsoRelative(iso, locale);
}
