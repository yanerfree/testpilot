import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/cli.ts', 'bin/testpilot.ts'],
  format: ['esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  target: 'node20',
});
