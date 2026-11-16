"use client";
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, TriangleAlert } from "lucide-react";

const CLAVE = "sirac_token";

export function token() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(CLAVE) || sessionStorage.getItem(CLAVE);
}
export function guardarToken(t, recordar) {
  localStorage.removeItem(CLAVE);
  sessionStorage.removeItem(CLAVE);
  (recordar ? localStorage : sessionStorage).setItem(CLAVE, t);
}
export function salir() {
  localStorage.removeItem(CLAVE);
  sessionStorage.removeItem(CLAVE);
  window.location.href = "/crm";
}

/** Llama a la API de Django (/api/...). Si la sesión venció, vuelve al acceso. */
export async function api(ruta, { metodo = "GET", datos, cabeceras = {} } = {}) {
  const h = { "Content-Type": "application/json", ...cabeceras };
  const t = token();
  if (t && !h["X-Sesion"]) h.Authorization = `Bearer ${t}`;
  const r = await fetch(`/api${ruta}`, { method: metodo, headers: h, body: datos ? JSON.stringify(datos) : undefined, cache: "no-store" });
  let j = null;
  try { j = await r.json(); } catch { /* sin cuerpo */ }
  if (r.status === 401 && ruta.startsWith("/crm/") && ruta !== "/crm/login") { salir(); throw new Error("sesion"); }
  if (!r.ok) throw new Error(j?.error || `Error ${r.status}`);
  return j;
}

export const soles = (v, dec = 0) => "S/ " + Number(v || 0).toLocaleString("es-PE", { minimumFractionDigits: dec, maximumFractionDigits: dec });
export const pct = (v, d = 0) => `${(Number(v || 0) * 100).toFixed(d)} %`;
const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];

export function hora(iso) {
  return new Date(iso).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", hour12: false });
}
export function hace(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "ahora";
  if (s < 3600) return `${Math.floor(s / 60)} min`;
  const d = new Date(iso), hoy = new Date();
  if (d.toDateString() === hoy.toDateString()) return hora(iso);
  const ayer = new Date(); ayer.setDate(hoy.getDate() - 1);
  if (d.toDateString() === ayer.toDateString()) return "ayer";
  const dias = Math.floor(s / 86400);
  return dias < 7 ? `${dias} días` : `${d.getDate()} ${MESES[d.getMonth()]}`;
}
export function dia(iso) {
  const d = new Date(iso), hoy = new Date();
  const ayer = new Date(); ayer.setDate(hoy.getDate() - 1);
  const base = `${DIAS[d.getDay()]} ${d.getDate()} ${MESES[d.getMonth()]}`;
  if (d.toDateString() === hoy.toDateString()) return `Hoy · ${base}`;
  if (d.toDateString() === ayer.toDateString()) return `Ayer · ${base}`;
  return base;
}

export const ETAPAS = [
  { k: "nuevo", n: "Nuevo" }, { k: "calificado", n: "Calificado por IA" }, { k: "cotizado", n: "Cotización enviada" },
  { k: "ganado", n: "Venta cerrada" }, { k: "perdido", n: "Perdido" },
];
export const ESTADOS = {
  inicio: "Inicio", saludo: "Saludo", consulta_general: "Consulta general", catalogo_enviado: "Catálogo enviado",
  producto_identificado: "Producto identificado", stock_verificado: "Stock verificado", precio_informado: "Precio informado",
  objecion_precio: "Objeción de precio", delivery_cotizado: "Delivery cotizado", datos_cliente: "Datos del cliente",
  listo_para_pagar: "Listo para pagar", perdido: "Perdido",
};
export const MOTIVOS = ["Precio", "Sin stock", "Sin respuesta", "Compró en otro lado"];

export function Av({ p, tam = "", cli = false }) {
  if (!p) return null;
  return <span className={`av ${tam} ${cli ? "av-cli" : ""}`} style={cli ? undefined : { background: p.color }}>{p.iniciales}</span>;
}
export function AvKinti({ tam = "" }) {
  return <span className={`av av-ia ${tam}`}><img src="/crm-img/kinti.webp" alt="Kinti" /></span>;
}
export function ChipKinti({ texto = "Kinti · IA" }) {
  return <span className="chip-kinti"><img src="/crm-img/kinti.webp" alt="" />{texto}</span>;
}
export function ChipEtapa({ etapa, nombre }) {
  const n = nombre || ETAPAS.find((e) => e.k === etapa)?.n || etapa;
  return <span className={`chip chip-${etapa}`}><i className="pt" />{n}</span>;
}

/** Aviso flotante que se cierra solo. */
export function useAviso() {
  const [aviso, setAviso] = useState(null);
  const t = useRef(null);
  const mostrar = (texto, error = false) => {
    setAviso({ texto, error });
    clearTimeout(t.current);
    t.current = setTimeout(() => setAviso(null), error ? 6000 : 4200);
  };
  const nodo = aviso ? (
    <div className={`aviso-toast ${aviso.error ? "error" : ""}`} role="status">
      {aviso.error ? <TriangleAlert className="i18" style={{ color: "#fff" }} /> : <CheckCircle2 className="i18" />}
      <span>{aviso.texto}</span>
    </div>
  ) : null;
  return [nodo, mostrar];
}

/** Ejecuta `fn` cada `ms` milisegundos mientras la pestaña está visible. */
export function useIntervalo(fn, ms, deps = []) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    const id = setInterval(() => { if (!document.hidden) ref.current(); }, ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}
