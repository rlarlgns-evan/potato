// VoyageAI · 강원 — GitHub Pages 정적 앱 로직
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const state = {
  view: "explore",
  query: "",
  meta: { title: "", summary: "", duration: "" },
  steps: [],
  focusOrder: 1,
  mapEngine: "",
  map: null,
};

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
function show(view) {
  if (view === "planner" && !state.steps.length) {
    toast("일정은 AI 코스를 먼저 만들면 열려요.");
    view = "explore";
  }
  if (view === "trips" || view === "community") {
    toast("🚧 곧 제공될 기능이에요.");
    return;
  }
  state.view = view;
  $("view-explore").classList.toggle("hidden", view !== "explore");
  $("view-planner").classList.toggle("hidden", view !== "planner");
  document.querySelectorAll(".nav-links a").forEach((a) => {
    a.classList.toggle("on", a.dataset.nav === view);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.addEventListener("click", (e) => {
  const nav = e.target.closest("[data-nav]");
  if (nav) { e.preventDefault(); show(nav.dataset.nav); }
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

function estDriveMin(km) {
  const speed = km > 80 ? 55 : km > 40 ? 48 : 42;
  return Math.max(8, Math.round((km / speed) * 60));
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
  for (let i = 0; i < steps.length - 1; i++) {
    const from = steps[i].spot;
    const to = steps[i + 1].spot;
    const km = haversineKm(from, to);
    const driveMin = estDriveMin(km);
    legs.push({ from: steps[i], to: steps[i + 1], km, driveMin });
    steps[i].move_to_next = `${to.name}까지 ${fmtKm(km)} · 차량 약 ${fmtMin(driveMin)}`;
  }
  return legs;
}

function routeSummary(steps, legs) {
  const driveKm = legs.reduce((a, l) => a + l.km, 0);
  const driveMin = legs.reduce((a, l) => a + l.driveMin, 0);
  const stayMin = steps.reduce((a, s) => a + (s.stay ?? s.spot.stay_min ?? 60), 0);
  return { stops: steps.length, driveKm, driveMin, stayMin, totalMin: driveMin + stayMin };
}

const SPOT_BY_NAME = Object.fromEntries(ENRICHED_SPOTS.map((s) => [s.name, s]));
const MAX_SPOTS_IN_PROMPT = 28;

function normalizeGeminiKey(raw) {
  let key = String(raw ?? "").trim();
  key = key.replace(/^value:\s*/i, "").trim();
  return key;
}

function compactSpotCatalog(prompt) {
  const kws = prompt.replace(/,/g, " ").split(/\s+/).filter((w) => w.length >= 2);
  let pool = ENRICHED_SPOTS;
  if (kws.length) {
    const ranked = ENRICHED_SPOTS.map((s) => {
      const blob = `${s.name} ${s.region} ${s.theme}`;
      const score = kws.reduce((acc, kw) => acc + (blob.includes(kw) ? 1 : 0), 0);
      return { score, s };
    }).sort((a, b) => b.score - a.score || a.s.name.localeCompare(b.s.name));
    const matched = ranked.filter((r) => r.score > 0).slice(0, MAX_SPOTS_IN_PROMPT).map((r) => r.s);
    pool = matched.length >= 6 ? matched : ranked.slice(0, MAX_SPOTS_IN_PROMPT).map((r) => r.s);
  } else {
    pool = ENRICHED_SPOTS.slice(0, MAX_SPOTS_IN_PROMPT);
  }
  return pool.map((s) => `${s.name}|${s.region}|${s.theme}`).join("\n");
}

function geminiFailToast(e) {
  if (e.status === 429 || /credit|billing|quota|RESOURCE_EXHAUSTED/i.test(e.detail || e.message || ""))
    toast("Gemini 크레딧/할당량 부족 — AI Studio 결제를 확인하세요.");
  else if (e.status === 503 || /high demand|UNAVAILABLE/i.test(e.detail || e.message || ""))
    toast("Gemini 서버 혼잡 — 잠시 후 다시 시도하세요.");
  else if (e.status === 400 || e.status === 403)
    toast("Gemini API 키 오류 — 키·제한 설정을 확인하세요.");
  else if (/empty response|JSON|no spots matched/i.test(e.message || ""))
    toast("Gemini 응답 파싱 실패 — 다시 시도하거나 다른 질문을 입력하세요.");
  else
    toast("Gemini 호출 실패 — 로컬 큐레이션으로 대체했어요.");
}

async function callGemini(body, key, retries = 1) {
  const url =
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" +
    encodeURIComponent(key);
  for (let attempt = 0; attempt <= retries; attempt++) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) return r.json();
    let detail = "";
    try {
      detail = (await r.json())?.error?.message || "";
    } catch (_) { /* ignore */ }
    if (r.status === 503 && attempt < retries) {
      await new Promise((res) => setTimeout(res, 1200 * (attempt + 1)));
      continue;
    }
    const e = new Error("Gemini HTTP " + r.status + (detail ? ": " + detail : ""));
    e.status = r.status;
    e.detail = detail;
    throw e;
  }
}

function parseGeminiCuration(raw, prompt) {
  let text = String(raw ?? "").trim();
  if (!text) throw new Error("empty response from Gemini");
  text = text.replace(/^```(?:json)?\s*/, "").replace(/\s*```$/, "");
  const parsed = JSON.parse(text);
  const steps = (parsed.route_steps || [])
    .map((st, i) => {
      const spot =
        SPOT_BY_NAME[st.spot_name] ||
        ENRICHED_SPOTS.find((s) => s.name.includes(st.spot_name) || st.spot_name?.includes(s.name));
      if (!spot) return null;
      return {
        order: i + 1,
        spot,
        stay: st.stay_minutes ?? spot.stay_min ?? 60,
        why: (st.why || `${spot.description}. ${spot.tip}`).trim(),
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
  };
}
function localCuration(prompt) {
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
    source: "local",
  };
}

/* ==================== Curation ==================== */
async function geminiCuration(prompt, key) {
  const catalog = compactSpotCatalog(prompt);
  const sys =
    "Gangwon (Korea) trip planner. Pick 1-4 spots from catalog; output JSON only. " +
    "Korean text values. Schema: " +
    '{"itinerary_title":"","summary":"","total_duration":"",' +
    '"route_steps":[{"order":1,"spot_name":"","stay_minutes":60,"why":""}]}. ' +
    "spot_name must copy catalog names exactly.\nCatalog name|region|theme:\n" + catalog;
  const body = {
    system_instruction: { parts: [{ text: sys }] },
    contents: [{ role: "user", parts: [{ text: prompt.slice(0, 800) }] }],
    generationConfig: {
      temperature: 0.5,
      maxOutputTokens: 2048,
      responseMimeType: "application/json",
      thinkingConfig: { thinkingBudget: 0 },
    },
  };
  const d = await callGemini(body, key);
  const c = d.candidates?.[0];
  const finish = c?.finishReason || "";
  const text = c?.content?.parts?.map((p) => p.text || "").join("") ?? "";
  if (!text && finish === "MAX_TOKENS")
    throw new Error("empty response from Gemini (token limit)");
  return parseGeminiCuration(text, prompt);
}

const curationCache = new Map();

async function runCuration(prompt) {
  const btn = $("search-btn");
  btn.disabled = true;
  $("search-btn-label").classList.add("hidden");
  $("search-spin").style.display = "inline-block";
  try {
    let result;
    if (curationCache.has(prompt)) {
      result = curationCache.get(prompt);
    } else {
      const key = normalizeGeminiKey(localStorage.getItem("gemini_key") || "");
      let fromGemini = false;
      if (key) {
        try {
          result = await geminiCuration(prompt, key);
          fromGemini = true;
        } catch (e) {
          console.warn("Gemini 실패 → 로컬 큐레이션:", e);
          geminiFailToast(e);
          result = localCuration(prompt);
        }
      } else {
        result = localCuration(prompt);
      }
      if (fromGemini || !key) curationCache.set(prompt, result);
    }
    state.query = prompt;
    state.meta = { title: result.title, summary: result.summary, duration: result.duration };
    state.steps = result.steps;
    state.focusOrder = 1;
    resetMapState();
    show("planner");
    renderPlanner();
  } finally {
    btn.disabled = false;
    $("search-btn-label").classList.remove("hidden");
    $("search-spin").style.display = "none";
  }
}

/* ==================== Planner render ==================== */
function courseCardHtml(step, active) {
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
      <div class="ai-lbl">✦ AI INSIGHT</div>
      <p>${esc(step.why)}</p>
    </div>
  </div>
</a>`;
}

function legHtml(leg) {
  return `<div class="course-leg">🚗 ${esc(leg.from.spot.name)} → ${esc(leg.to.spot.name)} · ${fmtKm(leg.km)} · 약 ${fmtMin(leg.driveMin)}</div>`;
}

function renderRouteSummary() {
  const legs = computeLegs(state.steps);
  const sum = routeSummary(state.steps, legs);
  $("route-summary").innerHTML = `
    <div class="route-stat"><strong>${sum.stops}</strong><span>정거장</span></div>
    <div class="route-stat"><strong>${fmtKm(sum.driveKm)}</strong><span>총 이동</span></div>
    <div class="route-stat"><strong>${fmtMin(sum.driveMin)}</strong><span>이동 시간</span></div>
    <div class="route-stat"><strong>${fmtMin(sum.totalMin)}</strong><span>예상 소요</span></div>`;
  $("chip-route").textContent = `🚗 ${fmtKm(sum.driveKm)} · ${fmtMin(sum.totalMin)}`;
}

function spotMapUrl(spot) {
  return `https://map.kakao.com/link/map/${encodeURIComponent(spot.name)},${spot.lat},${spot.lng}`;
}

function renderSpotDetail() {
  const step = state.steps.find((s) => s.order === state.focusOrder);
  const el = $("spot-detail");
  if (!step) { el.innerHTML = ""; return; }
  const s = step.spot;
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
      <div class="ai-lbl">✦ AI INSIGHT</div>
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
    parts.push(courseCardHtml(step, step.order === state.focusOrder));
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

function renderPlanner() {
  const { meta, steps, query } = state;
  $("plan-title").textContent = meta.title || "맞춤 여행 코스";
  $("plan-summary").textContent = meta.summary || "";
  $("plan-query").textContent = query ? `🔍 ${query}` : "";
  $("chip-duration").textContent = `⏱ ${meta.duration || "당일 코스"}`;
  $("chip-stops").textContent = `${steps.length}곳`;
  renderRouteSummary();
  renderCourses();
  $("kakao-link").href = kakaoRouteUrl(steps);
  updateMapChrome();
  renderSpotDetail();
  renderMap();
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
function pinDiv(label, focused) {
  return `<div class="order-pin${focused ? " focus" : ""}">${label || ""}</div>`;
}

function popupHtml(step) {
  const s = step.spot;
  return `<div style="min-width:200px;line-height:1.55;font-size:13px;font-family:Pretendard,sans-serif;padding:2px;">
    <strong style="color:#171d1c;">${step.order}. ${esc(s.name)}</strong><br/>
    <span style="color:#3e4947;">${esc(s.region)} · ${esc(s.theme)} · 약 ${step.stay}분</span><br/>
    <span style="color:#3e4947;">🕐 ${esc(s.hours)} · 💰 ${esc(s.fee)}</span><br/>
    <span style="color:#3e4947;">${esc(step.why)}</span></div>`;
}

function centerOf(steps) {
  const lat = steps.reduce((a, s) => a + s.spot.lat, 0) / steps.length;
  const lng = steps.reduce((a, s) => a + s.spot.lng, 0) / steps.length;
  return [lat, lng];
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
  const path = [];
  let openIw = null;
  let focusStep = null;

  state.steps.forEach((step) => {
    const pos = new kakao.maps.LatLng(step.spot.lat, step.spot.lng);
    bounds.extend(pos);
    path.push(pos);
    const focused = step.order === state.focusOrder;
    if (focused) focusStep = step;

    const dom = document.createElement("div");
    dom.innerHTML = pinDiv(step.order, focused);
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

  if (path.length > 1) {
    new kakao.maps.Polyline({
      path, strokeWeight: 4, strokeColor: "#006a61", strokeOpacity: 0.85, strokeStyle: "shortdash",
    }).setMap(map);
  }
  if (focusStep) {
    map.setCenter(new kakao.maps.LatLng(focusStep.spot.lat, focusStep.spot.lng));
    map.setLevel(6);
  } else if (path.length > 1) {
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
      html: pinDiv(step.order, focused), className: "",
      iconSize: focused ? [34, 34] : [28, 28], iconAnchor: focused ? [17, 17] : [14, 14],
    });
    const m = L.marker(ll, { icon }).addTo(map).bindPopup(popupHtml(step));
    if (focused) { focusLl = ll; m.openPopup(); }
  });
  if (latlngs.length > 1)
    L.polyline(latlngs, { color: "#006a61", weight: 4, opacity: 0.85, dashArray: "1 8", lineCap: "round" }).addTo(map);
  if (focusLl) map.setView(focusLl, 12);
  else if (latlngs.length > 1) map.fitBounds(latlngs, { padding: [44, 44] });
  setTimeout(() => map.invalidateSize(), 150);
}

/* ==================== Settings modal ==================== */
function refreshAiNote() {
  const key = normalizeGeminiKey(localStorage.getItem("gemini_key") || "");
  $("ai-mode-note").textContent = key ? "Gemini 연동 중 (내 키)" : "로컬 AI 모드 (⚙에서 Gemini 키 연결)";
}

$("btn-settings").addEventListener("click", () => {
  $("gemini-key").value = localStorage.getItem("gemini_key") || "";
  $("modal-bg").classList.add("show");
});
$("modal-bg").addEventListener("click", (e) => {
  if (e.target === $("modal-bg")) $("modal-bg").classList.remove("show");
});
$("btn-key-save").addEventListener("click", () => {
  const v = normalizeGeminiKey($("gemini-key").value);
  if (v) { localStorage.setItem("gemini_key", v); toast("Gemini 키를 저장했어요. (이 브라우저에만)"); }
  else { localStorage.removeItem("gemini_key"); }
  curationCache.clear();
  refreshAiNote();
  $("modal-bg").classList.remove("show");
});
$("btn-key-clear").addEventListener("click", () => {
  localStorage.removeItem("gemini_key");
  $("gemini-key").value = "";
  curationCache.clear();
  refreshAiNote();
  toast("키를 삭제했어요. 로컬 AI 모드로 동작합니다.");
});

/* ==================== Misc interactions ==================== */
$("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("search-input").value.trim();
  if (!v) { toast("여행 취향을 한 줄로 들려주세요!"); return; }
  $("last-query").textContent = v;
  $("last-query").classList.remove("hidden");
  $("search-input").value = "";
  runCuration(v);
});

$("nav-search").addEventListener("click", (e) => {
  e.preventDefault();
  show("explore");
  $("search-input").focus();
});

$("more-tags").addEventListener("click", () => {
  const btn = $("more-tags");
  const expanded = btn.dataset.x === "1";
  document.querySelectorAll("#interest-tags .extra").forEach((t) => t.remove());
  if (!expanded) {
    ["등산", "야경", "현지 시장"].forEach((t) => {
      const span = document.createElement("span");
      span.className = "tag extra";
      span.textContent = t;
      btn.before(span);
    });
    btn.textContent = "접기";
    btn.dataset.x = "1";
  } else {
    btn.textContent = "+3 더보기";
    btn.dataset.x = "0";
  }
});

$("btn-logout").addEventListener("click", (e) => {
  e.preventDefault();
  state.steps = [];
  state.query = "";
  $("last-query").classList.add("hidden");
  show("explore");
  toast("로그아웃했어요.");
});

function initHighlights() {
  $("highlights").innerHTML = HIGHLIGHTS.map(
    (h) =>
      `<div class="hl-card">
         <div class="hl-icon" style="background:${h.bg}">${h.icon}</div>
         <strong>${esc(h.title)}</strong>
         <span>${esc(h.region)}</span>
       </div>`
  ).join("");
}

/* ==================== Init ==================== */
function init() {
  $("intro").innerHTML = REGION_INTRO;
  $("spot-count").textContent = ENRICHED_SPOTS.length;
  $("suggest-pills").innerHTML = SUGGESTIONS
    .map((s) => `<button type="button" data-prompt="${esc(s.prompt)}">${esc(s.label)}</button>`)
    .join("");
  $("suggest-pills").querySelectorAll("button").forEach((b) => {
    b.addEventListener("click", () => {
      $("last-query").textContent = b.dataset.prompt;
      $("last-query").classList.remove("hidden");
      runCuration(b.dataset.prompt);
    });
  });
  refreshAiNote();
  initHighlights();
  initFestivals();
  initWeather();
}

init();
