// VoyageAI · 강원 — GitHub Pages 정적 앱 로직
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const SOURCE_LABELS = {
  gemini: "✓ Gemini",
  openai: "✓ OpenAI",
  local_skip: "◆ 로컬 매칭 (API 절약)",
  local: "◆ 로컬 AI",
  local_api_fail: "◆ 로컬 (API 실패)",
  ai_required_fail: "✕ AI 필요 (실패)",
};
function sourceLabel(src) {
  return SOURCE_LABELS[src] || "◆ 로컬 AI";
}
function insightLabel(src) {
  return src === "gemini" || src === "openai" ? "✦ AI INSIGHT" : sourceLabel(src);
}

const AGENT_WELCOME =
  "✦ 안녕하세요! 강원도 여행의 무엇이든 물어보세요.\n" +
  "출발지·교통·일정·동행·테마를 알려주시면 맞춤 동선과 지도를 만들어 드릴게요.";

const state = {
  view: "explore",
  query: "",
  meta: { title: "", summary: "", duration: "", source: "" },
  steps: [],
  focusOrder: 1,
  mapEngine: "",
  map: null,
  chat: [],
  chatTyping: false,
  communityFilter: "all",
  pendingView: null,
};

function formatAgentText(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function renderAgentChat() {
  const box = $("agent-messages");
  if (!box) return;
  box.innerHTML = state.chat
    .map((m) =>
      m.role === "user"
        ? `<div class="bubble-user">${esc(m.text)}</div>`
        : `<div class="bubble-ai">${formatAgentText(m.text)}</div>`
    )
    .join("");
  if (state.chatTyping) {
    box.innerHTML +=
      '<div class="bubble-ai bubble-typing"><span></span><span></span><span></span></div>';
  }
  box.scrollTop = box.scrollHeight;
  const starters = $("agent-starters");
  if (starters) {
    starters.classList.toggle("hidden", state.chat.some((m) => m.role === "user"));
  }
}

function pillPromptAttr(prompt) {
  return encodeURIComponent(String(prompt ?? ""));
}

function ensureAgentWelcome() {
  if (!state.chat.length) {
    state.chat.push({ role: "assistant", text: AGENT_WELCOME });
  }
}

function buildAgentReply(result) {
  const lines = [
    `**${result.title}**`,
    result.summary,
    `${sourceLabel(result.source)} · ${result.steps.length}곳`,
  ];
  const names = result.steps.map((s) => s.spot.name).join(" → ");
  if (names) lines.push(names);
  const intent = result.tripIntent || {};
  if (intent.origin) lines.push(`출발: ${intent.origin}`);
  if (intent.transport) lines.push(`이동: ${intent.transport}`);
  if (result.accommodation?.area) {
    lines.push(`숙소: ${result.accommodation.area} ${result.accommodation.type || ""}`.trim());
  }
  lines.push("일정·지도 화면으로 이동합니다 →");
  return lines.join("\n");
}

function setAgentBusy(busy) {
  const btn = $("agent-send");
  const spin = $("agent-spin");
  const label = $("agent-send-label");
  if (!btn) return;
  btn.disabled = busy;
  if (spin) spin.style.display = busy ? "inline-block" : "none";
  if (label) label.style.display = busy ? "none" : "inline";
  const input = $("agent-input");
  if (input) input.disabled = busy;
}

function autoResizeAgentInput() {
  const el = $("agent-input");
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
}

function submitAgentPrompt(raw) {
  const prompt = String(raw ?? "").trim();
  if (!prompt) {
    toast("여행 조건을 입력해 주세요.");
    return;
  }
  const input = $("agent-input");
  if (input) {
    input.value = "";
    autoResizeAgentInput();
  }
  runCuration(prompt);
}

/* ==================== Toast ==================== */
let toastTimer = null;
function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

/* ==================== View routing ==================== */
function syncBodyMode(view) {
  document.body.classList.toggle("mode-landing", view === "explore");
  document.body.classList.toggle(
    "mode-planner",
    view === "planner" || view === "community" || view === "trips"
  );
}

function updateSidebar(view) {
  document.querySelectorAll(".side .sb-item[data-nav]").forEach((el) => {
    el.classList.toggle("on", el.dataset.nav === view);
  });
  document.querySelectorAll(".app-tab[data-nav]").forEach((el) => {
    el.classList.toggle("on", el.dataset.nav === view);
  });
}

function show(view) {
  if (view === "planner" && !state.steps.length && !isLoggedIn()) {
    toast("일정은 AI 코스를 먼저 만들거나, 로그인 후 저장함에서 열 수 있어요.");
    view = "explore";
  }
  if (view === "trips" && !isLoggedIn()) {
    toast("저장함은 로그인 후 이용할 수 있어요.");
    state.pendingView = "trips";
    openLoginModal();
    return;
  }
  state.pendingView = null;
  state.view = view;
  syncBodyMode(view);
  $("view-explore")?.classList.toggle("hidden", view !== "explore");
  $("view-planner")?.classList.toggle("hidden", view !== "planner");
  $("view-community")?.classList.toggle("hidden", view !== "community");
  $("view-trips")?.classList.toggle("hidden", view !== "trips");
  updateSidebar(view);

  if (view === "explore") {
    ensureAgentWelcome();
    renderAgentChat();
    $("agent-input")?.focus();
    initLandingMap();
    setTimeout(() => landingMap?.invalidateSize(), 80);
  } else if (view === "planner") {
    pauseLandingMap();
    if (state.steps.length) renderPlanner();
    else renderPlannerEmpty();
  } else if (view === "community") {
    pauseLandingMap();
    renderCommunity();
  } else if (view === "trips") {
    pauseLandingMap();
    renderTrips().catch((err) => console.warn("renderTrips:", err));
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.addEventListener("click", (e) => {
  const nav = e.target.closest("[data-nav]");
  if (nav) { e.preventDefault(); show(nav.dataset.nav); }

  const likeBtn = e.target.closest("[data-like-id]");
  if (likeBtn) {
    e.preventDefault();
    if (!canUseCommunity()) {
      toast("좋아요는 Google·카카오 로그인 후 이용할 수 있어요.");
      openLoginModal();
      return;
    }
    toggleCommunityLike(likeBtn.dataset.likeId);
    return;
  }

  const aiBtn = e.target.closest("[data-ai-prompt]");
  if (aiBtn) {
    e.preventDefault();
    const prompt = decodeURIComponent(aiBtn.dataset.aiPrompt || "");
    if (prompt) {
      show("explore");
      submitAgentPrompt(prompt);
    }
  }

  const filterBtn = e.target.closest("[data-community-filter]");
  if (filterBtn) {
    e.preventDefault();
    state.communityFilter = filterBtn.dataset.communityFilter || "all";
    renderCommunity();
    return;
  }

  const deleteBtn = e.target.closest("[data-delete-post]");
  if (deleteBtn) {
    e.preventDefault();
    deleteCommunityPost(deleteBtn.dataset.deletePost);
    return;
  }

  const openTripBtn = e.target.closest("[data-open-trip]");
  if (openTripBtn) {
    e.preventDefault();
    openSavedTrip(openTripBtn.dataset.openTrip);
    return;
  }

  const deleteTripBtn = e.target.closest("[data-delete-trip]");
  if (deleteTripBtn) {
    e.preventDefault();
    deleteSavedTrip(deleteTripBtn.dataset.deleteTrip);
  }
});

/* ==================== Weather (Open-Meteo) ==================== */
function wmoToCondition(code) {
  if (code === 0) return "sunny";
  if (code === 1 || code === 2) return "partly_cloudy";
  if (code === 3) return "cloudy";
  if (code === 45 || code === 48) return "fog";
  if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return "rain";
  if ([71, 73, 75, 77, 85, 86].includes(code)) return "snow";
  if ([95, 96, 99].includes(code)) return "thunder";
  return "cloudy";
}

function weatherTip(temp, cond, hi, lo) {
  const tips = [];
  if (hi != null && lo != null) {
    const diff = Math.round(hi - lo);
    if (diff >= 8) tips.push(`일교차 ${diff}°C · 겉옷을 챙기세요`);
    else if (diff >= 5) tips.push("일교차 있음 · 가벼운 겉옷 추천");
  }
  if (temp <= 3) tips.push("체감이 춥습니다 · 따뜻하게 입으세요");
  else if (temp >= 28) tips.push("더워요 · 수분·자외선 차단");
  if (cond === "rain") tips.push("우산을 챙기세요");
  else if (cond === "snow") tips.push("미끄럼 주의 · 방한 필수");
  else if (cond === "fog") tips.push("시야가 짧을 수 있어요 · 운전 주의");
  else if (cond === "thunder") tips.push("번개 가능 · 실외 활동 주의");
  else if ((cond === "sunny" || cond === "partly_cloudy") && temp >= 8 && temp <= 22)
    tips.push("산책·드라이브 좋은 날씨");
  if (!tips.length) tips.push("외출 전 현지 날씨를 확인하세요");
  return tips.slice(0, 2).join(" · ");
}

let wxCities = [];
let wxIdx = 0;
let wxTimer = null;

async function fetchCityWeather(c) {
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${c.lat}&longitude=${c.lng}` +
    `&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min` +
    `&timezone=Asia%2FSeoul&forecast_days=1`;
  const r = await fetch(url);
  if (!r.ok) throw new Error("weather http " + r.status);
  const d = await r.json();
  const temp = Math.round(d.current?.temperature_2m ?? 0);
  const cond = wmoToCondition(Number(d.current?.weather_code ?? 3));
  const hi = d.daily?.temperature_2m_max?.[0];
  const lo = d.daily?.temperature_2m_min?.[0];
  const meta = WEATHER_ICONS[cond];
  return {
    city: c.city, temp, cond,
    icon: meta.icon, bg: meta.bg, label: meta.label,
    range: hi != null && lo != null ? `${Math.round(lo)}° ~ ${Math.round(hi)}°` : "",
    tip: weatherTip(temp, cond, hi, lo),
  };
}

function renderWeatherAt(i) {
  const c = wxCities[i];
  if (!c) return;
  $("wx-body").innerHTML =
    `<div class="w-row">
       <div class="w-thumb" style="background:${c.bg}">${c.icon}</div>
       <div>
         <p class="w-city">${esc(c.city)}</p>
         <p class="w-temp">${c.temp}°C</p>
         <p class="w-meta">${esc(c.label)}${c.range ? " · " + esc(c.range) : ""}</p>
       </div>
     </div>
     <p class="sub">${esc(c.tip)}</p>`;
  $("wx-dots").innerHTML = wxCities
    .map((_, j) => `<i class="${j === i ? "on" : ""}" data-i="${j}" title="${esc(wxCities[j].city)}"></i>`)
    .join("");
  $("wx-dots").querySelectorAll("i").forEach((dot) => {
    dot.addEventListener("click", () => {
      wxIdx = Number(dot.dataset.i);
      renderWeatherAt(wxIdx);
      resetWxTimer();
    });
  });
}

function resetWxTimer() {
  clearInterval(wxTimer);
  wxTimer = setInterval(() => {
    wxIdx = (wxIdx + 1) % wxCities.length;
    renderWeatherAt(wxIdx);
  }, 3000);
}

async function initWeather() {
  $("wx-body").innerHTML = `<p class="sub">날씨 불러오는 중…</p>`;
  const results = await Promise.allSettled(GANGWON_CITIES.map(fetchCityWeather));
  wxCities = results.filter((r) => r.status === "fulfilled").map((r) => r.value);
  if (!wxCities.length) {
    $("wx-body").innerHTML = `<p class="sub">날씨를 불러오지 못했습니다.</p>`;
    return;
  }
  renderWeatherAt(0);
  resetWxTimer();
}

/* ==================== Festival marquee ==================== */
function initFestivals() {
  const grads = [
    "linear-gradient(135deg,#006a61,#66bcb0)",
    "linear-gradient(135deg,#38bdf8,#7dd3fc)",
    "linear-gradient(135deg,#a78bfa,#ddd6fe)",
    "linear-gradient(135deg,#fb923c,#fed7aa)",
  ];
  const rows = FESTIVALS.map(
    (f, i) =>
      `<div class="fest-row">
         <div class="fest-thumb" style="background:${grads[i % 4]}">${FESTIVAL_ICONS[i % FESTIVAL_ICONS.length]}</div>
         <div><strong>${esc(f.title)}</strong><span>${esc(f.place)} · ${esc(f.period)}</span>${f.desc ? `<span class="fest-desc">${esc(f.desc)}</span>` : ""}</div>
       </div>`
  ).join("");
  $("fest-tr").innerHTML = rows + rows;
}

/* ==================== Route math ==================== */
function haversineKm(a, b) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function parseDurationMin(text) {
  if (!text) return 0;
  const t = String(text).toLowerCase().replace(/\s+/g, " ");
  let m = t.match(/(\d+)\s*시간\s*(\d+)\s*분/);
  if (m) return Number(m[1]) * 60 + Number(m[2]);
  m = t.match(/(\d+)\s*h\s*(\d+)/);
  if (m) return Number(m[1]) * 60 + Number(m[2]);
  m = t.match(/(\d+)\s*시간/);
  if (m) return Number(m[1]) * 60;
  m = t.match(/(\d+)\s*h\b/);
  if (m) return Number(m[1]) * 60;
  m = t.match(/(\d+)\s*분/);
  if (m) return Number(m[1]);
  return 0;
}

function estDriveMin(km) {
  if (km <= 0) return 0;
  if (km < 2) return 15;
  if (km < 10) return Math.round(12 + km * 2.8);
  const speed = km > 80 ? 58 : km > 40 ? 50 : 45;
  return Math.round((km / speed) * 60);
}

function estTransitMin(km, note) {
  const parsed = parseDurationMin(note);
  if (parsed > 0) return parsed;
  if (km >= 150) return 150;
  if (km >= 100) return 120;
  if (km >= 60) return 90;
  return estDriveMin(km);
}

function legDriveMin(km, note, isTransit) {
  const parsed = parseDurationMin(note);
  if (parsed > 0) return parsed;
  return isTransit ? estTransitMin(km, note) : estDriveMin(km);
}

function fmtKm(km) {
  return km < 1 ? `${Math.round(km * 1000)}m` : `${km.toFixed(km < 10 ? 1 : 0)}km`;
}

function fmtMin(m) {
  if (m < 60) return `${m}분`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h}시간 ${r}분` : `${h}시간`;
}

function computeLegs(steps) {
  const legs = [];
  const routeSteps = destinationSteps(steps);
  for (let i = 0; i < routeSteps.length - 1; i++) {
    const from = routeSteps[i].spot;
    const to = routeSteps[i + 1].spot;
    const km = haversineKm(from, to);
    const note = routeSteps[i].move_to_next || "";
    const driveMin = legDriveMin(km, note, false);
    if (!note) {
      routeSteps[i].move_to_next = `${to.name}까지 ${fmtKm(km)} · 차량 약 ${fmtMin(driveMin)}`;
    }
    legs.push({
      from: routeSteps[i],
      to: routeSteps[i + 1],
      km,
      driveMin,
      note: routeSteps[i].move_to_next,
    });
  }
  const origin = steps.find((s) => s.kind === "origin");
  if (origin && routeSteps.length) {
    const outbound =
      origin.move_to_next ||
      state.meta?.transitPlan?.outbound ||
      "";
    const km = haversineKm(origin.spot, routeSteps[0].spot);
    const driveMin = legDriveMin(km, outbound, true);
    if (!origin.move_to_next) {
      origin.move_to_next = outbound || `대중교통 · ${fmtKm(km)} · 약 ${fmtMin(driveMin)}`;
    }
    legs.unshift({
      from: origin,
      to: routeSteps[0],
      km,
      driveMin,
      note: origin.move_to_next,
      transit: true,
    });
  }
  return legs;
}

function routeSummary(steps, legs) {
  const routeSteps = destinationSteps(steps);
  const driveKm = legs.reduce((a, l) => a + l.km, 0);
  const driveMin = legs.reduce((a, l) => a + (l.driveMin || 0), 0);
  const transitMin = legs.filter((l) => l.transit).reduce((a, l) => a + (l.driveMin || 0), 0);
  const stayMin = routeSteps.reduce((a, s) => a + (s.stay ?? s.spot.stay_min ?? 60), 0);
  return {
    stops: routeSteps.length,
    driveKm,
    driveMin,
    transitMin,
    stayMin,
    totalMin: driveMin + stayMin,
  };
}

const SPOT_BY_NAME = Object.fromEntries(ENRICHED_SPOTS.map((s) => [s.name, s]));
const MAX_SPOTS_IN_PROMPT = 12;
const GEMINI_MIN_GAP_MS = 8000;
const CACHE_STORAGE_KEY = "voyage_curation_v2";
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;
let lastGeminiAt = 0;

function normalizePromptKey(prompt) {
  return String(prompt).trim().replace(/\s+/g, " ").toLowerCase();
}

function loadPersistedCache() {
  try {
    const raw = localStorage.getItem(CACHE_STORAGE_KEY);
    if (!raw) return {};
    const data = JSON.parse(raw);
    const now = Date.now();
    const out = {};
    for (const [k, v] of Object.entries(data)) {
      if (v?.ts && now - v.ts < CACHE_TTL_MS && v.data) out[k] = v.data;
    }
    return out;
  } catch {
    return {};
  }
}

function persistCacheEntry(key, data) {
  try {
    const store = loadPersistedCache();
    store[key] = { ts: Date.now(), data };
    localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(store));
  } catch { /* quota */ }
}

function clearPersistedCache() {
  try { localStorage.removeItem(CACHE_STORAGE_KEY); } catch { /* ignore */ }
}

const curationCache = new Map(Object.entries(loadPersistedCache()));

function saveCurationCache(prompt, result) {
  const k = normalizePromptKey(prompt);
  curationCache.set(k, result);
  persistCacheEntry(k, result);
}

function scoreLocalMatch(prompt) {
  const kws = prompt.replace(/,/g, " ").split(/\s+/).filter((w) => w.length >= 2);
  if (!kws.length) return { topScore: 0, strongHits: 0, top3Sum: 0 };
  const scores = ENRICHED_SPOTS.map((s) => {
    const blob = `${s.name} ${s.region} ${s.theme} ${s.description}`;
    return kws.reduce((acc, kw) => acc + (blob.includes(kw) ? 1 : 0), 0);
  }).sort((a, b) => b - a);
  return {
    topScore: scores[0] || 0,
    strongHits: scores.filter((s) => s >= 2).length,
    top3Sum: scores.slice(0, 3).reduce((a, b) => a + b, 0),
  };
}

const COMPLEX_PROMPT_RE = [
  /1박\s*2일|2박\s*3일|3박\s*4일|당일치기|무박|숙박|\d+박/i,
  /대중교통|KTX|기차|버스|열차|지하철|SRT|ITX|무궁화|고속버스/i,
  /에서\s*출발|출발|\w+시\b|\w+구\b|경기|서울|인천|부산|대전|광주/i,
  /여자친구|남자친구|커플|아이와|가족|친구와|연인|부모님|애인/i,
  /숙소|호텔|펜션|게스트하우스|리조트|민박|잠을|숙박/i,
  /최적\s*경로|길찾|이동\s*경로|동선/i,
];

function needsComplexAi(prompt) {
  return COMPLEX_PROMPT_RE.some((re) => re.test(prompt));
}

function detectThemes(prompt) {
  const themes = [];
  if (/바다|해변|해수욕|서핑|일몰/.test(prompt)) themes.push("바다");
  if (/산|트레킹|설악|등산|단풍/.test(prompt)) themes.push("산");
  if (/온천|스파/.test(prompt)) themes.push("온천");
  if (/커피|카페/.test(prompt)) themes.push("커피");
  if (/여자친구|남자친구|커플|연인|데이트|로맨틱/.test(prompt)) themes.push("로맨틱");
  return themes;
}

function detectOrigin(prompt) {
  const origins = typeof TRANSIT_ORIGINS !== "undefined" ? TRANSIT_ORIGINS : {};
  for (const name of Object.keys(origins).sort((a, b) => b.length - a.length)) {
    const short = name.replace(/[시군구]/g, "");
    if (prompt.includes(name) || (short.length >= 2 && prompt.includes(short))) return name;
  }
  const m = prompt.match(/(\S+(?:시|구|군))/);
  return m ? m[1] : "";
}

function transitHintBlock(origin) {
  const origins = typeof TRANSIT_ORIGINS !== "undefined" ? TRANSIT_ORIGINS : {};
  const data = origin && origins[origin] ? origins[origin] : null;
  const list = data ? [[origin, data]] : Object.entries(origins).slice(0, 4);
  if (!list.length) return "";
  return list
    .map(([city, d]) => {
      const routes = (d.routes || [])
        .slice(0, 3)
        .map((r) => `→${r.dest} ${r.mode} ${r.via} (${r.note || ""})`)
        .join("; ");
      return `${city} hub=${d.hub || ""} ${routes}`;
    })
    .join("\n");
}

function buildTripHints(prompt) {
  const origin = detectOrigin(prompt);
  const themes = detectThemes(prompt);
  const lines = ["Parse user request into trip_intent JSON fields."];
  if (origin) lines.push(`Detected origin hint: ${origin}`);
  if (themes.length) lines.push(`Detected theme hints: ${themes.join(", ")}`);
  const ref = transitHintBlock(origin);
  if (ref) lines.push(ref);
  return lines.join("\n");
}

function resolveOriginEntry(originText) {
  const raw = String(originText || "").trim();
  if (!raw) return null;
  const origins = typeof TRANSIT_ORIGINS !== "undefined" ? TRANSIT_ORIGINS : {};
  if (origins[raw]) return { label: raw, data: origins[raw] };
  for (const name of Object.keys(origins).sort((a, b) => b.length - a.length)) {
    const short = name.replace(/[시군구]/g, "");
    if (raw.includes(name) || (short.length >= 2 && raw.includes(short))) {
      return { label: name, data: origins[name] };
    }
  }
  return null;
}

function pickOriginCoords(data, transport) {
  const t = String(transport || "");
  if (data.hub_lat != null && /KTX|기차|ITX|SRT|열차|지하철|버스|대중교통/i.test(t)) {
    return { lat: data.hub_lat, lng: data.hub_lng };
  }
  if (data.lat != null && data.lng != null) return { lat: data.lat, lng: data.lng };
  return null;
}

function buildOriginStep(label, data, transport, outbound) {
  const coords = pickOriginCoords(data, transport);
  if (!coords) return null;
  const hub = data.hub || "";
  return {
    order: 1,
    kind: "origin",
    day: 0,
    stay: 0,
    why: hub ? `출발 · ${hub}` : `출발 · ${label}`,
    move_to_next: outbound || "",
    spot: {
      name: `출발 · ${label}`,
      region: label,
      lat: coords.lat,
      lng: coords.lng,
      theme: "출발",
      description: hub || "여행 출발 지점",
      stay_min: 0,
      fee: "-",
      hours: "-",
      parking: "-",
      best_time: "-",
      tip: outbound || "강원 여행 출발 지점",
    },
  };
}

function pickOutboundHint(data) {
  const route = (data.routes || [])[0];
  if (!route) return "";
  const parts = [route.mode, route.via, route.note].filter(Boolean);
  return parts.join(" · ");
}

function attachOriginStep(steps, meta, prompt) {
  const originText = meta.tripIntent?.origin || detectOrigin(prompt || state.query || "");
  const hit = resolveOriginEntry(originText);
  if (!hit) return steps;
  const outbound = meta.transitPlan?.outbound || pickOutboundHint(hit.data);
  const origin = buildOriginStep(
    hit.label,
    hit.data,
    meta.tripIntent?.transport,
    outbound
  );
  if (!origin) return steps;
  return [origin, ...steps.map((s, i) => ({ ...s, order: i + 2 }))];
}

function destinationSteps(steps) {
  return steps.filter((s) => s.kind !== "origin");
}

function shouldCallGemini(prompt) {
  if (needsComplexAi(prompt)) return true;
  const { topScore, strongHits, top3Sum } = scoreLocalMatch(prompt);
  if (topScore >= 3) return false;
  if (topScore >= 2 && strongHits >= 2) return false;
  if (top3Sum >= 5) return false;
  return true;
}

function normalizeGeminiKey(raw) {
  let key = String(raw ?? "").trim();
  key = key.replace(/^value:\s*/i, "").trim();
  if (!key || key === "YOUR_GEMINI_API_KEY") return "";
  return key;
}

/** 서비스 제공자가 배포 시 주입한 Gemini 키 (config.js) */
function getGeminiKey() {
  return normalizeGeminiKey(
    typeof window !== "undefined" ? window.GEMINI_API_KEY : ""
  );
}

function geminiAvailable() {
  return Boolean(getGeminiKey());
}

function compactSpotCatalog(prompt) {
  const kws = prompt.replace(/,/g, " ").split(/\s+/).filter((w) => w.length >= 2);
  const themes = detectThemes(prompt);
  const themeKws = [...themes];
  if (themes.includes("바다")) themeKws.push("해변", "해수욕", "서핑", "바다");
  let pool = ENRICHED_SPOTS;
  if (kws.length || themeKws.length) {
    const ranked = ENRICHED_SPOTS.map((s) => {
      const blob = `${s.name} ${s.region} ${s.theme} ${s.description || ""}`;
      let score = kws.reduce((acc, kw) => acc + (blob.includes(kw) ? 1 : 0), 0);
      score += themeKws.reduce((acc, kw) => acc + (blob.includes(kw) ? 2 : 0), 0);
      return { score, s };
    }).sort((a, b) => b.score - a.score || a.s.name.localeCompare(b.s.name));
    const matched = ranked.filter((r) => r.score > 0).slice(0, MAX_SPOTS_IN_PROMPT).map((r) => r.s);
    pool = matched.length >= 6 ? matched : ranked.slice(0, MAX_SPOTS_IN_PROMPT).map((r) => r.s);
  } else {
    pool = ENRICHED_SPOTS.slice(0, MAX_SPOTS_IN_PROMPT);
  }
  return pool.map((s) => `${s.name}|${s.region}|${s.theme}`).join("\n");
}

function isBilling429(detail) {
  return /prepay|credit.*deplet|billing|purchase|payment|depleted/i.test(detail || "");
}

async function waitGeminiSlot() {
  const wait = GEMINI_MIN_GAP_MS - (Date.now() - lastGeminiAt);
  if (wait > 0) await new Promise((res) => setTimeout(res, wait));
  lastGeminiAt = Date.now();
}

function geminiFailToast(e) {
  const d = e.detail || e.message || "";
  if (e.status === 429) {
    if (isBilling429(d))
      toast("AI 서비스 사용량이 초과됐어요. 잠시 후 다시 시도해 주세요.");
    else
      toast("요청이 많아 잠시 기다려 주세요. (1~2분 후 재시도)");
    return;
  }
  if (e.status === 503 || /high demand|UNAVAILABLE/i.test(d))
    toast("AI 서버 혼잡 — 잠시 후 다시 시도해 주세요.");
  else if (e.status === 403)
    toast("API 키 제한(리퍼러) — Google AI Studio에서 github.io 도메인을 허용했는지 확인하세요.");
  else if (e.status === 400)
    toast("AI 요청 형식 오류 — 잠시 후 다시 시도해 주세요.");
  else if (/no spots matched/i.test(e.message || ""))
    toast("AI가 등록된 장소명과 맞지 않아요 — 다시 시도해 주세요.");
  else if (/empty response/i.test(e.message || ""))
    toast("AI 응답이 비었어요 — 잠시 후 다시 시도해 주세요.");
  else if (/invalid JSON|JSON/i.test(e.message || ""))
    toast("AI 응답 파싱 실패 — 다시 시도하거나 다른 질문을 입력하세요.");
  else
    toast("AI 호출 실패 — 잠시 후 다시 시도해 주세요.");
}

async function callGemini(body, key, retries = 1) {
  const primary = typeof GEMINI_MODEL !== "undefined" ? GEMINI_MODEL : "gemini-3.5-flash";
  const models = [...new Set([primary, "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash"])];
  let lastErr = null;
  for (const model of models) {
    const generationConfig = {
      temperature: 0.4,
      maxOutputTokens: 4096,
      responseMimeType: "application/json",
    };
    if (/gemini-3[\.\-]/i.test(model)) {
      generationConfig.thinkingConfig = { thinkingLevel: "MINIMAL" };
    }
    const reqBody = { ...body, generationConfig };
    const url =
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=` +
      encodeURIComponent(key);
    const isPrimary = model === primary;
    const maxAttempts = isPrimary ? Math.max(retries + 2, 3) : retries + 1;
    try {
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const r = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(reqBody),
        });
        if (r.ok) {
          if (model !== primary) console.warn("Gemini: primary unavailable, used fallback:", model);
          return r.json();
        }
        let detail = "";
        try {
          detail = (await r.json())?.error?.message || "";
        } catch (_) { /* ignore */ }
        if (r.status === 404 && attempt < maxAttempts - 1) {
          await new Promise((res) => setTimeout(res, 800 * (attempt + 1)));
          continue;
        }
        if (r.status === 503 && attempt < maxAttempts - 1) {
          await new Promise((res) => setTimeout(res, 2000 * (attempt + 1)));
          continue;
        }
        const e = new Error("Gemini HTTP " + r.status + (detail ? ": " + detail : ""));
        e.status = r.status;
        e.detail = detail;
        e.model = model;
        throw e;
      }
    } catch (e) {
      lastErr = e;
      const tryNextModel =
        e.status === 404 ||
        e.status === 503 ||
        /not found|not supported|invalid.*model|unavailable|high demand/i.test(
          String(e.detail || e.message || "")
        );
      if (tryNextModel && model !== models[models.length - 1]) continue;
      throw e;
    }
  }
  throw lastErr || new Error("Gemini call failed");
}

function extractGeminiText(candidate) {
  const parts = candidate?.content?.parts;
  if (!parts?.length) return "";
  const visible = parts.filter((p) => p.text && !p.thought).map((p) => p.text);
  if (visible.length) return visible.join("");
  return parts.map((p) => p.text || "").join("");
}

function parseJsonFromGemini(raw) {
  let text = String(raw ?? "").trim();
  if (!text) throw new Error("empty response from Gemini");
  text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```\s*$/i, "");
  try {
    return JSON.parse(text);
  } catch (first) {
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) throw new Error("invalid JSON from Gemini");
    try {
      return JSON.parse(match[0]);
    } catch (second) {
      throw new Error("invalid JSON from Gemini: " + second.message);
    }
  }
}

function resolveSpotByName(name) {
  const raw = String(name ?? "").trim();
  if (!raw) return null;
  if (SPOT_BY_NAME[raw]) return SPOT_BY_NAME[raw];
  const hit = ENRICHED_SPOTS.find(
    (s) => s.name.includes(raw) || raw.includes(s.name)
  );
  return hit || null;
}

function parseGeminiCuration(raw, prompt) {
  const parsed = parseJsonFromGemini(raw);
  const steps = (parsed.route_steps || [])
    .map((st, i) => {
      const spot = resolveSpotByName(st.spot_name);
      if (!spot) return null;
      return {
        order: i + 1,
        day: st.day || 1,
        spot,
        stay: st.stay_minutes ?? spot.stay_min ?? 60,
        why: (st.why || `${spot.description}. ${spot.tip}`).trim(),
        move_to_next: (st.move_to_next || "").trim(),
      };
    })
    .filter(Boolean);
  if (!steps.length) throw new Error("no spots matched");
  const legs = computeLegs(steps);
  const sum = routeSummary(steps, legs);
  return {
    title: parsed.itinerary_title || "AI 추천 코스",
    summary: parsed.summary || `총 ${fmtKm(sum.driveKm)} · 체류 ${fmtMin(sum.stayMin)} · 이동 ${fmtMin(sum.driveMin)} (추정)`,
    duration: parsed.total_duration || (sum.totalMin <= 300 ? "반나절 코스" : "당일 코스"),
    steps,
    source: "gemini",
    tripIntent: parsed.trip_intent || {},
    transitPlan: parsed.transit_plan || {},
    accommodation: parsed.accommodation || {},
    dayPlans: parsed.day_plans || [],
  };
}
function localCuration(prompt, source = "local") {
  const kws = prompt.replace(/,/g, " ").split(/\s+/).filter((w) => w.length >= 2);
  const ranked = ENRICHED_SPOTS.map((s) => {
    const blob = `${s.name} ${s.region} ${s.theme} ${s.description}`;
    const score = kws.reduce((acc, kw) => acc + (blob.includes(kw) ? 1 : 0), 0);
    return { score, s };
  }).sort((a, b) => b.score - a.score || a.s.region.localeCompare(b.s.region));
  const picks = ranked.slice(0, 3).map((r) => r.s);
  const steps = picks.map((s, i) => ({
    order: i + 1,
    spot: s,
    stay: s.stay_min,
    why: `${s.description}. ${s.tip}`,
  }));
  const legs = computeLegs(steps);
  const sum = routeSummary(steps, legs);
  return {
    title: "🥔 로컬 추천 코스",
    summary: `총 ${fmtKm(sum.driveKm)} · 체류 ${fmtMin(sum.stayMin)} · 이동 ${fmtMin(sum.driveMin)} (추정)`,
    duration: sum.totalMin <= 300 ? "반나절 코스" : "당일 코스",
    steps,
    source,
  };
}

/* ==================== Curation ==================== */
async function geminiCuration(prompt, key) {
  await waitGeminiSlot();
  const catalog = compactSpotCatalog(prompt);
  const hints = buildTripHints(prompt);
  const sys =
    "Gangwon trip JSON only.Korean brief.why≤80chars.\n" +
    "Extract trip_intent: origin,transport,duration,companion,themes. " +
    "Plan outbound transit,lodging,return when user asks.\n" +
    hints + "\n" +
    '{"trip_intent":{"origin":"","transport":"","duration":"","companion":"","themes":[]},' +
    '"transit_plan":{"outbound":"","return":"","local_transit":""},' +
    '"accommodation":{"area":"","type":"","note":""},' +
    '"itinerary_title":"","summary":"","total_duration":"",' +
    '"day_plans":[{"day":1,"title":"","focus":""}],' +
    '"route_steps":[{"order":1,"day":1,"spot_name":"","stay_minutes":60,"why":"","move_to_next":""}]}\n' +
    "1박2일=2-4 spots; spot_name exact from catalog; move_to_next=KTX/버스/환승 when transit:\n" +
    catalog;
  const body = {
    system_instruction: { parts: [{ text: sys }] },
    contents: [{ role: "user", parts: [{ text: prompt.slice(0, 600) }] }],
  };
  const d = await callGemini(body, key, 2);
  const c = d.candidates?.[0];
  const finish = c?.finishReason || "";
  const text = extractGeminiText(c);
  if (!text) {
    if (finish === "MAX_TOKENS")
      throw new Error("empty response from Gemini (token limit)");
    throw new Error("empty response from Gemini");
  }
  if (finish === "MAX_TOKENS")
    console.warn("Gemini finishReason=MAX_TOKENS — JSON may be truncated");
  return parseGeminiCuration(text, prompt);
}

function buildComplexFailReply(e) {
  const lines = [
    "**AI 일정을 만들지 못했어요**",
    "출발·교통·숙박·기간 조건이 포함된 질문은 AI가 필요합니다.",
  ];
  if (e?.status === 429) {
    lines.push("요청이 많거나 사용량 한도에 도달했을 수 있어요. 1~2분 후 다시 시도해 주세요.");
  } else if (e?.status === 503) {
    lines.push("Gemini 서버가 일시적으로 혼잡합니다. 1~2분 후 다시 시도해 주세요.");
  } else if (e?.status === 403) {
    lines.push(
      "API 키 HTTP 리퍼러 제한일 수 있어요. Google AI Studio → API 키 → " +
        "`https://rlarlgns-evan.github.io/*` 를 허용 목록에 추가해 주세요."
    );
  } else if (e?.status === 404) {
    lines.push("AI 모델을 찾지 못했어요. 잠시 후 다시 시도해 주세요.");
  } else if (e?.detail || e?.message) {
    console.warn("Gemini 상세:", e.detail || e.message);
    lines.push("잠시 후 다시 시도하거나, 조건을 나눠서 질문해 보세요.");
  } else {
    lines.push("잠시 후 다시 시도하거나, 조건을 나눠서 질문해 보세요.");
  }
  return lines.join("\n");
}

function pushAgentFailure(text) {
  state.chat.push({ role: "assistant", text });
  renderAgentChat();
}

function applyCurationResult(prompt, result) {
  state.chat.push({ role: "assistant", text: buildAgentReply(result) });
  renderAgentChat();
  state.query = prompt;
  state.meta = {
    title: result.title,
    summary: result.summary,
    duration: result.duration,
    source: result.source || "local",
    tripIntent: result.tripIntent || {},
    transitPlan: result.transitPlan || {},
    accommodation: result.accommodation || {},
    dayPlans: result.dayPlans || [],
  };
  state.steps = attachOriginStep(result.steps, state.meta, prompt);
  state.focusOrder = 1;
  resetMapState();
  setTimeout(() => {
    show("planner");
    renderPlanner();
  }, 500);
}

async function runCuration(prompt) {
  state.chat.push({ role: "user", text: prompt });
  state.chatTyping = true;
  renderAgentChat();
  setAgentBusy(true);
  try {
    const cacheKey = normalizePromptKey(prompt);
    const complex = needsComplexAi(prompt);
    const key = getGeminiKey();

    if (curationCache.has(cacheKey)) {
      applyCurationResult(prompt, curationCache.get(cacheKey));
      return;
    }

    if (!shouldCallGemini(prompt)) {
      const result = localCuration(prompt, "local_skip");
      saveCurationCache(prompt, result);
      applyCurationResult(prompt, result);
      return;
    }

    if (!key) {
      if (complex) {
        pushAgentFailure(
          "**AI 일정을 만들 수 없어요**\n" +
            "출발·교통·숙박·기간 조건은 AI 키가 필요합니다. 잠시 후 다시 시도해 주세요."
        );
        return;
      }
      const result = localCuration(prompt, "local");
      saveCurationCache(prompt, result);
      applyCurationResult(prompt, result);
      return;
    }

    try {
      const result = await geminiCuration(prompt, key);
      saveCurationCache(prompt, result);
      applyCurationResult(prompt, result);
    } catch (e) {
      console.warn("Gemini 실패:", e);
      geminiFailToast(e);
      if (complex) {
        pushAgentFailure(buildComplexFailReply(e));
        return;
      }
      const result = localCuration(prompt, "local_api_fail");
      saveCurationCache(prompt, result);
      applyCurationResult(prompt, result);
    }
  } finally {
    state.chatTyping = false;
    setAgentBusy(false);
    renderAgentChat();
  }
}

/* ==================== Planner render ==================== */
function courseCardHtml(step, active, src) {
  if (step.kind === "origin") {
    const s = step.spot;
    return `
<a class="course-card origin-card${active ? " on" : ""}" data-order="${step.order}">
  <div class="course-body" style="padding:1rem 1.1rem">
    <div class="course-top">
      <h3>${esc(s.name)}</h3>
      <span class="course-price">출발</span>
    </div>
    <p class="course-loc">📍 ${esc(s.region)} · ${esc(s.description)}</p>
    <div class="course-ai">
      <div class="ai-lbl">DEPARTURE</div>
      <p>${esc(step.move_to_next || step.why || "강원 여행 출발 지점")}</p>
    </div>
  </div>
</a>`;
  }
  const t = THEME_BADGE[step.spot.theme] || { label: "SPOT", cls: "badge-nature" };
  const img = THEME_IMAGE[step.spot.theme] || DEFAULT_IMAGE;
  const s = step.spot;
  return `
<a class="course-card${active ? " on" : ""}" data-order="${step.order}">
  <div class="ci-wrap">
    <img src="${img}" alt="" loading="lazy" />
    <span class="course-badge ${t.cls}">${t.label}</span>
    <span class="course-step">STEP ${String(step.order).padStart(2, "0")}</span>
  </div>
  <div class="course-body">
    <div class="course-top">
      <h3>${esc(s.name)}</h3>
      <span class="course-price">약 ${step.stay}분</span>
    </div>
    <p class="course-loc">📍 ${esc(s.region)} · ${esc(s.theme)}</p>
    <div class="course-meta">
      <span>🕐 ${esc(s.hours)}</span>
      <span>🅿️ ${esc(s.parking)}</span>
      <span>💰 ${esc(s.fee)}</span>
    </div>
    <div class="course-ai">
      <div class="ai-lbl">${esc(insightLabel(src))}</div>
      <p>${esc(step.why)}</p>
    </div>
  </div>
</a>`;
}

function legHtml(leg) {
  const note = leg.note || leg.from.move_to_next;
  const transit = leg.transit || /KTX|버스|열차|지하철|대중교통|역|터미널|환승/i.test(note || "");
  const icon = transit ? "🚆" : "🚗";
  const mins = leg.driveMin || parseDurationMin(note) || estDriveMin(leg.km);
  const text =
    note ||
    (transit
      ? `${leg.from.spot.name} → ${leg.to.spot.name} · 대중교통 약 ${fmtMin(mins)}`
      : `${leg.from.spot.name} → ${leg.to.spot.name} · ${fmtKm(leg.km)} · 약 ${fmtMin(mins)}`);
  return `<div class="course-leg${transit ? " transit-leg" : ""}">${icon} ${esc(text)}</div>`;
}

function renderRouteSummary() {
  const legs = computeLegs(state.steps);
  const sum = routeSummary(state.steps, legs);
  $("route-summary").innerHTML = `
    <div class="route-stat"><strong>${sum.stops}</strong><span>정거장</span></div>
    <div class="route-stat"><strong>${fmtKm(sum.driveKm)}</strong><span>총 이동</span></div>
    <div class="route-stat"><strong>${fmtMin(sum.driveMin)}</strong><span>이동 시간</span></div>
    <div class="route-stat"><strong>${fmtMin(sum.totalMin)}</strong><span>예상 소요</span></div>`;
  const routeLabel = sum.transitMin > 0
    ? `🚆 ${fmtMin(sum.transitMin)} + 🚗 ${fmtMin(sum.driveMin - sum.transitMin)}`
    : `🚗 ${fmtKm(sum.driveKm)}`;
  $("chip-route").textContent = `${routeLabel} · ${fmtMin(sum.totalMin)}`;
}

function spotMapUrl(spot) {
  return `https://map.kakao.com/link/map/${encodeURIComponent(spot.name)},${spot.lat},${spot.lng}`;
}

function renderSpotDetail() {
  const step = state.steps.find((s) => s.order === state.focusOrder);
  const el = $("spot-detail");
  if (!step) { el.innerHTML = ""; return; }
  const s = step.spot;
  if (step.kind === "origin") {
    el.innerHTML = `
    <div class="spot-detail-head">
      <span class="spot-step">STEP ${String(step.order).padStart(2, "0")}</span>
      <span class="spot-theme">출발</span>
    </div>
    <h3>${esc(s.name)}</h3>
    <p class="spot-region">📍 ${esc(s.region)} · ${esc(s.description)}</p>
    <div class="spot-grid">
      <div class="spot-fact"><b>좌표</b>${s.lat.toFixed(4)}, ${s.lng.toFixed(4)}</div>
    </div>
    ${step.move_to_next ? `<p class="spot-move">→ ${esc(step.move_to_next)}</p>` : ""}
    <div class="spot-tip"><b>DEPARTURE</b> ${esc(step.why)}</div>
    <div class="spot-actions">
      <a class="primary" href="${spotMapUrl(s)}" target="_blank" rel="noopener">🧭 출발지 열기</a>
    </div>`;
    return;
  }
  const move = step.move_to_next
    ? `<p class="spot-move">→ ${esc(step.move_to_next)}</p>`
    : `<p class="spot-move">🏁 마지막 정거장 · ${esc(s.region)} 일대</p>`;
  el.innerHTML = `
    <div class="spot-detail-head">
      <span class="spot-step">STEP ${String(step.order).padStart(2, "0")}</span>
      <span class="spot-theme">${esc(s.theme)}</span>
    </div>
    <h3>${esc(s.name)}</h3>
    <p class="spot-region">📍 ${esc(s.region)} · 체류 약 ${step.stay}분 · ${esc(s.best_time)} 추천</p>
    <div class="spot-grid">
      <div class="spot-fact"><b>운영</b>${esc(s.hours)}</div>
      <div class="spot-fact"><b>요금</b>${esc(s.fee)}</div>
      <div class="spot-fact"><b>주차</b>${esc(s.parking)}</div>
      <div class="spot-fact"><b>좌표</b>${s.lat.toFixed(4)}, ${s.lng.toFixed(4)}</div>
    </div>
    ${move}
    <div class="spot-tip"><b>TRAVEL TIP</b> ${esc(s.tip)}</div>
    <div class="course-ai" style="margin-top:0.65rem">
      <div class="ai-lbl">${esc(insightLabel(state.meta.source))}</div>
      <p>${esc(step.why)}</p>
    </div>
    <div class="spot-actions">
      <a class="primary" href="${spotMapUrl(s)}" target="_blank" rel="noopener">🧭 이 장소 열기</a>
      <a href="${kakaoRouteUrl(state.steps)}" target="_blank" rel="noopener">전체 경로</a>
    </div>`;
}

function renderCourses() {
  const legs = computeLegs(state.steps);
  const parts = [];
  state.steps.forEach((step, i) => {
    parts.push(courseCardHtml(step, step.order === state.focusOrder, state.meta.source));
    if (legs[i]) parts.push(legHtml(legs[i]));
  });
  $("courses").innerHTML = parts.join("");
  $("courses").querySelectorAll(".course-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      e.preventDefault();
      state.focusOrder = Number(card.dataset.order);
      $("courses").querySelectorAll(".course-card").forEach((c) =>
        c.classList.toggle("on", Number(c.dataset.order) === state.focusOrder));
      updateMapChrome();
      renderSpotDetail();
      renderMap();
    });
  });
}

function renderTripPlan(meta) {
  const el = $("trip-plan");
  if (!el) return;
  const intent = meta.tripIntent || {};
  const transit = meta.transitPlan || {};
  const lodge = meta.accommodation || {};
  const days = meta.dayPlans || [];
  const hasIntent = intent.origin || intent.transport || intent.duration || intent.companion || (intent.themes || []).length;
  const hasTransit = transit.outbound || transit.return || transit.local_transit;
  const hasLodge = lodge.area || lodge.type || lodge.note;
  if (!hasIntent && !hasTransit && !hasLodge && !days.length) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  el.classList.remove("hidden");
  let html = "";
  if (hasIntent) {
    const chips = [];
    if (intent.origin) chips.push(`<span><b>출발</b>${esc(intent.origin)}</span>`);
    if (intent.transport) chips.push(`<span><b>이동</b>${esc(intent.transport)}</span>`);
    if (intent.duration) chips.push(`<span><b>일정</b>${esc(intent.duration)}</span>`);
    if (intent.companion) chips.push(`<span><b>동행</b>${esc(intent.companion)}</span>`);
    if ((intent.themes || []).length) chips.push(`<span><b>테마</b>${esc(intent.themes.join(", "))}</span>`);
    html += `<div class="trip-row">${chips.join("")}</div>`;
  }
  if (hasTransit) {
    html += `<div class="trip-block"><b>🚆 이동 경로</b><ul>`;
    if (transit.outbound) html += `<li><b>가는 길</b> ${esc(transit.outbound)}</li>`;
    if (transit.local_transit) html += `<li><b>현지</b> ${esc(transit.local_transit)}</li>`;
    if (transit.return) html += `<li><b>오는 길</b> ${esc(transit.return)}</li>`;
    html += `</ul></div>`;
  }
  if (hasLodge) {
    html += `<div class="trip-block"><b>🏨 숙소</b> <span>${esc(lodge.area || "")} ${esc(lodge.type || "")}</span>`;
    if (lodge.note) html += `<p>${esc(lodge.note)}</p>`;
    html += `</div>`;
  }
  if (days.length) {
    html += `<div class="trip-block"><b>📅 일정</b><ul>`;
    days.forEach((d) => {
      html += `<li><b>Day ${d.day || ""}</b> ${esc(d.title || "")}${d.focus ? ` — ${esc(d.focus)}` : ""}</li>`;
    });
    html += `</ul></div>`;
  }
  el.innerHTML = html;
}

function renderPlanner() {
  $("btn-save-trip")?.classList.remove("hidden");
  mapNote("");
  const { meta, steps, query } = state;
  $("plan-title").textContent = meta.title || "맞춤 여행 코스";
  $("plan-summary").textContent = meta.summary || "";
  $("plan-query").textContent = query ? `🔍 ${query}` : "";
  $("chip-duration").textContent = `⏱ ${meta.duration || meta.tripIntent?.duration || "당일 코스"}`;
  $("chip-source").textContent = sourceLabel(meta.source);
  $("chip-stops").textContent =
    `${destinationSteps(steps).length}곳` + (steps.some((s) => s.kind === "origin") ? " + 출발" : "");
  renderTripPlan(meta);
  renderRouteSummary();
  renderCourses();
  $("kakao-link").href = kakaoRouteUrl(steps);
  updateMapChrome();
  renderSpotDetail();
  renderMap();
}

function renderPlannerEmpty() {
  $("plan-title").textContent = "내 여행 일정";
  $("plan-summary").textContent = "저장한 코스를 열거나, AI로 새 일정을 만들어 보세요.";
  $("plan-query").textContent = "";
  $("chip-duration").textContent = "⏱ —";
  $("chip-source").textContent = "◆ —";
  $("chip-stops").textContent = "0곳";
  $("chip-route").textContent = "";
  $("route-summary").innerHTML = "";
  $("trip-plan")?.classList.add("hidden");
  $("courses").innerHTML =
    `<div class="planner-empty">` +
    `<p>아직 표시할 일정이 없어요.</p>` +
    `<p class="planner-empty-hint">저장함에 담아 둔 코스를 열거나, AI 여행에서 새 코스를 만들어 보세요.</p>` +
    `<div class="planner-empty-actions">` +
    `<button type="button" class="btn-primary" data-nav="trips">♡ 저장함 보기</button>` +
    `<button type="button" class="btn-secondary" data-nav="explore">✦ AI 여행 시작</button>` +
    `</div></div>`;
  $("btn-save-trip")?.classList.add("hidden");
  $("spot-detail").innerHTML = "";
  $("map-q").textContent = "🔍 강원 여행";
  $("map-f").textContent = "📍 일정 없음";
  $("kakao-link").href = "#";
  mapNote("코스를 만들거나 저장함에서 열면 지도가 표시됩니다.");
}

function updateMapChrome() {
  const focus = state.steps.find((s) => s.order === state.focusOrder);
  const q = state.query.length > 36 ? state.query.slice(0, 36) + "…" : state.query;
  $("map-q").textContent = `🔍 ${q || "강원 추천 동선"}`;
  $("map-f").textContent = `📍 ${focus ? focus.spot.name : "정거장 선택"}`;
}

function kakaoRouteUrl(steps) {
  if (!steps.length) return "#";
  if (steps.length === 1) {
    const s = steps[0].spot;
    return `https://map.kakao.com/link/map/${encodeURIComponent(s.name)},${s.lat},${s.lng}`;
  }
  return "https://map.kakao.com/link/by/car/" +
    steps.map((st) => `${encodeURIComponent(st.spot.name)},${st.spot.lat},${st.spot.lng}`).join("/");
}

/* ==================== Map: Kakao primary, Leaflet fallback ==================== */
function pinDiv(label, focused, isOrigin) {
  return `<div class="order-pin${isOrigin ? " origin" : ""}${focused ? " focus" : ""}">${label || ""}</div>`;
}

function popupHtml(step) {
  const s = step.spot;
  const meta =
    step.kind === "origin"
      ? `${esc(s.region)} · 출발지`
      : `${esc(s.region)} · ${esc(s.theme)} · 약 ${step.stay}분`;
  return `<div style="min-width:200px;line-height:1.55;font-size:13px;font-family:Pretendard,sans-serif;padding:2px;">
    <strong style="color:#171d1c;">${step.order}. ${esc(s.name)}</strong><br/>
    <span style="color:#3e4947;">${meta}</span><br/>
    ${step.kind === "origin" ? "" : `<span style="color:#3e4947;">🕐 ${esc(s.hours)} · 💰 ${esc(s.fee)}</span><br/>`}
    <span style="color:#3e4947;">${esc(step.why)}</span></div>`;
}

function centerOf(steps) {
  if (!steps.length) return [37.8228, 128.1555];
  const lat = steps.reduce((a, s) => a + s.spot.lat, 0) / steps.length;
  const lng = steps.reduce((a, s) => a + s.spot.lng, 0) / steps.length;
  return [lat, lng];
}

function drawMapRoutes(mapEngine, map, steps) {
  const origin = steps.find((s) => s.kind === "origin");
  const destSteps = destinationSteps(steps);
  if (mapEngine === "kakao") {
    if (origin && destSteps.length) {
      const transitPath = [
        new kakao.maps.LatLng(origin.spot.lat, origin.spot.lng),
        new kakao.maps.LatLng(destSteps[0].spot.lat, destSteps[0].spot.lng),
      ];
      new kakao.maps.Polyline({
        path: transitPath,
        strokeWeight: 3,
        strokeColor: "#64748b",
        strokeOpacity: 0.55,
        strokeStyle: "shortdot",
      }).setMap(map);
    }
    if (destSteps.length > 1) {
      const path = destSteps.map((st) => new kakao.maps.LatLng(st.spot.lat, st.spot.lng));
      new kakao.maps.Polyline({
        path,
        strokeWeight: 4,
        strokeColor: "#006a61",
        strokeOpacity: 0.85,
        strokeStyle: "shortdash",
      }).setMap(map);
    }
    return;
  }
  if (mapEngine === "leaflet") {
    if (origin && destSteps.length) {
      L.polyline(
        [
          [origin.spot.lat, origin.spot.lng],
          [destSteps[0].spot.lat, destSteps[0].spot.lng],
        ],
        { color: "#64748b", weight: 3, opacity: 0.55, dashArray: "2 10", lineCap: "round" }
      ).addTo(map);
    }
    if (destSteps.length > 1) {
      const path = destSteps.map((st) => [st.spot.lat, st.spot.lng]);
      L.polyline(path, {
        color: "#006a61",
        weight: 4,
        opacity: 0.85,
        dashArray: "1 8",
        lineCap: "round",
      }).addTo(map);
    }
  }
}

function normalizeKakaoKey(raw) {
  let key = String(raw ?? "").trim();
  if (!key || key === "YOUR_KAKAO_JAVASCRIPT_KEY") return "";
  // GitHub Secrets UI에서 "Value: xxx" 형태로 복사된 경우 대비
  key = key.replace(/^value:\s*/i, "").trim();
  return key;
}

function kakaoKey() {
  return normalizeKakaoKey(typeof window !== "undefined" ? window.KAKAO_JS_KEY : "");
}

function resetMapState() {
  state.mapEngine = "";
  state.map = null;
  mapBooting = false;
  mapNote("");
}

function mapNote(msg) {
  const el = $("map-note");
  if (!el) return;
  if (!msg) { el.classList.add("hidden"); return; }
  el.innerHTML = msg;
  el.classList.remove("hidden");
}

let mapBooting = false;

function renderMap() {
  if (!state.steps.length) return;
  if (state.mapEngine === "kakao") renderKakao();
  else if (state.mapEngine === "leaflet") renderLeaflet();
  else bootMapEngine();
}

function bootMapEngine() {
  if (mapBooting) return;
  mapBooting = true;
  const key = kakaoKey();
  if (!key) {
    loadLeaflet("카카오 키가 설정되지 않아 OSM 지도로 표시 중입니다.");
    return;
  }
  let settled = false;
  const fail = (why) => {
    if (settled) return;
    settled = true;
    loadLeaflet(
      "카카오맵 인증 실패(" + why + ") — OSM 지도로 대체했습니다.<br/>" +
      "Kakao Developers → 내 애플리케이션 → 플랫폼 Web에 <b>" +
      esc(location.origin) + "</b> 등록 후 새로고침하세요."
    );
  };
  const timer = setTimeout(() => fail("응답 시간 초과 · 도메인 미등록 가능성"), 4500);
  const sdk = document.createElement("script");
  sdk.src = "https://dapi.kakao.com/v2/maps/sdk.js?appkey=" + encodeURIComponent(key) + "&autoload=false";
  sdk.onload = () => {
    try {
      kakao.maps.load(() => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        state.mapEngine = "kakao";
        mapNote("");
        renderKakao();
      });
    } catch (e) { clearTimeout(timer); fail("SDK 오류"); }
  };
  sdk.onerror = () => { clearTimeout(timer); fail("스크립트 차단 · 키 오류"); };
  document.head.appendChild(sdk);
}

function loadLeaflet(noteMsg) {
  state.mapEngine = "leaflet";
  if (noteMsg) mapNote(noteMsg);
  if (typeof L !== "undefined") { renderLeaflet(); return; }
  const s = document.createElement("script");
  s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  s.onload = renderLeaflet;
  document.head.appendChild(s);
}

function relayoutKakaoMap(map) {
  if (!map || typeof map.relayout !== "function") return;
  map.relayout();
  requestAnimationFrame(() => map.relayout());
  setTimeout(() => map.relayout(), 150);
  setTimeout(() => map.relayout(), 600);
}

function renderKakao() {
  const el = $("map");
  el.innerHTML = "";
  const [clat, clng] = centerOf(state.steps);
  const map = new kakao.maps.Map(el, { center: new kakao.maps.LatLng(clat, clng), level: 8 });
  state.map = map;
  map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.LEFT);

  const bounds = new kakao.maps.LatLngBounds();
  let openIw = null;
  let focusStep = null;

  state.steps.forEach((step) => {
    const pos = new kakao.maps.LatLng(step.spot.lat, step.spot.lng);
    bounds.extend(pos);
    const focused = step.order === state.focusOrder;
    if (focused) focusStep = step;

    const dom = document.createElement("div");
    dom.innerHTML = pinDiv(step.order, focused, step.kind === "origin");
    new kakao.maps.CustomOverlay({ position: pos, content: dom, yAnchor: 0.5, xAnchor: 0.5, zIndex: focused ? 10 : 1 }).setMap(map);

    const iw = new kakao.maps.InfoWindow({
      position: pos, removable: true,
      content: `<div style="padding:8px 10px;">${popupHtml(step)}</div>`,
    });
    dom.style.cursor = "pointer";
    dom.addEventListener("click", () => {
      if (openIw) openIw.close();
      iw.open(map);
      openIw = iw;
    });
    if (focused) { iw.open(map); openIw = iw; }
  });

  drawMapRoutes("kakao", map, state.steps);

  if (focusStep) {
    map.setCenter(new kakao.maps.LatLng(focusStep.spot.lat, focusStep.spot.lng));
    map.setLevel(6);
  } else if (state.steps.length > 1) {
    map.setBounds(bounds);
  }
  relayoutKakaoMap(map);
}

function renderLeaflet() {
  const el = $("map");
  if (state.map) { state.map.remove(); state.map = null; }
  el.innerHTML = "";
  const [clat, clng] = centerOf(state.steps);
  const map = L.map(el).setView([clat, clng], 9);
  state.map = map;
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 19, attribution: "© OpenStreetMap © CARTO", subdomains: "abcd",
  }).addTo(map);

  const latlngs = [];
  let focusLl = null;
  state.steps.forEach((step) => {
    const ll = [step.spot.lat, step.spot.lng];
    latlngs.push(ll);
    const focused = step.order === state.focusOrder;
    const icon = L.divIcon({
      html: pinDiv(step.order, focused, step.kind === "origin"), className: "",
      iconSize: focused ? [34, 34] : [28, 28], iconAnchor: focused ? [17, 17] : [14, 14],
    });
    const m = L.marker(ll, { icon }).addTo(map).bindPopup(popupHtml(step));
    if (focused) { focusLl = ll; m.openPopup(); }
  });
  drawMapRoutes("leaflet", map, state.steps);
  if (focusLl) map.setView(focusLl, 12);
  else if (latlngs.length > 1) map.fitBounds(latlngs, { padding: [44, 44] });
  setTimeout(() => map.invalidateSize(), 150);
}

/* ==================== Misc interactions ==================== */
$("agent-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  submitAgentPrompt($("agent-input")?.value);
});

$("agent-input")?.addEventListener("input", autoResizeAgentInput);
$("agent-input")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("agent-form")?.requestSubmit();
  }
});

/* ==================== Landing map (interactive background) ==================== */
let landingMap = null;
let landingMarkers = [];
let landingBooting = false;

function gangwonBounds() {
  const lats = ENRICHED_SPOTS.map((s) => s.lat);
  const lngs = ENRICHED_SPOTS.map((s) => s.lng);
  return [
    [Math.min(...lats) - 0.08, Math.min(...lngs) - 0.12],
    [Math.max(...lats) + 0.08, Math.max(...lngs) + 0.12],
  ];
}

function landingPopupHtml(spot) {
  return (
    `<strong>${esc(spot.name)}</strong><br>` +
    `<span style="color:#3e4947">${esc(spot.region)} · ${esc(spot.theme)}</span><br>` +
    `<button type="button" class="landing-popup-btn" data-spot="${esc(spot.name)}">이곳 포함해서 추천 →</button>`
  );
}

function focusLandingSpot(spot) {
  landingMarkers.forEach(({ spot: s, marker, el }) => {
    const on = s.name === spot.name;
    if (el) el.classList.toggle("on", on);
    if (on && landingMap) landingMap.panTo([spot.lat, spot.lng], { animate: true, duration: 0.6 });
  });
}

function buildLandingMap() {
  const el = $("landing-map");
  if (!el || landingMap) return;
  landingMap = L.map(el, {
    zoomControl: false,
    attributionControl: true,
    scrollWheelZoom: true,
    dragging: true,
    touchZoom: true,
  });
  L.control.zoom({ position: "bottomright" }).addTo(landingMap);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 14,
    minZoom: 7,
    attribution: "© OpenStreetMap © CARTO",
    subdomains: "abcd",
  }).addTo(landingMap);
  landingMap.fitBounds(gangwonBounds(), { padding: [40, 40] });

  ENRICHED_SPOTS.forEach((spot) => {
    const icon = L.divIcon({
      className: "",
      html: '<div class="landing-spot-dot"></div>',
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
    const marker = L.marker([spot.lat, spot.lng], { icon }).addTo(landingMap);
    marker.bindPopup(landingPopupHtml(spot), { maxWidth: 240 });
    const dotEl = marker.getElement()?.querySelector(".landing-spot-dot");
    marker.on("mouseover", () => focusLandingSpot(spot));
    marker.on("mouseout", () => {
      if (dotEl) dotEl.classList.remove("on");
    });
    marker.on("popupopen", () => {
      focusLandingSpot(spot);
      const btn = marker.getPopup()?.getElement()?.querySelector(".landing-popup-btn");
      btn?.addEventListener("click", () => {
        const input = $("agent-input");
        if (input) {
          input.value = `${spot.name} 포함 강원 여행 코스 추천해줘`;
          autoResizeAgentInput();
          input.focus();
        }
        landingMap.closePopup();
      });
    });
    landingMarkers.push({ spot, marker, el: dotEl });
  });

  landingMap.on("click", () => landingMap.closePopup());
  setTimeout(() => landingMap?.invalidateSize(), 100);
  setTimeout(() => landingMap?.invalidateSize(), 500);
}

function initLandingMap() {
  if (landingMap || landingBooting) return;
  const el = $("landing-map");
  if (!el) return;
  if (typeof L !== "undefined") {
    buildLandingMap();
    return;
  }
  landingBooting = true;
  const s = document.createElement("script");
  s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  s.onload = () => {
    landingBooting = false;
    buildLandingMap();
  };
  document.head.appendChild(s);
}

function pauseLandingMap() {
  if (!landingMap) return;
  landingMap.closePopup();
}

function resetLandingMap() {
  if (landingMap) {
    landingMap.remove();
    landingMap = null;
  }
  landingMarkers = [];
}

$("btn-logout")?.addEventListener("click", (e) => {
  e.preventDefault();
  resetSession();
});

$("btn-logout-community")?.addEventListener("click", (e) => {
  e.preventDefault();
  resetSession();
});

function resetSession() {
  state.steps = [];
  state.query = "";
  state.chat = [];
  state.chatTyping = false;
  resetMapState();
  resetLandingMap();
  ensureAgentWelcome();
  renderAgentChat();
  show("explore");
  toast("처음 화면으로 돌아왔어요.");
}

/* ==================== Community ==================== */
const COMMUNITY_FILTERS = [
  { id: "all", label: "전체" },
  { id: "review", label: "후기" },
  { id: "question", label: "질문" },
  { id: "tip", label: "팁" },
];

const COMMUNITY_TYPE_LABELS = { review: "후기", question: "질문", tip: "팁" };

const COMMUNITY_SEED = [];

const COMMUNITY_LS = {
  likes: "voyageai_community_likes",
  posts: "voyageai_community_posts",
  nick: "voyageai_community_nick",
};

function loadCommunityLikes() {
  try {
    const raw = localStorage.getItem(COMMUNITY_LS.likes);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function saveCommunityLikes(set) {
  localStorage.setItem(COMMUNITY_LS.likes, JSON.stringify([...set]));
}

function loadUserCommunityPosts() {
  try {
    const raw = localStorage.getItem(COMMUNITY_LS.posts);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveUserCommunityPosts(posts) {
  localStorage.setItem(COMMUNITY_LS.posts, JSON.stringify(posts.slice(0, 30)));
}

function communityNick() {
  const auth = loadAuth();
  const el = $("community-nick");
  if (auth.loggedIn && auth.name) {
    if (el) el.value = auth.name;
    return auth.name;
  }
  const saved = localStorage.getItem(COMMUNITY_LS.nick) || "";
  if (el && !el.value && saved) el.value = saved;
  return String(el?.value || saved || "여행러").trim().slice(0, 12) || "여행러";
}

function allCommunityPosts() {
  const userPosts = loadUserCommunityPosts().map((p) => ({
    ...p,
    isUser: true,
    likes: p.likes ?? 0,
  }));
  return [...userPosts, ...COMMUNITY_SEED];
}

function communityLikeCount(post, liked) {
  const base = post.likes ?? 0;
  return base + (liked.has(post.id) ? 1 : 0);
}

function isOAuthProvider(provider) {
  return provider === "kakao" || provider === "google";
}

function canUseCommunity() {
  const auth = loadAuth();
  return Boolean(auth.loggedIn && isOAuthProvider(auth.provider));
}

function toggleCommunityLike(id) {
  if (!canUseCommunity()) {
    toast("좋아요는 Google·카카오 로그인 후 이용할 수 있어요.");
    openLoginModal();
    return;
  }
  const liked = loadCommunityLikes();
  if (liked.has(id)) liked.delete(id);
  else liked.add(id);
  saveCommunityLikes(liked);
  renderCommunity();
}

function deleteCommunityPost(id) {
  if (!canUseCommunity()) {
    toast("Google·카카오 로그인 후 삭제할 수 있어요.");
    openLoginModal();
    return;
  }
  if (!id || !String(id).startsWith("user-")) return;
  const posts = loadUserCommunityPosts();
  if (!posts.some((p) => p.id === id)) {
    toast("삭제할 수 없는 글이에요.");
    return;
  }
  if (!confirm("내가 작성한 글을 삭제할까요?")) return;
  saveUserCommunityPosts(posts.filter((p) => p.id !== id));
  const liked = loadCommunityLikes();
  if (liked.has(id)) {
    liked.delete(id);
    saveCommunityLikes(liked);
  }
  toast("글이 삭제되었어요.");
  renderCommunity();
}

function renderCommunityFilters() {
  const el = $("community-filters");
  if (!el) return;
  el.innerHTML = COMMUNITY_FILTERS.map(
    (f) =>
      `<button type="button" class="community-filter${state.communityFilter === f.id ? " on" : ""}" data-community-filter="${f.id}" role="tab" aria-selected="${state.communityFilter === f.id}">${esc(f.label)}</button>`
  ).join("");
}

function renderCommunityFeed() {
  const feed = $("community-feed");
  if (!feed) return;
  const liked = loadCommunityLikes();
  const filter = state.communityFilter;
  const posts = allCommunityPosts().filter((p) => filter === "all" || p.type === filter);

  if (!posts.length) {
    feed.innerHTML = `<p class="community-empty">아직 글이 없어요. 첫 번째 이야기를 남겨 보세요!</p>`;
    return;
  }

  feed.innerHTML = posts
    .map((p) => {
      const typeLabel = COMMUNITY_TYPE_LABELS[p.type] || "글";
      const likeCount = communityLikeCount(p, liked);
      const likedOn = liked.has(p.id);
      const tags = (p.tags || [])
        .map((t) => `<span class="community-tag">${esc(t)}</span>`)
        .join("");
      const aiPrompt = pillPromptAttr(p.aiPrompt || p.body || p.title);
      const title = p.title ? `<h3>${esc(p.title)}</h3>` : "";
      const deleteBtn = p.isUser && canUseCommunity()
        ? `<button type="button" class="community-delete" data-delete-post="${esc(p.id)}" aria-label="내 글 삭제">삭제</button>`
        : "";
      const likeControl = canUseCommunity()
        ? `<button type="button" class="community-like${likedOn ? " on" : ""}" data-like-id="${esc(p.id)}" aria-pressed="${likedOn}">♡ ${likeCount}</button>`
        : `<span class="community-like readonly" aria-hidden="true">♡ ${likeCount}</span>`;
      return (
        `<article class="community-card${p.isUser ? " user" : ""}">` +
        `<div class="community-card-thumb" style="background:${p.grad || "linear-gradient(135deg,#006a61,#66bcb0)"}"></div>` +
        `<div class="community-card-body">` +
        `<div class="community-card-meta">` +
        `<span class="community-type type-${esc(p.type)}">${esc(typeLabel)}</span>` +
        `<span>${esc(p.author)} · ${esc(p.region || "강원")}</span>` +
        (p.isUser ? `<span class="community-mine">내 글</span>` : "") +
        `<span class="community-ago">${esc(p.ago || "방금")}</span>` +
        deleteBtn +
        `</div>` +
        title +
        `<p class="community-text">${esc(p.body)}</p>` +
        (tags ? `<div class="community-tags">${tags}</div>` : "") +
        `<div class="community-actions">` +
        likeControl +
        (p.aiPrompt
          ? `<button type="button" class="community-ai" data-ai-prompt="${aiPrompt}">✦ AI 코스 만들기</button>`
          : "") +
        `</div></div></article>`
      );
    })
    .join("");
}

function renderCommunityCompose() {
  const form = $("community-form");
  const locked = $("community-compose-locked");
  const canPost = canUseCommunity();
  form?.classList.toggle("hidden", !canPost);
  locked?.classList.toggle("hidden", canPost);
  if (canPost) communityNick();
}

function renderCommunity() {
  renderCommunityCompose();
  renderCommunityFilters();
  renderCommunityFeed();
}

function submitCommunityPost(e) {
  e.preventDefault();
  if (!canUseCommunity()) {
    toast("글쓰기는 Google·카카오 로그인 후 이용할 수 있어요.");
    openLoginModal();
    return;
  }
  const input = $("community-input");
  const text = String(input?.value || "").trim();
  if (text.length < 8) {
    toast("8자 이상 입력해 주세요.");
    return;
  }
  const nick = communityNick();
  localStorage.setItem(COMMUNITY_LS.nick, nick);
  const type = $("community-type")?.value || "tip";
  const posts = loadUserCommunityPosts();
  posts.unshift({
    id: `user-${Date.now()}`,
    type,
    author: nick,
    region: "강원",
    title: text.length > 42 ? `${text.slice(0, 42)}…` : "",
    body: text,
    tags: [],
    likes: 0,
    ago: "방금",
    aiPrompt: `${text} — 이 조건으로 강원 여행 코스 추천해줘`,
    grad: "linear-gradient(135deg,#006a61,#88d6fd)",
  });
  saveUserCommunityPosts(posts);
  if (input) input.value = "";
  updateCommunityCharCount();
  toast("게시했어요!");
  renderCommunity();
}

function updateCommunityCharCount() {
  const input = $("community-input");
  const el = $("community-char");
  if (!input || !el) return;
  el.textContent = `${input.value.length} / 500`;
}

function initCommunity() {
  $("community-login-btn")?.addEventListener("click", openLoginModal);
  $("community-form")?.addEventListener("submit", submitCommunityPost);
  $("community-input")?.addEventListener("input", updateCommunityCharCount);
  const saved = localStorage.getItem(COMMUNITY_LS.nick);
  if (saved && $("community-nick")) $("community-nick").value = saved;
  updateCommunityCharCount();
}

/* ==================== Saved trips (login required) ==================== */
const TRIPS_LS = "voyageai_saved_trips";
const PENDING_VIEW_LS = "voyageai_pending_view";

function tripsStoreKey() {
  const auth = loadAuth();
  if (!auth.loggedIn) return "";
  return auth.userId || auth.name || "";
}

function loadAllTripsStore() {
  try {
    const raw = localStorage.getItem(TRIPS_LS);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveAllTripsStore(store) {
  localStorage.setItem(TRIPS_LS, JSON.stringify(store));
}

function loadSavedTripsLocal() {
  const key = tripsStoreKey();
  if (!key) return [];
  return loadAllTripsStore()[key] || [];
}

function persistSavedTripsLocal(trips) {
  const key = tripsStoreKey();
  if (!key) return;
  const store = loadAllTripsStore();
  store[key] = trips.slice(0, 30);
  saveAllTripsStore(store);
}

function canUseSupabaseCloud() {
  const auth = loadAuth();
  return Boolean(sb && auth.loggedIn && auth.userId && isOAuthProvider(auth.provider));
}

function rowToTrip(row) {
  return {
    id: row.id,
    savedAt: row.saved_at,
    query: row.query || "",
    meta: row.meta || {},
    steps: row.steps || [],
    focusOrder: row.focus_order ?? 1,
    stopNames: row.stop_names || "",
  };
}

async function loadSavedTripsForUser() {
  if (canUseSupabaseCloud()) {
    const { data, error } = await sb
      .from("saved_trips")
      .select("id, query, meta, steps, focus_order, stop_names, saved_at")
      .order("saved_at", { ascending: false })
      .limit(30);
    if (!error && data) return data.map(rowToTrip);
    console.warn("Supabase saved_trips load:", error);
  }
  return loadSavedTripsLocal();
}

async function persistSavedTrips(trips) {
  if (canUseSupabaseCloud()) return;
  persistSavedTripsLocal(trips);
}

function formatSavedWhen(iso) {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "저장됨";
    return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "저장됨";
  }
}

function saveCurrentTrip() {
  if (!isLoggedIn()) {
    toast("저장하려면 로그인해 주세요.");
    state.pendingView = null;
    openLoginModal();
    return;
  }
  if (!state.steps.length) {
    toast("저장할 코스가 없어요.");
    return;
  }
  saveCurrentTripAsync().catch((err) => {
    console.warn("saveCurrentTrip:", err);
    toast("저장에 실패했어요.");
  });
}

async function saveCurrentTripAsync() {
  const stops = destinationSteps(state.steps);
  const payload = {
    query: state.query,
    meta: JSON.parse(JSON.stringify(state.meta)),
    steps: JSON.parse(JSON.stringify(state.steps)),
    focus_order: state.focusOrder,
    stop_names: stops.map((s) => s.spot.name).join(" → "),
  };

  if (canUseSupabaseCloud()) {
    const { error } = await sb.from("saved_trips").insert(payload);
    if (error) throw error;
    toast("저장함에 담았어요. (클라우드)");
    return;
  }

  const trip = {
    id: `trip-${Date.now()}`,
    savedAt: new Date().toISOString(),
    focusOrder: state.focusOrder,
    stopNames: payload.stop_names,
    ...payload,
    meta: payload.meta,
    steps: payload.steps,
  };
  const trips = loadSavedTripsLocal();
  trips.unshift(trip);
  persistSavedTripsLocal(trips);
  toast("저장함에 담았어요.");
}

function deleteSavedTrip(id) {
  if (!isLoggedIn()) return;
  if (!confirm("저장한 코스를 삭제할까요?")) return;
  deleteSavedTripAsync(id).catch((err) => {
    console.warn("deleteSavedTrip:", err);
    toast("삭제에 실패했어요.");
  });
}

async function deleteSavedTripAsync(id) {
  if (canUseSupabaseCloud()) {
    const { error } = await sb.from("saved_trips").delete().eq("id", id);
    if (error) throw error;
  } else {
    persistSavedTripsLocal(loadSavedTripsLocal().filter((t) => t.id !== id));
  }
  toast("저장함에서 삭제했어요.");
  await renderTrips();
}

async function openSavedTrip(id) {
  if (!isLoggedIn()) return;
  const trips = await loadSavedTripsForUser();
  const trip = trips.find((t) => t.id === id);
  if (!trip) {
    toast("저장한 코스를 찾지 못했어요.");
    return;
  }
  state.query = trip.query || "";
  state.meta = trip.meta || {};
  state.steps = trip.steps || [];
  state.focusOrder = trip.focusOrder || 1;
  resetMapState();
  show("planner");
  renderPlanner();
}

async function renderTrips() {
  const list = $("trips-list");
  const chip = $("trips-count-chip");
  if (!list) return;
  const auth = loadAuth();
  const trips = await loadSavedTripsForUser();
  if (chip) chip.textContent = `${trips.length}개 저장`;

  if (!auth.loggedIn) {
    list.innerHTML = `<p class="trips-empty">로그인하면 저장함을 사용할 수 있어요.</p>`;
    return;
  }

  if (!trips.length) {
    list.innerHTML =
      `<div class="trips-empty">` +
      `<p>아직 저장한 코스가 없어요.</p>` +
      `<p class="trips-empty-hint">AI로 코스를 만든 뒤 <strong>♡ 저장함에 저장</strong>을 눌러 보세요.</p>` +
      `<button type="button" class="btn-primary" data-nav="explore">✦ AI 여행 시작</button>` +
      `</div>`;
    return;
  }

  list.innerHTML = trips
    .map((t) => {
      const title = t.meta?.title || "맞춤 여행 코스";
      const summary = t.meta?.summary || t.query || "";
      const duration = t.meta?.duration || t.meta?.tripIntent?.duration || "당일";
      const stops = t.stopNames || (t.steps || []).map((s) => s.spot?.name).filter(Boolean).join(" → ");
      return (
        `<article class="trips-card">` +
        `<div class="trips-card-body">` +
        `<div class="trips-card-meta">` +
        `<span class="chip">${esc(duration)}</span>` +
        `<span class="trips-when">${esc(formatSavedWhen(t.savedAt))}</span>` +
        `</div>` +
        `<h3>${esc(title)}</h3>` +
        `<p class="trips-summary">${esc(summary)}</p>` +
        (stops ? `<p class="trips-route">${esc(stops)}</p>` : "") +
        `<div class="trips-actions">` +
        `<button type="button" class="btn-primary trips-open" data-open-trip="${esc(t.id)}">일정 열기</button>` +
        `<button type="button" class="trips-delete" data-delete-trip="${esc(t.id)}">삭제</button>` +
        `</div></div></article>`
      );
    })
    .join("");
}

function initTrips() {
  $("btn-save-trip")?.addEventListener("click", saveCurrentTrip);
  $("btn-logout-trips")?.addEventListener("click", (e) => {
    e.preventDefault();
    resetSession();
  });
}

/* ==================== Auth (Supabase Google/Kakao + local nick) ==================== */
const AUTH_LS = "voyageai_auth_session";
let sb = null;

function hasSupabase() {
  const url = String(window.SUPABASE_URL || "");
  const key = String(window.SUPABASE_ANON_KEY || "");
  return Boolean(
    url && key && url.includes("supabase.co") && !url.includes("YOUR_PROJECT")
  );
}

function appRedirectUrl() {
  const u = new URL(window.location.href);
  u.hash = "";
  u.search = "";
  return u.toString();
}

function loadAuth() {
  try {
    const raw = localStorage.getItem(AUTH_LS);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return { loggedIn: false, name: "", userId: "", provider: "" };
}

function saveAuth(auth) {
  localStorage.setItem(AUTH_LS, JSON.stringify(auth));
}

function isLoggedIn() {
  return Boolean(loadAuth().loggedIn);
}

function authInitial(name) {
  const ch = String(name || "Y").trim()[0];
  return ch ? ch.toUpperCase() : "Y";
}

function applySupabaseUser(user) {
  const provider = user.app_metadata?.provider || "kakao";
  const meta = user.user_metadata || {};
  const name = String(
    meta.full_name ||
      meta.name ||
      meta.nickname ||
      meta.preferred_username ||
      meta.user_name ||
      user.email?.split("@")[0] ||
      "여행러"
  )
    .trim()
    .slice(0, 12);
  saveAuth({ loggedIn: true, name, userId: user.id, provider });
  localStorage.setItem(COMMUNITY_LS.nick, name);
  const nickEl = $("community-nick");
  if (nickEl) nickEl.value = name;
}

function clearStaleOAuthAuth() {
  const auth = loadAuth();
  if (isOAuthProvider(auth.provider)) {
    saveAuth({ loggedIn: false, name: "", userId: "", provider: "" });
  }
}

function renderAuthUI() {
  const auth = loadAuth();
  const loginBtn = $("auth-login-btn");
  const userBox = $("auth-user");
  const label = $("auth-label");
  const avatar = $("auth-avatar");
  if (!loginBtn || !userBox) return;

  if (auth.loggedIn && auth.name) {
    loginBtn.classList.add("hidden");
    userBox.classList.remove("hidden");
    if (label) label.textContent = auth.name;
    if (avatar) avatar.textContent = authInitial(auth.name);
  } else {
    loginBtn.classList.remove("hidden");
    userBox.classList.add("hidden");
  }
  if (state.view === "community") renderCommunity();
}

const OAUTH_PROVIDERS = {
  google: { label: "Google" },
  kakao: { label: "카카오" },
};

function syncLoginModalMode() {
  const desc = $("login-modal-desc");
  if (desc) {
    desc.textContent = hasSupabase()
      ? "Google·카카오로 로그인하면 저장함이 기기 간에 동기화됩니다."
      : "Google·카카오로 로그인하거나, 닉네임으로 체험해 보세요. (클라우드 동기화는 Supabase 연결 후)";
  }
}

function openLoginModal() {
  const modal = $("login-modal");
  const input = $("login-nick");
  if (!modal) return;
  syncLoginModalMode();
  const saved = localStorage.getItem(COMMUNITY_LS.nick) || loadAuth().name || "";
  if (input) {
    input.value = saved;
    setTimeout(() => {
      $("login-google")?.focus();
    }, 80);
  }
  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");
}

function closeLoginModal() {
  const modal = $("login-modal");
  if (!modal) return;
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
}

function resumePendingViewAfterAuth() {
  if (!isLoggedIn()) return;
  const pending = sessionStorage.getItem(PENDING_VIEW_LS) || state.pendingView;
  if (!pending) return;
  sessionStorage.removeItem(PENDING_VIEW_LS);
  state.pendingView = null;
  show(pending);
}

async function initSupabaseAuth() {
  if (!hasSupabase() || typeof window.supabase === "undefined") return;
  sb = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY, {
    auth: { persistSession: true, detectSessionInUrl: true, flowType: "pkce" },
  });
  const { data: { session } } = await sb.auth.getSession();
  if (session?.user) applySupabaseUser(session.user);
  else clearStaleOAuthAuth();

  sb.auth.onAuthStateChange((_event, session) => {
    if (session?.user) applySupabaseUser(session.user);
    else clearStaleOAuthAuth();
    renderAuthUI();
  });

  if (window.location.hash.includes("access_token") || window.location.search.includes("code=")) {
    window.history.replaceState({}, document.title, appRedirectUrl());
  }
  resumePendingViewAfterAuth();
}

async function loginWithOAuth(provider) {
  const info = OAUTH_PROVIDERS[provider];
  if (!info) return;
  if (!hasSupabase()) {
    toast("클라우드 로그인 설정(Supabase)이 아직 연결되지 않았어요.");
    return;
  }
  if (!sb) {
    toast(`${info.label} 로그인을 준비 중이에요. 잠시 후 다시 시도해 주세요.`);
    return;
  }
  if (state.pendingView) sessionStorage.setItem(PENDING_VIEW_LS, state.pendingView);
  closeLoginModal();
  const { error } = await sb.auth.signInWithOAuth({
    provider,
    options: { redirectTo: appRedirectUrl() },
  });
  if (error) {
    console.warn(`${info.label} OAuth:`, error);
    toast(`${info.label} 로그인을 시작하지 못했어요.`);
  }
}

function submitLogin() {
  const input = $("login-nick");
  const nick = String(input?.value || "").trim().slice(0, 12);
  if (nick.length < 2) {
    toast("닉네임은 2자 이상 입력해 주세요.");
    input?.focus();
    return;
  }
  saveAuth({ loggedIn: true, name: nick, userId: `local:${nick}`, provider: "local" });
  localStorage.setItem(COMMUNITY_LS.nick, nick);
  const communityNickEl = $("community-nick");
  if (communityNickEl) communityNickEl.value = nick;
  closeLoginModal();
  renderAuthUI();
  toast(`${nick}님, 체험 로그인했어요.`);
  resumePendingViewAfterAuth();
}

async function logoutAuth() {
  const auth = loadAuth();
  if (sb && isOAuthProvider(auth.provider)) {
    await sb.auth.signOut();
  }
  saveAuth({ loggedIn: false, name: "", userId: "", provider: "" });
  renderAuthUI();
  toast("로그아웃했어요.");
}

function initAuth() {
  $("auth-login-btn")?.addEventListener("click", openLoginModal);
  $("auth-logout-btn")?.addEventListener("click", () => {
    logoutAuth().catch((err) => console.warn("logout:", err));
  });
  $("login-google")?.addEventListener("click", () => {
    loginWithOAuth("google").catch((err) => console.warn("loginWithOAuth(google):", err));
  });
  $("login-kakao")?.addEventListener("click", () => {
    loginWithOAuth("kakao").catch((err) => console.warn("loginWithOAuth(kakao):", err));
  });
  $("login-submit")?.addEventListener("click", submitLogin);
  $("login-cancel")?.addEventListener("click", closeLoginModal);
  $("login-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "login-modal") closeLoginModal();
  });
  $("login-nick")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitLogin();
    }
  });
  syncLoginModalMode();
  renderAuthUI();
  initSupabaseAuth().catch((err) => console.warn("initSupabaseAuth:", err));
}

function initSuggestions() {
  const pillsEl = $("suggest-pills");
  if (!pillsEl) return;
  pillsEl.innerHTML = SUGGESTIONS.map(
    (s) =>
      `<button type="button" data-prompt="${pillPromptAttr(s.prompt)}">${esc(s.label)}</button>`
  ).join("");
  pillsEl.querySelectorAll("button").forEach((b) => {
    b.addEventListener("click", () => {
      submitAgentPrompt(decodeURIComponent(b.dataset.prompt || ""));
    });
  });
}

/* ==================== Init ==================== */
function init() {
  try {
    syncBodyMode("explore");
    const spotEl = $("spot-count");
    if (spotEl) spotEl.textContent = String(ENRICHED_SPOTS.length);
    initSuggestions();
    initCommunity();
    initTrips();
    initAuth();
    updateSidebar("explore");
    ensureAgentWelcome();
    renderAgentChat();
    if ($("agent-spin")) $("agent-spin").style.display = "none";
    initLandingMap();
    window.addEventListener("resize", () => {
      landingMap?.invalidateSize();
      state.map?.invalidateSize();
    }, { passive: true });
  } catch (err) {
    console.error("init failed:", err);
    toast("화면 로딩 오류 — 새로고침(Ctrl+Shift+R) 해 주세요.");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
