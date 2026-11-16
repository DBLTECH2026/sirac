"use client";
import { useCallback, useEffect, useState } from "react";
import { KeyRound, LoaderCircle, QrCode, RotateCcw, ShieldCheck, Smartphone, Unplug, UserPlus } from "lucide-react";
import { Top, useSesion } from "../../Marco";
import { api, soles, useAviso, useIntervalo } from "../../lib";

const ESTADO_WA = {
  open: ["Conectado", "chip-ganado"], connecting: ["Esperando el QR", "chip-aviso"], close: ["Desconectado", "chip-nuevo"],
  sin_instancia: ["Sin vincular", "chip-nuevo"], sin_configurar: ["Sin configurar", "chip-perdido"], sin_servicio: ["Evolution no responde", "chip-perdido"],
};

function ConexionWhatsapp({ mostrar }) {
  const [w, setW] = useState(null);
  const [qr, setQr] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const [palabra, setPalabra] = useState("");
  const cargar = useCallback(() => api("/crm/whatsapp").then((r) => {
    setW(r);
    setPalabra((p) => p || r.filtro.palabra);
    if (r.estado === "open") setQr(null);
  }).catch(() => {}), []);
  useEffect(() => { cargar(); }, [cargar]);
  useIntervalo(cargar, qr ? 3000 : 15000, [qr]);
  useIntervalo(() => { if (qr) api("/crm/whatsapp", { metodo: "POST", datos: { accion: "conectar" } }).then((r) => r.qr && setQr(r.qr)).catch(() => {}); }, 25000, [qr]);

  async function accion(datos, texto) {
    setOcupado(true);
    try {
      const r = await api("/crm/whatsapp", { metodo: "POST", datos });
      setW(r);
      if (datos.accion === "conectar") setQr(r.estado === "open" ? null : r.qr || null);
      if (datos.accion === "desconectar") setQr(null);
      if (texto) mostrar(texto);
    } catch (e) { mostrar(e.message, true); } finally { setOcupado(false); }
  }
  if (!w) return <div className="card"><LoaderCircle className="girar" /></div>;
  const [nombreEstado, chip] = ESTADO_WA[w.estado] || [w.estado, "chip-nuevo"];
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span className="av" style={{ background: "#0B6E4F" }}><Smartphone className="i18" /></span>
        <div style={{ flex: 1 }}><h3>WhatsApp real</h3><small className="muted">Conectado con Evolution API en el servidor de SIRAC</small></div>
        <span className={`chip ${chip}`}><i className="pt" style={{ background: "currentColor" }} />{nombreEstado}</span>
      </div>
      {w.estado === "open" && (
        <div className="caja-gris" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
          <div><b>{w.nombre || "WhatsApp"}</b><div className="muted" style={{ fontSize: 13 }}>+{w.numero} · {w.chats} chats reales en el CRM</div></div>
          <button className="btn btn-rojo btn-sm" disabled={ocupado} onClick={() => confirm("¿Desvincular este WhatsApp del CRM?") && accion({ accion: "desconectar" }, "WhatsApp desvinculado.")}><Unplug />Desvincular</button>
        </div>
      )}
      {w.estado === "sin_configurar" && <p className="muted" style={{ margin: 0, fontSize: 13.5 }}>Falta configurar Evolution API en el servidor (EVOLUTION_URL y EVOLUTION_API_KEY).</p>}
      {w.estado !== "open" && w.estado !== "sin_configurar" && !qr && (
        <button className="btn btn-verde btn-sm" style={{ alignSelf: "flex-start" }} disabled={ocupado} onClick={() => accion({ accion: "conectar" })}>
          {ocupado ? <LoaderCircle className="girar" /> : <QrCode />}Vincular WhatsApp
        </button>
      )}
      {qr && w.estado !== "open" && (
        <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          <img src={qr} alt="Código QR de WhatsApp" style={{ width: 210, height: 210, borderRadius: 12, border: "1px solid #DCE5EF" }} />
          <ol style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, lineHeight: 1.7, flex: 1, minWidth: 180 }}>
            <li>Abre WhatsApp en el celular.</li><li>Ve a <b>Dispositivos vinculados</b>.</li><li>Toca <b>Vincular un dispositivo</b> y escanea.</li>
            <li className="muted">El QR se renueva solo cada 25 s.</li>
          </ol>
        </div>
      )}
      <div style={{ borderTop: "1px solid #EDF2F7", paddingTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ShieldCheck className="i18" style={{ color: "#0A7A3C" }} />
          <b style={{ fontSize: 14, flex: 1 }}>Solo chats que mencionen una palabra clave</b>
          <button className={`toggle ${w.filtro.activo ? "on" : ""}`} onClick={() => accion({ accion: "filtro", activo: !w.filtro.activo, palabra }, w.filtro.activo ? "Kinti atenderá a todos los chats nuevos." : "Kinti solo atenderá chats con la palabra clave.")} />
        </div>
        <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>Protege tus chats personales: un chat nuevo entra al CRM solo si su mensaje dice la palabra (por ejemplo, «Hola Kusi»).</p>
        <form style={{ display: "flex", gap: 8 }} onSubmit={(e) => { e.preventDefault(); accion({ accion: "filtro", activo: w.filtro.activo, palabra }, `Palabra clave: «${palabra}».`); }}>
          <input className="input" style={{ height: 36 }} value={palabra} onChange={(e) => setPalabra(e.target.value)} />
          <button className="btn btn-borde btn-sm">Guardar</button>
        </form>
      </div>
    </div>
  );
}

const ROLES = { admin: "Administradora", gerente: "Gerente comercial", ventas: "Ventas" };
const VACIO = { nombre: "", correo: "", clave: "", rol: "ventas", zona: "Lima", especialidad: "cocina", meta: 5000 };

export default function Configuracion() {
  const { yo } = useSesion();
  const [usuarios, setUsuarios] = useState(null);
  const [form, setForm] = useState(VACIO);
  const [reiniciando, setReiniciando] = useState(false);
  const [aviso, mostrar] = useAviso();
  const cargar = useCallback(() => api("/crm/usuarios").then((r) => setUsuarios(r.usuarios)).catch(() => {}), []);
  useEffect(() => { cargar(); }, [cargar]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function crear(e) {
    e.preventDefault();
    try { const u = await api("/crm/usuarios", { metodo: "POST", datos: form }); mostrar(`${u.nombre} ya puede entrar al CRM.`); setForm(VACIO); cargar(); }
    catch (err) { mostrar(err.message, true); }
  }
  async function cambiar(u, datos, texto) {
    try { await api(`/crm/usuarios/${u.id}`, { metodo: "PATCH", datos }); mostrar(texto); cargar(); }
    catch (err) { mostrar(err.message, true); }
  }
  async function reiniciar() {
    if (!confirm("Se borrarán todos los clientes, chats y cambios del catálogo y se volverán a crear los datos de demostración. Los usuarios se mantienen. ¿Continuar?")) return;
    setReiniciando(true);
    try { const r = await api("/crm/demo/reiniciar", { metodo: "POST", datos: {} }); mostrar(`Demo reiniciada: ${r.clientes} clientes y ${r.mensajes} mensajes.`); }
    catch (err) { mostrar(err.message, true); } finally { setReiniciando(false); }
  }

  return (
    <main className="main">
      {aviso}
      <Top sobre="Kusi Hogar S.A.C." titulo="Configuración" sub="Usuarios del CRM, roles y datos de demostración." />
      <div className="dos-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <ConexionWhatsapp mostrar={mostrar} />
          <form className="card" onSubmit={crear} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <h3>Nuevo usuario</h3>
            <label className="campo"><span>Nombre y apellido</span><input className="input" required value={form.nombre} onChange={set("nombre")} /></label>
            <label className="campo"><span>Correo</span><input className="input" type="email" required value={form.correo} onChange={set("correo")} /></label>
            <label className="campo"><span>Contraseña (mínimo 8)</span><input className="input" type="password" minLength={8} required value={form.clave} onChange={set("clave")} autoComplete="new-password" /></label>
            <div className="grid2">
              <label className="campo"><span>Rol</span><select className="input" value={form.rol} onChange={set("rol")}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
              <label className="campo"><span>Zona</span><select className="input" value={form.zona} onChange={set("zona")}><option>Lima</option><option>Provincia</option></select></label>
            </div>
            {form.rol === "ventas" && (
              <div className="grid2">
                <label className="campo"><span>Especialidad</span><select className="input" value={form.especialidad} onChange={set("especialidad")}><option value="cocina">Cocina</option><option value="menaje">Menaje</option><option value="hogar">Hogar</option></select></label>
                <label className="campo"><span>Meta mensual (S/)</span><input className="input" type="number" min="0" value={form.meta} onChange={set("meta")} /></label>
              </div>
            )}
            <button className="btn btn-verde btn-sm" style={{ alignSelf: "flex-start" }}><UserPlus />Crear usuario</button>
          </form>
          <div className="card-osc ilus-card" style={{ minHeight: 250 }}>
            <div className="luna" /><img className="ilus" src="/crm-img/respaldo.webp" alt="" />
            <div className="lbl" style={{ color: "#0EB155" }}>Datos de demostración</div>
            <h3 style={{ fontSize: 19, maxWidth: 210, margin: "6px 0" }}>Vuelve a dejar la demo como nueva</h3>
            <p className="muted" style={{ fontSize: 13, maxWidth: 190 }}>Recrea los clientes de Kusi Hogar con conversaciones que pasan por Kinti · IA.</p>
            <button className="btn btn-verde btn-sm" onClick={reiniciar} disabled={reiniciando} style={{ position: "relative" }}>{reiniciando ? <><LoaderCircle className="girar" />Recreando…</> : <><RotateCcw />Reiniciar demo</>}</button>
          </div>
        </div>
        <div className="card" style={{ padding: 10 }}>
          {!usuarios ? <div className="cargando"><LoaderCircle className="girar" /></div> : (
            <table className="tabla">
              <thead><tr><th>Usuario</th><th>Rol</th><th>Zona</th><th>Meta</th><th>Activo</th><th /></tr></thead>
              <tbody>{usuarios.map((u) => (
                <tr key={u.id}>
                  <td><div style={{ display: "flex", gap: 10, alignItems: "center" }}><span className="av" style={{ background: u.color }}>{u.iniciales}</span><div><b>{u.nombre}</b><div className="muted" style={{ fontSize: 12 }}>{u.correo}</div></div></div></td>
                  <td><select className="sel-vendedor" value={u.rol} disabled={u.id === yo.id} onChange={(e) => cambiar(u, { rol: e.target.value }, `${u.nombre} ahora es ${ROLES[e.target.value]}.`)}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
                  <td>{u.zona}{u.rol === "ventas" ? ` · ${u.especialidad}` : ""}</td>
                  <td className="tnum">{u.rol === "ventas" ? soles(u.meta) : "—"}</td>
                  <td><button className={`toggle ${u.activo ? "on" : ""}`} disabled={u.id === yo.id} onClick={() => cambiar(u, { activo: !u.activo }, u.activo ? `${u.nombre} ya no puede entrar.` : `${u.nombre} puede entrar de nuevo.`)} /></td>
                  <td><button className="btn btn-borde btn-xs" onClick={() => { const c = prompt(`Nueva contraseña para ${u.nombre} (mínimo 8 caracteres):`); if (c) cambiar(u, { clave: c }, "Contraseña cambiada."); }}><KeyRound />Clave</button></td>
                </tr>))}</tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}
