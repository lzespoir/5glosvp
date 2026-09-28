import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import type { UserConfig } from 'vite';
import type { InlineConfig } from 'vitest/node';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // 开发服务器把 /api 代理到 FastAPI，前端默认使用相对路径 /api/v1
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';

  const config: UserConfig & { test: InlineConfig } = {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: { '/api': { target: proxyTarget, changeOrigin: true } },
    },
    preview: {
      host: '127.0.0.1',
      port: 4173,
      proxy: { '/api': { target: proxyTarget, changeOrigin: true } },
    },
    build: {
      // antd 单库压缩后约 1.2 MB，无法再拆分
      chunkSizeWarningLimit: 1300,
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: 'echarts', test: /node_modules[\\/](echarts|zrender)[\\/]/ },
              { name: 'antd', test: /node_modules[\\/](antd|@ant-design|@rc-component|rc-[^\\/]+)[\\/]/ },
              { name: 'vendor', test: /node_modules[\\/]/ },
            ],
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  };
  return config;
});
