import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: [
        'src/lib/grounding.ts',
        'src/lib/utils.ts',
        'src/lib/errors.ts',
        'src/middleware.ts',
        'src/components/theme-provider.tsx',
        'src/components/theme-toggle.tsx',
        'src/components/auth-guard.tsx',
        'src/components/trust-score-gauge.tsx',
        'src/components/grounding-attribution.tsx',
        'src/components/ui/stat-card.tsx',
      ],
      thresholds: {
        lines: 90,
        functions: 75,
        branches: 60,
        statements: 90,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
