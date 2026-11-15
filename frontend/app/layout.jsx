import { Inter, Sora } from "next/font/google";
import "./globals.css";

const sora = Sora({ subsets: ["latin"], weight: ["600", "700", "800"], variable: "--f-titulo" });
const inter = Inter({ subsets: ["latin"], variable: "--f-texto" });

export const metadata = {
  title: "SIRAC · Sistema Inteligente de Retroalimentación y Atención Comercial",
  description: "Proyecto académico UTP: atención por WhatsApp con IA, búsqueda y machine learning sobre datos simulados.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es-PE" className={`${sora.variable} ${inter.variable}`}>
      <body>{children}</body>
    </html>
  );
}
