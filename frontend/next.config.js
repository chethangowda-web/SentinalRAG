/** @type {import('next').NextConfig} */

// STATIC_EXPORT=1 builds plain HTML/JS/CSS (no Node server) that the backend serves itself,
// which lets the whole app run as one service. Rewrites and the body-size limit only exist
// for the standalone server, so they are left out of the export.
const staticExport = process.env.STATIC_EXPORT === "1";

const common = {
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
};

const nextConfig = staticExport
  ? {
      ...common,
      output: "export",
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {
      ...common,
      output: "standalone",
      middlewareClientMaxBodySize: "100MB",

      async rewrites() {
        return [
          {
            source: "/api/:path*",
            destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
          },
        ];
      },
    };

module.exports = nextConfig;
