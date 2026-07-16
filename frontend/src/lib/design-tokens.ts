/**
 * Dark-enterprise accent tones for StatCard / icons (Phase 7.5).
 * Colors resolve via CSS variables in globals.css + tailwind.config.js.
 */
export const accentTones = {
  blue: {
    bg: 'bg-accent-blue/10',
    text: 'text-accent-blue',
    border: 'border-accent-blue/20',
  },
  red: {
    bg: 'bg-accent-red/10',
    text: 'text-accent-red',
    border: 'border-accent-red/20',
  },
  green: {
    bg: 'bg-accent-green/10',
    text: 'text-accent-green',
    border: 'border-accent-green/20',
  },
  amber: {
    bg: 'bg-accent-amber/10',
    text: 'text-accent-amber',
    border: 'border-accent-amber/20',
  },
  purple: {
    bg: 'bg-accent-purple/10',
    text: 'text-accent-purple',
    border: 'border-accent-purple/20',
  },
} as const

export type AccentTone = keyof typeof accentTones

/** Shared surface class names (prefer these over one-off slate hex stacks). */
export const surfaces = {
  page: 'bg-background text-foreground',
  glass:
    'bg-card/80 backdrop-blur-xl border border-border rounded-2xl hover:border-border/80 transition-all',
  solid: 'bg-card border border-border rounded-xl',
} as const
