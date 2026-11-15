import Image from "next/image";
import { Asignacion, Calificar, Conversacion, Estado, Metricas, Proyeccion, Ruta } from "./Demos";

export default function Inicio() {
  return (
    <main>
      <header className="hero">
        <div className="contenedor hero-grid">
          <div>
            <Image src="/marca/logo-sirac-blanco.svg" alt="SIRAC" width={190} height={50} priority />
            <p className="etiqueta-hero">Avance 3 · Infraestructura e inteligencia artificial</p>
            <h1>Atiende al instante y aprende de cada venta</h1>
            <p className="lead">
              SIRAC atiende por WhatsApp con su asistente Kinti, deriva a los vendedores los clientes listos para comprar y
              le devuelve a Meta y a Google las ventas reales. Aquí puedes probar en vivo los algoritmos de búsqueda y los
              primeros modelos de machine learning que corren en nuestro servidor.
            </p>
            <Estado />
          </div>
          <div className="hero-ilustracion">
            <Image src="/ilustraciones/agente-saludando.webp" alt="Kinti, el asistente de SIRAC" width={420} height={360} priority />
          </div>
        </div>
      </header>

      <section className="contenedor seccion">
        <p className="kicker">Fase 3.3 · Machine learning</p>
        <h2>Primeros modelos</h2>
        <div className="grid-2">
          <Calificar />
          <Proyeccion />
        </div>
        <Metricas />
      </section>

      <section className="contenedor seccion">
        <p className="kicker">Fase 3.2 · Espacios de búsqueda</p>
        <h2>Algoritmos de búsqueda</h2>
        <div className="grid-2">
          <Ruta />
          <Conversacion />
        </div>
        <Asignacion />
      </section>

      <footer className="pie">
        <div className="contenedor">
          <p>
            Proyecto académico · Innovación y Transformación Digital · Universidad Tecnológica del Perú, 2026.
            Los datos de Kusi Hogar S.A.C. son <strong>simulados</strong> (caso hipotético).
          </p>
          <p>Django + Next.js en un VPS Hostinger KVM 2 · Despliegue continuo con GitHub Actions · HTTPS con Let&apos;s Encrypt.</p>
        </div>
      </footer>
    </main>
  );
}
