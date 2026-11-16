"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, CircleCheck, Eye, EyeOff, GraduationCap, LoaderCircle, Lock, Mail, MessageCircle, Timer } from "lucide-react";
import { api, guardarToken, token } from "./lib";

const DEMO = [
  { correo: "carla@kusihogar.pe", n: "Carla", r: "Administradora", i: "CM", c: "#1E2E4E" },
  { correo: "jorge@kusihogar.pe", n: "Jorge", r: "Gerente", i: "JS", c: "#0B6E85" },
  { correo: "diego@kusihogar.pe", n: "Diego", r: "Ventas", i: "DQ", c: "#0EB155" },
];

export default function Acceso() {
  const router = useRouter();
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [ver, setVer] = useState(false);
  const [recordar, setRecordar] = useState(true);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { if (token()) router.replace("/crm/dashboard"); }, [router]);

  async function entrar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      const r = await api("/crm/login", { metodo: "POST", datos: { correo, clave } });
      guardarToken(r.token, recordar);
      router.replace(r.usuario.rol === "ventas" ? "/crm/chats" : "/crm/dashboard");
    } catch (err) {
      setError(err.message);
      setEnviando(false);
    }
  }

  return (
    <div className="acceso">
      <section className="acceso-izq">
        <div className="cab">
          <img src="/marca/logo-sirac-noche.svg" alt="SIRAC" />
          <a className="volver" href="/"><ArrowLeft className="i16" />Volver al inicio</a>
        </div>
        <form className="acceso-form" onSubmit={entrar}>
          <div className="sobre">Acceso al panel</div>
          <h1>Hola de nuevo</h1>
          <p className="intro">Entra a tu panel para ver tus chats, tu embudo y todo lo que <b>Kinti · IA</b> avanzó por ti.</p>
          <label className="campo"><span>Correo</span>
            <div className="input input-ic"><Mail className="i18" />
              <input type="email" autoComplete="username" required value={correo} onChange={(e) => setCorreo(e.target.value)} placeholder="tu@empresa.pe" />
            </div>
          </label>
          <label className="campo"><span>Contraseña</span>
            <div className="input input-ic"><Lock className="i18" />
              <input type={ver ? "text" : "password"} autoComplete="current-password" required value={clave} onChange={(e) => setClave(e.target.value)} placeholder="Tu contraseña" />
              <button type="button" className="ver-clave" onClick={() => setVer(!ver)} title={ver ? "Ocultar" : "Mostrar"}>{ver ? <EyeOff className="i18" /> : <Eye className="i18" />}</button>
            </div>
          </label>
          <div className="recordar">
            <label><input type="checkbox" checked={recordar} onChange={(e) => setRecordar(e.target.checked)} />Mantener la sesión iniciada</label>
          </div>
          {error && <div className="error">{error}</div>}
          <button className="btn btn-verde btn-grande" disabled={enviando}>
            {enviando ? <LoaderCircle className="girar" /> : <>Iniciar sesión <ArrowRight /></>}
          </button>
          <div className="demo-cuentas">
            <span className="lbl">Cuentas de la demo · elige un rol</span>
            <div className="fila">
              {DEMO.map((d) => (
                <button type="button" key={d.correo} onClick={() => setCorreo(d.correo)}>
                  <span className="av av-sm" style={{ background: d.c, width: 28, height: 28 }}>{d.i}</span>{d.n} <small>{d.r}</small>
                </button>
              ))}
            </div>
          </div>
        </form>
        <div className="acceso-pie">
          <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}><GraduationCap className="i16" />Demo del proyecto SIRAC · UTP 2026</span>
          <a href="/whatsapp"><MessageCircle className="i14" style={{ verticalAlign: -2 }} /> Escribir como cliente</a>
        </div>
      </section>
      <section className="acceso-der">
        <div className="sello"><i />Datos de demostración · Kusi Hogar es ficticia</div>
        {[900, 1250, 1600].map((d) => <span key={d} className="orbita" style={{ width: d, height: d * 0.55, transform: "rotate(-24deg)" }} />)}
        <div style={{ position: "relative" }}>
          <div className="circulo"><img src="/crm-img/acceso.webp" alt="" /></div>
          <div className="flotante" style={{ left: -150, top: 20 }}>
            <span className="ic" style={{ background: "#EFEBFF", color: "#4B2FD0" }}><Timer className="i18" /></span>
            <div><span className="chip-kinti"><img src="/crm-img/kinti.webp" alt="" />Kinti · IA</span><div style={{ marginTop: 4 }}><b>Responde en segundos</b></div></div>
          </div>
          <div className="flotante" style={{ right: -170, bottom: 30 }}>
            <span className="ic" style={{ background: "#E2F7EB", color: "#0A7A3C" }}><CircleCheck className="i18" /></span>
            <div><small style={{ color: "#0A7A3C", fontWeight: 700 }}>Venta cerrada</small><div><b>Lucía · Aspiradora</b> <span className="muted">· S/ 467</span></div></div>
          </div>
        </div>
        <h2>Atiende, califica y deriva.</h2>
        <p>Kinti responde al instante, la IA calcula la probabilidad de compra y tu equipo cierra la venta. Tu equipo y tu IA, en un solo lugar.</p>
      </section>
    </div>
  );
}
