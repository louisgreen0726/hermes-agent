import { describe, expect, it } from "vitest";

import {
  BUILTIN_THEMES,
  DEFAULT_THEME_NAME,
  defaultLargeTheme,
  defaultTheme,
  hermesLightLargeTheme,
} from "./presets";

function luminance(hex: string): number {
  const channels = hex
    .replace("#", "")
    .match(/.{2}/g)!
    .map((part) => Number.parseInt(part, 16) / 255)
    .map((value) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
    );
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(a: string, b: string): number {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("Hermes Light (Large)", () => {
  it("is the unconfigured default without replacing Hermes Teal", () => {
    expect(DEFAULT_THEME_NAME).toBe("hermes-light-large");
    expect(BUILTIN_THEMES[DEFAULT_THEME_NAME]).toBe(hermesLightLargeTheme);
    expect(BUILTIN_THEMES.default).toBe(defaultTheme);
  });

  it("inherits the Teal Large scale and spacious layout", () => {
    expect(hermesLightLargeTheme.typography.baseSize).toBe(
      defaultLargeTheme.typography.baseSize,
    );
    expect(hermesLightLargeTheme.typography.lineHeight).toBe("1.65");
    expect(hermesLightLargeTheme.typography.letterSpacing).toBe("0");
    expect(hermesLightLargeTheme.layout).toEqual(defaultLargeTheme.layout);
    expect(hermesLightLargeTheme.typography.fontSans).toContain("PingFang SC");
    expect(hermesLightLargeTheme.typography.fontSans).toContain("Microsoft YaHei");
  });

  it("uses the locked palette and accessible semantic contrast", () => {
    const colors = hermesLightLargeTheme.colorOverrides!;
    expect(hermesLightLargeTheme.palette.background.hex).toBe("#FFFFFF");
    expect(hermesLightLargeTheme.palette.midground.hex).toBe("#171A1A");
    expect(colors.secondary).toBe("#F6F8F7");
    expect(colors.border).toBe("#D7DEDB");
    expect(colors.primary).toBe("#0F766E");
    expect(colors.accent).toBe("#E7F3F1");
    expect(colors.success).toBe("#147D4D");
    expect(colors.warning).toBe("#946200");
    expect(colors.destructive).toBe("#B42318");
    expect(contrast(colors.textPrimary!, "#FFFFFF")).toBeGreaterThanOrEqual(4.5);
    expect(contrast(colors.textSecondary!, "#FFFFFF")).toBeGreaterThanOrEqual(4.5);
    expect(contrast(colors.primary!, "#FFFFFF")).toBeGreaterThanOrEqual(4.5);
    expect(contrast(colors.ring!, "#FFFFFF")).toBeGreaterThanOrEqual(3);
    expect(contrast(colors.input!, "#FFFFFF")).toBeGreaterThanOrEqual(3);
  });

  it("uses the requested light terminal colors", () => {
    expect(hermesLightLargeTheme.terminalBackground).toBe("#F7F9F8");
    expect(hermesLightLargeTheme.terminalForeground).toBe("#17201E");
  });
});
