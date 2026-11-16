"use client";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight, CheckCheck, ChevronRight, CircleAlert, Clock, FileText, Hand, Link2, LoaderCircle, MapPin, Megaphone, MessageCircle,
  Package, PanelRight, Phone, Plus, Route, Search, Send, Shuffle, Sparkles, StickyNote, Truck, Undo2, User, X,
} from "lucide-react";
import { useSesion } from "../../Marco";
import { api, Av, AvKinti, ChipEtapa, ChipKinti, dia, ESTADOS, ETAPAS, hace, hora, MOTIVOS, pct, soles, useAviso, useIntervalo } from "../../lib";

const TABS_JEFE = [["todos", "Todos"], ["sin_asignar", "Sin asignar"], ["kinti", "Kinti · IA"]];
const TABS_VENTAS = [["todos", "Mis chats"], ["kinti", "Con Kinti · IA"]];
const PASO = { nuevo: 1, calificado: 2, cotizado: 3, ganado: 4, perdido: 0 };

function ItemLista({ c, sel, onClick }) {
  const u = c.ultimo;
  const quien = !u ? "" : u.autor === "kinti" ? "Kinti · IA" : u.autor === "vendedor" ? u.usuario || "Equipo" : c.nombre.split(" ")[0];
  return (
    <div className={`it ${sel ? "sel" : ""}`} onClick={onClick}>
      <span className="av av-cli">{c.iniciales}</span>
      <div className="cuerpo">
        <div className="l1"><b>{c.nombre}</b><small>· {c.distrito || "sin distrito"}</small><time className={c.no_leidos ? "nuevo" : ""}>{hace(c.actualizado)}</time></div>
        <div className="prev">
          <span className="txt">{u && <b className={u.autor === "kinti" ? "k" : ""}>{quien}: </b>}{u ? u.texto : "Sin mensajes"}</span>
          {c.no_leidos > 0 ? <span className="badge">{c.no_leidos}</span> : u && u.autor !== "cliente" && <CheckCheck className="i14" style={{ color: "#16B6D8" }} />}
        </div>
        <div className="l3">
          {c.kinti_activo && !["ganado", "perdido"].includes(c.etapa) ? <ChipKinti /> : c.vendedor
            ? <span style={{ display: "inline-flex", gap: 5, alignItems: "center", fontSize: 12, fontWeight: 600 }}><Av p={c.vendedor} tam="av-sm" />{c.vendedor.primer_nombre}</span>
            : <span className="chip chip-aviso">Sin asignar</span>}
          <ChipEtapa etapa={c.etapa} nombre={c.etapa_nombre} />
          {c.simulador && <span className="chip chip-borde" title="Llegó desde el simulador de WhatsApp">Simulador</span>}
          {c.whatsapp && <span className="chip chip-ganado" title="Chat real por WhatsApp (Evolution API)">WhatsApp</span>}
        </div>
      </div>
    </div>
  );
}

function Burbuja({ m, cliente }) {
  if (m.autor === "sistema") return <div className="msj-sistema"><ChipKinti />{m.texto.replace("Kinti · IA ", "")} · {hora(m.creado)}</div>;
  const tarjeta = m.producto && (
    <div className="tarjeta-prod">
      <img src={m.producto.foto} alt="" />
      <div style={{ flex: 1 }}><b>{m.producto.nombre}</b><small className="muted">{m.producto.detalle} · garantía {m.producto.garantia_meses} meses</small>
        <div className="precio">{soles(m.producto.precio)}</div></div>
    </div>
  );
  if (m.autor === "cliente") {
    return (
      <div className="fila-msj">
        <div className="burbuja cli">{m.texto}<div className="meta">{hora(m.creado)}</div></div>
      </div>
    );
  }
  const clase = { kinti: "ia", vendedor: "hum", nota: "nota" }[m.autor];
  const quien = m.autor === "kinti" ? "Kinti · IA" : m.autor === "nota" ? `Nota interna · ${m.usuario?.primer_nombre || ""}` : `${m.usuario?.primer_nombre || "Equipo"} · Ventas`;
  return (
    <div className="fila-msj der">
      <div className={`burbuja ${clase}`}>
        <div className="quien">{quien}</div>{m.texto}{tarjeta}
        <div className="meta">{hora(m.creado)}{m.segundos != null && <b>· respondió en {m.segundos} s</b>}{m.autor === "vendedor" && <CheckCheck className="i14" style={{ color: "#16B6D8" }} />}</div>
      </div>
      {m.autor === "kinti" ? <AvKinti tam="av-sm" /> : m.usuario ? <Av p={m.usuario} tam="av-sm" /> : null}
    </div>
  );
}

function Ficha({ f, yo, vendedores, onCambio, onCerrar, forzar }) {
  const [etiqueta, setEtiqueta] = useState("");
  const [motivo, setMotivo] = useState(null);
  if (!f) return <aside className={`col-ficha ${forzar ? "forzar" : ""}`}><div className="vacio"><LoaderCircle className="girar" /></div></aside>;
  const paso = PASO[f.etapa];
  const sig = { nuevo: "Calificado por IA", calificado: "Cotización", cotizado: "Venta cerrada" }[f.etapa];
  const prob = f.probabilidad || 0;
  const cambiarEtapa = (etapa) => (etapa === "perdido" ? setMotivo("") : onCambio({ etapa }));
  return (
    <aside className={`col-ficha ${forzar ? "forzar" : ""}`}>
      <div className="ficha-cab"><span className="lbl">Ficha del cliente</span><button className="icono-btn" style={{ width: 34, height: 34 }} onClick={onCerrar} title="Cerrar"><X className="i16" /></button></div>
      <div className="ficha-cli"><span className="av av-cli av-lg">{f.iniciales}</span>
        <div><h3>{f.nombre}</h3><div className="muted" style={{ fontSize: 13 }}>{f.distrito ? `${f.distrito}${f.provincia ? "" : ", Lima"}` : "Distrito por confirmar"} · {f.provincia ? "provincia" : "Lima"}</div></div></div>
      <div className="ficha-dato"><Phone className="i16" />{f.telefono || "—"}</div>
      <div className="ficha-dato"><Megaphone className="i16" /><span className="chip chip-osc">{f.origen_nombre} · {f.campana || "sin campaña"}</span></div>

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><span className="lbl">Etapa</span>
          <select className="sel-vendedor" value={f.etapa} onChange={(e) => cambiarEtapa(e.target.value)}>{ETAPAS.map((e) => <option key={e.k} value={e.k}>{e.n}</option>)}</select></div>
        {f.etapa === "perdido" ? <div className="chip chip-perdido" style={{ marginTop: 8 }}><i className="pt" />Perdido · {f.motivo_perdida}</div> : (
          <><div className="pasos" style={{ marginTop: 10 }}>{[1, 2, 3, 4].map((i) => <i key={i} className={i <= paso ? "on" : ""} />)}</div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginTop: 6 }}><span className="muted">Paso {paso} de 4</span>{sig && <span><span className="muted">Siguiente:</span> <b>{sig}</b></span>}</div></>
        )}
        {motivo !== null && (
          <div className="caja-gris" style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
            <b style={{ fontSize: 13 }}>¿Por qué se perdió?</b>
            <div className="etiquetas">{MOTIVOS.map((m) => <button key={m} className="btn btn-borde btn-xs" onClick={() => { onCambio({ etapa: "perdido", motivo: m }); setMotivo(null); }}>{m}</button>)}</div>
            <button className="btn btn-xs" style={{ alignSelf: "flex-start", background: "none" }} onClick={() => setMotivo(null)}>Cancelar</button>
          </div>
        )}
      </div>

      {["admin", "gerente"].includes(yo.rol) && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><span className="lbl">Vendedor</span>
          <select className="sel-vendedor" value={f.vendedor?.id || ""} onChange={(e) => onCambio({ vendedor_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">Sin asignar</option>{vendedores.map((v) => <option key={v.id} value={v.id}>{v.nombre}</option>)}
          </select></div>
      )}

      <div className="card-osc" style={{ padding: 14, borderRadius: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><ChipKinti texto="Kinti · IA" /><span className="lbl" style={{ color: "#9FB3CC" }}>Regresión logística</span></div>
        <div className="prob" style={{ marginTop: 8 }}><b>{pct(prob)}</b><span className="muted">probabilidad de compra</span></div>
        <div className="barra ia" style={{ background: "#1E2E4E", marginTop: 6 }}><i style={{ width: `${prob * 100}%`, background: prob >= 0.6 ? "#0EB155" : "#7C5CFC" }} /></div>
        <div style={{ fontSize: 13, marginTop: 8, color: "#C9D6E6" }}>{f.recomendacion}</div>
        <div style={{ borderTop: "1px solid #1E2E4E", marginTop: 10, paddingTop: 10, fontSize: 12.5 }}>
          <div className="muted">Conversación (grafo · BFS)</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
            <span className="chip chip-ia" style={{ height: 22 }}>{ESTADOS[f.conversacion.estado] || f.conversacion.estado}</span>
            {f.conversacion.siguiente && <><ArrowRight className="i14" style={{ color: "#9FB3CC" }} /><span>{f.conversacion.siguiente}</span></>}
          </div>
          {f.conversacion.faltan.length > 0 && <div className="muted" style={{ marginTop: 4 }}>Faltan {f.conversacion.faltan.length} pasos para «Listo para pagar»</div>}
        </div>
      </div>

      <div>
        <span className="lbl">Producto de interés</span>
        {f.producto ? (
          <div className="caja-gris" style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 8 }}>
            <img className="foto-prod" src={f.producto.foto} alt="" />
            <div style={{ flex: 1, minWidth: 0 }}><b style={{ fontSize: 14 }}>{f.producto.nombre}</b><div className="muted" style={{ fontSize: 12 }}>{f.cantidad} unid. · stock {f.producto.stock}</div></div>
            <b className="sora" style={{ fontSize: 17 }}>{soles(f.producto.precio)}</b>
          </div>
        ) : <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>Kinti aún no identificó el producto.</div>}
      </div>
      <div className="grid2">
        <div className="caja-gris"><div className="lbl" style={{ display: "flex", gap: 5, alignItems: "center" }}><Truck className="i12" />Entrega</div>
          <b style={{ fontSize: 14 }}>{f.delivery != null ? `${f.provincia ? "Agencia · 2-3 días" : `Delivery · ${f.ruta?.plazo || "24 h"}`}` : "Por cotizar"}</b></div>
        <div className="caja-gris"><div className="lbl">Total a pagar</div><b style={{ fontSize: 16 }}>{soles(f.monto)}</b></div>
      </div>
      {f.ruta && (
        <div>
          <span className="lbl" style={{ display: "flex", gap: 6, alignItems: "center" }}><Route className="i12" />Ruta de delivery · A*</span>
          <div className="ruta" style={{ marginTop: 6 }}>{f.ruta.camino.map((p) => <span key={p}>{p}</span>)}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{f.ruta.km} km desde el almacén de Mesa Redonda · {soles(f.ruta.costo)}</div>
        </div>
      )}
      <div>
        <span className="lbl">Etiquetas</span>
        <div className="etiquetas" style={{ marginTop: 8 }}>
          {f.etiquetas.map((t) => <span key={t}>{t}<button onClick={() => onCambio({ etiquetas: f.etiquetas.filter((x) => x !== t) })} title="Quitar"><X className="i12" /></button></span>)}
          <form onSubmit={(e) => { e.preventDefault(); if (etiqueta.trim()) { onCambio({ etiquetas: [...f.etiquetas, etiqueta.trim()] }); setEtiqueta(""); } }}>
            <input value={etiqueta} onChange={(e) => setEtiqueta(e.target.value)} placeholder="+ etiqueta" style={{ height: 28, width: 96, borderRadius: 999, border: "1px dashed #C8D8E8", padding: "0 10px", fontSize: 12.5 }} />
          </form>
        </div>
      </div>
      {f.notas.length > 0 && (
        <div><span className="lbl">Notas</span>
          {f.notas.map((n) => <div key={n.id} className="caja-gris" style={{ marginTop: 8, fontSize: 13 }}><StickyNote className="i14" style={{ color: "#B45309", verticalAlign: -2 }} /> {n.texto}<div className="muted" style={{ fontSize: 11.5, marginTop: 4 }}>{n.usuario?.primer_nombre} · {hora(n.creado)}</div></div>)}
        </div>
      )}
      <div><span className="lbl">Historial</span>
        <ul className="historial" style={{ marginTop: 6 }}>{f.eventos.map((e, i) => <li key={i}><i style={{ background: e.tipo === "etapa" || e.tipo === "pago" ? "#0EB155" : undefined }} />{e.texto}<time>{hace(e.creado)}</time></li>)}</ul>
      </div>
    </aside>
  );
}

function NuevoChat({ onCerrar, onCreado }) {
  const [d, setD] = useState({ nombre: "", texto: "Hola, vi su anuncio de la freidora de aire. ¿Cuánto está?", origen: "meta" });
  const [enviando, setEnviando] = useState(false);
  return (
    <div className="modal-fondo" onClick={onCerrar}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={async (e) => {
        e.preventDefault(); setEnviando(true);
        try { onCreado(await api("/crm/clientes/simular", { metodo: "POST", datos: d })); } finally { setEnviando(false); }
      }}>
        <h3>Simular un chat entrante</h3>
        <p className="muted" style={{ margin: 0, fontSize: 14 }}>Como si un cliente escribiera desde un anuncio. Kinti · IA le responde al instante.</p>
        <label className="campo"><span>Nombre del cliente</span><input className="input" value={d.nombre} onChange={(e) => setD({ ...d, nombre: e.target.value })} placeholder="Ej.: Valeria Ríos" /></label>
        <label className="campo"><span>Primer mensaje</span><textarea className="input" rows={3} value={d.texto} onChange={(e) => setD({ ...d, texto: e.target.value })} /></label>
        <label className="campo"><span>Llega desde</span>
          <select className="input" value={d.origen} onChange={(e) => setD({ ...d, origen: e.target.value })}><option value="meta">Meta Ads</option><option value="google">Google Ads</option><option value="organico">Orgánico</option><option value="directo">Directo</option></select></label>
        <div className="acciones"><button type="button" className="btn btn-borde" onClick={onCerrar}>Cancelar</button><button className="btn btn-verde" disabled={enviando}>{enviando ? <LoaderCircle className="girar" /> : <><Send />Enviar</>}</button></div>
      </form>
    </div>
  );
}

function Chats() {
  const { yo, refrescar } = useSesion();
  const params = useSearchParams();
  const router = useRouter();
  const jefe = ["admin", "gerente"].includes(yo.rol);
  const [filtro, setFiltro] = useState("todos");
  const [q, setQ] = useState(params.get("q") || "");
  const [buscar, setBuscar] = useState(!!params.get("q"));
  const [lista, setLista] = useState(null);
  const [conteos, setConteos] = useState({});
  const [sinResp, setSinResp] = useState(0);
  const [selId, setSelId] = useState(params.get("id") ? Number(params.get("id")) : null);
  const [msgs, setMsgs] = useState([]);
  const [ficha, setFicha] = useState(null);
  const [vendedores, setVendedores] = useState([]);
  const [productos, setProductos] = useState([]);
  const [texto, setTexto] = useState("");
  const [modo, setModo] = useState("responder");
  const [simular, setSimular] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [verFicha, setVerFicha] = useState(false);
  const [nuevo, setNuevo] = useState(false);
  const [menuProd, setMenuProd] = useState(false);
  const [aviso, mostrar] = useAviso();
  const fin = useRef(null);
  const ultimo = useRef(0);

  const cargarLista = useCallback(async () => {
    const r = await api(`/crm/clientes?filtro=${filtro}&q=${encodeURIComponent(q)}&limite=200`);
    setLista(r.clientes); setConteos(r.conteos); setSinResp(r.sin_responder);
    setSelId((s) => s ?? (r.clientes[0]?.id || null));
  }, [filtro, q]);
  useEffect(() => { cargarLista().catch(() => {}); }, [cargarLista]);
  useIntervalo(() => cargarLista().catch(() => {}), 4000, [cargarLista]);

  useEffect(() => {
    api("/crm/productos").then((r) => setProductos(r.productos.filter((p) => p.activo))).catch(() => {});
    if (jefe) api("/crm/vendedores").then((r) => setVendedores(r.vendedores)).catch(() => {});
  }, [jefe]);

  const cargarFicha = useCallback(() => selId && api(`/crm/clientes/${selId}`).then(setFicha).catch(() => {}), [selId]);
  const traerMensajes = useCallback(async (reset = false) => {
    if (!selId) return;
    const r = await api(`/crm/clientes/${selId}/mensajes?desde=${reset ? 0 : ultimo.current}&leido=1`);
    if (r.mensajes.length) {
      ultimo.current = r.mensajes[r.mensajes.length - 1].id;
      setMsgs((m) => (reset ? r.mensajes : [...m, ...r.mensajes]));
      if (!reset) cargarFicha();
      setTimeout(() => fin.current?.scrollIntoView({ behavior: reset ? "auto" : "smooth" }), 30);
    } else if (reset) setMsgs([]);
  }, [selId, cargarFicha]);
  useEffect(() => {
    ultimo.current = 0; setMsgs([]); setFicha(null);
    if (selId) { traerMensajes(true).then(() => refrescar()).catch(() => {}); cargarFicha(); }
  }, [selId, traerMensajes, cargarFicha, refrescar]);
  useIntervalo(() => traerMensajes().catch(() => {}), 2500, [traerMensajes]);

  const sel = useMemo(() => lista?.find((c) => c.id === selId) || ficha, [lista, selId, ficha]);
  const derivacion = useMemo(() => [...msgs].reverse().find((m) => m.autor === "sistema"), [msgs]);

  async function enviar(t = texto, extra = {}) {
    if (!t.trim() || !selId) return;
    setEnviando(true);
    try {
      await api(`/crm/clientes/${selId}/mensajes`, { metodo: "POST", datos: { texto: t, interno: modo === "nota", ...extra } });
      setTexto(""); await traerMensajes(); cargarFicha(); cargarLista();
    } catch (e) { mostrar(e.message, true); } finally { setEnviando(false); }
  }
  async function accion(a, datos = {}) {
    try {
      const r = await api(`/crm/clientes/${selId}/accion`, { metodo: "POST", datos: { accion: a, ...datos } });
      if (r.id) setFicha(r);
      await traerMensajes(); cargarLista();
      return r;
    } catch (e) { mostrar(e.message, true); }
  }
  async function cambiar(datos) {
    try { setFicha(await api(`/crm/clientes/${selId}`, { metodo: "PATCH", datos })); cargarLista(); }
    catch (e) { mostrar(e.message, true); }
  }
  async function repartir() {
    try {
      const r = await api("/crm/reasignar", { metodo: "POST", datos: {} });
      mostrar(r.asignados ? `Hill climbing repartió ${r.asignados} chats: el costo bajó de ${r.costo_inicial} a ${r.costo_final}.` : "No hay chats sin asignar.");
      cargarLista(); cargarFicha();
    } catch (e) { mostrar(e.message, true); }
  }

  const f = ficha;
  const primer = sel?.nombre?.split(" ")[0] || "";
  const rapidas = [
    ["Saludo", () => setTexto(`Hola ${primer}, soy ${yo.primer_nombre} de Kusi Hogar. ¿En qué te ayudo?`)],
    f?.producto && ["Precio", () => setTexto(`${f.producto.nombre} está a ${soles(f.producto.precio)} con ${f.producto.garantia_meses} meses de garantía.`)],
    f?.ruta && ["Delivery", () => setTexto(`El delivery a ${f.distrito} cuesta ${soles(f.ruta.costo)} y llega en ${f.ruta.plazo}.`)],
    ["Gracias", () => setTexto(`¡Gracias por tu compra, ${primer}! Cualquier consulta me escribes por aquí.`)],
  ].filter(Boolean);
  const cerrado = f && ["ganado", "perdido"].includes(f.etapa);
  const tabs = jefe ? TABS_JEFE : TABS_VENTAS;

  return (
    <main className={`main main-chats ${selId ? "con-chat" : ""}`}>
      {aviso}
      {nuevo && <NuevoChat onCerrar={() => setNuevo(false)} onCreado={(c) => { setNuevo(false); setFiltro("todos"); setSelId(c.id); cargarLista(); }} />}
      <section className="col-lista">
        <div className="lista-cab">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div><h1>{jefe ? "Chats" : "Mis chats"}</h1><div className="sub" style={{ fontSize: 13 }}><b>{conteos.todos ?? "…"}</b> en total · <b style={{ color: "#B45309" }}>{sinResp} sin responder</b></div></div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="icono-btn" title="Buscar" onClick={() => setBuscar(!buscar)}><Search className="i18" /></button>
              <button className="icono-btn" style={{ background: "#0EB155", borderColor: "#0EB155" }} title="Simular chat entrante" onClick={() => setNuevo(true)}><Plus className="i18" /></button>
            </div>
          </div>
          <div className="tabs">{tabs.map(([k, t]) => <button key={k} className={`tab ${filtro === k ? "on" : ""}`} onClick={() => setFiltro(k)}>{t}{conteos[k] != null && <span className="n">{conteos[k]}</span>}</button>)}</div>
          {buscar && <div className="buscar" style={{ width: "100%", height: 38 }}><Search className="i16" /><input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nombre, teléfono, distrito o producto" />{q && <X className="i16" style={{ cursor: "pointer" }} onClick={() => { setQ(""); router.replace("/crm/chats"); }} />}</div>}
          {jefe && conteos.sin_asignar > 0 && (
            <button className="btn btn-violeta btn-sm" onClick={repartir} title="Reparte los chats sin vendedor con Hill climbing (zona, especialidad y carga)"><Shuffle />Repartir {conteos.sin_asignar} sin asignar · Hill climbing</button>
          )}
        </div>
        <div className="lista">
          {!lista ? <div className="vacio"><LoaderCircle className="girar" /></div> : lista.length === 0 ? <div className="vacio"><img src="/crm-img/kinti-atendiendo.webp" alt="" />No hay chats con este filtro.</div>
            : lista.map((c) => <ItemLista key={c.id} c={c} sel={c.id === selId} onClick={() => { setSelId(c.id); setVerFicha(false); }} />)}
        </div>
      </section>

      <section className="col-chat">
        {!sel ? <div className="vacio" style={{ margin: "auto" }}><img src="/crm-img/kinti-saludando.webp" alt="" />Elige un chat de la lista.</div> : (
          <>
            <div className="chat-cab">
              <div className="f1">
                <span className="av av-cli av-lg">{sel.iniciales}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h2>{sel.nombre} <ChipEtapa etapa={sel.etapa} nombre={sel.etapa_nombre} /></h2>
                  <div className="meta"><Phone className="i14" />{sel.telefono} · vía {sel.origen_nombre}{sel.campana ? ` · ${sel.campana}` : ""}</div>
                </div>
                <button className="icono-btn" title="Ficha del cliente" onClick={() => setVerFicha(!verFicha)}><PanelRight className="i18" /></button>
              </div>
              <div className="f2">
                <span className="lbl">Asignado a</span>
                {sel.vendedor ? <span style={{ display: "inline-flex", gap: 6, alignItems: "center", fontWeight: 600, fontSize: 14 }}><Av p={sel.vendedor} tam="av-sm" />{sel.vendedor.nombre}</span> : <span className="chip chip-aviso">Sin asignar</span>}
                <span className="muted" style={{ fontSize: 12.5, display: "inline-flex", gap: 4, alignItems: "center" }}><Clock className="i14" />desde {hace(sel.creado)}</span>
                <span style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                  {!cerrado && (sel.kinti_activo
                    ? <button className="btn btn-verde btn-sm" onClick={() => accion("tomar")}><Hand />Tomar el chat</button>
                    : <button className="btn btn-violeta btn-sm" onClick={() => accion("devolver")}><Undo2 />Devolver a Kinti</button>)}
                </span>
              </div>
            </div>
            {derivacion && !cerrado && (
              <div className="banner-ia"><ChipKinti /><span>{derivacion.texto.replace("Kinti · IA ", "").replace(" · ", " · motivo: ")}</span>
                {sel.kinti_activo ? <em style={{ marginLeft: "auto" }}>Kinti sigue atendiendo</em> : <em style={{ marginLeft: "auto" }}>Kinti en pausa</em>}</div>
            )}
            <div className="mensajes">
              {msgs.map((m, i) => (
                <div key={m.id} style={{ display: "contents" }}>
                  {(i === 0 || new Date(m.creado).toDateString() !== new Date(msgs[i - 1].creado).toDateString()) && <div className="dia-sep">{dia(m.creado)}</div>}
                  <Burbuja m={m} cliente={sel} />
                </div>
              ))}
              <div ref={fin} />
            </div>
            <div className="compositor">
              <div className="simular" title="Solo para la demostración: escribe como si fueras el cliente">
                <User className="i16" /><span style={{ whiteSpace: "nowrap" }}>Demo · escribe como {primer}</span>
                <input value={simular} onChange={(e) => setSimular(e.target.value)} placeholder={sel.kinti_activo ? "Ej.: ¿Llega a Comas? Quiero pagar hoy" : "Mensaje del cliente (Kinti está en pausa)"}
                  onKeyDown={async (e) => { if (e.key === "Enter" && simular.trim()) { const t = simular; setSimular(""); await accion("simular", { texto: t }); } }} />
                <button className="btn btn-violeta btn-xs" style={{ background: "#7C5CFC", color: "#fff" }} disabled={!simular.trim()} onClick={async () => { const t = simular; setSimular(""); await accion("simular", { texto: t }); }}><Send />Enviar</button>
              </div>
              <div className="rapidas"><Sparkles className="i16" style={{ color: "#7C5CFC" }} />{rapidas.map(([t, fn]) => <button key={t} onClick={fn}>{t}</button>)}</div>
              <div className={`caja ${modo === "nota" ? "nota" : ""}`}>
                <div className="f" style={{ justifyContent: "space-between" }}>
                  <div className="seg" style={{ padding: 2 }}>
                    <button className={modo === "responder" ? "on" : ""} style={{ height: 28 }} onClick={() => setModo("responder")}>Responder</button>
                    <button className={modo === "nota" ? "on" : ""} style={{ height: 28 }} onClick={() => setModo("nota")}>Nota interna</button>
                  </div>
                  {sel.kinti_activo && modo === "responder" && <small className="muted">Al responder, tomas el chat y Kinti se pausa.</small>}
                </div>
                <textarea value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={modo === "nota" ? "Nota solo para el equipo…" : `Escribe un mensaje a ${primer}…`}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }} />
                <div className="f">
                  {modo === "responder" && (
                    <>
                      <div style={{ position: "relative" }}>
                        <button className="btn btn-borde btn-sm" onClick={() => setMenuProd(!menuProd)}><Package />Enviar producto</button>
                        {menuProd && (
                          <div className="card" style={{ position: "absolute", bottom: 40, left: 0, width: 300, padding: 8, zIndex: 20, maxHeight: 300, overflow: "auto", boxShadow: "0 10px 30px rgba(10,20,36,.18)" }}>
                            {productos.map((p) => (
                              <button key={p.id} className="prod-fila" style={{ width: "100%", border: 0, background: "none", textAlign: "left", padding: 6 }}
                                onClick={() => { setMenuProd(false); enviar(`Te comparto la ficha de ${p.nombre}: ${soles(p.precio)}.`, { producto_id: p.id }); }}>
                                <img src={p.foto} alt="" style={{ width: 36, height: 36 }} /><span style={{ flex: 1, fontSize: 13 }}>{p.nombre}</span><b style={{ fontSize: 13 }}>{soles(p.precio)}</b>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      {f?.producto && <button className="btn btn-borde btn-sm" onClick={() => enviar(`Te comparto la cotización: ${f.cantidad} × ${f.producto.nombre} (${soles(f.producto.precio)})${f.delivery != null ? ` + envío ${soles(f.delivery)}` : ""}. Total: ${soles(f.monto)}.`, { tipo: "cotizacion" })}><FileText />Enviar cotización</button>}
                      {f?.producto && <button className="btn btn-borde btn-sm" onClick={() => enviar(`Te envío el link de pago por ${soles(f.monto)} (pasarela de demostración). Puedes pagar con tarjeta, Yape o Plin.`, { tipo: "pago" })}><Link2 />Link de pago</button>}
                    </>
                  )}
                  <button className="enviar" disabled={!texto.trim() || enviando} onClick={() => enviar()} title="Enviar">{enviando ? <LoaderCircle className="i18 girar" /> : <Send className="i18" />}</button>
                </div>
              </div>
            </div>
          </>
        )}
      </section>
      {selId && <Ficha f={f} yo={yo} vendedores={vendedores} onCambio={cambiar} onCerrar={() => setVerFicha(false)} forzar={verFicha} />}
    </main>
  );
}

export default function PaginaChats() {
  return <Suspense fallback={<main className="main"><div className="cargando"><LoaderCircle className="girar" /></div></main>}><Chats /></Suspense>;
}
