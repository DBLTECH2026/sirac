import "./crm.css";

export const metadata = {
  title: "SIRAC · CRM",
  description: "CRM de SIRAC: chats atendidos por Kinti · IA, embudo de ventas y dashboard (datos de demostración de una empresa ficticia).",
};

export default function LayoutCrm({ children }) {
  return <div className="crm">{children}</div>;
}
