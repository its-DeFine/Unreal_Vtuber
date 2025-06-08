import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  outDir: 'dist',
  tsconfig: './tsconfig.build.json',
  sourcemap: true,
  clean: true,
  format: ['esm', 'cjs'],
  dts: true,
  splitting: false,
  external: [
    '@elizaos/core',
    '@elizaos/plugin-openai',
    '@elizaos/plugin-bootstrap',
    'dotenv',
    'fs',
    'path',
    'https',
    'http',
    'zod',
    'uuid',
    'events',
    'util',
    'crypto',
    'url',
    'querystring'
  ],
  esbuildOptions(options) {
    options.conditions = ['node'];
  },
});
