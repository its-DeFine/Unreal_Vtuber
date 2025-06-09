import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  outDir: 'dist',
  tsconfig: './tsconfig.build.json',
  sourcemap: true,
  clean: true,
  format: ['esm'],
  dts: false,
  external: [
    'dotenv',
    'fs',
    'path',
    'https',
    'http',
    'undici',
    '@elizaos/core',
  ],
});
