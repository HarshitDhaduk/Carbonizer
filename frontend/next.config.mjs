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

// Security response headers for the HTML origin.
//
// The API hardens itself (backend/app/core/security_headers.py), but this is
// the origin that renders the app and holds the session cookies, and it was
// shipping none of these. The CSP is deliberately limited to directives that
// don't constrain script/style loading: Next's runtime injects inline
// bootstrap scripts and styled-jsx tags, so a `script-src`/`style-src` policy
// needs nonce plumbing through middleware and belongs in its own change.
// `frame-ancestors` is what actually stops clickjacking, and it's safe here.
const CSP = [
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  // Redundant with frame-ancestors for modern browsers; kept for older ones.
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "geolocation=(), camera=(), microphone=(), payment=(), usb=()",
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // three.js ships untranspiled ESM examples; let Next transpile them.
  transpilePackages: ["three"],
  experimental: {
    optimizePackageImports: ["lucide-react", "@react-three/drei"],
  },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
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
