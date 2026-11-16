"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronsLeft, Funnel, LayoutDashboard, LoaderCircle, LogOut, MessageCircle, Package, Search, Settings, Sparkles } from "lucide-react";
import { api, salir, token, useIntervalo } from "./lib";

const Sesion = createContext(null);
export const useSesion = () => useContext(Sesion);

const MENUS = {
  admin: [["dashboard", "Dashboard", LayoutDashboard], ["chats", "Chats", MessageCircle, true], ["embudo", "Embudo", Funnel],
    ["entrenamiento", "Entrenamiento", Sparkles], ["catalogo", "Catálogo", Package], ["configuracion", "Configuración", Settings]],
  gerente: [["dashboard", "Dashboard", LayoutDashboard], ["chats", "Chats", MessageCircle, true], ["embudo", "Embudo", Funnel],
    ["entrenamiento", "Entrenamiento", Sparkles], ["catalogo", "Catálogo", Package]],
  ventas: [["dashboard", "Mi dashboard", LayoutDashboard], ["chats", "Mis chats", MessageCircle, true], ["embudo", "Mi embudo", Funnel],
    ["catalogo", "Catálogo", Package]],
};

export default function Marco({ children }) {
  const router = useRouter();
  const ruta = usePathname();
  const [yo, setYo] = useState(null);
  const [sinLeer, setSinLeer] = useState(0);
  const [mini, setMini] = useState(false);

  const cargar = useCallback(() => api("/crm/yo").then((r) => { setYo(r.usuario); setSinLeer(r.sin_leer); }).catch(() => {}), []);
  useEffect(() => {
    if (!token()) { router.replace("/crm"); return; }
    cargar();
    setMini(localStorage.getItem("sirac_mini") === "1");
  }, [cargar, router]);
  useIntervalo(cargar, 15000);

  if (!yo) return <div className="cargando"><LoaderCircle className="girar" /><span>Abriendo tu panel…</span></div>;
  const activo = ruta.split("/")[2] || "dashboard";
  const permitido = MENUS[yo.rol].some(([k]) => k === activo);

  return (
    <Sesion.Provider value={{ yo, sinLeer, refrescar: cargar }}>
      <div className={`app ${mini ? "mini" : ""}`}>
        <aside className="sb">
          <div className="sb-logo">
            <img src="/marca/logo-sirac-blanco.svg" alt="SIRAC" />
            <button className="sb-colapsar" title="Contraer menú" onClick={() => { localStorage.setItem("sirac_mini", mini ? "0" : "1"); setMini(!mini); }}>
              <ChevronsLeft className="i16" />
            </button>
          </div>
          <nav className="sb-nav">
            {MENUS[yo.rol].map(([k, t, Icono, cuenta]) => (
              <Link key={k} href={`/crm/${k}`} className={`sb-item ${k === activo ? "activo" : ""}`} title={t}>
                <Icono /><span>{t}</span>{cuenta && sinLeer > 0 && <span className="cnt">{sinLeer}</span>}
              </Link>
            ))}
          </nav>
          <div className="sb-demo"><i />Datos de demostración · Kusi Hogar es ficticia</div>
          <div className="sb-patron" />
          <div className="sb-user">
            <span className="av" style={{ background: yo.color }}>{yo.iniciales}</span>
            <div><div className="n">{yo.nombre}</div><div className="r">{yo.cargo}</div></div>
            <span className="on" />
            <button title="Cerrar sesión" onClick={salir}><LogOut className="i18" /></button>
          </div>
        </aside>
        {permitido ? children : (
          <main className="main"><div className="vacio"><img src="/crm-img/respaldo.webp" alt="" />Tu rol no tiene acceso a esta sección.</div></main>
        )}
      </div>
    </Sesion.Provider>
  );
}

/** Cabecera estándar de cada vista: sobretítulo, título, subtítulo, acciones, buscador y campana. */
export function Top({ sobre, titulo, sub, children }) {
  const router = useRouter();
  const { sinLeer } = useSesion();
  const [q, setQ] = useState("");
  return (
    <div className="top">
      <div>
        {sobre && <div className="sobre">{sobre}</div>}
        <div className="titulo">{titulo}</div>
        {sub && <div className="sub">{sub}</div>}
      </div>
      <div className="top-acciones">
        {children}
        <form className="buscar" onSubmit={(e) => { e.preventDefault(); router.push(`/crm/chats?q=${encodeURIComponent(q)}`); }}>
          <Search className="i18" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar cliente, chat o producto…" />
        </form>
        <Link href="/crm/chats" className="icono-btn" title="Chats sin leer"><Bell className="i18" />{sinLeer > 0 && <span className="dot">{sinLeer > 99 ? "99+" : sinLeer}</span>}</Link>
      </div>
    </div>
  );
}
