/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          '"Noto Sans"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          '"WenQuanYi Micro Hei"',
          "sans-serif",
        ],
        // 金融数字等宽字体：系统等宽栈 + JetBrains Mono（若本地安装）
        mono: [
          "JetBrains Mono",
          '"SF Mono"',
          '"Cascadia Code"',
          '"IBM Plex Mono"',
          "Consolas",
          '"Courier New"',
          "monospace",
        ],
        display: ["Orbitron", "sans-serif"],
      },
      // === 设计 token：严格执行 UI_DESIGN_GUIDE.md ===
      fontSize: {
        // 三档封顶：24 大数字 / 15 正文 / 12 标签（禁止 10/11px）
        "data-xl": ["24px", { lineHeight: "1.2", fontWeight: "600" }],
        body: ["15px", { lineHeight: "1.65" }],
        label: ["12px", { lineHeight: "1.5", fontWeight: "500" }],
        caption: ["12px", { lineHeight: "1.45" }],
      },
      colors: {
        // 涨跌色：仅用于涨跌
        up: "#DC2626", // red-600
        down: "#059669", // emerald-600
        accent: "#4F46E5", // indigo-600
      },
      borderRadius: {
        card: "8px", // rounded-lg
        btn: "6px", // rounded-md
      },
      boxShadow: {
        // 唯一允许的阴影：极浅，营造纸张感
        soft: "0 1px 2px 0 rgb(15 23 42 / 0.05)",
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            color: "#374151",
            p: {
              marginTop: "1.2em",
              marginBottom: "1.2em",
              lineHeight: "1.75",
              letterSpacing: "0.01em",
            },
            h1: {
              color: "#111827",
              fontWeight: "600",
              marginTop: "0",
              marginBottom: "0.8em",
              lineHeight: "1.2",
            },
            h2: {
              color: "#1f2937",
              fontWeight: "600",
              marginTop: "2em",
              marginBottom: "1em",
              lineHeight: "1.3",
            },
            h3: {
              color: "#1f2937",
              fontWeight: "600",
              marginTop: "1.5em",
              marginBottom: "0.6em",
            },
            li: {
              marginTop: "0.5em",
              marginBottom: "0.5em",
            },
            // 表格：斑马纹 + 分割线（反模式清单要求）
            table: {
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.875rem",
            },
            th: {
              backgroundColor: "#f9fafb",
              fontWeight: "600",
              border: "1px solid #e2e8f0",
              padding: "0.5rem 0.75rem",
              textAlign: "left",
            },
            td: {
              border: "1px solid #e2e8f0",
              padding: "0.5rem 0.75rem",
            },
            "tbody tr:nth-child(even)": {
              backgroundColor: "#f8fafc",
            },
            blockquote: {
              borderLeftColor: "#4F46E5",
              backgroundColor: "#eef2ff",
              padding: "0.75rem 1rem",
              borderRadius: "4px",
              color: "#475569",
            },
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
