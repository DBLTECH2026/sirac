/** En producción Caddy envía /api/* a Django; en desarrollo se reescribe al back-end local. */
const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    // /crm muestra el índice del prototipo navegable del CRM (archivos estáticos en public/crm)
    const crm = [{ source: "/crm", destination: "/crm/index.html" }];
    return process.env.NODE_ENV === "development"
      ? [...crm, { source: "/api/:ruta*", destination: `${BACKEND}/api/:ruta*` }]
      : crm;
  },
};

export default nextConfig;
