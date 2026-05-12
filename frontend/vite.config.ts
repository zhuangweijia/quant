import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return {
    plugins: [
      vue(),
      AutoImport({
        imports: ["vue", "vue-router", "pinia"],
        resolvers: [ElementPlusResolver()],
        dts: "src/auto-imports.d.ts",
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: "src/components.d.ts",
      }),
    ],
    resolve: {
      alias: {
        "@": resolve(__dirname, "src"),
      },
    },
    server: {
      port: 3000,
      proxy: {
        "/api": {
          target: env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
        "/ws": {
          target: env.VITE_WS_URL || "ws://localhost:8000",
          ws: true,
        },
      },
    },
    build: {
      target: "es2020",
      outDir: "dist",
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: (id: string) => {
            if (id.includes("node_modules/vue/") || id.includes("node_modules/vue-router/") || id.includes("node_modules/pinia/")) return "vue";
            if (id.includes("node_modules/element-plus/")) return "elementPlus";
            if (id.includes("node_modules/echarts/") || id.includes("node_modules/vue-echarts/")) return "echarts";
          },
        },
      },
    },
  };
});
