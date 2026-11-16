/** En producción Caddy envía /api/* a Django; en desarrollo se reescribe al back-end local. */
const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async redirects() {
    // El prototipo navegable se mudó de /crm a /prototipo: /crm ahora es el CRM funcional
    return [{ source: "/crm/vistas/:archivo*", destination: "/prototipo/vistas/:archivo*", permanent: false }];
  },
  async rewrites() {
    const prototipo = [{ source: "/prototipo", destination: "/prototipo/index.html" }];
    return process.env.NODE_ENV === "development"
      ? [...prototipo, { source: "/api/:ruta*", destination: `${BACKEND}/api/:ruta*` }]
      : prototipo;
  },
};

export default nextConfig;
