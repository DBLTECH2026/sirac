"use client";
import { useEffect, useState } from "react";
import { CircleCheck, Coins, LoaderCircle, MessageCircle, Percent, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { Top, useSesion } from "../../Marco";
import { api, Av, ChipKinti, pct, soles } from "../../lib";

const PERIODOS = [["hoy", "Hoy"], ["7d", "7 días"], ["30d", "30 días"]];

function Delta({ a, b }) {
  if (!b) return <span className="delta">nuevo</span>;
  const d = (a - b) / b;
  const baja = d < 0;
  return <span className={`delta ${baja ? "baja" : ""}`}>{baja ? <TrendingDown /> : <TrendingUp />}{baja ? "" : "+"}{Math.round(d * 100)} %</span>;
}

function Grafico({ serie }) {
  const W = 760, H = 250, top = 18, alto = 140, base = top + alto;
  const n = serie.length, paso = (W - 50) / n, ancho = Math.max(6, paso * 0.58);
  const maxI = Math.max(...serie.map((s) => s.ingresos), 1);
  const maxV = Math.max(...serie.map((s) => s.ventas), 1);
  const y0 = 220, altoV = 34;
  const puntos = serie.map((s, i) => `${44 + i * paso + paso / 2},${y0 - (s.ventas / maxV) * altoV}`).join(" ");
  const mejor = serie.reduce((m, s, i) => (s.ingresos > serie[m].ingresos ? i : m), 0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Ingresos y ventas por día">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1="40" x2={W} y1={base - f * alto} y2={base - f * alto} stroke="#E6EDF5" />
          <text x="34" y={base - f * alto + 4} fontSize="10.5" fill="#6E819A" textAnchor="end">{f === 0 ? "S/ 0" : `S/ ${Math.round((maxI * f) / 100) / 10}k`}</text>
        </g>
      ))}
      {serie.map((s, i) => {
        const x = 44 + i * paso;
        const h = (s.ingresos / maxI) * alto;
        const finde = s.semana >= 5;
        return (
          <g key={s.fecha}>
            {finde && <rect x={x} y={top - 6} width={paso} height={y0 - top + 12} fill="#EEF3F8" rx="4" />}
            <rect x={x + (paso - ancho) / 2} y={base - h} width={ancho} height={Math.max(h, 1)} rx="3" fill={i === n - 1 ? "#9BE3B8" : "#0EB155"}>
              <title>{`${s.fecha}: ${soles(s.ingresos)} · ${s.ventas} ventas`}</title>
            </rect>
            {(i % Math.ceil(n / 8) === 0 || i === n - 1) && <text x={x + paso / 2} y={H - 4} fontSize="10.5" fill="#6E819A" textAnchor="middle">{i === n - 1 ? "hoy" : s.dia}</text>}
          </g>
        );
      })}
      {serie[mejor].ingresos > 0 && (
        <text x={44 + mejor * paso + paso / 2} y={base - alto - 4} fontSize="11" fontWeight="700" fill="#0A1424" textAnchor="middle">{soles(serie[mejor].ingresos)}</text>
      )}
      <text x="40" y={y0 - altoV - 8} fontSize="10" fontWeight="700" fill="#0B6E85" letterSpacing="1">VENTAS POR DÍA</text>
      <polyline points={puntos} fill="none" stroke="#16B6D8" strokeWidth="2" />
      {serie.map((s, i) => <circle key={i} cx={44 + i * paso + paso / 2} cy={y0 - (s.ventas / maxV) * altoV} r="2.6" fill="#fff" stroke="#16B6D8" strokeWidth="1.6" />)}
    </svg>
  );
}

function Donut({ valor }) {
  const r = 46, c = 2 * Math.PI * r;
  return (
    <div className="donut">
      <svg viewBox="0 0 112 112" width="112" height="112">
        <circle cx="56" cy="56" r={r} fill="none" stroke="#16B6D8" strokeWidth="11" />
        <circle cx="56" cy="56" r={r} fill="none" stroke="#7C5CFC" strokeWidth="11" strokeDasharray={`${c * valor} ${c}`} transform="rotate(-90 56 56)" strokeLinecap="round" />
      </svg>
      <div className="c"><div><b>{Math.round(valor * 100)} %</b><small>sin ayuda</small></div></div>
    </div>
  );
}

export default function Dashboard() {
  const { yo } = useSesion();
  const [periodo, setPeriodo] = useState("30d");
  const [d, setD] = useState(null);
  useEffect(() => { api(`/crm/tablero?periodo=${periodo}`).then(setD).catch(() => {}); }, [periodo]);
  const ventas = yo.rol === "ventas";
  const nombreP = PERIODOS.find((p) => p[0] === periodo)[1].toLowerCase();

  return (
    <main className="main">
      <Top sobre={`Resumen · ${periodo === "hoy" ? "hoy" : `últimos ${nombreP}`}`} titulo={ventas ? "Mi dashboard" : "Dashboard"}
        sub={`Hola, ${yo.primer_nombre}. Así le fue a ${ventas ? "tu cartera" : "Kusi Hogar"} ${periodo === "hoy" ? "hoy" : `en los últimos ${nombreP}`}.`}>
        <div className="seg">{PERIODOS.map(([k, t]) => <button key={k} className={periodo === k ? "on" : ""} onClick={() => setPeriodo(k)}>{t}</button>)}</div>
      </Top>
      {!d ? <div className="cargando"><LoaderCircle className="girar" /></div> : (
        <>
          <div className="kpis">
            <div className="card kpi"><div className="l"><MessageCircle />Chats nuevos</div><div className="v tnum">{d.actual.chats.toLocaleString("es-PE")}</div>
              <div className="pie"><Delta a={d.actual.chats} b={d.anterior.chats} />vs periodo anterior</div></div>
            <div className="card kpi"><div className="l"><Sparkles />Chats calificados</div><div className="v tnum">{d.actual.calificados}<ChipKinti /></div>
              <div className="pie"><b style={{ color: "#4B2FD0" }}>{d.actual.chats ? pct(d.actual.calificados / d.actual.chats) : "0 %"}</b> de los chats</div></div>
            <div className="card kpi"><div className="l"><CircleCheck />Ventas cerradas</div><div className="v tnum">{d.actual.ventas}</div>
              <div className="pie"><Delta a={d.actual.ventas} b={d.anterior.ventas} />vs periodo anterior</div></div>
            <div className="card kpi"><div className="l"><Coins />Ingresos</div><div className="v tnum">{soles(d.actual.ingresos)}</div>
              <div className="pie"><Delta a={d.actual.ingresos} b={d.anterior.ingresos} />vs periodo anterior</div></div>
            <div className="card kpi"><div className="l"><Percent />Conversión <small className="muted">chat → venta</small></div><div className="v tnum">{pct(d.actual.conversion, 1)}</div>
              <div className="pie">Ticket promedio <b style={{ color: "#0A1424", marginLeft: "auto" }}>{soles(d.actual.ticket)}</b></div></div>
          </div>

          <div className="dash-fila f1">
            <div className="card grafico">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div><h3>Ingresos y ventas por día</h3>
                  <div className="sub" style={{ fontSize: 13 }}>Últimos {d.serie.length} días · {soles(d.serie.reduce((a, s) => a + s.ingresos, 0))} en {d.serie.reduce((a, s) => a + s.ventas, 0)} ventas · las franjas son fines de semana</div></div>
                <div className="leyenda"><span><i style={{ background: "#0EB155" }} />Ingresos (S/)</span><span><i style={{ background: "#16B6D8" }} />Ventas</span><span><i style={{ background: "#EEF3F8", border: "1px solid #DCE5EF" }} />Fin de semana</span></div>
              </div>
              <div style={{ marginTop: 10 }}><Grafico serie={d.serie} /></div>
            </div>
            <div className="card-osc" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><ChipKinti /><span className="chip chip-ia"><i className="pt" />{d.kinti.chats} chats</span></div>
              <h3 style={{ fontSize: 19 }}>Así atendió Kinti</h3>
              <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
                <Donut valor={d.kinti.pct_sin_ayuda} />
                <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
                  <div><div style={{ display: "flex", justifyContent: "space-between" }}><b>Resueltos sin ayuda</b><b>{d.kinti.sin_ayuda}</b></div><small className="muted">respondidos de principio a fin</small></div>
                  <div><div style={{ display: "flex", justifyContent: "space-between" }}><b>Derivados a vendedor</b><b>{d.kinti.derivados}</b></div><small className="muted">listos para cerrar</small></div>
                </div>
              </div>
              <div className="grid2">
                <div className="mini-card"><div className="lbl" style={{ color: "#16B6D8" }}>Primera respuesta</div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginTop: 6 }}><span>Kinti · IA</span><b>{d.kinti.segundos} s</b></div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginTop: 4 }}><span>Equipo</span><b>{d.kinti.minutos_equipo != null ? `${d.kinti.minutos_equipo} min` : "—"}</b></div></div>
                <div className="mini-card"><div className="lbl" style={{ color: "#16B6D8" }}>Atendiendo ahora</div>
                  <div style={{ fontFamily: "var(--f-titulo)", fontSize: 26, fontWeight: 800, marginTop: 4 }}>{d.kinti.atendiendo}</div><small className="muted">chats abiertos con Kinti</small></div>
              </div>
            </div>
          </div>

          <div className="dash-fila f2">
            <div className="card">
              <h3>{ventas ? "Mi avance de meta" : "Ranking de vendedores"}</h3>
              <table className="tabla" style={{ marginTop: 8 }}>
                <thead><tr><th>#</th><th>Vendedor</th><th>Ventas</th><th>Ingresos</th><th>Avance de meta</th></tr></thead>
                <tbody>
                  {d.ranking.map((r, i) => (
                    <tr key={r.id} className="rank-fila">
                      <td><span className={`pos ${i === 0 ? "p1" : ""}`}>{i + 1}</span></td>
                      <td><div style={{ display: "flex", gap: 9, alignItems: "center" }}><Av p={r} /><div><b>{r.nombre}</b><div className="muted" style={{ fontSize: 12 }}>{r.cargo} · {r.abiertos} abiertos</div></div></div></td>
                      <td className="tnum">{r.ventas}</td>
                      <td className="tnum"><b>{soles(r.ingresos)}</b></td>
                      <td style={{ minWidth: 130 }}><div style={{ fontSize: 12 }}><b>{pct(r.avance)}</b> <span className="muted">de {soles(r.meta)}</span></div><div className="barra" style={{ marginTop: 4 }}><i style={{ width: `${Math.min(100, r.avance * 100)}%` }} /></div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card">
              <h3>Top productos</h3>
              <div style={{ marginTop: 8 }}>
                {d.top.length === 0 && <div className="vacio">Aún no hay ventas en este periodo.</div>}
                {d.top.map((t) => (
                  <div className="prod-fila" key={t.producto.id}>
                    <img src={t.producto.foto} alt="" />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><b style={{ fontSize: 14 }}>{t.producto.nombre}</b><b className="tnum">{soles(t.ingresos)}</b></div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}><div className="barra" style={{ flex: 1 }}><i style={{ width: `${t.pct * 100}%` }} /></div><small className="muted">{t.unidades} u.</small></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="card embudo-mini">
              <h3>Embudo</h3>
              <div style={{ marginTop: 8 }}>
                {d.embudo.map((e) => {
                  const max = Math.max(...d.embudo.map((x) => x.n), 1);
                  const color = { nuevo: "", calificado: "ia", cotizado: "cel", ganado: "", perdido: "" }[e.etapa];
                  return (
                    <div className="paso" key={e.etapa}>
                      <span>{e.nombre}</span>
                      <div className={`barra ${color}`}><i style={{ width: `${(e.n / max) * 100}%`, background: e.etapa === "perdido" ? "#C3122F" : e.etapa === "nuevo" ? "#9FB3CC" : undefined }} /></div>
                      <b className="tnum" style={{ textAlign: "right" }}>{e.n}</b>
                    </div>
                  );
                })}
              </div>
              <div className="lbl" style={{ marginTop: 14 }}>De dónde llegan</div>
              {d.origenes.map((o) => (
                <div key={o.origen} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "5px 0", borderBottom: "1px solid #EDF2F7" }}>
                  <span>{o.nombre}</span><span className="muted">{o.chats} chats · <b style={{ color: "#0A7A3C" }}>{o.ventas} ventas</b></span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </main>
  );
}
