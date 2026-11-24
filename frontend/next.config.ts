import { dirname } from "path";
import { fileURLToPath } from "url";
import type { NextConfig } from "next";

// фронтенд проксирует /api/v1 на бэкенд чтобы cookie жили в одном origin
const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const isDev = process.env.NODE_ENV === "development";

// умеренная csp: инлайн-стили нужны react, eval только для дев-режима next
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' https: data:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "object-src 'none'",
].join("; ");

const nextConfig: NextConfig = {
  // встречные чужие lockfile выше по дереву не должны сбивать определение корня
  outputFileTracingRoot: dirname(fileURLToPath(import.meta.url)),

  poweredByHeader: false,

  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
      {
        // административная панель живёт на бэкенде
        source: "/admin/:path*",
        destination: `${backendOrigin}/admin/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Content-Security-Policy", value: csp },
        ],
      },
    ];
  },
};

export default nextConfig;
