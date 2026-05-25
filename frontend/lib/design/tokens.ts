export const mentoriumTokens = {
  colors: {
    base: "#1a2f3f",
    s1: "#152738",
    s2: "#0f1e2a",
    s3: "#0a1520",
    s4: "#2a4a61",
    s5: "#243f55",
    gold: "#c9a96e",
    gold2: "#dfc08a",
    gold3: "rgba(201,169,110,0.14)",
    goldLight: "rgba(201,169,110,0.28)",
    silver: "#a8b8c4",
    textPrimary: "#e8eef2",
    textMuted: "rgba(168,184,196,0.78)",
    textSoft: "rgba(232,238,242,0.68)",
    lineSubtle: "rgba(168,184,196,0.14)",
    lineGold: "rgba(201,169,110,0.24)",
    lineStrong: "rgba(168,184,196,0.18)",
    panel: "rgba(10,21,32,0.84)",
    panelSoft: "rgba(21,39,56,0.92)",
    success: "#7ec9a2",
    warning: "#dfc08a",
    caution: "#d39a82"
  },
  gradients: {
    shell: "linear-gradient(180deg, rgba(26,47,63,0.98) 0%, rgba(10,21,32,1) 100%)",
    hero: "linear-gradient(135deg, rgba(21,39,56,0.96) 0%, rgba(10,21,32,1) 100%)",
    goldGlow: "radial-gradient(circle, rgba(201,169,110,0.24) 0%, rgba(201,169,110,0) 70%)",
    frame: "linear-gradient(180deg, rgba(15,30,42,0.98) 0%, rgba(10,21,32,0.98) 100%)",
    mist: "radial-gradient(circle at top, rgba(42,74,97,0.34), transparent 38%), radial-gradient(circle at right top, rgba(201,169,110,0.12), transparent 24%)"
  },
  fonts: {
    serif: 'Georgia, "Times New Roman", serif',
    sans: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    mono: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
  }
} as const;

export const capabilityStatusTone = {
  implemented_and_tested: "support",
  implemented_but_needs_manual_validation: "attention",
  partially_implemented: "review",
  foundation_only: "review",
  metadata_only: "support",
  not_implemented: "muted"
} as const;
