// Configuración Tailwind (Play CDN) — Sistema visual SIRAC v0.1
// Se carga ANTES de https://cdn.tailwindcss.com
window.tailwind = window.tailwind || {};
tailwind.config = {
  theme: {
    extend: {
      colors: {
        noche: { DEFAULT: '#0A1424', 2: '#14213A', 3: '#1E2E4E' },
        niebla: '#EEF3F8',
        verde: { DEFAULT: '#0EB155', osc: '#0A8A42', claro: '#E2F7EB', texto: '#0A7A3C' },
        violeta: { DEFAULT: '#7C5CFC', claro: '#EFEBFF', texto: '#4B2FD0' },
        celeste: { DEFAULT: '#16B6D8', claro: '#E3F7FB', texto: '#0B6E85' },
        tinta: { 2: '#6E819A', 3: '#9FB3CC' },
        borde: '#C8D8E8',
        linea: '#DCE5EF',
        aviso: { DEFAULT: '#B45309', claro: '#FFF4E5' },
        error: { DEFAULT: '#C3122F', claro: '#FDECEF' },
      },
      fontFamily: {
        sora: ['Sora', 'sans-serif'],
        inter: ['Inter', 'sans-serif'],
      },
      borderRadius: { card: '20px', xl2: '16px' },
      boxShadow: { card: '0 1px 2px rgba(10,20,36,.04), 0 1px 0 rgba(10,20,36,.02)' },
    },
  },
};
