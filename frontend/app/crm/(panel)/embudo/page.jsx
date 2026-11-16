"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, Kanban, List, LoaderCircle, MapPin, Plus, Shuffle, Sparkles, TrendingUp, TriangleAlert, Truck } from "lucide-react";
import { Top, useSesion } from "../../Marco";
import { api, Av, ChipEtapa, ChipKinti, ETAPAS, hace, MOTIVOS, pct, soles, useAviso, useIntervalo } from "../../lib";

const COLS = ["nuevo", "calificado", "cotizado", "ganado"];
const PUNTO = { nuevo: "#9FB3CC", calificado: "#7C5CFC", cotizado: "#16B6D8", ganado: "#0EB155", perdido: "#C3122F" };
const DIA = 86400000;

function Tarjeta({ c, onAbrir, onArrastre }) {
  const estancada = c.etapa === "cotizado" && Date.now() - new Date(c.actualizado).getTime() > 2 * DIA;
  return (
    <div className="op" draggable onDragStart={(e) => { e.dataTransfer.setData("text/plain", String(c.id)); onArrastre(c.id); }} onDragEnd={() => onArrastre(null)} onClick={() => onAbrir(c.id)}>
      <div className="f1"><b>{c.nombre}</b><span className="m tnum">{soles(c.monto)}</span></div>
      <div className="f2"><span><MapPin className="i12" />{c.distrito || "—"}{c.provincia ? " · provincia" : ""}</span><span><Clock className="i12" />{hace(c.actualizado)}</span></div>
      {c.producto && (
        <div className="prod"><img src={c.producto.foto} alt="" /><div><b>{c.producto.nombre}{c.cantidad > 1 ? ` ×${c.cantidad}` : ""}</b>
          <small>{c.cantidad} unid. · {c.delivery != null ? (c.provincia ? "envío por agencia" : "delivery") : "entrega por definir"}</small></div></div>
      )}
      {estancada && <div className="alerta"><TriangleAlert className="i14" />{Math.floor((Date.now() - new Date(c.actualizado).getTime()) / DIA)} días sin respuesta</div>}
      {c.etapa === "ganado" && <div className="ok"><Sparkles className="i14" />Venta lista para enviarse a Meta y Google</div>}
      <div className="f4">
        {c.kinti_activo && c.etapa !== "ganado" ? <ChipKinti /> : c.vendedor
          ? <span style={{ display: "inline-flex", gap: 6, alignItems: "center", fontSize: 13, fontWeight: 600 }}><Av p={c.vendedor} tam="av-sm" />{c.vendedor.primer_nombre}</span>
          : <span className="muted" style={{ fontSize: 12.5 }}>Sin asignar</span>}
        {c.probabilidad != null && <span className="prob-mini" title="Probabilidad de compra (regresión logística)">{pct(c.probabilidad)}</span>}
        <span className="chip chip-borde" style={{ height: 22, fontSize: 11 }}>{c.origen_nombre.replace(" Ads", "")}</span>
      </div>
    </div>
  );
}

function NuevaOportunidad({ productos, vendedores, jefe, onCerrar, onCreada }) {
  const [d, setD] = useState({ nombre: "", telefono: "", distrito: "", producto_id: productos[0]?.id || "", cantidad: 1, origen: "directo", vendedor_id: "" });
  const [error, setError] = useState("");
  const [distritos, setDistritos] = useState([]);
  useEffect(() => { api("/busqueda/distritos").then((r) => setDistritos(r.distritos)).catch(() => {}); }, []);
  const set = (k) => (e) => setD({ ...d, [k]: e.target.value });
  return (
    <div className="modal-fondo" onClick={onCerrar}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={async (e) => {
        e.preventDefault(); setError("");
        try { onCreada(await api("/crm/clientes", { metodo: "POST", datos: { ...d, producto_id: Number(d.producto_id) || null, vendedor_id: Number(d.vendedor_id) || null } })); }
        catch (err) { setError(err.message); }
      }}>
        <h3>Nueva oportunidad</h3>
        <div className="grid2">
          <label className="campo"><span>Cliente</span><input className="input" required value={d.nombre} onChange={set("nombre")} placeholder="Nombre y apellido" /></label>
          <label className="campo"><span>Teléfono</span><input className="input" value={d.telefono} onChange={set("telefono")} placeholder="+51 9…" /></label>
        </div>
        <label className="campo"><span>Producto</span><select className="input" value={d.producto_id} onChange={set("producto_id")}>{productos.map((p) => <option key={p.id} value={p.id}>{p.nombre} · {soles(p.precio)}</option>)}</select></label>
        <div className="grid2">
          <label className="campo"><span>Cantidad</span><input className="input" type="number" min="1" max="50" value={d.cantidad} onChange={set("cantidad")} /></label>
          <label className="campo"><span>Distrito o ciudad</span><input className="input" list="distritos" value={d.distrito} onChange={set("distrito")} placeholder="Ej.: Comas o Arequipa" />
            <datalist id="distritos">{distritos.map((x) => <option key={x} value={x} />)}</datalist></label>
        </div>
        <div className="grid2">
          <label className="campo"><span>Origen</span><select className="input" value={d.origen} onChange={set("origen")}><option value="directo">Directo</option><option value="meta">Meta Ads</option><option value="google">Google Ads</option><option value="organico">Orgánico</option></select></label>
          {jefe && <label className="campo"><span>Vendedor</span><select className="input" value={d.vendedor_id} onChange={set("vendedor_id")}><option value="">Sin asignar</option>{vendedores.map((v) => <option key={v.id} value={v.id}>{v.nombre}</option>)}</select></label>}
        </div>
        <p className="muted" style={{ margin: 0, fontSize: 12.5, display: "flex", gap: 6 }}><Truck className="i16" />Si es un distrito de Lima, el delivery se calcula con A* desde Mesa Redonda.</p>
        {error && <div className="chip chip-perdido">{error}</div>}
        <div className="acciones"><button type="button" className="btn btn-borde" onClick={onCerrar}>Cancelar</button><button className="btn btn-verde"><Plus />Crear</button></div>
      </form>
    </div>
  );
}

export default function Embudo() {
  const { yo } = useSesion();
  const router = useRouter();
  const jefe = ["admin", "gerente"].includes(yo.rol);
  const [lista, setLista] = useState(null);
  const [vista, setVista] = useState("kanban");
  const [vendedor, setVendedor] = useState("");
  const [origen, setOrigen] = useState("");
  const [vendedores, setVendedores] = useState([]);
  const [productos, setProductos] = useState([]);
  const [arrastrando, setArrastrando] = useState(null);
  const [sobre, setSobre] = useState(null);
  const [perdida, setPerdida] = useState(null);
  const [nueva, setNueva] = useState(false);
  const [aviso, mostrar] = useAviso();

  const cargar = useCallback(() => api(`/crm/clientes?vista=embudo&limite=400${vendedor ? `&vendedor=${vendedor}` : ""}`).then((r) => setLista(r.clientes)).catch(() => {}), [vendedor]);
  useEffect(() => { cargar(); }, [cargar]);
  useIntervalo(cargar, 8000, [cargar]);
  useEffect(() => {
    api("/crm/productos").then((r) => setProductos(r.productos.filter((p) => p.activo))).catch(() => {});
    if (jefe) api("/crm/vendedores").then((r) => setVendedores(r.vendedores)).catch(() => {});
  }, [jefe]);

  const filtrada = useMemo(() => (lista || []).filter((c) => !origen || c.origen === origen), [lista, origen]);
  const por = (k) => filtrada.filter((c) => c.etapa === k);
  const abiertas = filtrada.filter((c) => ["nuevo", "calificado", "cotizado"].includes(c.etapa));
  const enJuego = abiertas.reduce((a, c) => a + c.monto, 0);
  const ganados = por("ganado"), perdidos = por("perdido");
  const conversion = ganados.length + perdidos.length ? ganados.length / (ganados.length + perdidos.length) : 0;
  const estancadas = por("cotizado").filter((c) => Date.now() - new Date(c.actualizado).getTime() > 2 * DIA).length;

  async function mover(id, etapa, motivo) {
    const c = lista.find((x) => x.id === id);
    if (!c || c.etapa === etapa) return;
    if (etapa === "perdido" && !motivo) { setPerdida(id); return; }
    setLista((l) => l.map((x) => (x.id === id ? { ...x, etapa, actualizado: new Date().toISOString() } : x)));
    try {
      await api(`/crm/clientes/${id}`, { metodo: "PATCH", datos: { etapa, motivo } });
      mostrar(`${c.nombre} pasó a «${ETAPAS.find((e) => e.k === etapa).n}».`);
    } catch (e) { mostrar(e.message, true); }
    cargar();
  }
  const soltar = (etapa) => (e) => { e.preventDefault(); setSobre(null); const id = Number(e.dataTransfer.getData("text/plain")); if (id) mover(id, etapa); };
  const encima = (etapa) => (e) => { e.preventDefault(); setSobre(etapa); };

  async function repartir() {
    try {
      const r = await api("/crm/reasignar", { metodo: "POST", datos: {} });
      mostrar(r.asignados ? `Hill climbing repartió ${r.asignados} oportunidades (costo ${r.costo_inicial} → ${r.costo_final}).` : "No hay oportunidades sin asignar.");
      cargar();
    } catch (e) { mostrar(e.message, true); }
  }
  const sinAsignar = abiertas.filter((c) => !c.vendedor).length;

  return (
    <main className="main">
      {aviso}
      {nueva && <NuevaOportunidad productos={productos} vendedores={vendedores} jefe={jefe} onCerrar={() => setNueva(false)} onCreada={(c) => { setNueva(false); mostrar(`Oportunidad creada para ${c.nombre}.`); cargar(); }} />}
      {perdida && (
        <div className="modal-fondo" onClick={() => setPerdida(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>¿Por qué se perdió?</h3>
            <div className="etiquetas">{MOTIVOS.map((m) => <button key={m} className="btn btn-borde btn-sm" onClick={() => { const id = perdida; setPerdida(null); mover(id, "perdido", m); }}>{m}</button>)}</div>
            <div className="acciones"><button className="btn btn-borde" onClick={() => setPerdida(null)}>Cancelar</button></div>
          </div>
        </div>
      )}
      <Top sobre="Ventas en curso" titulo={jefe ? "Embudo" : "Mi embudo"} sub={<><b>{soles(enJuego)}</b> en juego · <b>{abiertas.length}</b> oportunidades abiertas</>}>
        <div className="seg"><button className={vista === "kanban" ? "on" : ""} onClick={() => setVista("kanban")}><Kanban className="i16" />Kanban</button><button className={vista === "lista" ? "on" : ""} onClick={() => setVista("lista")}><List className="i16" />Lista</button></div>
        <button className="btn btn-verde" onClick={() => setNueva(true)}><Plus />Nueva oportunidad</button>
      </Top>
      <div className="filtros">
        {jefe && <select className="filtro-sel" value={vendedor} onChange={(e) => setVendedor(e.target.value)}><option value="">Vendedor: todos</option>{vendedores.map((v) => <option key={v.id} value={v.id}>{v.nombre}</option>)}</select>}
        <select className="filtro-sel" value={origen} onChange={(e) => setOrigen(e.target.value)}><option value="">Origen: todos</option><option value="meta">Meta Ads</option><option value="google">Google Ads</option><option value="organico">Orgánico</option><option value="directo">Directo</option></select>
        {jefe && sinAsignar > 0 && <button className="btn btn-violeta btn-sm" onClick={repartir}><Shuffle />Repartir {sinAsignar} sin asignar · Hill climbing</button>}
        <span style={{ marginLeft: "auto" }} className="chip chip-cotizado"><TrendingUp className="i14" />Cierre (30 días) {pct(conversion, 1)}</span>
        {estancadas > 0 && <span className="chip chip-aviso"><TriangleAlert className="i14" />{estancadas} estancada{estancadas > 1 ? "s" : ""} · ≥2 días</span>}
      </div>
      {!lista ? <div className="cargando"><LoaderCircle className="girar" /></div> : vista === "lista" ? (
        <div className="card" style={{ padding: 8 }}>
          <table className="tabla">
            <thead><tr><th>Cliente</th><th>Producto</th><th>Monto</th><th>Etapa</th><th>Prob. IA</th><th>Vendedor</th><th>Origen</th><th>Actualizado</th></tr></thead>
            <tbody>{filtrada.map((c) => (
              <tr key={c.id} style={{ cursor: "pointer" }} onClick={() => router.push(`/crm/chats?id=${c.id}`)}>
                <td><b>{c.nombre}</b><div className="muted" style={{ fontSize: 12 }}>{c.distrito}</div></td><td>{c.producto?.nombre || "—"}</td><td className="tnum"><b>{soles(c.monto)}</b></td>
                <td><ChipEtapa etapa={c.etapa} nombre={c.etapa_nombre} /></td><td>{c.probabilidad != null ? pct(c.probabilidad) : "—"}</td>
                <td>{c.vendedor ? c.vendedor.nombre : <span className="muted">Sin asignar</span>}</td><td>{c.origen_nombre}</td><td className="muted">{hace(c.actualizado)}</td>
              </tr>))}</tbody>
          </table>
        </div>
      ) : (
        <div className="tablero">
          {COLS.map((k) => {
            const items = por(k);
            const total = items.reduce((a, c) => a + c.monto, 0);
            const visibles = k === "ganado" ? items.slice(0, 12) : items;
            return (
              <div key={k} className={`columna c-${k} ${sobre === k ? "sobre-drop" : ""}`} onDragOver={encima(k)} onDragLeave={() => setSobre(null)} onDrop={soltar(k)}>
                <div className="col-cab">
                  <div className="n1"><i style={{ background: PUNTO[k] }} />{ETAPAS.find((e) => e.k === k).n}<span className="cnt">{items.length}</span></div>
                  <div className="n2"><b className="tnum">{soles(total)}</b><small>{k === "ganado" ? "últimos 30 días" : `prom. ${soles(items.length ? total / items.length : 0)}`}</small></div>
                </div>
                {visibles.map((c) => <Tarjeta key={c.id} c={c} onAbrir={(id) => router.push(`/crm/chats?id=${id}`)} onArrastre={setArrastrando} />)}
                {k === "nuevo" && (
                  <div className="op" style={{ cursor: "default", border: "1.5px dashed #C8D8E8", background: "#F7FAFC" }}>
                    <ChipKinti />
                    <span style={{ fontSize: 13, lineHeight: 1.5, color: "#33445C" }}>Responde cada chat nuevo en segundos y, cuando la regresión logística supera el 80 %, lo pasa a «Calificado por IA».</span>
                  </div>
                )}
                {k === "ganado" && items.length > visibles.length && <button className="mas" onClick={() => setVista("lista")}>Ver las {items.length} ventas</button>}
                {arrastrando && items.length === 0 && <div className="vacio" style={{ border: "1.5px dashed #9FB3CC", borderRadius: 14 }}>Suelta aquí</div>}
              </div>
            );
          })}
          <div className={`columna c-perdido ${sobre === "perdido" ? "sobre-drop" : ""}`} onDragOver={encima("perdido")} onDragLeave={() => setSobre(null)} onDrop={soltar("perdido")}>
            <div className="col-cab" style={{ textAlign: "center" }}><div className="n1" style={{ justifyContent: "center" }}>Perdidos</div>
              <div className="sora" style={{ fontSize: 30, fontWeight: 800 }}>{perdidos.length}</div><small className="muted">{soles(perdidos.reduce((a, c) => a + c.monto, 0))} · 30 días</small></div>
            <div className="lbl" style={{ padding: "0 6px" }}>Motivos</div>
            {MOTIVOS.map((m) => {
              const n = perdidos.filter((c) => c.motivo_perdida === m).length;
              return <div key={m} style={{ padding: "0 6px", fontSize: 12.5 }}><div style={{ display: "flex", justifyContent: "space-between" }}><span>{m}</span><b>{n}</b></div><div className="barra" style={{ height: 5, marginTop: 3 }}><i style={{ width: `${perdidos.length ? (n / perdidos.length) * 100 : 0}%`, background: "#C3122F" }} /></div></div>;
            })}
            {perdidos.slice(0, 4).map((c) => (
              <div key={c.id} className="op-mini" draggable onDragStart={(e) => e.dataTransfer.setData("text/plain", String(c.id))} onClick={() => router.push(`/crm/chats?id=${c.id}`)}>
                <b>{c.nombre}</b><span className="muted">{c.producto?.nombre || "—"}</span><span className="chip chip-perdido" style={{ height: 20, fontSize: 11, alignSelf: "flex-start" }}>{c.motivo_perdida}</span>
              </div>
            ))}
            <div className="vacio" style={{ padding: 10, fontSize: 12.5 }}><img src="/crm-img/kinti-derivando.webp" alt="" style={{ width: 90 }} />Arrastra aquí para marcar perdida</div>
          </div>
        </div>
      )}
    </main>
  );
}
