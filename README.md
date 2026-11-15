# SIRAC · Sistema Inteligente de Retroalimentación y Atención Comercial

Proyecto del curso **Innovación y Transformación Digital** (Universidad Tecnológica del Perú, 2026).
SIRAC atiende por WhatsApp con un asistente de IA (Kinti), deriva a los vendedores los clientes listos para comprar
y devuelve a Meta y a Google las ventas reales para que los anuncios aprendan a buscar compradores.

**En línea:** https://sirac.dbltech.tech · **API:** https://sirac.dbltech.tech/api/salud

> Los datos de la empresa Kusi Hogar S.A.C. son **simulados** (caso hipotético) y se generan con una semilla fija.

## Arquitectura

| Capa | Tecnología |
|---|---|
| Servidor (IaaS) | VPS Hostinger KVM 2 · Ubuntu 26.04 LTS · 2 vCPU · 8 GB RAM · 100 GB NVMe |
| Dominio y DNS | `sirac.dbltech.tech` con registros A (IPv4) y AAAA (IPv6) |
| HTTPS | Caddy 2 con certificado automático de Let's Encrypt |
| Back-end | Python 3.12 · Django 5.2 LTS · Gunicorn · PostgreSQL 17 |
| Front-end | Next.js 16 · React 19 |
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions: pruebas → compilación → despliegue por SSH con verificación de salud y rollback |
| Seguridad | Firewall UFW (22, 80, 443) · fail2ban · SSH solo con llaves · usuario de despliegue sin root |

```
Internet ─► Caddy (443, SSL) ─┬─► /api/* ─► Django + Gunicorn ─► PostgreSQL
                              └─► /*     ─► Next.js
```

## Inteligencia artificial

**Búsqueda (`backend/ia/busqueda.py`)**
- *BFS y DFS* sobre el flujo de conversación de Kinti: del saludo a «listo para pagar».
- *A\** para la ruta de delivery entre distritos de Lima (heurística: distancia en línea recta, admisible).
- *Hill climbing* para repartir clientes entre vendedores minimizando espera y penalidades.

**Machine learning (`backend/ia/ml/`)**
- Regresión **lineal, logarítmica y polinómica**: inversión diaria en anuncios → conversaciones.
- Regresión **logística**: probabilidad de que un cliente compre.

## Desarrollo local

```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
python -m ia.ml.entrenar && python manage.py migrate && python manage.py runserver
cd ../frontend && npm install && npm run dev   # http://localhost:3000
```

Pruebas: `cd backend && pytest -v`

## Equipo

López Lapa, Luis Alessandro · Lope Carbajal, Frank Carlos · Espinoza Flores, Yelina Lariza ·
Rivera López, Eduardo Alejandro Danilo · Condori Sotelo, Marlon Gerardo.
Docente: Orrego Granados, David Leandro.
