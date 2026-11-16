"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, CheckCheck, LoaderCircle, RotateCcw, Send } from "lucide-react";

const CLAVE = "sirac_wa";
const SUGERENCIAS = ["¿Cuánto está la freidora de aire?", "¿Llega a Comas?", "¿Dónde está su tienda?", "¿Aceptan Yape?", "Quiero pagar hoy", "¿Me atiende una persona?"];
const hora = (iso) => new Date(iso).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", hour12: false });

async function llamar(ruta, sesion, datos) {
  const r = await fetch(`/api/wa/${ruta}`, {
    method: datos ? "POST" : "GET", cache: "no-store",
    headers: { "Content-Type": "application/json", ...(sesion ? { "X-Sesion": sesion } : {}) },
    body: datos ? JSON.stringify(datos) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(j.error || `Error ${r.status}`); e.status = r.status; throw e; }
  return j;
}

export default function Simulador() {
  const [sesion, setSesion] = useState(null);
  const [nombre, setNombre] = useState("");
  const [msgs, setMsgs] = useState([]);
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(false);
  const [estado, setEstado] = useState({ kinti_activo: true, vendedor: null });
  const [error, setError] = useState("");
  const ultimo = useRef(0);
  const fin = useRef(null);

  useEffect(() => { setSesion(localStorage.getItem(CLAVE)); }, []);

  const traer = useCallback(async () => {
    if (!sesion) return;
    try {
      const r = await llamar(`mensajes?desde=${ultimo.current}`, sesion);
      setEstado({ kinti_activo: r.kinti_activo, vendedor: r.vendedor });
      if (r.mensajes.length) {
        ultimo.current = r.mensajes[r.mensajes.length - 1].id;
        setMsgs((m) => [...m, ...r.mensajes]);
        if (r.mensajes.some((m) => m.autor !== "cliente")) setEsperando(false);
        setTimeout(() => fin.current?.scrollIntoView({ behavior: "smooth" }), 30);
      }
    } catch (e) {
      if (e.status === 401) { localStorage.removeItem(CLAVE); setSesion(null); setMsgs([]); ultimo.current = 0; }
    }
  }, [sesion]);
  useEffect(() => { ultimo.current = 0; setMsgs([]); traer(); }, [traer]);
  useEffect(() => { const id = setInterval(() => { if (!document.hidden) traer(); }, 2000); return () => clearInterval(id); }, [traer]);

  async function empezar(e) {
    e.preventDefault(); setError("");
    try { const r = await llamar("iniciar", null, { nombre }); localStorage.setItem(CLAVE, r.sesion); setSesion(r.sesion); }
    catch (err) { setError(err.message); }
  }
  async function enviar(t = texto) {
    if (!t.trim()) return;
    setTexto(""); setEsperando(estado.kinti_activo); setError("");
    try { await llamar("mensajes", sesion, { texto: t }); await traer(); }
    catch (err) { setError(err.message); setEsperando(false); }
  }
  function reiniciar() { localStorage.removeItem(CLAVE); setSesion(null); setMsgs([]); ultimo.current = 0; setNombre(""); }

  return (
    <div className="wa">
      <section className="wa-info">
        <img className="logo" src="/marca/logo-sirac-blanco.svg" alt="SIRAC" />
        <h1>Escribe como cliente de Kusi Hogar</h1>
        <p>Es un simulador de WhatsApp conectado al CRM real de SIRAC. Lo que escribas llega al instante a la bandeja de chats, y Kinti · IA te responde.</p>
        <div className="wa-pasos">
          <div><b>1</b>Pregunta por un producto: freidora, licuadora, olla arrocera, aspiradora…</div>
          <div><b>2</b>Dile tu distrito: Kinti calcula el delivery con A* desde Mesa Redonda.</div>
          <div><b>3</b>Escribe «quiero pagar»: la IA te califica y te deriva a un vendedor.</div>
        </div>
        <p style={{ fontSize: 13 }}>Kusi Hogar S.A.C. es una empresa ficticia. No escribas datos personales reales. <a href="/crm">Entrar al CRM <ArrowRight className="i14" style={{ verticalAlign: -2 }} /></a></p>
      </section>
      <div className="telefono">
        <div className="pantalla">
          <div className="wa-cab">
            <img src="/crm-img/kinti.webp" alt="" />
            <div style={{ flex: 1 }}><b>Kusi Hogar</b><small>{estado.kinti_activo ? "Kinti · asistente virtual · en línea" : estado.vendedor ? `${estado.vendedor} · Ventas` : "en línea"}</small></div>
            {sesion && <button onClick={reiniciar} title="Empezar otra conversación" style={{ background: "none", border: 0, color: "#fff" }}><RotateCcw className="i18" /></button>}
          </div>
          {!sesion ? (
            <form className="wa-inicio" onSubmit={empezar}>
              <h2>Hola, ¿cómo te llamas?</h2>
              <p>Así te verá el equipo de Kusi Hogar en su CRM. Puedes usar un nombre inventado.</p>
              <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Tu nombre" maxLength={40} required minLength={2} />
              {error && <p style={{ color: "#C3122F" }}>{error}</p>}
              <button>Empezar a chatear</button>
            </form>
          ) : (
            <>
              <div className="wa-msjs">
                <div className="wa-aviso">Simulación con fines académicos · los mensajes llegan al CRM de SIRAC</div>
                {msgs.map((m) => (
                  <div key={m.id} className={`wa-b ${m.autor === "cliente" ? "yo" : "ellos"}`}>
                    {m.autor === "kinti" && <div className="de ia">Kinti · asistente virtual</div>}
                    {m.autor === "vendedor" && <div className="de">{m.usuario?.primer_nombre || "Kusi Hogar"} · Ventas</div>}
                    {m.texto}
                    {m.producto && (
                      <div className="prodc"><img src={m.producto.foto} alt="" /><div><b style={{ fontSize: 13 }}>{m.producto.nombre}</b><div style={{ fontWeight: 800 }}>S/ {m.producto.precio}</div></div></div>
                    )}
                    <div className="h">{hora(m.creado)} {m.autor === "cliente" && <CheckCheck className="i12" style={{ color: "#53BDEB", verticalAlign: -2 }} />}</div>
                  </div>
                ))}
                {esperando && <div className="escribiendo">Kinti está escribiendo…</div>}
                {error && <div className="wa-aviso" style={{ background: "#FDECEF", color: "#C3122F" }}>{error}</div>}
                <div ref={fin} />
              </div>
              <div className="wa-sug">{SUGERENCIAS.map((s) => <button key={s} onClick={() => enviar(s)}>{s}</button>)}</div>
              <form className="wa-pie" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
                <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Mensaje" maxLength={500} />
                <button title="Enviar">{esperando ? <LoaderCircle className="i18 girar" /> : <Send className="i18" />}</button>
              </form>
            </>
          )}
        </div>
      </div>
      <div className="wa-lado" />
    </div>
  );
}
