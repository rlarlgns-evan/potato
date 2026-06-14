/* VoyageAI — unified stroke icons (brand teal via currentColor) */
const VICO_SVG = {
  ai: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/><circle cx="12" cy="12" r="3.5"/></svg>`,
  spots: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 20h18"/><path d="M6 20l4-9 3 5 3-7 2 11"/></svg>`,
  festivals: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3v18"/><path d="M5 3c2.5-.8 4.5.8 7 0s4.5.8 7 0"/></svg>`,
  weather: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`,
  community: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h10a3 3 0 0 1 3 3v5a3 3 0 0 1-3 3h-3l-4 3v-3H7a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3z"/><path d="M9 11h.01M12 11h.01M15 11h.01"/></svg>`,
  planner: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v4M16 3v4M4 11h16"/></svg>`,
  trips: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5l-1-.85C5.5 15.2 3 12.8 3 9.5A4.5 4.5 0 0 1 12 6a4.5 4.5 0 0 1 9 3.5c0 3.3-2.5 5.7-8 10.15L12 20.5z"/></svg>`,
  profile: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>`,
  info: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 10v6M12 7h.01"/></svg>`,
  logout: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3"/><path d="M12 8l4 4-4 4M8 12h8"/></svg>`,
  login: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-3"/><path d="M12 8l-4 4 4 4M8 12h8"/></svg>`,
};

function initIcons() {
  document.querySelectorAll("[data-vico]").forEach((el) => {
    const name = el.dataset.vico;
    if (VICO_SVG[name]) el.innerHTML = VICO_SVG[name];
  });
}
