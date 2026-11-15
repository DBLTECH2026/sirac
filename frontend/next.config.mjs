/** En producción Caddy envía /api/* a Django; en desarrollo se reescribe al back-end local. */
const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return process.env.NODE_ENV === "development" ? [{ source: "/api/:ruta*", destination: `${BACKEND}/api/:ruta*` }] : [];
  },
};

export default nextConfig;
