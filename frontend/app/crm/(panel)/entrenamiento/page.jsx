"use client";
import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, Pencil, Plus, Send, Sparkles, Trash2 } from "lucide-react";
import { Top } from "../../Marco";
import { api, ChipKinti, ESTADOS, pct, useAviso } from "../../lib";

const VACIA = { tema: "", palabras: "", respuesta: "" };

export default function Entrenamiento() {
  const [d, setD] = useState(null);
  const [form, setForm] = useState(VACIA);
  const [editando, setEditando] = useState(null);
  const [prueba, setPrueba] = useState("¿Cuánto está la freidora de aire? Estoy en Comas");
  const [res, setRes] = useState(null);
  const [probando, setProbando] = useState(false);
  const [aviso, mostrar] = useAviso();

  const cargar = useCallback(() => api("/crm/entrenamiento").then(setD).catch(() => {}), []);
  useEffect(() => { cargar(); }, [cargar]);

  async function guardar(e) {
    e.preventDefault();
    try {
      if (editando) await api(`/crm/entrenamiento/${editando}`, { metodo: "PATCH", datos: form });
      else await api("/crm/entrenamiento", { metodo: "POST", datos: form });
      mostrar(editando ? "Respuesta actualizada. Kinti ya la usa." : "Kinti aprendió una respuesta nueva.");
      setForm(VACIA); setEditando(null); cargar();
    } catch (err) { mostrar(err.message, true); }
  }
  async function probar(e) {
    e.preventDefault();
    setProbando(true);
    try { setRes(await api("/crm/entrenamiento/probar", { metodo: "POST", datos: { texto: prueba } })); }
    catch (err) { mostrar(err.message, true); } finally { setProbando(false); }
  }

  return (
    <main className="main">
      {aviso}
      <Top sobre="Kinti · IA" titulo="Entrenamiento" sub="Las respuestas que Kinti usa cuando el cliente pregunta por garantía, pagos, tienda y más." />
      {!d ? <div className="cargando"><LoaderCircle className="girar" /></div> : (
        <div className="dos-col">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card-osc ilus-card" style={{ minHeight: 230 }}>
              <div className="luna" /><img className="ilus" src="/crm-img/kinti-aprendiendo.webp" alt="" />
              <ChipKinti />
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 14, maxWidth: 190, position: "relative" }}>
                <div><div className="sora" style={{ fontSize: 26, fontWeight: 800 }}>{d.estadisticas.mensajes.toLocaleString("es-PE")}</div><small className="muted">mensajes respondidos</small></div>
                <div><div className="sora" style={{ fontSize: 22, fontWeight: 800 }}>{d.estadisticas.segundos} s</div><small className="muted">tiempo de respuesta promedio</small></div>
                <div><div className="sora" style={{ fontSize: 22, fontWeight: 800, color: "#0EB155" }}>{pct(d.estadisticas.sin_ayuda)}</div><small className="muted">de chats sin derivar</small></div>
              </div>
            </div>
            <form className="card" onSubmit={probar} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <h3>Probar a Kinti</h3>
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>Escribe como un cliente. No se guarda nada.</p>
              <textarea className="input" rows={2} value={prueba} onChange={(e) => setPrueba(e.target.value)} />
              <button className="btn btn-noche btn-sm" style={{ alignSelf: "flex-start" }} disabled={probando}>{probando ? <LoaderCircle className="girar" /> : <><Send />Probar</>}</button>
              {res && (
                <div className="prueba-res">
                  {res.respuestas.map((r, i) => <div className="b" key={i}>{r}</div>)}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, fontSize: 12 }}>
                    {res.intenciones.map((x) => <span key={x} className="chip chip-ia" style={{ height: 22 }}>intención: {x}</span>)}
                    {res.producto && <span className="chip chip-ganado" style={{ height: 22 }}>{res.producto}</span>}
                    {res.distrito && <span className="chip chip-cotizado" style={{ height: 22 }}>{res.distrito}</span>}
                    {res.respuesta_entrenada && <span className="chip chip-aviso" style={{ height: 22 }}>usó: {res.respuesta_entrenada}</span>}
                    <span className="chip chip-osc" style={{ height: 22 }}>estado: {ESTADOS[res.estado] || res.estado}</span>
                  </div>
                </div>
              )}
            </form>
            <div className="card-osc">
              <h3>Cómo decide Kinti</h3>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.5 }}>Avanza por el grafo de la conversación (BFS), cotiza el delivery con A*, calcula la probabilidad de compra con la regresión logística y reparte a los vendedores con el costo del Hill climbing.</p>
              <div className="estado-graf">{d.estadisticas.estados.map((s) => <span key={s}>{ESTADOS[s] || s}</span>)}</div>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <form className="card" onSubmit={guardar} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <h3>{editando ? "Editar respuesta" : "Enseñar una respuesta nueva"}</h3>
              <div className="grid2">
                <label className="campo"><span>Tema</span><input className="input" value={form.tema} onChange={(e) => setForm({ ...form, tema: e.target.value })} placeholder="Ej.: Instalación" required /></label>
                <label className="campo"><span>Palabras clave (separadas por comas)</span><input className="input" value={form.palabras} onChange={(e) => setForm({ ...form, palabras: e.target.value })} placeholder="instalan, instalacion" required /></label>
              </div>
              <label className="campo"><span>Respuesta de Kinti</span><textarea className="input" rows={3} value={form.respuesta} onChange={(e) => setForm({ ...form, respuesta: e.target.value })} required /></label>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-verde btn-sm">{editando ? <><Pencil />Guardar cambios</> : <><Plus />Agregar</>}</button>
                {editando && <button type="button" className="btn btn-borde btn-sm" onClick={() => { setEditando(null); setForm(VACIA); }}>Cancelar</button>}
              </div>
            </form>
            {d.respuestas.map((r) => (
              <div key={r.id} className={`respuesta ${r.activa ? "" : "off"}`}>
                <div className="f1"><Sparkles className="i16" style={{ color: "#7C5CFC" }} /><b>{r.tema}</b><span className="muted" style={{ fontSize: 12 }}>usada {r.usos} {r.usos === 1 ? "vez" : "veces"}</span>
                  <span style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
                    <button className={`toggle ${r.activa ? "on" : ""}`} title={r.activa ? "Desactivar" : "Activar"} onClick={async () => { await api(`/crm/entrenamiento/${r.id}`, { metodo: "PATCH", datos: { activa: !r.activa } }); cargar(); }} />
                    <button className="icono-btn" style={{ width: 32, height: 32 }} title="Editar" onClick={() => { setEditando(r.id); setForm({ tema: r.tema, palabras: r.palabras, respuesta: r.respuesta }); window.scrollTo({ top: 0, behavior: "smooth" }); }}><Pencil className="i14" /></button>
                    <button className="icono-btn" style={{ width: 32, height: 32 }} title="Eliminar" onClick={async () => { if (confirm(`¿Eliminar la respuesta «${r.tema}»?`)) { await api(`/crm/entrenamiento/${r.id}`, { metodo: "DELETE" }); cargar(); } }}><Trash2 className="i14" /></button>
                  </span></div>
                <div className="palabras">{r.palabras.split(",").map((p) => p.trim()).filter(Boolean).map((p) => <span key={p}>{p}</span>)}</div>
                <p>{r.respuesta}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
