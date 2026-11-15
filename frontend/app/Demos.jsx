"use client";
import { useEffect, useState } from "react";

const api = async (ruta, opciones) => {
  const r = await fetch(`/api/${ruta}`, opciones);
  if (!r.ok) throw new Error(`Error ${r.status}`);
  return r.json();
};
const pct = (x) => `${(x * 100).toFixed(1)} %`;

export function Estado() {
  const [s, setS] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => { api("salud").then(setS).catch(() => setError(true)); }, []);
  if (error) return <p className="estado estado-mal">API sin respuesta</p>;
  if (!s) return <p className="estado">Consultando el servidor…</p>;
  return (
    <p className="estado estado-ok">
      <span className="punto" /> API en línea · versión <b>{s.version}</b> · {s.servidor} · Python {s.python} · base de datos {s.motor_bd}
    </p>
  );
}

const PRODUCTOS = [["Freidora de aire 5 L", 279], ["Olla arrocera 1.8 L", 129], ["Batería de ollas 9 piezas", 349], ["Aspiradora 2000 W", 459], ["Termo de acero 1 L", 59]];

export function Calificar() {
  const [f, setF] = useState({ minutos_respuesta: 1, mensajes: 6, pidio_precio: true, pidio_delivery: true, origen: "meta", provincia: false, precio: 279 });
  const [r, setR] = useState(null);
  const cambiar = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const enviar = async () => setR(await api("ia/calificar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...f, fuera_de_horario: f.minutos_respuesta > 480 }) }));
  useEffect(() => { enviar(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <article className="tarjeta">
      <span className="chip chip-ia">Regresión logística</span>
      <h3>¿Este cliente va a comprar?</h3>
      <label>Minutos hasta la primera respuesta: <b>{f.minutos_respuesta}</b>
        <input type="range" min="0" max="900" value={f.minutos_respuesta} onChange={(e) => cambiar("minutos_respuesta", +e.target.value)} /></label>
      <label>Mensajes del cliente: <b>{f.mensajes}</b>
        <input type="range" min="1" max="15" value={f.mensajes} onChange={(e) => cambiar("mensajes", +e.target.value)} /></label>
      <div className="fila">
        <label className="check"><input type="checkbox" checked={f.pidio_precio} onChange={(e) => cambiar("pidio_precio", e.target.checked)} /> Pidió el precio</label>
        <label className="check"><input type="checkbox" checked={f.pidio_delivery} onChange={(e) => cambiar("pidio_delivery", e.target.checked)} /> Pidió delivery</label>
        <label className="check"><input type="checkbox" checked={f.provincia} onChange={(e) => cambiar("provincia", e.target.checked)} /> Es de provincia</label>
      </div>
      <div className="fila">
        <select value={f.origen} onChange={(e) => cambiar("origen", e.target.value)}>
          <option value="meta">Anuncio de Meta</option><option value="google">Anuncio de Google</option>
          <option value="organico">Orgánico</option><option value="directo">Directo</option>
        </select>
        <select value={f.precio} onChange={(e) => cambiar("precio", +e.target.value)}>
          {PRODUCTOS.map(([n, p]) => <option key={n} value={p}>{n} · S/ {p}</option>)}
        </select>
      </div>
      <button onClick={enviar}>Calificar cliente</button>
      {r && (
        <div className={`resultado r-${r.etiqueta === "frío" ? "frio" : r.etiqueta}`}>
          <div className="barra"><span style={{ width: pct(r.probabilidad_compra) }} /></div>
          <p><b>{pct(r.probabilidad_compra)}</b> de probabilidad de compra · cliente <b>{r.etiqueta}</b></p>
          <p className="sutil">{r.recomendacion}</p>
        </div>
      )}
    </article>
  );
}

export function Proyeccion() {
  const [inv, setInv] = useState(228);
  const [r, setR] = useState(null);
  useEffect(() => { const t = setTimeout(() => api(`ia/proyectar?inversion=${inv}`).then(setR), 200); return () => clearTimeout(t); }, [inv]);
  return (
    <article className="tarjeta">
      <span className="chip chip-dato">Regresión no lineal</span>
      <h3>¿Cuántas conversaciones trae la inversión?</h3>
      <label>Inversión diaria en anuncios: <b>S/ {inv}</b>
        <input type="range" min="50" max="600" step="10" value={inv} onChange={(e) => setInv(+e.target.value)} /></label>
      {r && (
        <div className="numeros">
          <div><b>{r.conversaciones_dia}</b><span>conversaciones al día</span></div>
          <div><b>{r.conversaciones_mes.toLocaleString("es-PE")}</b><span>al mes (30 días)</span></div>
        </div>
      )}
      <p className="sutil">Modelo elegido: <b>{r ? r.modelo : "…"}</b>. Cada sol extra rinde menos que el anterior (rendimientos decrecientes).</p>
    </article>
  );
}

export function Metricas() {
  const [m, setM] = useState(null);
  useEffect(() => { api("ia/metricas").then(setM); }, []);
  if (!m) return null;
  const reg = m.regresion.modelos, c = m.clasificacion.metricas;
  return (
    <article className="tarjeta ancha">
      <h3>Métricas en el conjunto de prueba</h3>
      <div className="tabla-scroll">
        <table>
          <thead><tr><th>Regresión</th><th>R²</th><th>MAE</th><th>RMSE</th></tr></thead>
          <tbody>{Object.entries(reg).map(([k, v]) => <tr key={k} className={k === m.regresion.mejor ? "mejor" : ""}><td>{k}</td><td>{v.r2}</td><td>{v.mae}</td><td>{v.rmse}</td></tr>)}</tbody>
        </table>
        <table>
          <thead><tr><th>Regresión logística</th><th>Valor</th></tr></thead>
          <tbody>{Object.entries(c).map(([k, v]) => <tr key={k}><td>{k.replaceAll("_", " ")}</td><td>{v}</td></tr>)}</tbody>
        </table>
      </div>
      <p className="sutil">{m.nota}</p>
    </article>
  );
}

export function Ruta() {
  const [ds, setDs] = useState([]);
  const [o, setO] = useState("Ate");
  const [d, setD] = useState("Comas");
  const [r, setR] = useState(null);
  useEffect(() => { api("busqueda/distritos").then((x) => setDs(x.distritos)); }, []);
  useEffect(() => { if (o !== d) api(`busqueda/ruta?origen=${encodeURIComponent(o)}&destino=${encodeURIComponent(d)}`).then(setR); }, [o, d]);
  return (
    <article className="tarjeta">
      <span className="chip chip-ok">A* · búsqueda informada</span>
      <h3>Ruta de delivery desde el almacén</h3>
      <div className="fila">
        <select value={o} onChange={(e) => setO(e.target.value)}>{ds.map((x) => <option key={x}>{x}</option>)}</select>
        <span>→</span>
        <select value={d} onChange={(e) => setD(e.target.value)}>{ds.map((x) => <option key={x}>{x}</option>)}</select>
      </div>
      {r && (
        <>
          <ol className="camino">{r.a_estrella.camino.map((x) => <li key={x}>{x}</li>)}</ol>
          <table>
            <thead><tr><th>Algoritmo</th><th>Km</th><th>Distritos revisados</th></tr></thead>
            <tbody>{[r.a_estrella, r.costo_uniforme, r.bfs].map((x) => <tr key={x.algoritmo}><td>{x.algoritmo}</td><td>{x.km}</td><td>{x.expandidos}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </article>
  );
}

export function Conversacion() {
  const [r, setR] = useState(null);
  useEffect(() => { api("busqueda/conversacion").then(setR); }, []);
  if (!r) return <article className="tarjeta"><h3>Flujo de conversación</h3></article>;
  return (
    <article className="tarjeta">
      <span className="chip chip-ia">BFS y DFS · búsqueda no informada</span>
      <h3>¿Cuál es el camino más corto hasta la venta?</h3>
      {[r.bfs, r.dfs].map((x) => (
        <div key={x.algoritmo} className="bloque">
          <p><b>{x.algoritmo}</b>: {x.pasos} acciones · {x.expandidos} estados revisados</p>
          <ol className="camino chico">{x.acciones.map((a, i) => <li key={i}>{a}</li>)}</ol>
        </div>
      ))}
    </article>
  );
}

export function Asignacion() {
  const [semilla, setSemilla] = useState(7);
  const [r, setR] = useState(null);
  const ejecutar = () => api(`busqueda/asignar?semilla=${semilla}`).then(setR);
  useEffect(() => { ejecutar(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <article className="tarjeta ancha">
      <span className="chip chip-ok">Hill climbing · búsqueda local</span>
      <h3>Reparto de clientes entre vendedores</h3>
      <div className="fila">
        <label>Escenario <input type="number" min="1" max="999" value={semilla} onChange={(e) => setSemilla(+e.target.value)} /></label>
        <button onClick={ejecutar}>Optimizar reparto</button>
      </div>
      {r && (
        <>
          <div className="numeros">
            <div><b>{r.costo_inicial}</b><span>costo por turnos</span></div>
            <div><b>{r.costo_final}</b><span>costo optimizado</span></div>
            <div><b>{r.mejora_pct} %</b><span>de mejora en {r.iteraciones} pasos</span></div>
          </div>
          <div className="tabla-scroll">
            <table>
              <thead><tr><th>Cliente</th><th>Zona</th><th>Categoría</th><th>Urgencia</th><th>Por turnos</th><th>Optimizado</th></tr></thead>
              <tbody>{r.asignacion.map((a) => <tr key={a.lead} className={a.vendedor !== a.vendedor_inicial ? "mejor" : ""}><td>#{a.lead}</td><td>{a.zona}</td><td>{a.categoria}</td><td>{a.urgencia}</td><td>{a.vendedor_inicial}</td><td>{a.vendedor}</td></tr>)}</tbody>
            </table>
          </div>
        </>
      )}
    </article>
  );
}
