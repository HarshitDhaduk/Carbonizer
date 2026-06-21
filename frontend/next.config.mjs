import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  // Phase 4.4 — opt-in via `ANALYZE=true npm run build` so a developer can
  // diff the report after a dependency change. Off by default to keep CI
  // builds quick.
  enabled: process.env.ANALYZE === "true",
});

// Local-dev API proxy. Mirrors the production Vercel rewrite (vercel.json) so
// the browser can call same-origin `/api/v1/...` in both environments — first-
// party cookies survive third-party-cookie blockers (Safari ITP, Brave,
// Firefox-strict). In dev the target is the local backend on port 8000; in
// production Vercel's own rewrites take precedence and route to Render.
const LOCAL_API_TARGET =
  process.env.LOCAL_API_TARGET ?? "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // three.js ships untranspiled ESM examples; let Next transpile them.
  transpilePackages: ["three"],
  experimental: {
    optimizePackageImports: ["lucide-react", "@react-three/drei"],
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${LOCAL_API_TARGET}/api/v1/:path*`,
      },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);
