// SIRAC · marco común de las vistas del CRM (barra lateral, cabecera y submenú de Configuración).
// Uso en cada vista:
//   <body data-rol="admin|gerente|ventas" data-activo="dashboard|chats|embudo|entrenamiento|catalogo|configuracion" data-sub="numeros|catalogo|empresa|usuarios|sistema">
//   <div class="app"><aside class="sb" id="sb"></aside><main class="main">
//     <div class="top" id="top" data-sobre="..." data-titulo="..." data-sub="..."> (acciones propias opcionales) </div>
//     ... contenido ...
//   Configuración: <div class="cfg"><nav class="cfg-menu" id="cfgmenu" data-k="..." data-t="..." data-d="..." data-img="ruta" data-barra="62"></nav><section style="flex:1;min-width:0">...</section></div>
(function () {
  const RAIZ = (document.currentScript && document.currentScript.src.replace(/js\/shell\.js.*$/, '')) || '../';
  const S = window.SIRAC = Object.assign({
    empresa: 'Kusi Hogar S.A.C.',         // empresa demo (inventada): importadora de electrohogar y menaje, Mesa Redonda
    agente: 'Kinti',                      // agente IA = colibrí "Kinti" (q'inti); SIEMPRE se muestra como "Kinti · IA"
    usuarios: {
      admin: { n: 'Carla Mendoza', r: 'Administradora', c: '#1E2E4E', i: 'CM' },
      gerente: { n: 'Jorge Salas', r: 'Gerente comercial', c: '#16B6D8', i: 'JS' },
      ventas: { n: 'Diego Quispe', r: 'Ventas · Lima', c: '#0EB155', i: 'DQ' },
    },
  }, window.SIRAC || {});

  const MENUS = {
    admin: [['dashboard', 'Dashboard', 'layout-dashboard'], ['chats', 'Chats', 'message-circle', 24], ['embudo', 'Embudo', 'filter'], ['entrenamiento', 'Entrenamiento', 'sparkles'], ['configuracion', 'Configuración', 'settings']],
    gerente: [['dashboard', 'Dashboard', 'layout-dashboard'], ['chats', 'Chats', 'message-circle', 24], ['embudo', 'Embudo', 'filter'], ['entrenamiento', 'Entrenamiento', 'sparkles'], ['configuracion', 'Configuración', 'settings']],
    ventas: [['dashboard', 'Mi dashboard', 'layout-dashboard'], ['chats', 'Mis chats', 'message-circle', 3], ['embudo', 'Mi embudo', 'filter'], ['catalogo', 'Catálogo', 'package']],
  };
  const SUB = [['numeros', 'Números de WhatsApp', 'smartphone'], ['catalogo', 'Catálogo', 'package'], ['empresa', 'Empresa', 'building-2'], ['usuarios', 'Usuarios', 'users'], ['sistema', 'Sistema', 'hard-drive']];

  function ic(n) { return `<i data-lucide="${n}"></i>`; }

  function sidebar() {
    const el = document.getElementById('sb'); if (!el) return;
    const rol = document.body.dataset.rol || 'admin';
    const act = document.body.dataset.activo || 'dashboard';
    const u = S.usuarios[rol] || S.usuarios.admin;
    el.innerHTML = `
      <div class="sb-logo"><img src="${RAIZ}assets/marca/logo-sirac-blanco.svg" alt="SIRAC"><span class="sb-colapsar">${ic('chevrons-left')}</span></div>
      <nav class="sb-nav">${MENUS[rol].map(([k, t, i, c]) => `<a class="sb-item${k === act ? ' activo' : ''}">${ic(i)}<span>${t}</span>${c ? `<span class="cnt">${c}</span>` : ''}</a>`).join('')}</nav>
      <div class="sb-demo"><i class="pt"></i>Datos de demostración · Kusi Hogar es ficticia</div>
      <div class="sb-patron" style="background-image:url('${RAIZ}assets/marca/patron-orbitas.svg')"></div>
      <div class="sb-user"><span class="av" style="background:${u.c}">${u.i}</span><div><div class="n">${u.n}</div><div class="r">${u.r}</div></div><span class="on"></span>${ic('log-out')}</div>`;
  }

  function cabecera() {
    const el = document.getElementById('top'); if (!el) return;
    const acciones = el.innerHTML;
    el.innerHTML = `
      <div><div class="sobre">${el.dataset.sobre || ''}</div><div class="titulo">${el.dataset.titulo || ''}</div>${el.dataset.sub ? `<div class="sub">${el.dataset.sub}</div>` : ''}</div>
      <div style="display:flex;align-items:center;gap:10px">${acciones}<div class="buscar">${ic('search')}<span>Buscar cliente, chat o producto…</span></div><span class="icono-btn">${ic('bell')}<span class="dot"></span></span></div>`;
  }

  function submenu() {
    const el = document.getElementById('cfgmenu'); if (!el) return;
    const sub = document.body.dataset.sub || 'numeros';
    const d = el.dataset;
    el.innerHTML = SUB.map(([k, t, i]) => `<a class="cfg-item${k === sub ? ' activo' : ''}">${ic(i)}<span>${t}</span></a>`).join('') + `
      <div class="cfg-card"><div class="luna"></div>${d.img ? `<img class="ilus" src="${RAIZ}${d.img}" data-asset alt="">` : ''}
        <div class="k">${d.k || ''}</div><div class="t">${d.t || ''}</div><div class="d">${d.d || ''}</div>${d.barra ? `<div class="barra${d.barraIa !== undefined ? ' ia' : ''}"><i style="width:${d.barra}%"></i></div>` : ''}</div>`;
  }

  function iconos() { if (window.lucide) window.lucide.createIcons({ attrs: { 'stroke-width': 1.8 } }); }

  // Imagen aún no generada → marcador limpio con su nombre (en vez del ícono roto)
  function marcadores() {
    document.querySelectorAll('img[data-asset]').forEach(img => {
      const poner = () => {
        const n = (img.getAttribute('src') || '').split('/').pop().replace(/\.(png|jpg|webp|svg)$/, '');
        const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300'><rect width='400' height='300' rx='18' fill='#E6EDF5'/><path d='M0 300 L400 0' stroke='#D5DFEA' stroke-width='2'/><text x='200' y='158' font-family='Inter,Arial' font-size='15' fill='#6E819A' text-anchor='middle'>${n}</text></svg>`;
        img.onerror = null; img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
      };
      if (img.complete && img.naturalWidth === 0) poner(); else img.addEventListener('error', poner, { once: true });
    });
  }

  document.addEventListener('DOMContentLoaded', () => { sidebar(); cabecera(); submenu(); iconos(); marcadores(); });
  window.SIRAC.iconos = iconos;
})();
