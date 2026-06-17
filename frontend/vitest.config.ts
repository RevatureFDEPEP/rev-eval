import path from 'path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    coverage: {
      provider: 'v8',
      include: [
        'src/app/_components/**',
        'src/lib/hooks/useTimer.ts',
        'src/lib/schemas/**',
        'src/lib/utils.ts',
        'src/lib/utils/date.ts',
      ],
      thresholds: {
        lines: 70,
        functions: 70,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // `server-only` is provided by Next at build; stub it so server modules
      // (e.g. lib/api/server.ts) can be imported in tests.
      'server-only': path.resolve(__dirname, './src/__tests__/stubs/server-only.ts'),
    },
  },
})
