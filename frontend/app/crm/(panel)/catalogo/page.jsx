"use client";
import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, Save, ShieldCheck, Star } from "lucide-react";
import { Top, useSesion } from "../../Marco";
import { api, soles, useAviso } from "../../lib";

function Producto({ p, editable, onGuardar }) {
  const [precio, setPrecio] = useState(p.precio);
  const [stock, setStock] = useState(p.stock);
  const cambio = Number(precio) !== p.precio || Number(stock) !== p.stock;
  return (
    <div className="prod-card">
      <img src={p.foto} alt={p.nombre} />
      <div className="c">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {p.mas_vendido && <span className="chip chip-ganado" style={{ height: 22 }}><Star className="i12" />Más vendido</span>}
          {p.stock === 0 ? <span className="chip chip-perdido" style={{ height: 22 }}><i className="pt" />Sin stock</span> : <span className="chip chip-nuevo" style={{ height: 22 }}>{p.stock} en stock</span>}
        </div>
        <b style={{ fontSize: 15 }}>{p.nombre}</b>
        <small className="muted">{p.detalle} · <ShieldCheck className="i12" style={{ verticalAlign: -2 }} /> {p.garantia_meses} meses de garantía</small>
        <div className="precio">{soles(p.precio)}</div>
        {editable && (
          <div className="edit">
            <label className="campo" style={{ flex: 1 }}><span>Precio</span><input type="number" min="1" value={precio} onChange={(e) => setPrecio(e.target.value)} /></label>
            <label className="campo" style={{ flex: 1 }}><span>Stock</span><input type="number" min="0" value={stock} onChange={(e) => setStock(e.target.value)} /></label>
          </div>
        )}
        {editable && cambio && <button className="btn btn-verde btn-sm" onClick={() => onGuardar(p.id, { precio: Number(precio), stock: Number(stock) })}><Save />Guardar</button>}
      </div>
    </div>
  );
}

export default function Catalogo() {
  const { yo } = useSesion();
  const [lista, setLista] = useState(null);
  const [aviso, mostrar] = useAviso();
  const editable = ["admin", "gerente"].includes(yo.rol);
  const cargar = useCallback(() => api("/crm/productos").then((r) => setLista(r.productos)).catch(() => {}), []);
  useEffect(() => { cargar(); }, [cargar]);
  async function guardar(id, datos) {
    try { const p = await api(`/crm/productos/${id}`, { metodo: "PATCH", datos }); mostrar(`${p.nombre} actualizado. Kinti ya cotiza con el precio nuevo.`); cargar(); }
    catch (e) { mostrar(e.message, true); }
  }
  return (
    <main className="main">
      {aviso}
      <Top sobre="Kusi Hogar" titulo="Catálogo" sub={editable ? "Precios y stock que Kinti usa para cotizar. Si cambias un precio, Kinti lo usa en el siguiente mensaje." : "Precios y stock vigentes para cotizar."} />
      {!lista ? <div className="cargando"><LoaderCircle className="girar" /></div> : (
        <div className="catalogo">{lista.map((p) => <Producto key={`${p.id}-${p.precio}-${p.stock}`} p={p} editable={editable} onGuardar={guardar} />)}</div>
      )}
    </main>
  );
}
