// 강원 온도(ON道) · GitHub Pages 정적 앱 로직
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
  "안녕하세요! 저는 **강원도 관광 전문 AI 가이드**예요.\n\n" +
  "강원도 여행·맛집·축제·동선을 한국관광공사(KTO) 공식 데이터를 바탕으로 안내해 드려요. " +
  "목적지 일정을 요청하시면 **1안(목적지 집중)** 과 **2안(인구감소지역 경유·상생 코스)** 두 가지를 제안해요. " +
  "「춘천시 소개해줘」「강릉 바다 코스」처럼 시·군·테마 질문도 환영해요. " +
  "강원도 밖 지역은 안내하지 않으며, 궁금한 것을 편하게 물어보세요.";

const P = typeof TOUR_PROMPTS !== "undefined" ? TOUR_PROMPTS : {};
const ROUTING = P.routing || {};

const GANGWON_AGENT_ROLE_TWO_TRACK = P.GANGWON_AGENT_ROLE_TWO_TRACK || "";
const KTO_TWO_TRACK_OUTPUT_FORMAT = P.KTO_TWO_TRACK_OUTPUT_FORMAT || "";
const GANGWON_AGENT_ROLE = P.GANGWON_AGENT_ROLE || "";
const KTO_OUTPUT_FORMAT = P.KTO_OUTPUT_FORMAT || "";
const GANGWON_AGENT_ROLE_ROUTING = P.GANGWON_AGENT_ROLE_ROUTING || "";
const KTO_OUTPUT_FORMAT_ROUTING = P.KTO_OUTPUT_FORMAT_ROUTING || "";
const KTO_FALLBACK_INTRO = P.KTO_FALLBACK_INTRO || "";

const GANGWON_REGION_NAMES = ROUTING.gangwon_region_names || [];
const MAIN_DESTINATION_REGIONS = ROUTING.main_destination_regions || [];
const POPULATION_DECLINE_REGIONS = ROUTING.population_decline_regions || [];
const TRANSIT_BY_DESTINATION = ROUTING.transit_by_destination || {};

function pickMainDestination(prompt) {
  const regions = regionsInPrompt(prompt);
  if (!regions.length) return null;
  for (const region of regions) {
    if (MAIN_DESTINATION_REGIONS.includes(region)) return region;
  }
  return regions[0];
}

function resolveTransitArea(mainRegion) {
  if (!mainRegion) return null;
  if (TRANSIT_BY_DESTINATION[mainRegion]) return TRANSIT_BY_DESTINATION[mainRegion];
  return null;
}

function shouldUseTwoTrackWorkflow(prompt) {
  const msg = String(prompt || "").trim();
  if (!msg) return false;
  if (!hasTripPlanIntent(msg) && !needsComplexAi(msg)) return false;
  const main = pickMainDestination(msg);
  if (!main) return false;
  const transit = resolveTransitArea(main);
  return Boolean(transit && transit !== main);
}

function regionsInPrompt(msg) {
  const found = [];
  for (const region of GANGWON_REGION_NAMES) {
    const base = region.replace(/[시군]$/, "");
    if (msg.includes(region) || msg.includes(base)) found.push(region);
  }
  return found;
}

const REGION_INFO_INTENT_RE =
  /(?:설명|소개|알려|안내|어때|특징|정보|대해|대해서|어떤|가볼|볼거리|먹거리|특산|뭐가\s*좋)/i;
const TRIP_PLAN_INTENT_RE =
  /(?:코스|일정|경로|동선|루트|하루|당일|\d+박|숙소|펜션|호텔|길찾|계획|짜\s*줘|만들어|추천해\s*줘)/i;

function hasTripPlanIntent(msg) {
  return TRIP_PLAN_INTENT_RE.test(String(msg || ""));
}

function isRegionInfoOnlyPrompt(prompt) {
  const msg = String(prompt || "").trim();
  const regions = regionsInPrompt(msg);
  if (!regions.length || !REGION_INFO_INTENT_RE.test(msg)) return false;
  return !hasTripPlanIntent(msg);
}

function isMultiIntentPrompt(prompt) {
  const msg = String(prompt || "").trim();
  return regionsInPrompt(msg).length > 0 && REGION_INFO_INTENT_RE.test(msg) && hasTripPlanIntent(msg);
}

function regionEmptyFallbackMessage() {
  return KTO_FALLBACK_INTRO;
}

function collectKtoCatalogEntries(region) {
  const agg = TOUR_AGGREGATED_SPOTS?.regions?.[region];
  if (!agg?.length) {
    console.warn("[KTO] aggregated catalog missing for", region);
    return [];
  }
  return agg.map((e) => ({
    name: e.name,
    region: e.region || region,
    theme: e.theme || "culture",
    rank: e.rank ?? 999,
    source: e.source || "KTO",
    lat: e.lat ?? null,
    lng: e.lng ?? null,
    categoryLabel: e.categoryLabel || "",
    description: e.description || "",
    imageUrl: e.imageUrl || "",
    related: e.related || [],
    visitorCount: e.visitorCount,
  }));
}

function ktoEntryToSpot(entry, region) {
  const enriched = resolveSpotByNameInEnriched(entry.name, [region]);
  if (enriched) return enriched;
  return {
    name: entry.name,
    region,
    theme: entry.theme || "culture",
    lat: entry.lat ?? 0,
    lng: entry.lng ?? 0,
    description: `${entry.name} — KTO ${entry.source}`,
    tip: "현장에서 운영 시간·요금을 확인해 주세요.",
    stay_min: 60,
    fee: "현장 확인",
    hours: "연중",
    parking: "인근 주차 가능",
    best_time: "주말·휴일",
    tags: [region.replace(/[시군]$/, ""), "KTO"],
  };
}

function ktoThemeDisplayLabel(entry) {
  const cat = String(entry.categoryLabel || "").trim();
  if (cat) {
    if (/자연|생태|산|숲|경관/.test(cat)) return "자연/풍경";
    if (/레저|스포츠|체험/.test(cat)) return "레저/체험";
    if (/문화|예술|역사/.test(cat)) return "문화/예술";
    return cat.replace(/관광/g, "").trim() || "관광";
  }
  if (entry.theme === "nature") return "자연/풍경";
  if (entry.theme === "experience") return "레저/체험";
  return "문화/예술";
}

function ktoSpotVisitorCount(region, rank, entry) {
  if (entry?.visitorCount != null && entry.visitorCount !== "—") return entry.visitorCount;
  const stats = typeof TOUR_VISITOR_STATS !== "undefined" ? TOUR_VISITOR_STATS?.regions?.[region] : null;
  const base = stats?.avg_daily || stats?.total || 0;
  if (!base) return "—";
  const weight = rank <= 5 ? (6 - Math.min(rank, 5)) / 15 : 1 / (rank + 5);
  return Math.max(100, Math.round(base * weight));
}

function normSpotKey(name) {
  return String(name ?? "").replace(/[\s·\-]+/g, "").trim();
}

function isProvinceWidePrompt(msg) {
  return /강원도?/.test(String(msg || "")) && !regionsInPrompt(msg).length;
}

function inferRegionsForCuration(prompt, intro = "") {
  const fromPrompt = regionsInPrompt(prompt);
  if (fromPrompt.length) return fromPrompt;
  return regionsInPrompt(intro);
}

/** User-requested region(s); prompt always wins over AI intro text. */
function strictRegionsForCuration(prompt, intro = "") {
  const fromPrompt = regionsInPrompt(prompt);
  if (fromPrompt.length) return fromPrompt;
  if (intro) return regionsInPrompt(intro);
  return [];
}

function primaryRegionForPrompt(prompt, intro = "") {
  const regions = strictRegionsForCuration(prompt, intro);
  return regions[0] || null;
}

function hasKtoCatalogForRegion(region) {
  return collectKtoCatalogEntries(region).length > 0;
}

function regionalFallbackSpots(regions, limit = 3) {
  if (!regions?.length) return [];
  return pickRegionalSpots(regions, limit);
}

function emptyRegionalCurationShell(regions, { summary, source = "gemini", title } = {}) {
  const region = regions?.[0] || "";
  const msg =
    summary ||
    (region && !hasKtoCatalogForRegion(region) ? regionEmptyFallbackMessage() : KTO_FALLBACK_INTRO);
  return {
    title: title || (region ? `${region} 안내` : "강원도 안내"),
    summary: msg,
    duration: "",
    steps: [],
    source,
    tripIntent: {},
    transitPlan: {},
    accommodation: {},
    dayPlans: [],
  };
}

const KTO_XML_SPOT_ALIASES = {
  경포대: ["경포해변", "강릉 경포대", "경포대"],
  "안목해변 카페거리": ["안목해변", "강릉 안목해변 커피거리", "안목해변 카페거리"],
  "대관령 양떼목장": ["대관령양떼목장", "대관령 양떼목장"],
  "봉평 메밀꽃밭": ["고랭길", "봉평", "메밀"],
};

function ktoAliasCandidates(name) {
  const raw = String(name ?? "").trim();
  const out = [raw];
  const aliases = KTO_XML_SPOT_ALIASES[raw];
  if (aliases) out.push(...aliases);
  for (const [xmlName, alts] of Object.entries(KTO_XML_SPOT_ALIASES)) {
    if (alts.some((a) => raw.includes(a) || a.includes(raw))) out.push(xmlName, ...alts);
  }
  return [...new Set(out.filter(Boolean))];
}

function resolveKtoSpotByName(name, regionsHint = []) {
  const candidates = ktoAliasCandidates(name);
  for (const cand of candidates) {
    const raw = String(cand ?? "").trim();
    if (!raw) continue;
    const key = normSpotKey(raw);
    const searchRegions = regionsHint.length ? regionsHint : GANGWON_REGION_NAMES;
    for (const region of searchRegions) {
      for (const entry of collectKtoCatalogEntries(region)) {
        const entryName = String(entry.name || "");
        const entryKey = normSpotKey(entryName);
        if (!entryName) continue;
        if (
          entryName === raw ||
          entryKey === key ||
          entryName.includes(raw) ||
          raw.includes(entryName) ||
          entryKey.includes(key) ||
          key.includes(entryKey)
        ) {
          return ktoEntryToSpot(entry, region);
        }
      }
    }
  }
  return null;
}

function pickProvinceWideSpots(limit = 3) {
  const out = [];
  const seen = new Set();
  for (const region of GANGWON_REGION_NAMES) {
    if (out.length >= limit) break;
    const entries = collectKtoCatalogEntries(region);
    if (!entries.length) continue;
    const spot = ktoEntryToSpot(entries[0], region);
    if (!seen.has(spot.name)) {
      seen.add(spot.name);
      out.push(spot);
    }
  }
  return out;
}

function regionShortName(region) {
  return String(region || "").replace(/(시|군)$/, "");
}

function detectPromptThemes(prompt) {
  const msg = String(prompt || "");
  const themes = [];
  if (/바다|해변|해수욕|일몰|서핑|오션|물놀이/.test(msg)) themes.push("sea");
  if (/맛|먹|음식|카페|커피|맛집|시장|디저트|회|해산물|먹거리/.test(msg)) themes.push("food");
  if (/자연|산|숲|트레킹|생태|힐링|계곡/.test(msg)) themes.push("nature");
  if (/문화|역사|박물관|축제|체험/.test(msg)) themes.push("culture");
  return themes;
}

function ktoCategoryForXml(entry, prompt) {
  const name = String(entry.name || "");
  const base = ktoThemeDisplayLabel(entry);
  const themes = detectPromptThemes(prompt);
  if (themes.includes("food") && /시장|먹거리/.test(name)) return "음식/먹거리";
  if (themes.includes("food") && /안목|카페|커피/.test(name)) return "음식/카페";
  if (/양떼|목장/.test(name) || entry.source === "생태관광") return "생태관광";
  if (themes.includes("sea") && /해변|해수욕|경포|바다/.test(name)) return "자연/풍경";
  return base;
}

function ktoXmlSpotName(entry, region, prompt) {
  const name = String(entry.name || "");
  const themes = detectPromptThemes(prompt);
  if (name === "경포해변" || name === "강릉 경포대") return "경포대";
  if (name === "안목해변" && (themes.includes("food") || /카페|커피|맛/.test(prompt))) {
    return "안목해변 카페거리";
  }
  if (name === "대관령양떼목장") return "대관령 양떼목장";
  if (name === "고랭길" || name === "고랭길(메밀꽃필드)") return "봉평 메밀꽃밭";
  const enriched = resolveSpotByNameInEnriched(name, [region]);
  if (enriched?.name) {
    const stripped = enriched.name
      .replace(/^(강릉|속초|춘천|원주|동해|삼척|평창|정선)\s*/, "")
      .split("·")[0]
      .trim();
    if (stripped.length >= 2) return stripped;
  }
  return name.replace(/([가-힣])(목장|해변)/, "$1 $2");
}

function scoreKtoEntryForPrompt(entry, prompt, { isTransit = false } = {}) {
  const themes = detectPromptThemes(prompt);
  const text = `${entry.name} ${entry.categoryLabel || ""} ${ktoThemeDisplayLabel(entry)}`;
  let score = Math.max(0, 8 - (entry.rank ?? 99));
  if (/숙박|호텔|리조트|모노그램|휘닉스|라마다/.test(text)) score -= 10;
  if (themes.includes("sea") && /해변|해수욕|바다|경포|안목|주문진|정동진/.test(text)) score += 6;
  if (themes.includes("food") && /시장|음식|카페|커피|쇼핑|맛|먹거리|회/.test(text)) score += 6;
  if (themes.includes("nature") && /자연|생태|산|숲|목장|계곡/.test(text)) score += 4;
  if (themes.includes("culture") && /문화|역사|사찰|박물관|메밀|봉평|고랭길/.test(text)) score += 4;
  if (isTransit && /고랭길|메밀|봉평/.test(text)) score += 8;
  if (isTransit && /양떼|목장/.test(text)) score += 5;
  if (!themes.length) score += 1;
  return score;
}

function ktoRowsForRegion(region, prompt, maxRows = 6, { isTransit = false } = {}) {
  const entries = collectKtoCatalogEntries(region)
    .filter((e) => !/숙박|호텔|리조트|모노그램|휘닉스|라마다/.test(`${e.name} ${e.categoryLabel || ""}`))
    .slice()
    .sort(
      (a, b) =>
        scoreKtoEntryForPrompt(b, prompt, { isTransit }) -
        scoreKtoEntryForPrompt(a, prompt, { isTransit })
    );
  const rows = [];
  const seenXml = new Set();
  for (const entry of entries) {
    if (rows.length >= maxRows) break;
    const xmlName = ktoXmlSpotName(entry, region, prompt);
    const key = normSpotKey(xmlName);
    if (seenXml.has(key)) continue;
    seenXml.add(key);
    rows.push({
      name: xmlName,
      sourceName: entry.name,
      category: ktoCategoryForXml(entry, prompt),
      visitors: ktoSpotVisitorCount(region, entry.rank, entry),
      entry,
    });
  }
  return rows;
}

const MAX_TRIP_DAYS = 14;
const KAKAO_MAX_ROUTE_POINTS = 7;

function clampTripDays(days) {
  return Math.min(Math.max(Number(days) || 1, 1), MAX_TRIP_DAYS);
}

function detectTripDuration(prompt) {
  const msg = String(prompt || "");
  const han = { 일: 1, 이: 2, 삼: 3, 사: 4, 오: 5, 육: 6, 칠: 7, 팔: 8, 구: 9, 십: 10 };

  let m = msg.match(/(\d+)\s*박\s*(\d+)\s*일/);
  if (m) {
    const nights = Number(m[1]);
    const days = clampTripDays(Number(m[2]));
    return { nights, days, label: `${nights}박 ${days}일` };
  }
  m = msg.match(/([일이삼사오육칠팔구십])\s*박\s*([일이삼사오육칠팔구십])\s*일/);
  if (m && han[m[1]] && han[m[2]]) {
    const nights = han[m[1]];
    const days = clampTripDays(han[m[2]]);
    return { nights, days, label: `${nights}박 ${days}일` };
  }
  if (/당일치기|당일\s*여행|무박/.test(msg) && !/\d+\s*박|[일이삼]박/.test(msg)) {
    return { nights: 0, days: 1, label: "당일" };
  }
  m = msg.match(/(\d+)\s*박/);
  if (m) {
    const nights = Number(m[1]);
    const days = clampTripDays(nights + 1);
    return { nights, days, label: `${nights}박 ${days}일` };
  }
  m = msg.match(/(\d+)\s*일(?:\s*여행|\s*일정)?/);
  if (m && !/\d+\s*박/.test(msg)) {
    const days = clampTripDays(Number(m[1]));
    return {
      nights: Math.max(0, days - 1),
      days,
      label: days === 1 ? "당일" : `${days}일`,
    };
  }
  if (hasTripPlanIntent(msg) || needsComplexAi(msg)) {
    return { nights: 1, days: 2, label: "1박 2일" };
  }
  return { nights: 0, days: 1, label: "당일" };
}

function buildDurationPromptBlock(prompt) {
  const d = detectTripDuration(prompt);
  return (
    "# TRIP DURATION (STRICT)\n" +
    `- Detected/default duration: **${d.label}** (${d.days} days, up to ${MAX_TRIP_DAYS} days supported).\n` +
    `- If the user specifies N박 M일 or N일, use that exactly — do NOT shorten to 1박2일 or 2박3일.\n` +
    `- Each option MUST include exactly **${d.days}** objects in the "days" array (day: 1..${d.days}).\n` +
    "- Each day schedule MUST have 4+ slots: 오전 관광, 점심 식사, 오후 관광, 저녁 식사.\n" +
    '- Set "duration_detected" to exactly this label in Korean (e.g. "3박 4일").\n'
  );
}

function isRestaurantEntry(entry) {
  const text = `${entry?.name || ""} ${entry?.categoryLabel || ""}`;
  return /시장|음식|맛집|식당|카페|커피|쇼핑|먹거리|회|한정식|삼겹|닭갈비|막국수|빵|베이커리|레스토랑/.test(text);
}

function getRegionSpecialty(region) {
  if (typeof REGION_PROFILE !== "undefined" && REGION_PROFILE[region]) {
    return REGION_PROFILE[region].specialty || "지역 먹거리";
  }
  return "지역 먹거리";
}

function cityCoordsForRegion(region, name = "") {
  const short = regionShortName(region);
  const city = (typeof GANGWON_CITIES !== "undefined" ? GANGWON_CITIES : []).find(
    (c) => c.city === short
  );
  const base = city ? { lat: city.lat, lng: city.lng } : { lat: 37.5, lng: 128.0 };
  if (!name) return base;
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  const a = ((Math.abs(h) % 360) * Math.PI) / 180;
  const r = 0.002 + (Math.abs(h) % 80) / 40000;
  return { lat: base.lat + Math.sin(a) * r, lng: base.lng + Math.cos(a) * r };
}

function synthesizeRestaurantRow(region, prompt) {
  const entries = collectKtoCatalogEntries(region);
  const market = entries.find((e) => /시장/.test(e.name));
  if (market) {
    return {
      name: ktoXmlSpotName(market, region, prompt),
      category: "음식/먹거리",
      visitors: ktoSpotVisitorCount(region, market.rank, market),
      entry: market,
    };
  }
  const specialty = getRegionSpecialty(region).split("·")[0].trim();
  const name = `${regionShortName(region)} ${specialty} 맛집`;
  const coords = cityCoordsForRegion(region, name);
  return {
    name,
    category: "음식/먹거리",
    visitors: "—",
    entry: {
      name,
      region,
      theme: "food",
      rank: 500,
      source: "KTO",
      lat: coords.lat,
      lng: coords.lng,
      categoryLabel: "음식",
    },
  };
}

function ktoSplitRowsForRegion(region, prompt, maxEach = 5, { isTransit = false } = {}) {
  const pool = ktoRowsForRegion(region, prompt, maxEach * 3, { isTransit });
  const attractions = pool.filter((r) => !isRestaurantEntry(r.entry));
  let restaurants = pool.filter((r) => isRestaurantEntry(r.entry));
  if (!restaurants.length) restaurants = [synthesizeRestaurantRow(region, prompt)];
  return {
    attractions: attractions.slice(0, maxEach),
    restaurants: restaurants.slice(0, maxEach),
  };
}

function formatTwoTrackRegionXml(tag, region, prompt, split) {
  const short = regionShortName(region);
  const attrs =
    tag === "transit_area"
      ? ` name="${short}" type="인구소멸지역"`
      : ` name="${short}"`;
  const parts = [];
  if (split.attractions?.length) {
    parts.push(
      "**관광지**",
      "| 관광지명 | 카테고리 | 방문자수 |",
      "|---|---|---|",
      ...split.attractions.map((r) => `| ${r.name} | ${r.category} | ${r.visitors} |`)
    );
  }
  if (split.restaurants?.length) {
    if (parts.length) parts.push("");
    parts.push(
      "**음식점**",
      "| 음식점명 | 카테고리 | 방문자수 |",
      "|---|---|---|",
      ...split.restaurants.map((r) => `| ${r.name} | ${r.category} | ${r.visitors} |`)
    );
  }
  if (!parts.length) return `<${tag}${attrs}>\n</${tag}>`;
  return `<${tag}${attrs}>\n${parts.join("\n")}\n</${tag}>`;
}

function buildTwoTrackKtoXml(prompt, maxEach = 3) {
  const main = pickMainDestination(prompt);
  if (!main) {
    return "<kto_data>\n<!-- region_required: include 시·군 name -->\n</kto_data>";
  }
  const transit = resolveTransitArea(main) || POPULATION_DECLINE_REGIONS[0];
  return [
    formatTwoTrackRegionXml(
      "main_destination",
      main,
      prompt,
      ktoSplitRowsForRegion(main, prompt, maxEach)
    ),
    formatTwoTrackRegionXml(
      "transit_area",
      transit,
      prompt,
      ktoSplitRowsForRegion(transit, prompt, maxEach, { isTransit: true })
    ),
  ].join("\n\n");
}

function buildThemePromptBlock(prompt) {
  const themes = detectPromptThemes(prompt);
  if (!themes.length) return "";
  const labels = {
    sea: "바다·해변",
    food: "맛집·음식",
    nature: "자연·힐링",
    culture: "문화·체험",
  };
  return (
    "# USER THEME\n" +
    `User request themes: ${themes.map((t) => labels[t] || t).join(", ")}.\n` +
    "- option_1 MUST prioritize spots matching these themes from <main_destination>.\n" +
    "- option_2: start with <transit_area> gems, then main destination highlights.\n"
  );
}

function buildKtoDataXml(prompt, maxRows = 8) {
  const regions = regionsInPrompt(prompt);
  const provinceWide = isProvinceWidePrompt(prompt);
  if (!regions.length && !provinceWide) {
    return "<kto_data>\n<!-- region_required: include 시·군 name -->\n</kto_data>";
  }
  const targetRegions = provinceWide ? GANGWON_REGION_NAMES : regions;
  const cap = provinceWide ? Math.max(maxRows, 12) : maxRows;
  const lines = ["<kto_data>"];
  let count = 0;
  const regionList = provinceWide && !regions.length ? targetRegions : targetRegions;
  for (const region of regionList) {
    if (count >= cap) break;
    for (const entry of collectKtoCatalogEntries(region)) {
      if (count >= cap) break;
      const theme = ktoThemeDisplayLabel(entry);
      const visitors = ktoSpotVisitorCount(region, entry.rank, entry);
      const related = (entry.related || []).slice(0, 3).join(", ");
      const attrs = [
        `name="${String(entry.name).replace(/"/g, "&quot;")}"`,
        `region="${region.replace(/(시|군)$/, "")}"`,
        `theme="${theme}"`,
        `visitors="${visitors}"`,
      ];
      if (entry.imageUrl) attrs.push(`image="${String(entry.imageUrl).replace(/"/g, "&quot;")}"`);
      if (related) attrs.push(`related="${related.replace(/"/g, "&quot;")}"`);
      lines.push(`  <spot ${attrs.join(" ")}/>`);
      count++;
    }
  }
  lines.push("</kto_data>");
  return count ? lines.join("\n") : "<kto_data>\n</kto_data>";
}

function hubRankMap(region) {
  const map = new Map();
  collectKtoCatalogEntries(region).forEach((e) => map.set(e.name, e.rank));
  return map;
}

function pickRegionalSpots(regions, limit = 3) {
  if (!regions?.length) return [];
  const region = regions[0];
  let local = ENRICHED_SPOTS.filter((s) => regions.includes(s.region));
  if (local.length) {
    const ranks = hubRankMap(region);
    local = local.slice().sort((a, b) => {
      const ra = ranks.get(a.name) ?? 999;
      const rb = ranks.get(b.name) ?? 999;
      if (ra !== rb) return ra - rb;
      return a.name.localeCompare(b.name, "ko");
    });
    return local.slice(0, limit);
  }
  return collectKtoCatalogEntries(region)
    .slice(0, limit)
    .map((e) => ktoEntryToSpot(e, region));
}

function regionFocusPromptBlock(prompt) {
  const regions = regionsInPrompt(prompt);
  if (!regions.length) return "";
  const multi = isMultiIntentPrompt(prompt);
  const lines = [
    "# REGION FOCUS (STRICT)",
    `User focus region(s): ${regions.join(", ")}.`,
    "- Use ONLY rows inside <kto_data> that match these region(s).",
    "- Rank by 방문자수(빅데이터) within the requested region only.",
  ];
  if (multi) {
    lines.push(
      "- MULTI-INTENT: User wants intro AND itinerary.",
      "- introduction: Step 1 — KTO data-backed regional intro from <kto_data>.",
      "- itinerary: Step 2 — non-empty array from <kto_data> spot names; NEVER skip."
    );
  } else {
    lines.push("- summary: polite Korean (해요체) introducing this region using KTO context — sights, food, mood.");
  }
  lines.push(
    "- spot_name in itinerary MUST be EXACT names from <kto_data> for these region(s).",
    "- Do NOT include spots from other cities/counties unless multi-city was requested."
  );
  return lines.join("\n") + "\n";
}

function pickSpotsForPrompt(prompt, limit = 3) {
  const regions = regionsInPrompt(prompt);
  if (regions.length) {
    const regional = pickRegionalSpots(regions, limit);
    if (regional.length) return regional;
    return [];
  }
  const { scores } = getPromptSpotContext(prompt);
  let ranked = ENRICHED_SPOTS.map((spot, index) => ({ spot, index, score: scores[index] }));
  ranked.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.spot.name.localeCompare(b.spot.name, "ko");
  });
  return ranked.slice(0, limit).map((r) => r.spot);
}

function constrainStepsToRegions(steps, regions, { strict = true } = {}) {
  if (!regions?.length || !steps?.length) return steps;
  const kept = steps.filter((s) => s.spot && regions.includes(s.spot.region));
  const mapSteps = (spotList) =>
    spotList.slice(0, steps.length).map((spot, i) => ({
      order: i + 1,
      day: steps[i]?.day || 1,
      spot,
      stay: spot.stay_min ?? 60,
      why: steps[i]?.why || `${spot.description}. ${spot.tip || ""}`.trim(),
      move_to_next: steps[i]?.move_to_next || "",
    }));
  if (strict && kept.length !== steps.length) {
    const fallback = regionalFallbackSpots(regions, Math.max(steps.length, 3));
    return fallback.length ? mapSteps(fallback) : [];
  }
  if (kept.length) return kept.map((s, i) => ({ ...s, order: i + 1 }));
  const fallback = regionalFallbackSpots(regions, Math.min(steps.length, 3));
  if (!fallback.length) return [];
  return mapSteps(fallback);
}

function formatRelateContextHint(region, relate, maxAnchors = 2) {
  const byAnchor = relate?.by_anchor?.[region];
  if (!byAnchor) return "";
  return Object.entries(byAnchor)
    .slice(0, maxAnchors)
    .map(([anchor, rows]) => {
      const names = (rows || []).slice(0, 2).map((r) => r.name).filter(Boolean);
      return names.length ? `${anchor}→${names.join(", ")}` : "";
    })
    .filter(Boolean)
    .join(" · ");
}

function ktoEntriesBySource(region, sourceLabel) {
  return collectKtoCatalogEntries(region).filter((e) =>
    String(e.source || "").includes(sourceLabel)
  );
}

function buildKtoApiContext(prompt) {
  const regions = regionsInPrompt(prompt);
  const pool = regions.length ? regions : GANGWON_REGION_NAMES.slice(0, 6);
  const stats = typeof TOUR_VISITOR_STATS !== "undefined" ? TOUR_VISITOR_STATS : null;
  const relate = typeof TOUR_RELATE_SPOTS !== "undefined" ? TOUR_RELATE_SPOTS : null;
  const fest = typeof TOUR_KOR_FESTIVALS !== "undefined" ? TOUR_KOR_FESTIVALS : null;
  const lines = ["# KTO API CONTEXT (Gangwon only)"];
  for (const region of pool.slice(0, 6)) {
    const parts = [];
    const vis = stats?.regions?.[region];
    if (vis?.label) parts.push(`방문 ${vis.label}`);
    const hubNames = ktoEntriesBySource(region, "중심").slice(0, 2).map((h) => h.name).filter(Boolean);
    if (hubNames.length) parts.push(`중심관광지 ${hubNames.join(", ")}`);
    const relateHint = formatRelateContextHint(region, relate, 2);
    if (relateHint) parts.push(`연관관광지 ${relateHint}`);
    const korNames = ktoEntriesBySource(region, "공식").slice(0, 2).map((k) => k.name).filter(Boolean);
    if (korNames.length) parts.push(`공식관광지 ${korNames.join(", ")}`);
    const ecoNames = ktoEntriesBySource(region, "생태").slice(0, 2).map((e) => e.name).filter(Boolean);
    if (ecoNames.length) parts.push(`생태관광 ${ecoNames.join(", ")}`);
    const f0 = fest?.regions?.[region]?.[0];
    if (f0?.title) parts.push(`축제 ${f0.title}${f0.period ? ` (${f0.period})` : ""}`);
    if (parts.length) lines.push(`- ${region}: ${parts.join(" | ")}`);
  }
  if (stats?.province?.label) lines.push(`- 강원 전체 방문: ${stats.province.label}`);
  return lines.length > 1 ? lines.join("\n") : "";
}

function outOfGangwonReply(prompt) {
  const msg = String(prompt || "").trim();
  if (!msg) return null;
  if (/강원|춘천|원주|강릉|속초|동해|삼척|태백|홍천|횡성|영월|평창|정선|철원|화천|양구|인제|고성|양양/i.test(msg)) return null;
  if (!/(?:부산|제주|제주도|해운대|서울|경주|여수|대전|대구|인천|광주|울산|명동|홍대|이태원|강남|판교|수원|해외|일본|태국|유럽|미국|중국|베트남)/.test(msg)) return null;
  if (!/(맛집|관광|여행|코스|추천|숙소|호텔|비행기|항공|기차표|날씨|일정|설명|소개|안내|대해)/i.test(msg)) return null;
  if (/부산|해운대/.test(msg)) {
    return (
      "죄송해요, 저는 강원도 지역 관광 및 경제 활성화를 위한 전용 가이드라서 타 지역 정보는 제공하지 않아요. " +
      "아름다운 바다를 즐기고 싶으시다면 강릉 경포대나 속초 해수욕장 주변 해산물 맛집을 추천해 드릴까요?"
    );
  }
  if (/제주/.test(msg)) {
    return (
      "저는 강원도 관광 전문 가이드라서 제주도 관련 정보는 알려드리기 어려워요. " +
      "원주 공항이나 양양 국제공항을 이용한 강원도 여행 계획을 함께 세워볼까요?"
    );
  }
  if (/서울|명동|홍대|이태원|강남/.test(msg)) {
    return (
      "죄송해요, 서울 등 강원도 밖 지역은 안내 범위가 아니에요. " +
      "도심 감성을 원하시면 춘천 명동거리나 원주 뮤지엄산 근처 산책 코스는 어떠세요?"
    );
  }
  return (
    "죄송해요, 저는 강원도 관광 전용 AI라서 해당 지역 정보는 제공하지 않아요. " +
    "강원도 안에서 비슷한 분위기의 장소나 코스를 찾아드릴까요?"
  );
}

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
  communityOpenComments: new Set(),
  spotsFilter: "all",
  pendingView: null,
  kakaoRoute: { path: [], legs: null, stepsKey: "", source: "", loading: false },
};

const VIEW_IDS = new Set(["explore", "spots", "community", "weather", "festivals", "about", "planner", "trips"]);
const VIEW_LS = "voyageai_last_view";
const PENDING_VIEW_LS = "voyageai_pending_view";

function parseViewFromLocation() {
  const hash = window.location.hash.replace(/^#/, "").trim();
  if (VIEW_IDS.has(hash)) return hash;
  const saved = sessionStorage.getItem(VIEW_LS);
  if (saved && VIEW_IDS.has(saved)) return saved;
  return "explore";
}

function updateViewHash(view) {
  const base = window.location.pathname + window.location.search;
  const nextHash = view === "explore" ? "" : `#${view}`;
  const nextUrl = nextHash ? base + nextHash : base;
  if (window.location.pathname + window.location.search + window.location.hash !== nextUrl) {
    history.replaceState({ view }, "", nextUrl);
  }
  sessionStorage.setItem(VIEW_LS, view);
}

const SPOT_THEME_LABELS = {
  all: "전체",
  nature: "자연",
  culture: "문화",
  experience: "체험",
  calm: "힐링",
  night: "야경",
  drive: "드라이브",
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
  if (state.steps.length && !state.chatTyping) appendPlannerOpenButton();
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
  const lines = [];
  if (result.courseOptions?.length > 1) {
    lines.push(`**${result.title}**`, result.summary, `${sourceLabel(result.source)}`);
    if (result.duration) lines.push(`기간: ${result.duration}`);
    for (const opt of result.courseOptions) {
      if (!opt.steps?.length) continue;
      lines.push("", `**${opt.title}** · ${opt.steps.length}곳`);
      if (opt.dayPlans?.length) {
        opt.dayPlans.forEach((d) => {
          lines.push(`- Day ${d.day}: ${d.focus || "일정"}`);
        });
      } else if (opt.summary) {
        lines.push(opt.summary);
      }
      lines.push(opt.steps.map((s) => s.spot.name).join(" → "));
    }
    const active = result.courseOptions.find((o) => o.key === result.activeCourseOption);
    if (active?.steps?.length) {
      lines.push("", `지도에는 **${active.title}** 이 표시됩니다. 플래너에서 1안/2안을 바꿀 수 있어요.`);
      lines.push("아래 **일정·지도 열기** 버튼으로 확인하세요.");
    }
    return lines.join("\n");
  }
  lines.push(
    `**${result.title}**`,
    result.summary,
    `${sourceLabel(result.source)} · ${result.steps.length}곳`
  );
  const names = result.steps.map((s) => s.spot.name).join(" → ");
  if (names) lines.push(names);
  const intent = result.tripIntent || {};
  if (intent.origin) lines.push(`출발: ${intent.origin}`);
  if (intent.transport) lines.push(`이동: ${intent.transport}`);
  if (result.accommodation?.area) {
    lines.push(`숙소: ${result.accommodation.area} ${result.accommodation.type || ""}`.trim());
  }
  if (result.steps.length) {
    lines.push("아래 **일정·지도 열기** 버튼으로 확인하세요.");
  } else {
    lines.push("시·군 이름을 넣어 다시 질문하시면 일정·지도도 만들어 드릴게요.");
  }
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
function toast(msg, opts = {}) {
  const el = $("toast");
  if (!el) return;
  const duration = opts.duration ?? (opts.error ? 6200 : 2600);
  el.textContent = msg;
  el.classList.toggle("toast-error", !!opts.error);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("show");
    if (opts.error) el.classList.remove("toast-error");
  }, duration);
}

/* ==================== View routing ==================== */
function syncBodyMode(view) {
  document.body.classList.toggle("mode-landing", view === "explore");
  document.body.classList.toggle(
    "mode-planner",
    view === "planner" || view === "community" || view === "trips" || view === "spots" || view === "weather" || view === "festivals" || view === "about"
  );
}

function updateSidebar(view) {
  document.querySelectorAll(".app-tab[data-nav]").forEach((el) => {
    el.classList.toggle("on", el.dataset.nav === view);
  });
}

function closeProfileMenu() {
  $("profile-dropdown")?.classList.add("hidden");
  $("profile-trigger")?.setAttribute("aria-expanded", "false");
}

function toggleProfileMenu() {
  const dd = $("profile-dropdown");
  const trigger = $("profile-trigger");
  if (!dd || !trigger) return;
  const willOpen = dd.classList.contains("hidden");
  if (willOpen) {
    dd.classList.remove("hidden");
    trigger.setAttribute("aria-expanded", "true");
  } else {
    closeProfileMenu();
  }
}

function show(view, opts = {}) {
  if (view === "planner" && !state.steps.length && !isLoggedIn()) {
    toast("내 일정은 로그인 후 이용할 수 있어요.");
    state.pendingView = "planner";
    openLoginModal();
    return;
  }
  if (view === "trips" && !isLoggedIn()) {
    toast("찜 목록은 로그인 후 이용할 수 있어요.");
    state.pendingView = "trips";
    openLoginModal();
    return;
  }
  state.pendingView = null;
  sessionStorage.removeItem(PENDING_VIEW_LS);
  state.view = view;
  closeProfileMenu();
  closeProfileModal();
  syncBodyMode(view);
  $("view-explore")?.classList.toggle("hidden", view !== "explore");
  $("view-spots")?.classList.toggle("hidden", view !== "spots");
  $("view-weather")?.classList.toggle("hidden", view !== "weather");
  $("view-festivals")?.classList.toggle("hidden", view !== "festivals");
  $("view-about")?.classList.toggle("hidden", view !== "about");
  $("view-planner")?.classList.toggle("hidden", view !== "planner");
  $("view-community")?.classList.toggle("hidden", view !== "community");
  $("view-trips")?.classList.toggle("hidden", view !== "trips");
  updateSidebar(view);
  if (!opts.skipHash) updateViewHash(view);

  if (view === "explore") {
    ensureAgentWelcome();
    renderAgentChat();
    initLandingMap();
  } else if (view === "spots") {
    pauseLandingMap();
    renderSpots();
  } else if (view === "weather") {
    pauseLandingMap();
    renderWeather().catch((err) => console.warn("renderWeather:", err));
  } else if (view === "festivals") {
    pauseLandingMap();
    renderFestivals();
  } else if (view === "about") {
    pauseLandingMap();
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
  window.scrollTo(0, 0);
}

document.addEventListener("click", (e) => {
  if (!e.target.closest("#profile-menu")) closeProfileMenu();

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

  const spotsFilterBtn = e.target.closest("[data-spots-filter]");
  if (spotsFilterBtn) {
    e.preventDefault();
    state.spotsFilter = spotsFilterBtn.dataset.spotsFilter || "all";
    renderSpots();
    return;
  }

  const spotCard = e.target.closest("[data-spot-prompt]");
  if (spotCard) {
    e.preventDefault();
    const prompt = decodeURIComponent(spotCard.dataset.spotPrompt || "");
    if (prompt) {
      show("explore");
      submitAgentPrompt(prompt);
    }
    return;
  }

  const openPlannerBtn = e.target.closest("#chat-open-planner, .chat-open-planner");
  if (openPlannerBtn) {
    e.preventDefault();
    if (state.steps.length) {
      show("planner");
      renderPlanner();
    }
    return;
  }

  const festCard = e.target.closest("[data-fest-prompt]");
  if (festCard) {
    e.preventDefault();
    const prompt = decodeURIComponent(festCard.dataset.festPrompt || "");
    if (prompt) {
      show("explore");
      submitAgentPrompt(prompt);
    }
    return;
  }

  const deleteBtn = e.target.closest("[data-delete-post]");
  if (deleteBtn) {
    e.preventDefault();
    deleteCommunityPost(deleteBtn.dataset.deletePost);
    return;
  }

  const toggleCommentsBtn = e.target.closest("[data-toggle-comments]");
  if (toggleCommentsBtn) {
    e.preventDefault();
    toggleCommunityComments(toggleCommentsBtn.dataset.toggleComments);
    return;
  }

  const deleteCommentBtn = e.target.closest("[data-delete-comment]");
  if (deleteCommentBtn) {
    e.preventDefault();
    deleteCommunityComment(deleteCommentBtn.dataset.deleteComment);
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

document.addEventListener("submit", (e) => {
  const form = e.target.closest("[data-comment-form]");
  if (!form) return;
  e.preventDefault();
  const postId = form.dataset.postId || "";
  const input = form.querySelector("textarea");
  submitCommunityComment(postId, input?.value || "");
  if (input) input.value = "";
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

let wxCache = null;
let wxCacheAt = 0;
let wxLoading = false;
const WX_TTL_MS = 10 * 60 * 1000;
const WX_CHUNK_SIZE = 6;

function isWeatherCacheFresh() {
  if (!wxCache || wxCache.length !== GANGWON_CITIES.length) return false;
  if (!wxCacheAt || Date.now() - wxCacheAt > WX_TTL_MS) return false;
  return wxCache.every((c) => c.updatedAt && Number.isFinite(c.temp));
}

function formatWeatherUpdated(cities) {
  const stamp = cities.find((c) => c.updatedAt)?.updatedAt;
  const now = new Date();
  const refreshed = `${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}`;
  if (stamp) {
    const observed = stamp.slice(11, 16);
    return `${observed} 관측 · ${refreshed} 갱신`;
  }
  return `${refreshed} 갱신`;
}

async function fetchOpenMeteo(url) {
  const r = await fetch(`${url}&_=${Date.now()}`, { cache: "no-store" });
  if (!r.ok) throw new Error("weather http " + r.status);
  return r.json();
}

function parseWeatherEntry(entry) {
  const temp = Math.round(Number(entry?.current?.temperature_2m ?? NaN));
  const code = Number(entry?.current?.weather_code ?? 3);
  const hi = entry?.daily?.temperature_2m_max?.[0];
  const lo = entry?.daily?.temperature_2m_min?.[0];
  const cond = wmoToCondition(code);
  const meta = WEATHER_ICONS[cond] || WEATHER_ICONS.cloudy;
  return {
    temp: Number.isFinite(temp) ? temp : null,
    cond,
    icon: meta.icon,
    bg: meta.bg,
    label: meta.label,
    range: hi != null && lo != null ? `${Math.round(lo)}° ~ ${Math.round(hi)}°` : "",
    tip: weatherTip(Number.isFinite(temp) ? temp : 0, cond, hi, lo),
    updatedAt: entry?.current?.time || "",
  };
}

function mapWeatherChunk(cities, entries) {
  const list = Array.isArray(entries) ? entries : [entries];
  const ordered =
    list.length === cities.length
      ? list
      : [...list].sort((a, b) => (a.location_id ?? 0) - (b.location_id ?? 0));
  return cities.map((c, i) => {
    const parsed = parseWeatherEntry(ordered[i]);
    if (!Number.isFinite(parsed.temp)) throw new Error(`weather missing ${c.city}`);
    return { city: c.city, ...parsed, temp: parsed.temp };
  });
}

async function fetchWeatherChunk(cities) {
  const lats = cities.map((c) => c.lat).join(",");
  const lngs = cities.map((c) => c.lng).join(",");
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lngs}` +
    `&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min` +
    `&timezone=Asia%2FSeoul&forecast_days=1`;
  const payload = await fetchOpenMeteo(url);
  return mapWeatherChunk(cities, payload);
}

async function fetchCityWeather(c) {
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${c.lat}&longitude=${c.lng}` +
    `&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min` +
    `&timezone=Asia%2FSeoul&forecast_days=1`;
  const d = await fetchOpenMeteo(url);
  const parsed = parseWeatherEntry(d);
  if (!Number.isFinite(parsed.temp)) throw new Error(`weather missing ${c.city}`);
  return { city: c.city, ...parsed, temp: parsed.temp };
}

async function fetchAllGangwonWeather() {
  const chunks = [];
  for (let i = 0; i < GANGWON_CITIES.length; i += WX_CHUNK_SIZE) {
    chunks.push(GANGWON_CITIES.slice(i, i + WX_CHUNK_SIZE));
  }

  try {
    const parts = await Promise.all(chunks.map((group) => fetchWeatherChunk(group)));
    return parts.flat();
  } catch (err) {
    console.warn("weather chunk fetch:", err);
  }

  const results = await Promise.allSettled(GANGWON_CITIES.map(fetchCityWeather));
  const cities = results.filter((x) => x.status === "fulfilled").map((x) => x.value);
  if (cities.length !== GANGWON_CITIES.length) {
    throw new Error(`weather partial ${cities.length}/${GANGWON_CITIES.length}`);
  }
  return cities;
}

function weatherSkeletonHtml() {
  return GANGWON_CITIES.map(
    (c) =>
      `<article class="weather-card weather-skeleton" aria-hidden="true">` +
      `<div class="weather-card-icon"></div>` +
      `<div class="weather-card-body">` +
      `<h3>${esc(c.city)}</h3>` +
      `<p class="weather-card-temp">--°</p>` +
      `<p class="weather-card-label">불러오는 중…</p>` +
      `</div></article>`
  ).join("");
}

function renderWeatherGrid(cities) {
  const grid = $("weather-grid");
  if (!grid) return;
  grid.innerHTML = cities
    .map(
      (c) =>
        `<article class="weather-card weather-card-${esc(c.cond)}">` +
        `<div class="weather-card-icon" style="background:${c.bg}">${c.icon}</div>` +
        `<div class="weather-card-body">` +
        `<h3>${esc(c.city)}</h3>` +
        `<p class="weather-card-temp">${c.temp}<span>°C</span></p>` +
        `<p class="weather-card-label">${esc(c.label)}</p>` +
        (c.range ? `<p class="weather-card-range">${esc(c.range)}</p>` : "") +
        `<p class="weather-card-tip">${esc(c.tip)}</p>` +
        `</div></article>`
    )
    .join("");
}

async function renderWeather(force) {
  const grid = $("weather-grid");
  const updated = $("weather-updated");
  if (!grid) return;

  if (!force && isWeatherCacheFresh()) {
    renderWeatherGrid(wxCache);
    if (updated) updated.textContent = formatWeatherUpdated(wxCache);
    return;
  }
  if (wxLoading && !force) return;
  wxLoading = true;

  grid.innerHTML = weatherSkeletonHtml();
  if (updated) updated.textContent = "동기화 중…";

  try {
    const results = await fetchAllGangwonWeather();
    wxCache = results;
    wxCacheAt = Date.now();
    if (updated) updated.textContent = formatWeatherUpdated(wxCache);
    renderWeatherGrid(wxCache);
  } catch (err) {
    console.warn("renderWeather:", err);
    wxCache = null;
    wxCacheAt = 0;
    grid.innerHTML =
      `<div class="weather-empty">` +
      `<p>날씨 정보를 불러오지 못했어요.<br>네트워크 연결 후 다시 시도해 주세요.</p>` +
      `<button type="button" class="btn-secondary" id="weather-retry">다시 동기화</button>` +
      `</div>`;
    if (updated) updated.textContent = "동기화 실패";
    $("weather-retry")?.addEventListener("click", () => {
      renderWeather(true).catch((e) => console.warn("renderWeather retry:", e));
    });
  } finally {
    wxLoading = false;
  }
}

/* ==================== Festivals catalog ==================== */
function getFestivalsCatalog() {
  if (typeof TOUR_KOR_FESTIVALS !== "undefined" && Array.isArray(TOUR_KOR_FESTIVALS.items)) {
    return TOUR_KOR_FESTIVALS.items.map((f) => ({ ...f, source: "api" }));
  }
  return [];
}

function renderFestivals() {
  const grid = $("festivals-grid");
  if (!grid) return;
  const catalog = getFestivalsCatalog();
  const totalEl = $("festivals-total");
  if (totalEl) totalEl.textContent = String(catalog.length);
  if (!catalog.length) {
    grid.innerHTML =
      `<div class="festivals-empty">` +
      `<p>KTO API에서 불러온 축제 정보가 없어요.</p>` +
      `<p class="festivals-empty-hint">배포 시 TourAPI 키가 설정되면 자동으로 표시됩니다.</p>` +
      `</div>`;
    return;
  }
  const grads = FEST_FALLBACK_GRADS;
  grid.innerHTML = catalog.map((f, i) => {
    const prompt = pillPromptAttr(`${f.title}(${f.place}) 포함 강원 여행 코스 추천해줘`);
    const grad = grads[i % grads.length];
    const icon = FESTIVAL_ICONS[i % FESTIVAL_ICONS.length];
    const festCandidates = collectFestivalImageCandidates(f);
    const thumb = festCandidates.length
      ? imgWithFallback(festCandidates, {
          className: "fest-card-thumb",
          fbKind: "fest",
          fbGrad: grad,
          fbIcon: icon,
        })
      : `<span class="fest-card-icon" style="background:${grad}">${icon}</span>`;
    return (
      `<button type="button" class="fest-card" data-fest-prompt="${prompt}">` +
      thumb +
      `<strong>${esc(f.title)}</strong>` +
      `<span class="fest-card-meta">${esc(f.place)} · ${esc(f.period)}</span>` +
      (f.desc ? `<span class="fest-card-desc">${esc(f.desc)}</span>` : "") +
      `<span class="fest-card-cta"><span class="vico vico-action" data-vico="ai"></span> AI 코스 만들기</span>` +
      `</button>`
    );
  }).join("");
  initIcons();
}

/* ==================== Kakao routing (SSOT — no straight-line math) ==================== */
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

function fmtKm(km) {
  return km < 1 ? `${Math.round(km * 1000)}m` : `${km.toFixed(km < 10 ? 1 : 0)}km`;
}

function fmtMin(m) {
  if (m < 60) return `${m}분`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h}시간 ${r}분` : `${h}시간`;
}

function stepsRouteKey(steps) {
  return steps.map((s) => `${s.spot?.lat},${s.spot?.lng}`).join("|");
}

function routePointsFromSpots(spots) {
  return spots
    .filter((s) => Number.isFinite(s?.lat) && Number.isFinite(s?.lng))
    .map((s) => ({ spot: s, lng: s.lng, lat: s.lat, name: s.name }));
}

function routePointsFromSteps(steps) {
  return steps
    .filter((s) => Number.isFinite(s.spot?.lat) && Number.isFinite(s.spot?.lng))
    .map((s) => ({ step: s, lng: s.spot.lng, lat: s.spot.lat, name: s.spot.name }));
}

function kakaoRestKey() {
  const raw =
    typeof window !== "undefined" ? window.KAKAO_REST_KEY || window.KAKAO_NAVI_KEY || "" : "";
  return normalizeKakaoKey(raw);
}

function kakaoDirectionsParams(points) {
  const origin = points[0];
  const destination = points[points.length - 1];
  const middle = points.slice(1, -1);
  const params = new URLSearchParams({
    origin: `${origin.lng},${origin.lat}`,
    destination: `${destination.lng},${destination.lat}`,
    priority: "RECOMMEND",
  });
  if (middle.length) {
    params.set("waypoints", middle.map((p) => `${p.lng},${p.lat}`).join("|"));
  }
  return params;
}

async function fetchKakaoViaSupabaseProxy(points) {
  if (typeof hasSupabase !== "function" || !hasSupabase()) return null;
  const base = String(window.SUPABASE_URL || "").replace(/\/$/, "");
  const anon = String(window.SUPABASE_ANON_KEY || "");
  if (!base || !anon) return null;
  try {
    const r = await fetch(
      `${base}/functions/v1/kakao-directions?${kakaoDirectionsParams(points)}`,
      {
        headers: {
          Authorization: `Bearer ${anon}`,
          apikey: anon,
        },
      }
    );
    if (!r.ok) {
      const detail = await r.text().catch(() => "");
      if (r.status === 404) {
        console.warn(
          "[Kakao proxy] Edge Function kakao-directions 미배포(404). " +
            "Supabase에서 `supabase functions deploy kakao-directions --no-verify-jwt` 실행 필요. OSRM 폴백 사용."
        );
      } else {
        console.warn("[Kakao proxy]", r.status, detail.slice(0, 200));
      }
      return null;
    }
    return r.json();
  } catch (e) {
    console.warn("[Kakao proxy] fetch failed", e);
    return null;
  }
}

async function fetchKakaoDirectionsDirect(points) {
  const key = kakaoRestKey();
  if (!key) return null;
  try {
    const r = await fetch(
      `https://apis-navi.kakaomobility.com/v1/directions?${kakaoDirectionsParams(points)}`,
      { headers: { Authorization: `KakaoAK ${key}` } }
    );
    if (!r.ok) {
      const detail = await r.text().catch(() => "");
      console.warn("[Kakao Directions]", r.status, detail.slice(0, 200));
      return null;
    }
    return r.json();
  } catch (e) {
    console.warn("[Kakao Directions] CORS/network — Supabase 프록시 또는 OSRM 폴백 사용", e);
    return null;
  }
}

async function fetchKakaoDirectionsRaw(points) {
  if (points.length < 2) return null;
  if (points.length > KAKAO_MAX_ROUTE_POINTS) return null;
  return (await fetchKakaoViaSupabaseProxy(points)) || (await fetchKakaoDirectionsDirect(points));
}

async function fetchOsrmLeg(from, to) {
  const coords = `${from.lng},${from.lat};${to.lng},${to.lat}`;
  const url =
    `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`;
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    const data = await r.json();
    const route = data.routes?.[0];
    if (!route) return null;
    const leg = route.legs?.[0];
    return {
      distance_m: leg?.distance ?? route.distance ?? 0,
      duration_s: leg?.duration ?? route.duration ?? 0,
      coordinates: route.geometry?.coordinates || [],
    };
  } catch (e) {
    console.warn("[OSRM]", e);
    return null;
  }
}

function parseOsrmRoutePlan(spots, segments) {
  const legs = [];
  const polyline = [];
  let totalDist = 0;
  let totalDur = 0;
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    const distM = seg.distance_m || 0;
    const durS = seg.duration_s || 0;
    const km = distM / 1000;
    const driveMin = distM < 30 ? 0 : Math.max(1, Math.round(durS / 60));
    totalDist += distM;
    totalDur += durS;
    for (const c of seg.coordinates || []) {
      if (c.length >= 2) polyline.push({ lng: c[0], lat: c[1] });
    }
    const moveLabel =
      driveMin > 0
        ? `${spots[i + 1].name}까지 ${fmtKm(km)} · 차량 약 ${fmtMin(driveMin)} (도로 추정)`
        : `${spots[i + 1].name}까지 도보권`;
    legs.push({
      from_name: spots[i].name,
      to_name: spots[i + 1].name,
      distance_km: km,
      distance_m: distM,
      duration_min: driveMin,
      duration_s: durS,
      summary: moveLabel,
    });
  }
  return {
    spots,
    legs,
    polyline,
    totals: {
      km: totalDist / 1000,
      min: Math.round(totalDur / 60),
      distance_m: totalDist,
      duration_s: totalDur,
    },
    provider: "osrm",
  };
}

async function buildOsrmRoutePlan(spots) {
  const points = routePointsFromSpots(spots);
  if (points.length < 2) return null;
  const segments = [];
  for (let i = 0; i < points.length - 1; i++) {
    if (i > 0 && i % 4 === 0) await new Promise((r) => setTimeout(r, 150));
    const seg = await fetchOsrmLeg(points[i], points[i + 1]);
    if (!seg) return null;
    segments.push(seg);
  }
  return parseOsrmRoutePlan(
    points.map((p) => p.spot),
    segments
  );
}

function mergeRoutePolylines(parts) {
  const out = [];
  for (const part of parts) {
    for (const p of part) {
      const prev = out[out.length - 1];
      if (prev && prev.lat === p.lat && prev.lng === p.lng) continue;
      out.push(p);
    }
  }
  return out;
}

async function buildKakaoRoutePlanChained(spots) {
  const points = routePointsFromSpots(spots);
  if (points.length < 2) return null;
  const spotList = points.map((p) => p.spot);
  const allLegs = [];
  const polyParts = [];
  let totalDist = 0;
  let totalDur = 0;

  for (let start = 0; start < points.length - 1; start += KAKAO_MAX_ROUTE_POINTS - 1) {
    const end = Math.min(start + KAKAO_MAX_ROUTE_POINTS - 1, points.length - 1);
    const chunk = points.slice(start, end + 1);
    const chunkSpots = chunk.map((p) => p.spot);
    const data = await fetchKakaoDirectionsRaw(chunk);
    if (!data) return null;
    const plan = parseKakaoRoutePlan(chunkSpots, data);
    if (!plan?.legs?.length) return null;
    allLegs.push(...plan.legs);
    polyParts.push(plan.polyline || []);
    for (const leg of plan.legs) {
      totalDist += leg.distance_m || 0;
      totalDur += leg.duration_s || 0;
    }
  }

  return {
    spots: spotList,
    legs: allLegs,
    polyline: mergeRoutePolylines(polyParts),
    totals: {
      km: totalDist / 1000,
      min: Math.round(totalDur / 60),
      distance_m: totalDist,
      duration_s: totalDur,
    },
    provider: "kakao",
  };
}

function parseKakaoRoutePlan(spots, kakaoData) {
  const route = kakaoData?.routes?.[0];
  if (!route) return null;

  const polyline = [];
  for (const section of route.sections || []) {
    for (const road of section.roads || []) {
      const v = road.vertexes || [];
      for (let i = 0; i + 1 < v.length; i += 2) {
        polyline.push({ lng: v[i], lat: v[i + 1] });
      }
    }
  }

  const legs = [];
  for (let i = 0; i < spots.length - 1; i++) {
    const sec = route.sections?.[i];
    if (!sec) break;
    const distM = sec.distance || 0;
    const durS = sec.duration || 0;
    const km = distM / 1000;
    const driveMin = distM < 30 ? 0 : Math.max(1, Math.round(durS / 60));
    legs.push({
      from_name: spots[i].name,
      to_name: spots[i + 1].name,
      distance_km: km,
      distance_m: distM,
      duration_min: driveMin,
      duration_s: durS,
      summary:
        driveMin > 0
          ? `${spots[i + 1].name}까지 ${fmtKm(km)} · 차량 약 ${fmtMin(driveMin)} (카카오)`
          : `${spots[i + 1].name}까지 도보권`,
    });
  }

  const summary = route.summary || {};
  return {
    spots,
    legs,
    polyline,
    totals: {
      km: (summary.distance || 0) / 1000,
      min: Math.round((summary.duration || 0) / 60),
      distance_m: summary.distance || 0,
      duration_s: summary.duration || 0,
    },
    provider: "kakao",
  };
}

async function buildRoutePlan(spots) {
  const points = routePointsFromSpots(spots);
  if (points.length < 2) return null;
  const spotList = points.map((p) => p.spot);

  if (points.length <= KAKAO_MAX_ROUTE_POINTS) {
    const kakaoData = await fetchKakaoDirectionsRaw(points);
    if (kakaoData) {
      const plan = parseKakaoRoutePlan(spotList, kakaoData);
      if (plan) return plan;
    }
  } else {
    const chained = await buildKakaoRoutePlanChained(spots);
    if (chained) return chained;
  }
  return buildOsrmRoutePlan(spots);
}

async function buildKakaoRoutePlan(spots) {
  return buildRoutePlan(spots);
}

function spotsFromSteps(steps) {
  return routePointsFromSteps(steps).map((p) => p.spot);
}

let routeRefreshGen = 0;

async function refreshRouteForSteps(steps) {
  const points = routePointsFromSteps(steps);
  if (points.length < 2) {
    resetKakaoRouteState();
    return;
  }
  const key = stepsRouteKey(steps);
  const expectedLegs = points.length - 1;
  if (
    state.kakaoRoute.stepsKey === key &&
    !state.kakaoRoute.loading &&
    (state.kakaoRoute.legs?.length || 0) >= expectedLegs
  ) {
    return;
  }
  if (state.kakaoRoute.stepsKey === key && state.kakaoRoute.loading) return;

  const gen = ++routeRefreshGen;
  state.kakaoRoute = {
    path: state.kakaoRoute.path || [],
    legs: state.kakaoRoute.legs,
    stepsKey: key,
    source: state.kakaoRoute.source || "",
    loading: true,
  };
  if (stepsRouteKey(state.steps) === key) {
    renderRouteSummary([]);
    const chip = $("chip-route");
    if (chip) chip.textContent = "🧭 경로 계산 중…";
  }

  const spots = points.map((p) => p.spot);
  let plan = null;
  try {
    plan = await buildRoutePlan(spots);
  } catch (e) {
    console.warn("[Route refresh]", e);
  }

  if (gen !== routeRefreshGen) return;
  if (stepsRouteKey(state.steps) !== key) return;

  if (plan) {
    applyRoutePlanToState(plan, state.steps);
  } else {
    state.kakaoRoute = {
      path: [],
      legs: [],
      stepsKey: key,
      source: "",
      loading: false,
    };
  }

  const legs = getRouteLegs(state.steps);
  renderRouteSummary(legs);
  renderCourses(legs);
  updateMapChrome();
  renderSpotDetail();
  renderMap();
}

function formatRoutingContextForGemini(plan) {
  if (!plan?.legs?.length) {
    return (
      "# ROUTING DATA\n" +
      "Route planner unavailable. Write copy only; do not invent driving times.\n"
    );
  }
  const engine =
    plan.provider === "kakao"
      ? "Kakao Mobility"
      : plan.provider === "osrm"
        ? "OSRM road estimate"
        : "Route engine";
  const lines = [
    `# ROUTING DATA (${engine} — IMMUTABLE)`,
    "Pre-calculated driving times for Gangwon-do roads. Do NOT invent distance or duration.",
    "",
    `Total driving: ${fmtKm(plan.totals.km)}, ${fmtMin(plan.totals.min)}`,
    "",
    "Legs:",
  ];
  plan.legs.forEach((leg, i) => {
    lines.push(
      `${i + 1}. ${leg.from_name} -> ${leg.to_name}: ` +
        `Driving time ${leg.duration_min} mins, Distance ${fmtKm(leg.distance_km)}`
    );
  });
  lines.push("", "Fixed stop order (spot_name MUST match exactly):");
  plan.spots.forEach((s, i) => {
    lines.push(`  ${i + 1}. ${s.name}${s.region ? ` (${s.region})` : ""}`);
  });
  return lines.join("\n");
}

function legsFromRoutePlan(routePlan, steps) {
  if (!routePlan?.legs?.length) return [];
  const rows = routePointsFromSteps(steps);
  return routePlan.legs
    .map((leg, i) => {
      const fromStep = rows[i]?.step;
      const toStep = rows[i + 1]?.step;
      if (!fromStep || !toStep) return null;
      fromStep.move_to_next = leg.summary;
      return {
        from: fromStep,
        to: toStep,
        km: leg.distance_km,
        driveMin: leg.duration_min,
        note: leg.summary,
        kakao: routePlan.provider === "kakao",
        provider: routePlan.provider || "kakao",
        transit: fromStep.kind === "origin",
      };
    })
    .filter(Boolean);
}

function applyRoutePlanToState(routePlan, steps) {
  if (!routePlan) {
    resetKakaoRouteState();
    return;
  }
  state.kakaoRoute = {
    path: routePlan.polyline || [],
    legs: legsFromRoutePlan(routePlan, steps),
    stepsKey: stepsRouteKey(steps),
    source: routePlan.provider || "kakao",
    loading: false,
  };
}

function resetKakaoRouteState() {
  state.kakaoRoute = { path: [], legs: null, stepsKey: "", source: "", loading: false };
}

function getRouteLegs(steps) {
  const key = stepsRouteKey(steps);
  if (state.kakaoRoute.stepsKey === key && Array.isArray(state.kakaoRoute.legs)) {
    return state.kakaoRoute.legs;
  }
  return [];
}

function routeDurationLabel(totals) {
  if (!totals?.min) return "";
  return totals.min <= 300 ? "반나절 코스" : "당일 코스";
}

function buildStepsFromRoutePlan(routePlan, parsed, prompt) {
  const regions = strictRegionsForCuration(prompt, parsed.introduction || "");
  const whyByName = {};
  for (const item of parsed.stop_narratives || parsed.itinerary || []) {
    if (item.spot_name) whyByName[item.spot_name] = item.why || item.reason;
  }
  return routePlan.spots
    .map((spot, i) => {
      const resolved =
        resolveSpotByName(spot.name, regions, { strict: true }) ||
        (spot.lat != null ? spot : null);
      if (!resolved) return null;
      return {
        order: i + 1,
        day: 1,
        spot: resolved,
        stay: resolved.stay_min ?? 60,
        why: whyByName[spot.name] || `${spot.name} — KTO 추천`,
        move_to_next: routePlan.legs[i]?.summary || "",
      };
    })
    .filter(Boolean);
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
const SPOT_SEARCH_BLOBS = ENRICHED_SPOTS.map(
  (s) => `${s.name} ${s.region} ${s.theme} ${s.description || ""}`
);
const SPOT_FUZZY_LIST = ENRICHED_SPOTS.slice().sort((a, b) => b.name.length - a.name.length);
const TRANSIT_ORIGIN_MATCHES = (() => {
  const origins = typeof TRANSIT_ORIGINS !== "undefined" ? TRANSIT_ORIGINS : {};
  return Object.keys(origins)
    .sort((a, b) => b.length - a.length)
    .map((name) => ({ name, short: name.replace(/[시군구]/g, "") }));
})();
const MAX_SPOTS_IN_PROMPT = 12;
const PROMPT_SCORE_CACHE_MAX = 48;
const promptSpotScoreCache = new Map();

function tokenizeSearchKeywords(prompt) {
  const words = String(prompt).replace(/,/g, " ").split(/\s+/).filter((w) => w.length >= 2);
  const fromRegions = regionsInPrompt(prompt).flatMap((r) => [r, r.replace(/[시군]$/, "")]);
  return [...new Set([...words, ...fromRegions])];
}

function expandThemeSearchTerms(themes) {
  const terms = themes.slice();
  if (themes.includes("바다")) terms.push("해변", "해수욕", "서핑", "바다");
  return terms;
}

function computeSpotScores(keywords, themeTerms = [], themeWeight = 2) {
  const scores = new Array(ENRICHED_SPOTS.length);
  for (let i = 0; i < ENRICHED_SPOTS.length; i++) {
    const blob = SPOT_SEARCH_BLOBS[i];
    let score = 0;
    for (let k = 0; k < keywords.length; k++) {
      if (blob.includes(keywords[k])) score++;
    }
    for (let t = 0; t < themeTerms.length; t++) {
      if (blob.includes(themeTerms[t])) score += themeWeight;
    }
    scores[i] = score;
  }
  return scores;
}

function getPromptSpotContext(prompt) {
  const key = normalizePromptKey(prompt);
  let ctx = promptSpotScoreCache.get(key);
  if (ctx) return ctx;
  const keywords = tokenizeSearchKeywords(prompt);
  const themes = detectThemes(prompt);
  const themeTerms = expandThemeSearchTerms(themes);
  ctx = { keywords, themes, themeTerms, scores: computeSpotScores(keywords, themeTerms) };
  if (promptSpotScoreCache.size >= PROMPT_SCORE_CACHE_MAX) promptSpotScoreCache.clear();
  promptSpotScoreCache.set(key, ctx);
  return ctx;
}

/** O(N) — full sort 없이 상위 점수 요약 */
function summarizeSpotScores(scores) {
  let top = 0;
  let second = 0;
  let third = 0;
  let strongHits = 0;
  for (let i = 0; i < scores.length; i++) {
    const s = scores[i];
    if (s >= 2) strongHits++;
    if (s > top) {
      third = second;
      second = top;
      top = s;
    } else if (s > second) {
      third = second;
      second = s;
    } else if (s > third) {
      third = s;
    }
  }
  return { topScore: top, strongHits, top3Sum: top + second + third };
}

function rankSpotIndices(scores, limit = ENRICHED_SPOTS.length, regionTieBreak = false) {
  const ranked = [];
  for (let i = 0; i < scores.length; i++) {
    ranked.push({ score: scores[i], index: i });
  }
  ranked.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const spotA = ENRICHED_SPOTS[a.index];
    const spotB = ENRICHED_SPOTS[b.index];
    if (regionTieBreak) return spotA.region.localeCompare(spotB.region);
    return spotA.name.localeCompare(spotB.name);
  });
  return ranked.slice(0, limit);
}

function matchTransitOrigin(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  const origins = typeof TRANSIT_ORIGINS !== "undefined" ? TRANSIT_ORIGINS : {};
  if (origins[raw]) return { label: raw, data: origins[raw] };
  for (let i = 0; i < TRANSIT_ORIGIN_MATCHES.length; i++) {
    const { name, short } = TRANSIT_ORIGIN_MATCHES[i];
    if (raw.includes(name) || (short.length >= 2 && raw.includes(short))) {
      return { label: name, data: origins[name] };
    }
  }
  return null;
}
const GEMINI_MIN_GAP_MS = 8000;
const GEMINI_USER_PROMPT_MAX_CHARS = 4000;
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

const curationCache = new Map(Object.entries(loadPersistedCache()));

function saveCurationCache(prompt, result) {
  const k = normalizePromptKey(prompt);
  curationCache.set(k, result);
  persistCacheEntry(k, result);
}

function scoreLocalMatch(prompt) {
  const { keywords, scores } = getPromptSpotContext(prompt);
  if (!keywords.length) return { topScore: 0, strongHits: 0, top3Sum: 0 };
  return summarizeSpotScores(scores);
}

const COMPLEX_PROMPT_RE = [
  /1박\s*2일|2박\s*3일|3박\s*4일|당일치기|무박|숙박|\d+박/i,
  /대중교통|KTX|기차|버스|열차|지하철|SRT|ITX|무궁화|고속버스/i,
  /에서\s*출발|출발|(?:경기(?:도)?|서울|인천|부산|대전|광주|수원|대구|의정부)/i,
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
  const hit = matchTransitOrigin(prompt);
  if (hit) return hit.label;
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
  return matchTransitOrigin(originText);
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
  const regions = regionsInPrompt(prompt);
  if (regions.length && hasTripPlanIntent(prompt)) return true;
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

function isBilling429(detail) {
  return /prepay|credit.*deplet|billing|purchase|payment|depleted/i.test(detail || "");
}

async function waitGeminiSlot() {
  const wait = GEMINI_MIN_GAP_MS - (Date.now() - lastGeminiAt);
  if (wait > 0) await new Promise((res) => setTimeout(res, wait));
  lastGeminiAt = Date.now();
}

function clampPromptForGemini(prompt) {
  const raw = String(prompt || "").trim();
  if (raw.length <= GEMINI_USER_PROMPT_MAX_CHARS) {
    return { text: raw, truncated: false, originalLength: raw.length };
  }
  const head = Math.floor(GEMINI_USER_PROMPT_MAX_CHARS * 0.8);
  const tail = GEMINI_USER_PROMPT_MAX_CHARS - head - 32;
  const omitted = Math.max(0, raw.length - head - tail);
  const text =
    raw.slice(0, head) +
    `\n\n[중간 ${omitted}자 생략]\n\n` +
    raw.slice(-tail);
  return { text, truncated: true, originalLength: raw.length };
}

function describeGeminiFailure(e) {
  const d = String(e?.detail || e?.message || "");
  const status = Number(e?.status) || 0;

  if (status === 429 || /RESOURCE_EXHAUSTED|quota/i.test(d)) {
    if (isBilling429(d)) {
      return {
        reason: "Google AI 할당량(RPM/TPM)을 모두 썼기",
        action: "Google AI Studio에서 사용량을 확인한 뒤 1~2분 후 다시 시도해 주세요",
      };
    }
    return {
      reason: "요청이 API 한도를 초과했기",
      action: "1~2분 기다린 후 다시 시도해 주세요",
    };
  }
  if (status === 503 || /high demand|UNAVAILABLE|overloaded/i.test(d)) {
    return {
      reason: "선택한 Gemini 모델 서버가 일시적으로 과부하 상태이기",
      action: "잠시 후 다시 시도하거나 다른 모델로 자동 전환될 때까지 기다려 주세요",
    };
  }
  if (status === 403) {
    return {
      reason: "API 키 HTTP 리퍼러 제한에 걸렸기",
      action: "Google AI Studio에서 github.io 도메인을 허용한 뒤 다시 시도해 주세요",
    };
  }
  if (status === 400) {
    return {
      reason: "AI 요청 형식에 문제가 있기",
      action: "질문을 짧게 바꿔 다시 시도해 주세요",
    };
  }
  if (status === 404) {
    return {
      reason: "AI 모델을 찾지 못했기",
      action: "잠시 후 다시 시도해 주세요",
    };
  }
  if (/token limit|MAX_TOKENS/i.test(d)) {
    return {
      reason: "응답 길이가 한도에 걸렸기",
      action: "일정 일수를 줄이거나 질문을 나눠 다시 시도해 주세요",
    };
  }
  if (/no spots matched/i.test(d)) {
    return {
      reason: "AI가 등록된 장소명과 맞지 않았기",
      action: "다른 지역·조건으로 다시 질문해 주세요",
    };
  }
  if (/empty response/i.test(d)) {
    return {
      reason: "AI 응답이 비어 있기",
      action: "잠시 후 다시 시도해 주세요",
    };
  }
  if (/invalid JSON|JSON/i.test(d)) {
    return {
      reason: "AI 응답을 해석하지 못했기",
      action: "다시 시도하거나 질문을 나눠 입력해 주세요",
    };
  }
  if (!status && /failed to fetch|network|load failed/i.test(d)) {
    return {
      reason: "네트워크 연결이 불안정하기",
      action: "인터넷을 확인한 뒤 다시 시도해 주세요",
    };
  }
  return {
    reason: "AI 서버와 통신하지 못했기",
    action: "잠시 후 다시 시도해 주세요",
  };
}

function formatGeminiFailureNotice(e, { fallbackHint = false } = {}) {
  const { reason, action } = describeGeminiFailure(e);
  const attempts = e?.attemptsMade || e?.maxAttempts;
  const prefix = attempts ? `${attempts}번 재시도했지만 실패했어요. ` : "";
  const suffix = fallbackHint ? " 대신 로컬 일정을 보여드릴게요." : "";
  return `${prefix}${reason} 때문에 ${action}.${suffix}`;
}

function geminiFailToast(e, opts = {}) {
  toast(formatGeminiFailureNotice(e, opts), { error: true });
}

function normalizeGeminiRequestBody(body) {
  const sys = body.systemInstruction || body.system_instruction;
  const out = { contents: body.contents || [] };
  if (sys) out.systemInstruction = sys;
  return out;
}

const GEMINI_MODEL_FALLBACK_ORDER = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"];
const GEMINI_ATTEMPTS_PER_MODEL = 3;

function geminiModelCandidates() {
  const preferred = String(typeof GEMINI_MODEL !== "undefined" ? GEMINI_MODEL : "").trim();
  const ordered = preferred
    ? [preferred, ...GEMINI_MODEL_FALLBACK_ORDER]
    : [...GEMINI_MODEL_FALLBACK_ORDER];
  return [...new Set(ordered.filter(Boolean))];
}

function geminiRetryDelayMs(attempt, retryAfterSec = 0) {
  if (retryAfterSec > 0) return Math.min(retryAfterSec * 1000, 60000);
  const base = 2000 * 2 ** attempt;
  const jitter = Math.floor(Math.random() * 1200);
  return Math.min(base + jitter, 60000);
}

function isGeminiRetryableStatus(status) {
  return [408, 429, 500, 502, 503, 504].includes(Number(status));
}

function isGeminiOverloadStatus(status, detail = "") {
  const s = Number(status);
  if ([502, 503, 504].includes(s)) return true;
  return /high demand|UNAVAILABLE|overloaded/i.test(detail);
}

function geminiOutputTokenBudget(twoTrack, tripDays) {
  if (twoTrack) {
    return Math.min(6144, 2600 + tripDays * 420);
  }
  return 2048;
}

function canFallbackToNextGeminiModel(e) {
  const status = Number(e?.status) || 0;
  if (!status) return true;
  if ([400, 401, 403].includes(status)) return false;
  return true;
}

async function callGeminiWithModel(model, normalized, key, maxAttempts, maxOutputTokens) {
  const attempts = Math.max(1, Number(maxAttempts) || GEMINI_ATTEMPTS_PER_MODEL);
  let lastErr = null;
  let lastStatus = 0;

  for (let attempt = 0; attempt < attempts; attempt++) {
    const shrink =
      lastStatus === 503 && attempt >= 2
        ? Math.max(0.55, 1 - (attempt - 1) * 0.12)
        : 1;
    const effectiveMaxTokens = Math.max(1024, Math.floor(maxOutputTokens * shrink));
    const generationConfig = {
      temperature: 0.4,
      maxOutputTokens: effectiveMaxTokens,
      responseMimeType: "application/json",
    };
    const reqBody = { ...normalized, generationConfig };
    const payloadChars = JSON.stringify(reqBody).length;
    if (payloadChars > 48000) {
      console.warn("Gemini large request payload", { model, chars: payloadChars, maxTokens: effectiveMaxTokens });
    }
    const url =
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=` +
      encodeURIComponent(key);
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reqBody),
      });
      if (r.ok) return r.json();

      let detail = "";
      try {
        detail = (await r.json())?.error?.message || "";
      } catch (_) { /* ignore */ }

      const status = r.status;
      lastStatus = status;
      const retryAfter = Number(r.headers?.get?.("retry-after")) || 0;
      if (isGeminiOverloadStatus(status, detail)) {
        const e = new Error("Gemini HTTP " + status + (detail ? ": " + detail : ""));
        e.status = status;
        e.detail = detail;
        e.model = model;
        e.attemptsMade = attempt + 1;
        e.maxAttempts = attempts;
        e.overload = true;
        e.retryExhausted = true;
        console.warn(`Gemini ${model} overloaded (${status}) — switching model without retry`);
        throw e;
      }
      if (isGeminiRetryableStatus(status) && attempt < attempts - 1) {
        const wait = geminiRetryDelayMs(attempt, retryAfter);
        console.warn(
          `Gemini ${model} HTTP ${status}, retry ${attempt + 1}/${attempts - 1} in ${Math.round(wait / 1000)}s` +
            (shrink < 1 ? ` (maxTokens→${effectiveMaxTokens})` : ""),
          detail.slice(0, 160)
        );
        await new Promise((res) => setTimeout(res, wait));
        continue;
      }

      const e = new Error("Gemini HTTP " + status + (detail ? ": " + detail : ""));
      e.status = status;
      e.detail = detail;
      e.model = model;
      e.attemptsMade = attempt + 1;
      e.maxAttempts = attempts;
      e.retryExhausted = true;
      throw e;
    } catch (e) {
      lastErr = e;
      if (e.status) lastStatus = e.status;
      if (!e.attemptsMade) {
        e.attemptsMade = attempt + 1;
        e.maxAttempts = attempts;
      }
      if (e.status && !isGeminiRetryableStatus(e.status)) {
        e.retryExhausted = true;
        throw e;
      }
      if (attempt < attempts - 1) {
        const wait = geminiRetryDelayMs(attempt, 0);
        console.warn(`Gemini ${model} request failed, retry ${attempt + 1}/${attempts - 1}`, e.message);
        await new Promise((res) => setTimeout(res, wait));
        continue;
      }
      e.retryExhausted = true;
      throw e;
    }
  }
  const err = lastErr || new Error("Gemini call failed");
  err.attemptsMade = attempts;
  err.maxAttempts = attempts;
  err.retryExhausted = true;
  throw err;
}

async function callGemini(body, key, attemptsPerModel = GEMINI_ATTEMPTS_PER_MODEL, maxOutputTokens = 4096) {
  const normalized = normalizeGeminiRequestBody(body);
  const models = geminiModelCandidates();
  let lastErr = null;
  let totalAttempts = 0;
  let totalMaxAttempts = 0;

  for (let idx = 0; idx < models.length; idx++) {
    const model = models[idx];
    try {
      const result = await callGeminiWithModel(model, normalized, key, attemptsPerModel, maxOutputTokens);
      if (idx > 0) {
        console.warn(`[Gemini] fallback model used: ${model}`);
      }
      return result;
    } catch (e) {
      lastErr = e;
      totalAttempts += Number(e?.attemptsMade || 0);
      totalMaxAttempts += Number(e?.maxAttempts || 0);
      const hasNext = idx < models.length - 1;
      if (!hasNext || !canFallbackToNextGeminiModel(e)) {
        e.attemptsMade = totalAttempts || e.attemptsMade;
        e.maxAttempts = totalMaxAttempts || e.maxAttempts;
        e.triedModels = models.slice(0, idx + 1);
        throw e;
      }
      console.warn(
        `[Gemini] ${model} failed (${e.status || "network"}), fallback to ${models[idx + 1]}`
      );
    }
  }

  const err = lastErr || new Error("Gemini call failed");
  err.attemptsMade = totalAttempts || err.attemptsMade;
  err.maxAttempts = totalMaxAttempts || err.maxAttempts;
  err.retryExhausted = true;
  err.triedModels = models;
  throw err;
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

function resolveSpotByNameInEnriched(name, regions = []) {
  const raw = String(name ?? "").trim();
  if (!raw) return null;
  const list = regions.length
    ? SPOT_FUZZY_LIST.filter((s) => regions.includes(s.region))
    : SPOT_FUZZY_LIST;
  const exact = regions.length
    ? list.find((s) => s.name === raw)
    : SPOT_BY_NAME[raw];
  if (exact) return exact;
  for (let i = 0; i < list.length; i++) {
    const spot = list[i];
    if (spot.name.includes(raw) || raw.includes(spot.name)) return spot;
  }
  return null;
}

function resolveSpotByName(name, regions = [], { strict = null } = {}) {
  const raw = String(name ?? "").trim();
  if (!raw) return null;
  const scoped = regions.length ? regions : regionsInPrompt(state.query || "");
  const useStrict = strict !== null ? strict : scoped.length > 0;
  const enriched = resolveSpotByNameInEnriched(raw, scoped);
  if (enriched) return enriched;
  const kto = resolveKtoSpotByName(raw, scoped);
  if (kto) return kto;
  if (useStrict) return null;
  const globalKto = resolveKtoSpotByName(raw, GANGWON_REGION_NAMES);
  if (globalKto) return globalKto;
  if (scoped.length) {
    const global = resolveSpotByNameInEnriched(raw, []);
    if (global) return global;
  }
  return null;
}

function buildStepsFromItinerary(itinerary, prompt, intro = "") {
  const inferredRegions = strictRegionsForCuration(prompt, intro);
  const usedNames = new Set();
  const steps = [];
  for (let i = 0; i < (itinerary || []).length; i++) {
    const item = itinerary[i];
    const rawName = String(item.spot_name || "").trim();
    if (!rawName) continue;
    let spot = resolveSpotByName(rawName, inferredRegions, { strict: true });
    if (!spot && inferredRegions.length) {
      spot = regionalFallbackSpots(inferredRegions, 5).find((s) => !usedNames.has(s.name));
    }
    if (!spot || usedNames.has(spot.name)) continue;
    if (inferredRegions.length && !inferredRegions.includes(spot.region)) continue;
    usedNames.add(spot.name);
    steps.push({
      order: item.step ?? i + 1,
      day: 1,
      spot,
      stay: spot.stay_min ?? 60,
      why: (item.reason || `${spot.description}. ${spot.tip || ""}`).trim(),
      move_to_next: "",
    });
  }
  return steps;
}

function ensureCurationHasSteps(result, parsed, prompt, routePlan = null) {
  if (result.steps?.length) {
    if (routePlan) {
      result.routePlan = routePlan;
      result.duration = routeDurationLabel(routePlan.totals);
    }
    return result;
  }
  const intro = parsed.introduction || result.summary || "";
  const inferredRegions = strictRegionsForCuration(prompt, intro);

  if (parsed.itinerary?.length) {
    const steps = buildStepsFromItinerary(parsed.itinerary, prompt, intro);
    if (steps.length) {
      const scoped = constrainStepsToRegions(steps, inferredRegions);
      if (!scoped.length) {
        return emptyRegionalCurationShell(inferredRegions, {
          summary: intro || result.summary,
          source: result.source || "gemini",
          title: result.title,
        });
      }
      return {
        ...result,
        steps: scoped,
        routePlan,
        duration: routePlan ? routeDurationLabel(routePlan.totals) : "당일 코스",
        title: inferredRegions[0] ? `${inferredRegions[0]} AI 추천 코스` : result.title,
      };
    }
  }

  const picks = inferredRegions.length
    ? regionalFallbackSpots(inferredRegions, 3)
    : isProvinceWidePrompt(prompt)
      ? pickProvinceWideSpots(3)
      : [];
  if (!picks.length) {
    return emptyRegionalCurationShell(inferredRegions, {
      summary: intro || result.summary,
      source: result.source || "gemini",
      title: result.title,
    });
  }

  const steps = picks.map((spot, i) => ({
    order: i + 1,
    day: 1,
    spot,
    stay: spot.stay_min ?? 60,
    why: `${spot.description}. ${spot.tip || ""}`.trim(),
    move_to_next: routePlan?.legs?.[i]?.summary || "",
  }));
  return {
    ...result,
    steps,
    routePlan,
    duration: routePlan ? routeDurationLabel(routePlan.totals) : "당일 코스",
    title: inferredRegions[0] ? `${inferredRegions[0]} AI 추천 코스` : "강원도 AI 추천 코스",
  };
}

function resolveSpotWithRegionalFallback(name, regions, usedNames) {
  let spot = resolveSpotByName(name, regions, { strict: true });
  if (spot && (!regions.length || regions.includes(spot.region))) {
    if (!usedNames.has(spot.name)) return spot;
  }
  if (!regions.length) return null;
  return regionalFallbackSpots(regions, 5).find((s) => !usedNames.has(s.name)) || null;
}

function itineraryToSteps(itinerary, prompt, intro, allowedRegions = []) {
  if (!itinerary?.length) return [];
  const usedNames = new Set();
  const steps = [];
  for (let i = 0; i < itinerary.length; i++) {
    const item = itinerary[i];
    const rawName = String(item.spot_name || "").trim();
    if (!rawName) continue;
    let spot = resolveSpotByName(rawName, allowedRegions, { strict: true });
    if (!spot && allowedRegions.length) {
      spot = regionalFallbackSpots(allowedRegions, 5).find((s) => !usedNames.has(s.name));
    }
    if (!spot || usedNames.has(spot.name)) continue;
    if (allowedRegions.length && !allowedRegions.includes(spot.region)) continue;
    usedNames.add(spot.name);
    steps.push({
      order: item.step ?? i + 1,
      day: 1,
      spot,
      stay: spot.stay_min ?? 60,
      why: (item.reason || `${spot.description}. ${spot.tip || ""}`).trim(),
      move_to_next: "",
    });
  }
  if (!steps.length && allowedRegions.length) {
    return regionalFallbackSpots(allowedRegions, 3).map((spot, i) => ({
      order: i + 1,
      day: 1,
      spot,
      stay: spot.stay_min ?? 60,
      why: `${spot.description}. ${spot.tip || ""}`.trim(),
      move_to_next: "",
    }));
  }
  return steps;
}

function isMealTimeSlot(timeSlot) {
  return /식사|점심|저녁|아침|음식|맛집/.test(String(timeSlot || ""));
}

function resolveScheduleSpot(spotName, regions, prompt) {
  const name = String(spotName || "").trim();
  if (!name) return null;
  return resolveSpotByName(name, regions, { strict: true });
}

function syntheticScheduleSpot(name, region, description, isMeal) {
  const coords = cityCoordsForRegion(region, name);
  return {
    name,
    region,
    theme: isMeal ? "맛집" : "관광",
    lat: coords.lat,
    lng: coords.lng,
    description: description || `${name} — KTO`,
    tip: isMeal ? "현장 혼잡도·영업시간을 확인해 주세요." : "현장에서 운영 시간·요금을 확인해 주세요.",
    stay_min: isMeal ? 75 : 60,
    fee: isMeal ? "메뉴·가격 현장 확인" : "현장 확인",
    hours: isMeal ? "11:00–21:00" : "연중",
    parking: "인근 주차 가능",
    best_time: isMeal ? "점심·저녁" : "주말·휴일",
    tags: [regionShortName(region), "KTO"],
  };
}

function scheduleItemToStep(item, dayNum, order, prompt, regions, usedNames = new Set()) {
  const slot = String(item.time_slot || "").trim();
  const rawName = String(item.spot_name || "").trim();
  const desc = String(item.description || item.reason || "").trim();
  if (!rawName) return null;
  const isMeal = isMealTimeSlot(slot);
  let spot = resolveScheduleSpot(rawName, regions, prompt);
  if (!spot && regions.length) {
    const pool = regionalFallbackSpots(regions, 8);
    spot = pool.find((s) => !usedNames.has(s.name)) || pool[(order - 1) % pool.length];
  }
  if (!spot) return null;
  usedNames.add(spot.name);
  if (isMeal) {
    spot = { ...spot, theme: "맛집", stay_min: 75 };
  }
  return {
    order,
    day: dayNum,
    spot,
    stay: isMeal ? 75 : spot.stay_min ?? 60,
    why: slot ? `[${slot}] ${desc || spot.description}`.trim() : desc || spot.description,
    move_to_next: "",
  };
}

function optionToSteps(option, prompt, regions) {
  const usedNames = new Set();
  if (option?.days?.length) {
    const steps = [];
    let order = 1;
    for (const dayBlock of option.days) {
      const dayNum = dayBlock.day || 1;
      for (const item of dayBlock.schedule || []) {
        const step = scheduleItemToStep(item, dayNum, order++, prompt, regions, usedNames);
        if (step) steps.push(step);
      }
    }
    if (steps.length) return steps;
  }
  const fromItinerary = itineraryToSteps(option?.itinerary, prompt, "", regions);
  if (fromItinerary.length) return fromItinerary;
  if (regions.length) {
    return regionalFallbackSpots(regions, 3).map((spot, i) => ({
      order: i + 1,
      day: 1,
      spot,
      stay: spot.stay_min ?? 60,
      why: `${spot.description}. ${spot.tip || ""}`.trim(),
      move_to_next: "",
    }));
  }
  return [];
}

function buildDayPlansFromOption(option) {
  if (!option?.days?.length) return [];
  return option.days.map((d) => ({
    day: d.day,
    title: `Day ${d.day}`,
    focus: (d.schedule || []).map((s) => s.time_slot).filter(Boolean).join(" · "),
  }));
}

function parseTwoTrackCuration(parsed, prompt) {
  const main = pickMainDestination(prompt) || "";
  const transit = resolveTransitArea(main) || "";
  const intro = parsed.intro || parsed.introduction || "";
  const durationLabel =
    parsed.duration_detected || detectTripDuration(prompt).label;

  const opt1Raw = parsed.option_1 || {};
  const opt2Raw = parsed.option_2 || {};
  const mainRegions = main ? [main] : [];
  const hybridRegions = [transit, main].filter(Boolean);

  let steps1 = optionToSteps(opt1Raw, prompt, mainRegions);
  let steps2 = optionToSteps(opt2Raw, prompt, hybridRegions);
  if (opt2Raw.storytelling && steps2.length) {
    steps2 = steps2.map((s, i) =>
      i === 0 ? { ...s, why: `${opt2Raw.storytelling} ${s.why}`.trim() } : s
    );
  }

  const courseOptions = [];
  if (opt1Raw.days?.length || opt1Raw.itinerary || steps1.length) {
    courseOptions.push({
      key: "option_1",
      title: opt1Raw.title || (main ? `1안: ${regionShortName(main)} 알짜배기 집중 코스` : "1안: 목적지 집중 코스"),
      summary: "",
      steps: steps1,
      days: opt1Raw.days || [],
      dayPlans: buildDayPlansFromOption(opt1Raw),
    });
  }
  if (opt2Raw.days?.length || opt2Raw.itinerary || steps2.length) {
    courseOptions.push({
      key: "option_2",
      title:
        opt2Raw.title ||
        (transit ? `2안: ${regionShortName(transit)} 상생 하이브리드 코스` : "2안: 지역 상생 하이브리드 코스"),
      summary: opt2Raw.storytelling || "",
      steps: steps2,
      days: opt2Raw.days || [],
      dayPlans: buildDayPlansFromOption(opt2Raw),
    });
  }

  const activeKey =
    courseOptions.find((o) => o.key === "option_2" && o.steps.length)?.key ||
    courseOptions.find((o) => o.steps.length)?.key ||
    "option_1";
  const active = courseOptions.find((o) => o.key === activeKey);
  const steps = active?.steps || [];

  return {
    title: main ? `${regionShortName(main)} ${durationLabel} · 2가지 코스` : `강원도 ${durationLabel} · 2가지 코스`,
    summary: intro,
    duration: durationLabel || "",
    steps,
    courseOptions,
    activeCourseOption: activeKey,
    source: "gemini",
    tripIntent: { mainDestination: main, transitArea: transit, duration: durationLabel },
    transitPlan: {},
    accommodation: {},
    dayPlans: active?.dayPlans || [],
  };
}

function parseGeminiCuration(raw, prompt, routePlan = null) {
  const parsed = parseJsonFromGemini(raw);
  if (parsed.option_1 != null || parsed.option_2 != null) {
    return parseTwoTrackCuration(parsed, prompt);
  }
  const regions = regionsInPrompt(prompt);
  const intro = parsed.introduction || KTO_FALLBACK_INTRO;

  if (parsed.fallback_triggered) {
    return ensureCurationHasSteps(
      {
        title: regions[0] ? `${regions[0]} 안내` : "강원도 안내",
        summary: intro,
        duration: "",
        steps: [],
        source: "gemini",
        tripIntent: {},
        transitPlan: {},
        accommodation: {},
        dayPlans: [],
      },
      parsed,
      prompt,
      routePlan
    );
  }

  if (routePlan || Array.isArray(parsed.stop_narratives)) {
    const inferredRegions = strictRegionsForCuration(prompt, intro);
    let steps = routePlan
      ? buildStepsFromRoutePlan(routePlan, parsed, prompt)
      : [];
    if (!steps.length && parsed.stop_narratives?.length) {
      steps = buildStepsFromItinerary(
        parsed.stop_narratives.map((n, i) => ({
          step: i + 1,
          spot_name: n.spot_name,
          reason: n.why,
        })),
        prompt,
        intro
      );
    }
    steps = constrainStepsToRegions(
      steps,
      regions.length ? regions : inferredRegions,
      { strict: true }
    );
    const totals = routePlan?.totals;
    const driveLabel = totals
      ? `총 ${fmtKm(totals.km)} · 차량 ${fmtMin(totals.min)} (카카오)`
      : "";
    return ensureCurationHasSteps(
      {
        title: regions[0]
          ? `${regions[0]} AI 추천 코스`
          : inferredRegions[0]
            ? `${inferredRegions[0]} AI 추천 코스`
            : "강원도 AI 추천 코스",
        summary: intro + (driveLabel ? `\n${driveLabel}` : ""),
        duration: routePlan ? routeDurationLabel(routePlan.totals) : "",
        steps,
        routePlan,
        source: "gemini",
        tripIntent: {},
        transitPlan: {},
        accommodation: {},
        dayPlans: [],
      },
      parsed,
      prompt,
      routePlan
    );
  }

  if (parsed.introduction != null || Array.isArray(parsed.itinerary)) {
    const inferredRegions = strictRegionsForCuration(prompt, intro);
    let steps = parsed.itinerary?.length
      ? buildStepsFromItinerary(parsed.itinerary, prompt, intro)
      : [];
    steps = constrainStepsToRegions(
      steps,
      regions.length ? regions : inferredRegions,
      { strict: true }
    );
    let result = {
      title: regions[0]
        ? `${regions[0]} AI 추천 코스`
        : inferredRegions[0]
          ? `${inferredRegions[0]} AI 추천 코스`
          : "강원도 AI 추천 코스",
      summary: intro,
      duration: "",
      steps,
      source: "gemini",
      tripIntent: {},
      transitPlan: {},
      accommodation: {},
      dayPlans: [],
    };
    return ensureCurationHasSteps(result, parsed, prompt, routePlan);
  }

  const usedNames = new Set();
  const steps = (parsed.route_steps || [])
    .map((st, i) => {
      const spot = resolveSpotWithRegionalFallback(st.spot_name, regions, usedNames);
      if (!spot) return null;
      if (regions.length && !regions.includes(spot.region)) return null;
      usedNames.add(spot.name);
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
  if (!steps.length) {
    const scopedRegions = strictRegionsForCuration(prompt, parsed.summary || intro || "");
    if (scopedRegions.length && !regionalFallbackSpots(scopedRegions, 1).length) {
      return {
        ...emptyRegionalCurationShell(scopedRegions, {
          summary: regionEmptyFallbackMessage(),
          source: "gemini",
        }),
        tripIntent: parsed.trip_intent || {},
        transitPlan: parsed.transit_plan || {},
        accommodation: parsed.accommodation || {},
        dayPlans: parsed.day_plans || [],
      };
    }
    return ensureCurationHasSteps(
      {
        title: regions[0] ? `${regions[0]} AI 추천 코스` : "강원도 AI 추천 코스",
        summary: parsed.summary || intro || KTO_FALLBACK_INTRO,
        duration: parsed.total_duration || "",
        steps: [],
        source: "gemini",
        tripIntent: parsed.trip_intent || {},
        transitPlan: parsed.transit_plan || {},
        accommodation: parsed.accommodation || {},
        dayPlans: parsed.day_plans || [],
      },
      parsed,
      prompt
    );
  }
  const scoped = constrainStepsToRegions(steps, regions, { strict: true });
  if (!scoped.length && regions.length) {
    const msg = regionEmptyFallbackMessage();
    return {
      title: `${regions[0]} AI 추천 코스`,
      summary: parsed.summary || msg,
      duration: parsed.total_duration || "",
      steps: [],
      source: "gemini",
      tripIntent: parsed.trip_intent || {},
      transitPlan: parsed.transit_plan || {},
      accommodation: parsed.accommodation || {},
      dayPlans: parsed.day_plans || [],
    };
  }
  return {
    title: parsed.itinerary_title || (regions[0] ? `${regions[0]} AI 추천 코스` : "AI 추천 코스"),
    summary: parsed.summary || intro,
    duration: parsed.total_duration || "당일 코스",
    steps: scoped,
    routePlan,
    source: "gemini",
    tripIntent: parsed.trip_intent || {},
    transitPlan: parsed.transit_plan || {},
    accommodation: parsed.accommodation || {},
    dayPlans: parsed.day_plans || [],
  };
}
async function localCuration(prompt, source = "local") {
  const regions = regionsInPrompt(prompt);
  const picks = pickSpotsForPrompt(prompt, 3);
  if (!picks.length) {
    const msg = regions[0] ? regionEmptyFallbackMessage() : "현재 필터에 맞는 장소가 없습니다.";
    return {
      title: regions[0] ? `${regions[0]} 안내` : "맞춤 코스",
      summary: msg,
      duration: "",
      steps: [],
      source,
    };
  }
  const routePlan = picks.length >= 2 ? await buildKakaoRoutePlan(picks) : null;
  const steps = picks.map((s, i) => ({
    order: i + 1,
    spot: s,
    stay: s.stay_min,
    why: `${s.description}. ${s.tip}`,
    move_to_next: routePlan?.legs?.[i]?.summary || "",
  }));
  const regionLabel = regions[0] || picks[0]?.region || "";
  const routeLabel =
    routePlan?.provider === "kakao" ? "카카오" : routePlan?.provider === "osrm" ? "도로 추정" : "경로";
  const driveLabel = routePlan?.totals
    ? `총 ${fmtKm(routePlan.totals.km)} · 차량 ${fmtMin(routePlan.totals.min)} (${routeLabel})`
    : "";
  return {
    title: regionLabel ? `${regionLabel} 맞춤 코스` : "🥔 로컬 추천 코스",
    summary:
      (regionLabel ? `${regionLabel} 중심 · ` : "") +
      (driveLabel || "경로 데이터 없음 — 이동 시간은 지도에서 확인해 주세요."),
    duration: routePlan ? routeDurationLabel(routePlan.totals) : "당일 코스",
    steps,
    routePlan,
    source,
  };
}

/* ==================== Curation ==================== */
async function geminiCuration(prompt, key) {
  await waitGeminiSlot();
  const twoTrack = shouldUseTwoTrackWorkflow(prompt);
  const ktoXml = twoTrack ? buildTwoTrackKtoXml(prompt) : buildKtoDataXml(prompt);
  const regionFocus = regionFocusPromptBlock(prompt);
  const provinceBlock =
    !twoTrack && isProvinceWidePrompt(prompt)
      ? "# PROVINCE-WIDE QUERY\n" +
        "User asks about Gangwon-do broadly (no single city/county).\n" +
        "- Use ROUTING DATA stop order when present.\n" +
        "- stop_narratives MUST match ROUTING DATA spot names.\n"
      : "";

  let routePlan = null;
  let routingContext = "";
  if (!twoTrack) {
    const picks = pickSpotsForPrompt(prompt, 3);
    if (picks.length >= 2) {
      routePlan = await buildKakaoRoutePlan(picks);
    }
    routingContext = formatRoutingContextForGemini(routePlan);
  }

  const routeContext = twoTrack
    ? `# ROUTE CONTEXT\n- main_destination: ${regionShortName(pickMainDestination(prompt) || "")}\n- transit_area: ${regionShortName(resolveTransitArea(pickMainDestination(prompt)) || "")} (인구소멸·상생 경유지)\n`
    : "";
  const themeBlock = twoTrack ? buildThemePromptBlock(prompt) : "";
  const durationBlock = twoTrack ? buildDurationPromptBlock(prompt) : "";

  const sys = twoTrack
    ? GANGWON_AGENT_ROLE_TWO_TRACK +
      "\n\n" +
      ktoXml +
      "\n\n" +
      KTO_TWO_TRACK_OUTPUT_FORMAT +
      (routeContext ? "\n\n" + routeContext : "") +
      (durationBlock ? "\n\n" + durationBlock : "") +
      (themeBlock ? "\n\n" + themeBlock : "") +
      (regionFocus ? "\n\n" + regionFocus : "")
    : GANGWON_AGENT_ROLE_ROUTING +
      "\n\n" +
      routingContext +
      "\n\n" +
      ktoXml +
      "\n\n" +
      KTO_OUTPUT_FORMAT_ROUTING +
      (provinceBlock ? "\n\n" + provinceBlock : "") +
      (regionFocus ? "\n\n" + regionFocus : "");

  const promptPayload = clampPromptForGemini(prompt);
  if (promptPayload.truncated) {
    toast(
      `입력이 길어 Gemini에는 ${GEMINI_USER_PROMPT_MAX_CHARS}자 기준으로 압축 전송했어요.`,
      { duration: 4200 }
    );
  }

  const body = {
    systemInstruction: { parts: [{ text: sys }] },
    contents: [{ role: "user", parts: [{ text: promptPayload.text }] }],
  };
  const tripDays = detectTripDuration(prompt).days;
  const maxTokens = geminiOutputTokenBudget(twoTrack, tripDays);
  const d = await callGemini(body, key, GEMINI_ATTEMPTS_PER_MODEL, maxTokens);
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
  return parseGeminiCuration(text, prompt, routePlan);
}

function buildComplexFailReply(e) {
  const { reason, action } = describeGeminiFailure(e);
  const attempts = e?.attemptsMade || e?.maxAttempts;
  const retryLine = attempts ? `${attempts}번 재시도했지만 실패했어요.\n` : "";
  return [
    "**AI 일정을 만들지 못했어요**",
    "출발·교통·숙박·기간 조건이 포함된 질문은 AI가 필요합니다.",
    `${retryLine}${reason} 때문에 ${action}.`,
  ].join("\n");
}

function pushAgentFailure(text) {
  state.chat.push({ role: "assistant", text });
  renderAgentChat();
}

function switchCourseOption(key) {
  const opts = state.meta.courseOptions || [];
  const picked = opts.find((o) => o.key === key && o.steps?.length);
  if (!picked) return;
  state.meta.activeCourseOption = key;
  state.meta.title = picked.title;
  state.meta.dayPlans = picked.dayPlans || [];
  if (picked.summary && state.meta.courseOptions.length > 1) {
    state.meta.summary = `${state.meta._intro || state.meta.summary}\n\n${picked.summary}`.trim();
  }
  state.steps = attachOriginStep(picked.steps, state.meta, state.query);
  state.focusOrder = 1;
  resetMapState();
  resetKakaoRouteState();
  renderPlanner();
}

function applyCurationResult(prompt, result, opts = {}) {
  const { skipChat = false, chatPrefix = "" } = opts;
  if (!skipChat) {
    const text = chatPrefix ? `${chatPrefix}\n\n${buildAgentReply(result)}` : buildAgentReply(result);
    state.chat.push({ role: "assistant", text });
    renderAgentChat();
  }
  if (!result.steps?.length) return;
  state.query = prompt;
  state.meta = {
    title: result.title,
    summary: result.summary,
    _intro: result.summary,
    duration: result.duration,
    source: result.source || "local",
    tripIntent: result.tripIntent || {},
    transitPlan: result.transitPlan || {},
    accommodation: result.accommodation || {},
    dayPlans: result.dayPlans || [],
    courseOptions: result.courseOptions || [],
    activeCourseOption: result.activeCourseOption || null,
  };
  state.steps = attachOriginStep(result.steps, state.meta, prompt);
  state.focusOrder = 1;
  resetMapState();
  resetKakaoRouteState();
  appendPlannerOpenButton();
}

function appendPlannerOpenButton() {
  const box = $("agent-messages");
  if (!box || !state.steps.length) return;
  if (box.querySelector(".chat-open-planner")) return;
  box.insertAdjacentHTML(
    "beforeend",
    `<div class="chat-open-planner-wrap">` +
      `<button type="button" class="btn-primary chat-open-planner" id="chat-open-planner">▤ 일정·지도 열기</button>` +
      `</div>`
  );
}

function saveCurationAndApply(prompt, result, opts = {}) {
  saveCurationCache(prompt, result);
  applyCurationResult(prompt, result, opts);
}

async function runRegionTrip(prompt, key, complex) {
  const multiIntent = isMultiIntentPrompt(prompt);
  const cacheKey = normalizePromptKey(prompt);
  if (curationCache.has(cacheKey)) {
    const cached = curationCache.get(cacheKey);
    const prefix = multiIntent && cached.source !== "gemini" ? buildRegionInfoReply(prompt) : "";
    applyCurationResult(prompt, cached, { chatPrefix: prefix });
    return;
  }

  let result;
  if (key) {
    try {
      result = await geminiCuration(prompt, key);
    } catch (e) {
      console.warn("Gemini 실패:", e);
      geminiFailToast(e, { fallbackHint: !complex });
      if (complex) {
        pushAgentFailure(buildComplexFailReply(e));
        return;
      }
      const regions = strictRegionsForCuration(prompt);
      result =
        regions.length && !regionalFallbackSpots(regions, 1).length
          ? emptyRegionalCurationShell(regions, { source: "local_api_fail" })
          : await localCuration(prompt, "local_api_fail");
    }
  } else {
    if (complex) {
      pushAgentFailure(
        "**AI 일정을 만들 수 없어요**\n" +
          "출발·교통·숙박·기간 조건은 AI 키가 필요합니다. 잠시 후 다시 시도해 주세요."
      );
      return;
    }
    result = await localCuration(prompt, "local");
  }

  const prefix = multiIntent && result.source !== "gemini" ? buildRegionInfoReply(prompt) : "";
  saveCurationAndApply(prompt, result, { chatPrefix: prefix });
}

async function tryGeminiCurationWithFallback(prompt, key, complex) {
  try {
    const result = await geminiCuration(prompt, key);
    saveCurationAndApply(prompt, result);
  } catch (e) {
    console.warn("Gemini 실패:", e);
    geminiFailToast(e, { fallbackHint: !complex });
    if (complex) {
      pushAgentFailure(buildComplexFailReply(e));
      return;
    }
    const regions = strictRegionsForCuration(prompt);
    const fallback =
      regions.length && !regionalFallbackSpots(regions, 1).length
        ? emptyRegionalCurationShell(regions, { source: "local_api_fail" })
        : await localCuration(prompt, "local_api_fail");
    saveCurationAndApply(prompt, fallback);
  }
}

async function runCuration(prompt) {
  state.chat.push({ role: "user", text: prompt });
  state.chatTyping = true;
  renderAgentChat();
  setAgentBusy(true);
  try {
    const refusal = outOfGangwonReply(prompt);
    if (refusal) {
      pushAgentFailure(refusal);
      return;
    }

    if (isRegionInfoOnlyPrompt(prompt)) {
      state.chat.push({ role: "assistant", text: buildRegionInfoReply(prompt) });
      return;
    }

    const regions = regionsInPrompt(prompt);
    if (regions.length && hasTripPlanIntent(prompt)) {
      await runRegionTrip(prompt, getGeminiKey(), needsComplexAi(prompt));
      return;
    }

    const cacheKey = normalizePromptKey(prompt);
    if (curationCache.has(cacheKey)) {
      applyCurationResult(prompt, curationCache.get(cacheKey));
      return;
    }

    const complex = needsComplexAi(prompt);
    const key = getGeminiKey();

    if (!shouldCallGemini(prompt)) {
      saveCurationAndApply(prompt, await localCuration(prompt, "local_skip"));
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
      saveCurationAndApply(prompt, await localCuration(prompt, "local"));
      return;
    }

    await tryGeminiCurationWithFallback(prompt, key, complex);
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
  const s = step.spot;
  const apiImgCandidates = collectSpotImageCandidates(s.region, s.name, s);
  const mediaHtml = apiImgCandidates.length
    ? imgWithFallback(apiImgCandidates, { alt: s.name, fbKind: "course", fbCls: t.cls, fbLabel: t.label })
    : `<div class="course-img-fallback ${esc(t.cls)}" aria-hidden="true"><span>${esc(t.label)}</span></div>`;
  return `
<a class="course-card${active ? " on" : ""}" data-order="${step.order}">
  <div class="ci-wrap">
    ${mediaHtml}
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
  const icon = leg.kakao ? "🧭" : transit ? "🚆" : "🚗";
  const mins = leg.driveMin || parseDurationMin(note);
  const text =
    note ||
    (mins
      ? transit
        ? `${leg.from.spot.name} → ${leg.to.spot.name} · 대중교통 약 ${fmtMin(mins)}`
        : `${leg.from.spot.name} → ${leg.to.spot.name} · ${fmtKm(leg.km || 0)} · 약 ${fmtMin(mins)}`
      : `${leg.from.spot.name} → ${leg.to.spot.name}`);
  return `<div class="course-leg${transit ? " transit-leg" : ""}">${icon} ${esc(text)}</div>`;
}

function renderRouteSummary(legs) {
  const sum = routeSummary(state.steps, legs);
  $("route-summary").innerHTML = `
    <div class="route-stat"><strong>${sum.stops}</strong><span>정거장</span></div>
    <div class="route-stat"><strong>${fmtKm(sum.driveKm)}</strong><span>총 이동</span></div>
    <div class="route-stat"><strong>${fmtMin(sum.driveMin)}</strong><span>이동 시간</span></div>
    <div class="route-stat"><strong>${fmtMin(sum.totalMin)}</strong><span>예상 소요</span></div>`;
  if (state.kakaoRoute.loading) {
    $("chip-route").textContent = "🧭 경로 계산 중…";
    return;
  }
  const routeTag =
    state.kakaoRoute.source === "kakao"
      ? "🧭 카카오"
      : state.kakaoRoute.source === "osrm"
        ? "🗺️ 도로 추정"
        : "";
  const routeLabel = sum.transitMin > 0
    ? `🚆 ${fmtMin(sum.transitMin)}${routeTag ? ` + ${routeTag} ${fmtKm(sum.driveKm)}` : ""}`
    : routeTag
      ? `${routeTag} ${fmtKm(sum.driveKm)}`
      : sum.driveKm > 0
        ? `🚗 ${fmtKm(sum.driveKm)}`
        : !state.kakaoRoute.loading &&
            routePointsFromSteps(state.steps).length >= 2 &&
            state.kakaoRoute.stepsKey === stepsRouteKey(state.steps)
          ? "경로 계산 실패"
          : "경로 —";
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

function renderCourses(legs) {
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

function renderCourseOptionTabs() {
  const host = $("course-option-tabs");
  if (!host) return;
  const opts = (state.meta.courseOptions || []).filter((o) => o.steps?.length);
  if (opts.length < 2) {
    host.innerHTML = "";
    host.classList.add("hidden");
    return;
  }
  host.classList.remove("hidden");
  const active = state.meta.activeCourseOption || opts[0].key;
  host.innerHTML = opts
    .map(
      (o) =>
        `<button type="button" class="course-option-tab${o.key === active ? " on" : ""}" data-course-option="${o.key}">` +
        `${esc(o.title)} <span class="course-option-count">${o.steps.length}곳</span></button>`
    )
    .join("");
  host.querySelectorAll("[data-course-option]").forEach((btn) => {
    btn.addEventListener("click", () => switchCourseOption(btn.dataset.courseOption));
  });
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
  renderCourseOptionTabs();
  const legs = getRouteLegs(steps);
  renderTripPlan(meta);
  renderRouteSummary(legs);
  renderCourses(legs);
  $("kakao-link").href = kakaoRouteUrl(steps);
  updateMapChrome();
  renderSpotDetail();
  renderMap();
  refreshRouteForSteps(steps).catch((e) => console.warn("refreshRouteForSteps:", e));
}

function renderPlannerEmpty() {
  $("plan-title").textContent = "내 여행 일정";
  $("plan-summary").textContent = "찜한 코스를 열거나, AI로 새 일정을 만들어 보세요.";
  $("plan-query").textContent = "";
  $("chip-duration").textContent = "⏱ —";
  $("chip-source").textContent = "◆ —";
  $("course-option-tabs")?.classList.add("hidden");
  $("course-option-tabs") && ($("course-option-tabs").innerHTML = "");
  $("chip-stops").textContent = "0곳";
  $("chip-route").textContent = "";
  $("route-summary").innerHTML = "";
  $("trip-plan")?.classList.add("hidden");
  $("courses").innerHTML =
    `<div class="planner-empty">` +
    `<p>아직 표시할 일정이 없어요.</p>` +
    `<p class="planner-empty-hint">찜에 담아 둔 코스를 열거나, AI 여행에서 새 코스를 만들어 보세요.</p>` +
    `<div class="planner-empty-actions">` +
    `<button type="button" class="btn-primary" data-nav="trips">♡ 찜 목록 보기</button>` +
    `<button type="button" class="btn-secondary" data-nav="explore">✦ AI 여행 시작</button>` +
    `</div></div>`;
  $("btn-save-trip")?.classList.add("hidden");
  $("spot-detail").innerHTML = "";
  $("map-q").textContent = "🔍 강원 여행";
  $("map-f").textContent = "📍 일정 없음";
  $("kakao-link").href = "#";
  mapNote("코스를 만들거나 찜 목록에서 열면 지도가 표시됩니다.");
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
  const kakaoPath = state.kakaoRoute.path || [];
  const useRoadPath =
    kakaoPath.length >= 2 &&
    (state.kakaoRoute.source === "kakao" || state.kakaoRoute.source === "osrm");

  if (mapEngine === "kakao") {
    if (useRoadPath) {
      const path = kakaoPath.map((p) => new kakao.maps.LatLng(p.lat, p.lng));
      new kakao.maps.Polyline({
        path,
        strokeWeight: 5,
        strokeColor: "#006a61",
        strokeOpacity: 0.9,
        strokeStyle: "solid",
      }).setMap(map);
      return;
    }
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
    if (useRoadPath) {
      L.polyline(
        kakaoPath.map((p) => [p.lat, p.lng]),
        { color: "#006a61", weight: 5, opacity: 0.9, lineCap: "round" }
      ).addTo(map);
      return;
    }
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
  resetKakaoRouteState();
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

/* ==================== Landing map (Gangwon hero SVG) ==================== */
const LANDING_MAP = {
  vbW: 960,
  vbH: 820,
  offsetX: 40,
  offsetY: 36,
  ax: 324.1915365510603,
  bx: -41.70425776670251,
  cx: -39606.001266482825,
  ay: 7.878191440342917,
  by: -435.0998319758161,
  cy: 15799.760903133569,
};

let landingBuilt = false;
let landingSvgLoaded = false;
let landingMarkers = [];

function landingRegionSpotCount(region) {
  return ENRICHED_SPOTS.filter((s) => s.region === region).length;
}

const REGION_PROFILE = {
  강릉시: {
    tagline: "동해안·커피·해변, 강원 대표 해양 관광 도시",
    pop: "약 21.3만",
    specialty: "커피·초당순두부·오징어순대",
    highlight: "경포·안목·주문진",
  },
  고성군: {
    tagline: "설악산·DMZ·국립공원 북쪽 관문",
    pop: "약 2.7만",
    specialty: "수산물·잣·DMZ 기념품",
    highlight: "속초·고성 해안·천학동굴",
  },
  동해시: {
    tagline: "해변·항구·Mural Village 드라이브",
    pop: "약 9.1만",
    specialty: "묵호회·맥주·멸치",
    highlight: "추암·망상·Mural Village",
  },
  삼척시: {
    tagline: "동굴·해변·씨라인·해안 트레킹",
    pop: "약 6.5만",
    specialty: "대게·오징어·동굴 관광",
    highlight: "환선굴·덕풍계곡·씨라인",
  },
  속초시: {
    tagline: "설악산·아바이마을·해산물·단풍",
    pop: "약 8.4만",
    specialty: "오징어·닭강정·홍게",
    highlight: "설악산·아바이·영금정",
  },
  양구군: {
    tagline: "DMZ·철원 평야·역사·생태 체험",
    pop: "약 2.4만",
    specialty: "한우·오디·DMZ 체험",
    highlight: "파로호·DMZ·펀치볼",
  },
  양양군: {
    tagline: "낙산·하조대·서핑·해변 캠핑",
    pop: "약 2.7만",
    specialty: "송이·송어·서핑",
    highlight: "낙산·하조대·죽도",
  },
  영월군: {
    tagline: "단종·패러글라이딩·동강·석벽",
    pop: "약 3.7만",
    specialty: "와인·메밀·단종 유적",
    highlight: "동강·청령포·패러글라이딩",
  },
  원주시: {
    tagline: "치악산·뮤지엄·도심·문화 공연",
    pop: "약 35.1만",
    specialty: "치악산 떡·한우·문화예술",
    highlight: "치악산·뮤지엄·댄싱카니발",
  },
  인제군: {
    tagline: "백두대간·원대리·스키·숲 트레킹",
    pop: "약 3.2만",
    specialty: "메밀·버섯·산나물",
    highlight: "원대리·방태산·백두대간",
  },
  정선군: {
    tagline: "아리랑·레일바이크·폐광·산악 드라이브",
    pop: "약 3.5만",
    specialty: "곤드레밥·아리랑·사과",
    highlight: "레일바이크·아리랑·화암동굴",
  },
  철원군: {
    tagline: "한탄강 주상절리·평야·DMZ·평화 레일",
    pop: "약 4.8만",
    specialty: "오디·한탄강 메기·평야 쌀",
    highlight: "한탄강·고석정·평화레일",
  },
  춘천시: {
    tagline: "남이섬·소양강·막국수·호수 힐링",
    pop: "약 28.2만",
    specialty: "막국수·닭갈비·닭강정",
    highlight: "남이섬·소양강·춘천호",
  },
  태백시: {
    tagline: "탄광·눈꽃·고원 도시·겨울 축제",
    pop: "약 4.2만",
    specialty: "황기·마늘·탄광 문화",
    highlight: "태백산·황기·탄광박물관",
  },
  평창군: {
    tagline: "대관령·올림픽·스키·송어·고랭지",
    pop: "약 4.3만",
    specialty: "송어·한우·감자",
    highlight: "대관령·알펜시아·송어축제",
  },
  홍천군: {
    tagline: "강촌·패러글라이딩·온천·계곡",
    pop: "약 7.0만",
    specialty: "감·송어·온천",
    highlight: "강촌·비발디·팔봉산",
  },
  화천군: {
    tagline: "산천어·DMZ·청정·겨울 축제",
    pop: "약 2.6만",
    specialty: "산천어·콩·DMZ 생태",
    highlight: "산천어축제·파로호·DMZ",
  },
  횡성군: {
    tagline: "한우·둔내·계곡·힐링 드라이브",
    pop: "약 4.6만",
    specialty: "횡성한우·송이·잣",
    highlight: "둔내·횡성한우·안흥",
  },
};

function landingRegionProfile(region) {
  return REGION_PROFILE[region] || {
    tagline: "강원도의 매력 있는 여행지",
    pop: "—",
    specialty: "지역 먹거리·자연",
    highlight: "AI 맞춤 코스 추천",
  };
}

function buildRegionInfoReply(prompt) {
  const regions = regionsInPrompt(prompt);
  const region = regions[0];
  if (!region) return "강원도 시·군 이름을 포함해 다시 물어봐 주세요.";

  const profile = landingRegionProfile(region);
  const spots = landingRegionSpots(region);
  const wx = landingRegionWeather(region);
  const fest = landingRegionFestival(region);
  const visitors = landingRegionVisitors(region);
  const hubs = landingRegionHubSpots(region);
  const relatePairs = landingRegionRelatePairs(region);
  const korSpots = landingRegionKorSpots(region);
  const ecoSpots = landingRegionEcoSpots(region);

  const lines = [`**${region}**`, "", profile.tagline, ""];
  lines.push(`- **인구** ${profile.pop}`);
  lines.push(`- **특산·먹거리** ${profile.specialty}`);
  lines.push(`- **대표** ${profile.highlight}`);

  if (visitors?.label) {
    lines.push(
      `- **방문**(KTO) ${visitors.label}` +
        (visitors.detail ? ` (${visitors.detail})` : "")
    );
  }
  if (hubs?.length) {
    lines.push(`- **중심 관광지** ${hubs.slice(0, 3).map((h) => h.name).join(", ")}`);
  }
  if (relatePairs?.length) {
    lines.push(
      `- **연관 관광지** ${relatePairs
        .slice(0, 3)
        .map((p) => `${p.anchor} → ${p.related.join(", ")}`)
        .join(" · ")}`
    );
  }
  if (korSpots?.length) {
    lines.push(`- **공식 관광지** ${korSpots.slice(0, 4).map((k) => k.title).join(", ")}`);
  }
  if (ecoSpots?.length) {
    lines.push(`- **생태관광** ${ecoSpots.slice(0, 3).map((e) => e.title).join(", ")}`);
  }
  if (fest?.title) {
    lines.push(`- **축제** ${fest.title}${fest.period ? ` (${fest.period})` : ""}`);
  }
  if (wx) {
    lines.push(`- **날씨** ${wx.city} ${wx.temp}° · ${wx.label}`);
  }

  if (spots.length) {
    lines.push("", "**온도 큐레이션 관광지**");
    spots.forEach((s) => {
      lines.push(`- **${s.name}** — ${s.description}${s.tip ? ` · ${s.tip}` : ""}`);
    });
  }

  lines.push(
    "",
    `"${region} 맞춤 코스 짜줘"라고 하시면 동선·일정도 바로 만들어 드려요.`
  );
  return lines.join("\n");
}

function regionCityKey(region) {
  return String(region ?? "").replace(/(시|군)$/, "");
}

function landingRegionWeather(region) {
  if (!wxCache?.length) return null;
  const key = regionCityKey(region);
  return wxCache.find((w) => w.city === key) || null;
}

function landingRegionFestival(region) {
  if (typeof TOUR_KOR_FESTIVALS === "undefined") return null;
  return (
    TOUR_KOR_FESTIVALS?.regions?.[region]?.[0] ||
    TOUR_KOR_FESTIVALS?.items?.find((f) => f.place === region) ||
    null
  );
}

function landingRegionSpots(region) {
  return ENRICHED_SPOTS.filter((s) => s.region === region);
}

function landingRegionVisitors(region) {
  const stats = typeof TOUR_VISITOR_STATS !== "undefined" ? TOUR_VISITOR_STATS : null;
  const row = stats?.regions?.[region];
  if (!row?.label) return null;
  return row;
}

function landingRegionHubSpots(region) {
  const hubs = ktoEntriesBySource(region, "중심");
  return hubs.length ? hubs.slice(0, 3).map((h) => ({ name: h.name, rank: h.rank })) : null;
}

function landingRegionRelatePairs(region, maxAnchors = 3) {
  const byAnchor =
    typeof TOUR_RELATE_SPOTS !== "undefined" ? TOUR_RELATE_SPOTS?.by_anchor?.[region] : null;
  if (!byAnchor) return null;
  const pairs = Object.entries(byAnchor)
    .slice(0, maxAnchors)
    .map(([anchor, rows]) => ({
      anchor,
      related: (rows || []).slice(0, 3).map((r) => r.name).filter(Boolean),
    }))
    .filter((p) => p.related.length);
  return pairs.length ? pairs : null;
}

function landingRegionKorSpots(region) {
  const spots = ktoEntriesBySource(region, "공식");
  return spots.length ? spots.slice(0, 3).map((k) => ({ title: k.name, image: k.imageUrl })) : null;
}

function landingRegionEcoSpots(region) {
  const spots = ktoEntriesBySource(region, "생태");
  return spots.length ? spots.slice(0, 2).map((e) => ({ title: e.name, image: e.imageUrl })) : null;
}

function normSpotTitle(s) {
  return String(s || "").replace(/\s/g, "");
}

/* ==================== Spot images + 404 fallback ==================== */
const BAD_IMAGE_URLS = new Set();
const FEST_FALLBACK_GRADS = [
  "linear-gradient(135deg,#006a61,#66bcb0)",
  "linear-gradient(135deg,#38bdf8,#7dd3fc)",
  "linear-gradient(135deg,#a78bfa,#ddd6fe)",
  "linear-gradient(135deg,#fb923c,#fed7aa)",
];

function imageUrlVariants(url) {
  const u = String(url || "").trim();
  if (!u) return [];
  const out = [u];
  if (u.startsWith("http://")) out.push("https://" + u.slice(7));
  else if (u.startsWith("https://")) out.push("http://" + u.slice(8));
  return out;
}

function pushImageCandidates(bucket, url) {
  for (const v of imageUrlVariants(url)) {
    if (!v || bucket.seen.has(v) || BAD_IMAGE_URLS.has(v)) continue;
    bucket.seen.add(v);
    bucket.list.push(v);
  }
}

function uniqImageUrls(urls) {
  const bucket = { seen: new Set(), list: [] };
  for (const u of urls) pushImageCandidates(bucket, u);
  return bucket.list;
}

function regionFromPlace(place) {
  const p = String(place || "");
  return GANGWON_REGION_NAMES.find((r) => p.includes(r) || p.includes(r.replace(/[시군]$/, ""))) || null;
}

function collectRegionImageCandidates(region) {
  const bucket = { seen: new Set(), list: [] };
  if (typeof TOUR_REGION_PHOTO_GALLERY !== "undefined") {
    for (const u of TOUR_REGION_PHOTO_GALLERY[region] || []) pushImageCandidates(bucket, u);
  }
  if (typeof REGION_TOUR_PHOTOS !== "undefined" && REGION_TOUR_PHOTOS[region]) {
    pushImageCandidates(bucket, REGION_TOUR_PHOTOS[region]);
  }
  for (const entry of collectKtoCatalogEntries(region)) {
    if (entry.imageUrl) pushImageCandidates(bucket, entry.imageUrl);
  }
  if (typeof SPOT_TOUR_IMAGES !== "undefined") {
    for (const s of ENRICHED_SPOTS) {
      if (s.region === region && SPOT_TOUR_IMAGES[s.name]) {
        pushImageCandidates(bucket, SPOT_TOUR_IMAGES[s.name]);
      }
    }
  }
  return bucket.list;
}

function collectSpotImageCandidates(region, spotName, spot) {
  const bucket = { seen: new Set(), list: [] };
  if (spot?.tourImage) pushImageCandidates(bucket, spot.tourImage);
  if (typeof SPOT_TOUR_IMAGES !== "undefined" && spotName && SPOT_TOUR_IMAGES[spotName]) {
    pushImageCandidates(bucket, SPOT_TOUR_IMAGES[spotName]);
  }
  const entries = collectKtoCatalogEntries(region);
  const n = normSpotTitle(spotName);
  if (n) {
    for (const entry of entries) {
      if (!entry.imageUrl) continue;
      const t = normSpotTitle(entry.name);
      if (t && (t.includes(n) || n.includes(t))) pushImageCandidates(bucket, entry.imageUrl);
    }
  }
  for (const entry of entries) {
    if (entry.imageUrl) pushImageCandidates(bucket, entry.imageUrl);
  }
  for (const u of collectRegionImageCandidates(region)) pushImageCandidates(bucket, u);
  return bucket.list;
}

function collectFestivalImageCandidates(f) {
  const bucket = { seen: new Set(), list: [] };
  if (f?.image) pushImageCandidates(bucket, f.image);
  const region = regionFromPlace(f?.place);
  if (region) {
    for (const u of collectRegionImageCandidates(region)) pushImageCandidates(bucket, u);
  }
  return bucket.list;
}

function imgWithFallback(candidates, opts = {}) {
  const {
    className = "",
    alt = "",
    fbKind = "spot",
    fbCls = "badge-nature",
    fbLabel = "SPOT",
    fbGrad = "",
    fbIcon = "🎉",
  } = opts;
  const list = uniqImageUrls(Array.isArray(candidates) ? candidates : [candidates].filter(Boolean));
  if (!list.length) return "";
  const [primary, ...rest] = list;
  const restAttr = rest.length ? ` data-img-rest="${esc(JSON.stringify(rest))}"` : "";
  const cls = className ? ` class="${esc(className)}"` : "";
  return (
    `<img src="${esc(primary)}" alt="${esc(alt)}" loading="lazy" decoding="async"` +
    `${cls} data-img-fallback="1" data-img-fb-kind="${esc(fbKind)}"` +
    ` data-img-fb-cls="${esc(fbCls)}" data-img-fb-label="${esc(fbLabel)}"` +
    ` data-img-fb-grad="${esc(fbGrad)}" data-img-fb-icon="${esc(fbIcon)}"` +
    `${restAttr} />`
  );
}

function onSpotImgError(img) {
  if (!img || img.dataset.imgDone === "1") return;
  const failed = img.currentSrc || img.src;
  if (failed) BAD_IMAGE_URLS.add(failed);

  let rest = [];
  try {
    rest = JSON.parse(img.dataset.imgRest || "[]");
  } catch (_) {
    rest = [];
  }
  rest = rest.filter((u) => u && u !== failed && !BAD_IMAGE_URLS.has(u));
  const next = rest.shift();
  if (next) {
    img.dataset.imgRest = JSON.stringify(rest);
    img.src = next;
    return;
  }

  img.dataset.imgDone = "1";
  const kind = img.dataset.imgFbKind || "spot";
  const fbCls = img.dataset.imgFbCls || "badge-nature";
  const fbLabel = img.dataset.imgFbLabel || "SPOT";
  const fbGrad = img.dataset.imgFbGrad || FEST_FALLBACK_GRADS[0];
  const fbIcon = img.dataset.imgFbIcon || "🎉";

  if (kind === "course") {
    const el = document.createElement("div");
    el.className = `course-img-fallback ${fbCls}`;
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = `<span>${fbLabel}</span>`;
    img.replaceWith(el);
    return;
  }
  if (kind === "fest") {
    const span = document.createElement("span");
    span.className = "fest-card-icon";
    span.style.background = fbGrad;
    span.textContent = fbIcon;
    img.replaceWith(span);
    return;
  }
  if (kind === "region") {
    const wrap = img.closest(".landing-region-tip-photo");
    if (wrap) wrap.remove();
    else img.remove();
    return;
  }
  const span = document.createElement("span");
  span.className = `spot-card-thumb spot-card-thumb-fallback ${fbCls}`;
  span.textContent = "📍";
  span.setAttribute("aria-hidden", "true");
  img.replaceWith(span);
}

function initImageFallback() {
  document.addEventListener(
    "error",
    (e) => {
      const t = e.target;
      if (t?.tagName === "IMG" && t.dataset?.imgFallback === "1") onSpotImgError(t);
    },
    true
  );
}

function landingRegionPhoto(region) {
  const url = typeof REGION_TOUR_PHOTOS !== "undefined" ? REGION_TOUR_PHOTOS[region] : null;
  return url ? { image: url } : null;
}

function regionTourPhoto(region, spotName) {
  return collectSpotImageCandidates(region, spotName, null)[0] || null;
}

function resolveSpotImage(region, spotName, spot) {
  return collectSpotImageCandidates(region, spotName, spot)[0] || null;
}

function buildLandingRegionTipHtml(region) {
  const spots = landingRegionSpots(region);
  const profile = landingRegionProfile(region);
  const wx = landingRegionWeather(region);
  const fest = landingRegionFestival(region);
  const visitors = landingRegionVisitors(region);
  const hubs = landingRegionHubSpots(region);
  const relatePairs = landingRegionRelatePairs(region);
  const korSpots = landingRegionKorSpots(region);
  const ecoSpots = landingRegionEcoSpots(region);
  const photo = landingRegionPhoto(region);
  const themes = [...new Set(spots.map((s) => SPOT_THEME_LABELS[s.theme] || s.theme))].slice(0, 3);
  const names = spots.slice(0, 3).map((s) => s.name);

  const wxHtml = wx
    ? `<span class="landing-region-tip-wx">${esc(wx.icon)} ${wx.temp}° · ${esc(wx.label)}</span>`
    : "";

  const metaHtml =
    `<div class="landing-region-tip-meta">` +
    `<span class="landing-region-tip-meta-item"><span class="landing-region-tip-label">인구</span> ${esc(profile.pop)}</span>` +
    `<span class="landing-region-tip-meta-item"><span class="landing-region-tip-label">특산</span> ${esc(profile.specialty)}</span>` +
    (visitors
      ? `<span class="landing-region-tip-meta-item"><span class="landing-region-tip-label">방문</span> ${esc(visitors.label)}${visitors.detail ? ` <span class="landing-region-tip-visit-detail">(${esc(visitors.detail)})</span>` : ""}</span>`
      : "") +
    `</div>`;

  const highlightHtml = profile.highlight
    ? `<p class="landing-region-tip-highlight"><span class="landing-region-tip-label">대표</span> ${esc(profile.highlight)}</p>`
    : "";

  const tagsHtml = themes.length
    ? `<div class="landing-region-tip-tags">${themes.map((t) => `<span class="landing-region-tip-tag">${esc(t)}</span>`).join("")}</div>`
    : "";

  let spotsLine = "";
  if (names.length) {
    const extra = spots.length > names.length ? ` 외 ${spots.length - names.length}곳` : "";
    spotsLine = `<p class="landing-region-tip-spots"><span class="landing-region-tip-label">큐레이션</span> ${esc(names.join(" · "))}${esc(extra)}</p>`;
  } else {
    spotsLine = `<p class="landing-region-tip-spots muted">큐레이션 준비 중 · AI로 맞춤 코스를 만들어 보세요</p>`;
  }

  const festHtml = fest
    ? `<p class="landing-region-tip-fest">🎉 ${esc(fest.title)} <span>· ${esc(fest.period)}</span></p>`
    : "";

  const photoHtml = photo?.image
    ? (() => {
        const regionCandidates = collectRegionImageCandidates(region);
        const candidates = uniqImageUrls([photo.image, ...regionCandidates]);
        return candidates.length
          ? `<div class="landing-region-tip-photo">${imgWithFallback(candidates, {
              alt: photo.title || region,
              fbKind: "region",
            })}<span class="landing-region-tip-photo-cap">${esc(photo.title || "")}</span></div>`
          : "";
      })()
    : "";

  const hubHtml = hubs?.length
    ? `<p class="landing-region-tip-spots"><span class="landing-region-tip-label">중심 관광지</span> ${esc(hubs.map((h) => h.name).join(" · "))}</p>`
    : "";

  const relateHtml = relatePairs?.length
    ? `<p class="landing-region-tip-spots"><span class="landing-region-tip-label">연관 관광지</span> ${esc(
        relatePairs.map((p) => `${p.anchor} → ${p.related.join(", ")}`).join(" · ")
      )}</p>`
    : "";

  const korHtml = korSpots?.length
    ? `<p class="landing-region-tip-spots"><span class="landing-region-tip-label">공식 관광지</span> ${esc(korSpots.map((k) => k.title).join(" · "))}</p>`
    : "";

  const ecoHtml = ecoSpots?.length
    ? `<p class="landing-region-tip-spots"><span class="landing-region-tip-label">생태관광</span> ${esc(ecoSpots.map((e) => e.title).join(" · "))}</p>`
    : "";

  return (
    photoHtml +
    `<div class="landing-region-tip-head">` +
    `<strong>${esc(region)}</strong>${wxHtml}` +
    `</div>` +
    metaHtml +
    `<p class="landing-region-tip-blurb">${esc(profile.tagline)}</p>` +
    highlightHtml +
    hubHtml +
    relateHtml +
    korHtml +
    ecoHtml +
    tagsHtml +
    spotsLine +
    festHtml +
    `<span class="landing-region-tip-cta">클릭하면 AI 맞춤 코스 →</span>`
  );
}

function placementOverflow(x, y, tipW, tipH, maxW, maxH, pad) {
  return (
    Math.max(0, pad - x) +
    Math.max(0, pad - y) +
    Math.max(0, x + tipW - (maxW - pad)) +
    Math.max(0, y + tipH - (maxH - pad))
  );
}

let landingRegionTipPath = null;

function positionLandingRegionTip(path, tip) {
  const svg = path.ownerSVGElement;
  const stage = $("landing-map");
  if (!svg || !stage || !tip) return;

  const bb = path.getBBox();
  const pt = svg.createSVGPoint();
  pt.x = bb.x + bb.width / 2;
  pt.y = bb.y + bb.height / 2;
  const ctm = path.getCTM();
  if (!ctm) return;

  const abs = pt.matrixTransform(ctm);
  const svgRect = svg.getBoundingClientRect();
  const stageRect = stage.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  const w = vb.width || 960;
  const h = vb.height || 820;

  const anchorX = svgRect.left - stageRect.left + (abs.x / w) * svgRect.width;
  const anchorY = svgRect.top - stageRect.top + (abs.y / h) * svgRect.height;

  tip.classList.remove("hidden");
  tip.style.visibility = "hidden";
  tip.style.left = "0px";
  tip.style.top = "0px";

  const tipW = tip.offsetWidth;
  const tipH = tip.offsetHeight;
  tip.style.visibility = "";

  const pad = 12;
  const gap = 12;
  const maxW = stageRect.width;
  const maxH = stageRect.height;

  const candidates = [
    { placement: "above", x: anchorX - tipW / 2, y: anchorY - tipH - gap },
    { placement: "below", x: anchorX - tipW / 2, y: anchorY + gap },
    { placement: "above-left", x: anchorX - tipW - gap, y: anchorY - tipH - gap },
    { placement: "above-right", x: anchorX + gap, y: anchorY - tipH - gap },
    { placement: "below-left", x: anchorX - tipW - gap, y: anchorY + gap },
    { placement: "below-right", x: anchorX + gap, y: anchorY + gap },
    { placement: "right", x: anchorX + gap, y: anchorY - tipH / 2 },
    { placement: "left", x: anchorX - tipW - gap, y: anchorY - tipH / 2 },
  ];

  let best = candidates[0];
  let bestScore = Infinity;
  for (const c of candidates) {
    const score = placementOverflow(c.x, c.y, tipW, tipH, maxW, maxH, pad);
    if (score < bestScore) {
      bestScore = score;
      best = c;
    }
  }

  const x = Math.min(Math.max(best.x, pad), Math.max(pad, maxW - tipW - pad));
  const y = Math.min(Math.max(best.y, pad), Math.max(pad, maxH - tipH - pad));

  tip.style.left = `${x}px`;
  tip.style.top = `${y}px`;
  tip.dataset.placement = best.placement;
  landingRegionTipPath = path;
}

function refreshLandingRegionTipPosition() {
  const tip = $("landing-region-tip");
  if (!landingRegionTipPath || !tip || tip.classList.contains("hidden")) return;
  positionLandingRegionTip(landingRegionTipPath, tip);
}

function ensureLandingWeatherCache() {
  if (isWeatherCacheFresh() || wxLoading) return;
  fetchAllGangwonWeather()
    .then((cities) => {
      wxCache = cities;
      wxCacheAt = Date.now();
    })
    .catch((err) => console.warn("landing weather prefetch:", err));
}

async function loadLandingHeroSvg() {
  const host = $("landing-map-svg");
  if (!host || landingSvgLoaded) return;
  const res = await fetch(`assets/gangwon-hero.svg?v=1`);
  if (!res.ok) throw new Error(`gangwon-hero.svg ${res.status}`);
  host.innerHTML = await res.text();
  const svg = host.querySelector("svg");
  if (svg) {
    svg.classList.add("landing-hero-svg");
    svg.setAttribute("aria-label", "강원도 행정구역 지도");
  }
  setupLandingMapFocus(host);
  initLandingDistrictHover(host);
  landingSvgLoaded = true;
}

function setupLandingMapFocus(host) {
  const svg = host.querySelector("svg");
  if (!svg) return;

  const mapRoot = svg.querySelector(":scope > g > g");
  mapRoot?.querySelectorAll(":scope > g:not(.gw-surface):not(.gw-labels)").forEach((g) => {
    g.classList.add("gw-extrude");
  });

  host.querySelectorAll(".gw-surface path[data-region]").forEach((path) => {
    const region = path.getAttribute("data-region") || "";
    const curated = landingRegionSpotCount(region) > 0;
    path.classList.toggle("gw-curated", curated);
    path.classList.remove("gw-muted");
  });
}

function hideLandingRegionTip() {
  const tip = $("landing-region-tip");
  tip?.classList.add("hidden");
  if (tip) {
    tip.style.left = "";
    tip.style.top = "";
    tip.style.visibility = "";
    delete tip.dataset.placement;
  }
  landingRegionTipPath = null;
  $("landing-map-svg")?.classList.remove("has-district-hover");
  $("landing-map-svg")?.querySelectorAll(".gw-district.on").forEach((el) => el.classList.remove("on"));
  landingMarkers.forEach(({ el }) => el?.classList.remove("muted"));
}

function initLandingDistrictHover(host) {
  const tip = $("landing-region-tip");
  const paths = host.querySelectorAll(".gw-surface path[data-region]");
  paths.forEach((path) => {
    path.classList.add("gw-district");
    const region = path.getAttribute("data-region") || "";
    path.setAttribute("role", "button");
    path.setAttribute("tabindex", "0");
    path.setAttribute("aria-label", region);

    const activate = () => {
      host.classList.add("has-district-hover");
      paths.forEach((p) => p.classList.toggle("on", p === path));
      landingMarkers.forEach(({ spot, el }) => {
        el?.classList.toggle("muted", spot.region !== region);
      });
      if (tip) {
        tip.innerHTML = buildLandingRegionTipHtml(region);
        positionLandingRegionTip(path, tip);
        tip.classList.remove("hidden");
      }
    };

    path.addEventListener("mouseenter", activate);
    path.addEventListener("focus", activate);
    path.addEventListener("mouseleave", hideLandingRegionTip);
    path.addEventListener("blur", hideLandingRegionTip);
    path.addEventListener("click", () => {
      const input = $("agent-input");
      if (input && region) {
        input.value = `${region} 여행 코스 추천해줘`;
        autoResizeAgentInput();
        input.focus();
      }
    });
    path.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        path.click();
      }
    });
  });
}

function latLngToLandingMap(spot) {
  const x = LANDING_MAP.ax * spot.lng + LANDING_MAP.bx * spot.lat + LANDING_MAP.cx;
  const y = LANDING_MAP.ay * spot.lng + LANDING_MAP.by * spot.lat + LANDING_MAP.cy;
  return { x, y };
}

function landingSpotPinPosition(spot, host) {
  const path = host?.querySelector(`.gw-surface path[data-region="${spot.region}"]`);
  if (!path) return latLngToLandingMap(spot);

  const svg = path.ownerSVGElement;
  const ctm = path.getCTM();
  if (!svg || !ctm) return latLngToLandingMap(spot);

  const bb = path.getBBox();
  const pt = svg.createSVGPoint();
  pt.x = bb.x + bb.width / 2;
  pt.y = bb.y + bb.height / 2;
  const center = pt.matrixTransform(ctm);

  const city = GANGWON_CITIES.find((c) => c.city === regionCityKey(spot.region));
  const dLat = spot.lat - (city?.lat ?? spot.lat);
  const dLng = spot.lng - (city?.lng ?? spot.lng);

  let x = center.x + (dLng / 0.32) * bb.width * 0.36;
  let y = center.y - (dLat / 0.24) * bb.height * 0.36;

  const siblings = ENRICHED_SPOTS.filter((s) => s.region === spot.region);
  if (siblings.length > 1) {
    const idx = siblings.findIndex((s) => s.name === spot.name);
    const spread = Math.min(bb.width, bb.height) * 0.07;
    x += Math.cos((idx / siblings.length) * Math.PI * 2) * spread;
    y += Math.sin((idx / siblings.length) * Math.PI * 2) * spread;
  }

  x = Math.min(LANDING_MAP.vbW - 10, Math.max(10, x));
  y = Math.min(LANDING_MAP.vbH - 10, Math.max(10, y));
  return { x, y };
}

function hideLandingTip() {
  $("landing-tip")?.classList.add("hidden");
  landingMarkers.forEach(({ el }) => el?.classList.remove("on"));
}

function showLandingTip(spot) {
  const tip = $("landing-tip");
  if (!tip) return;
  tip.innerHTML =
    `<strong>${esc(spot.name)}</strong>` +
    `<span>${esc(spot.region)} · ${esc(spot.theme)}</span>` +
    `<button type="button" class="landing-popup-btn">이곳 포함해서 추천 →</button>`;
  tip.classList.remove("hidden");
  tip.querySelector(".landing-popup-btn")?.addEventListener("click", () => {
    const input = $("agent-input");
    if (input) {
      input.value = `${spot.name} 포함 강원 여행 코스 추천해줘`;
      autoResizeAgentInput();
      input.focus();
    }
    hideLandingTip();
  });
}

function focusLandingSpot(spot) {
  landingMarkers.forEach(({ spot: s, el }) => {
    el?.classList.toggle("on", s.name === spot.name);
  });
}

function buildLandingMap() {
  const pinsG = $("landing-pins");
  const host = $("landing-map-svg");
  if (!pinsG || !host || landingBuilt) return;
  landingBuilt = true;

  ENRICHED_SPOTS.forEach((spot) => {
    const { x, y } = landingSpotPinPosition(spot, host);
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "landing-pin");
    g.setAttribute("transform", `translate(${x.toFixed(1)}, ${y.toFixed(1)})`);
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute("aria-label", spot.name);

    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    ring.setAttribute("class", "landing-pin-ring");
    ring.setAttribute("r", "13");

    const core = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    core.setAttribute("class", "landing-pin-core");
    core.setAttribute("r", "5");

    g.append(ring, core);
    g.addEventListener("mouseenter", () => focusLandingSpot(spot));
    g.addEventListener("mouseleave", () => g.classList.remove("on"));
    g.addEventListener("click", (e) => {
      e.stopPropagation();
      focusLandingSpot(spot);
      showLandingTip(spot);
    });
    g.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        focusLandingSpot(spot);
        showLandingTip(spot);
      }
    });

    pinsG.appendChild(g);
    landingMarkers.push({ spot, el: g });
  });

  $("landing-map")?.addEventListener("click", (e) => {
    if (!e.target.closest(".landing-pin") && !e.target.closest(".landing-tip")) hideLandingTip();
    if (!e.target.closest(".gw-district") && !e.target.closest(".landing-region-tip")) hideLandingRegionTip();
  });
}

function initLandingMap() {
  ensureLandingWeatherCache();
  loadLandingHeroSvg()
    .then(() => buildLandingMap())
    .catch((err) => console.warn("loadLandingHeroSvg:", err));
}

function pauseLandingMap() {
  hideLandingTip();
  hideLandingRegionTip();
}

function resetLandingMap() {
  landingBuilt = false;
  landingSvgLoaded = false;
  landingMarkers = [];
  $("landing-pins")?.replaceChildren();
  $("landing-map-svg")?.replaceChildren("");
  hideLandingTip();
  hideLandingRegionTip();
}

/* ==================== Spots catalog ==================== */
function spotThemeKey(theme) {
  return String(theme || "").toLowerCase();
}

function renderSpotsFilters() {
  const el = $("spots-filters");
  if (!el) return;
  const themes = ["all", ...new Set(ENRICHED_SPOTS.map((s) => spotThemeKey(s.theme)).filter(Boolean))];
  el.innerHTML = themes
    .map(
      (t) =>
        `<button type="button" class="spots-filter${state.spotsFilter === t ? " on" : ""}" data-spots-filter="${esc(t)}" role="tab" aria-selected="${state.spotsFilter === t}">${esc(SPOT_THEME_LABELS[t] || t)}</button>`
    )
    .join("");
}

function renderSpotsGrid() {
  const grid = $("spots-grid");
  if (!grid) return;
  const filter = state.spotsFilter;
  const spots = ENRICHED_SPOTS.filter((s) => filter === "all" || spotThemeKey(s.theme) === filter);
  const totalEl = $("spots-total");
  if (totalEl) totalEl.textContent = String(ENRICHED_SPOTS.length);

  if (!spots.length) {
    grid.innerHTML = `<p class="spots-empty">해당 테마의 명소가 없어요.</p>`;
    return;
  }

  grid.innerHTML = spots
    .map((s) => {
      const prompt = pillPromptAttr(`${s.name}(${s.region}) 포함 강원 여행 코스 추천해줘`);
      const theme = SPOT_THEME_LABELS[spotThemeKey(s.theme)] || s.theme;
      const themeKey = spotThemeKey(s.theme);
      const badge = THEME_BADGE[themeKey] || { label: "SPOT", cls: "badge-nature" };
      const thumbCandidates = collectSpotImageCandidates(s.region, s.name, s);
      const thumbHtml = thumbCandidates.length
        ? imgWithFallback(thumbCandidates, {
            className: "spot-card-thumb",
            fbKind: "spot",
            fbCls: badge.cls,
            fbLabel: badge.label,
          })
        : "";
      return (
        `<button type="button" class="spot-card" data-spot-prompt="${prompt}">` +
        thumbHtml +
        `<span class="spot-card-theme">${esc(theme)}</span>` +
        `<strong>${esc(s.name)}</strong>` +
        `<span class="spot-card-region">📍 ${esc(s.region)}</span>` +
        `<span class="spot-card-tip">${esc(s.tip || s.description || "")}</span>` +
        `<span class="spot-card-cta">✦ AI 코스 만들기</span>` +
        `</button>`
      );
    })
    .join("");
}

function renderSpots() {
  renderSpotsFilters();
  renderSpotsGrid();
}

function initSpots() {
  renderSpots();
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
  comments: "voyageai_community_comments",
  nick: "voyageai_community_nick",
};

function postCreatedAt(post) {
  if (post?.createdAt) {
    const d = new Date(post.createdAt);
    if (!Number.isNaN(d.getTime())) return d;
  }
  const m = String(post?.id || "").match(/^user-(\d+)$/);
  if (m) {
    const d = new Date(Number(m[1]));
    if (!Number.isNaN(d.getTime())) return d;
  }
  const cmt = String(post?.id || "").match(/^cmt-(\d+)-/);
  if (cmt) {
    const d = new Date(Number(cmt[1]));
    if (!Number.isNaN(d.getTime())) return d;
  }
  return null;
}

function formatRelativeTime(d) {
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 45) return "방금 전";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}일 전`;
  const week = Math.floor(day / 7);
  if (week < 5) return `${week}주 전`;
  const month = Math.floor(day / 30);
  if (month < 12) return `${month}개월 전`;
  const year = Math.floor(day / 365);
  return `${year}년 전`;
}

function formatCommunityItemTime(item) {
  const d = postCreatedAt(item);
  if (!d) return "시간 정보 없음";
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  const recorded = d.toLocaleString("ko-KR", {
    year: sameYear ? undefined : "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${recorded} · ${formatRelativeTime(d)}`;
}

function formatCommunityPostTime(post) {
  return formatCommunityItemTime(post);
}

function communityPostTimeTitle(post) {
  const d = postCreatedAt(post);
  if (!d) return "";
  return d.toLocaleString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

let communityTimeTimer = null;

function scheduleCommunityTimeRefresh() {
  if (communityTimeTimer) clearInterval(communityTimeTimer);
  communityTimeTimer = setInterval(() => {
    if (state.view === "community") renderCommunityFeed();
    else {
      clearInterval(communityTimeTimer);
      communityTimeTimer = null;
    }
  }, 60000);
}

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

function loadCommunityComments() {
  try {
    const raw = localStorage.getItem(COMMUNITY_LS.comments);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveCommunityComments(comments) {
  localStorage.setItem(COMMUNITY_LS.comments, JSON.stringify(comments.slice(0, 500)));
}

function commentsForPost(postId) {
  return loadCommunityComments()
    .filter((c) => c.postId === postId)
    .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
}

function getCommunityUserId() {
  const auth = loadAuth();
  return String(auth.userId || "").trim();
}

function isOwnCommunityComment(comment) {
  const uid = getCommunityUserId();
  return Boolean(uid && comment?.authorId && comment.authorId === uid);
}

function toggleCommunityComments(postId) {
  if (state.communityOpenComments.has(postId)) state.communityOpenComments.delete(postId);
  else state.communityOpenComments.add(postId);
  renderCommunityFeed();
}

function submitCommunityComment(postId, text) {
  if (!canUseCommunity()) {
    toast("댓글은 Google·카카오 로그인 후 남길 수 있어요.");
    openLoginModal();
    return;
  }
  const body = String(text || "").trim();
  if (body.length < 2) {
    toast("댓글은 2자 이상 입력해 주세요.");
    return;
  }
  if (body.length > 300) {
    toast("댓글은 300자까지 입력할 수 있어요.");
    return;
  }
  const postExists = allCommunityPosts().some((p) => p.id === postId);
  if (!postExists) {
    toast("게시글을 찾지 못했어요.");
    return;
  }
  const now = new Date();
  const comments = loadCommunityComments();
  comments.push({
    id: `cmt-${now.getTime()}-${Math.random().toString(36).slice(2, 7)}`,
    postId,
    author: getCommunityAuthorName(),
    authorId: getCommunityUserId(),
    body,
    createdAt: now.toISOString(),
  });
  saveCommunityComments(comments);
  state.communityOpenComments.add(postId);
  toast("댓글을 남겼어요.");
  renderCommunityFeed();
}

function deleteCommunityComment(commentId) {
  if (!canUseCommunity()) {
    toast("Google·카카오 로그인 후 삭제할 수 있어요.");
    openLoginModal();
    return;
  }
  const comments = loadCommunityComments();
  const target = comments.find((c) => c.id === commentId);
  if (!target || !isOwnCommunityComment(target)) {
    toast("삭제할 수 없는 댓글이에요.");
    return;
  }
  if (!confirm("내 댓글을 삭제할까요?")) return;
  saveCommunityComments(comments.filter((c) => c.id !== commentId));
  toast("댓글이 삭제되었어요.");
  renderCommunityFeed();
}

function renderCommunityCommentsHtml(post) {
  const comments = commentsForPost(post.id);
  const open = state.communityOpenComments.has(post.id);
  const toggleLabel = open
    ? `💬 댓글 ${comments.length} · 접기`
    : comments.length
      ? `💬 댓글 ${comments.length}`
      : "💬 댓글 달기";

  let html =
    `<div class="community-comments">` +
    `<button type="button" class="community-comment-toggle" data-toggle-comments="${esc(post.id)}" aria-expanded="${open}">` +
    `${esc(toggleLabel)}</button>`;

  if (!open) return html + `</div>`;

  if (comments.length) {
    html += `<ul class="community-comment-list">`;
    for (const c of comments) {
      const delBtn = isOwnCommunityComment(c)
        ? `<button type="button" class="community-comment-delete" data-delete-comment="${esc(c.id)}" aria-label="댓글 삭제">삭제</button>`
        : "";
      html +=
        `<li class="community-comment">` +
        `<div class="community-comment-head">` +
        `<strong>${esc(c.author)}</strong>` +
        `<time datetime="${esc(c.createdAt || "")}" title="${esc(communityPostTimeTitle(c))}">${esc(formatCommunityItemTime(c))}</time>` +
        delBtn +
        `</div>` +
        `<p class="community-comment-body">${esc(c.body)}</p>` +
        `</li>`;
    }
    html += `</ul>`;
  } else {
    html += `<p class="community-comment-empty">첫 댓글을 남겨 보세요.</p>`;
  }

  if (canUseCommunity()) {
    html +=
      `<form class="community-comment-form" data-comment-form data-post-id="${esc(post.id)}">` +
      `<textarea rows="2" maxlength="300" placeholder="댓글을 입력하세요…" aria-label="댓글 입력"></textarea>` +
      `<div class="community-comment-form-foot">` +
      `<button type="submit" class="btn-secondary community-comment-submit">등록</button>` +
      `</div></form>`;
  } else {
    html += `<p class="community-comment-locked">댓글은 <strong>Google·카카오 로그인</strong> 후 남길 수 있어요.</p>`;
  }

  return html + `</div>`;
}

function getCommunityAuthorName() {
  const auth = loadAuth();
  return String(auth.loggedIn && auth.name ? auth.name : "여행러").trim().slice(0, 12) || "여행러";
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
  saveCommunityComments(loadCommunityComments().filter((c) => c.postId !== id));
  state.communityOpenComments.delete(id);
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
    feed.innerHTML = `<p class="community-empty">아직 게시글이 없어요.${canUseCommunity() ? " 첫 번째 이야기를 남겨 보세요!" : ""}</p>`;
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
        `<time class="community-ago" datetime="${esc(postCreatedAt(p)?.toISOString() || "")}" title="${esc(communityPostTimeTitle(p))}">${esc(formatCommunityPostTime(p))}</time>` +
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
        `</div>` +
        renderCommunityCommentsHtml(p) +
        `</div></article>`
      );
    })
    .join("");
}

function renderCommunityCompose() {
  const form = $("community-form");
  const locked = $("community-compose-locked");
  const authorEl = $("community-author");
  const canPost = canUseCommunity();
  form?.classList.toggle("hidden", !canPost);
  locked?.classList.toggle("hidden", canPost);
  if (authorEl && canPost) {
    authorEl.textContent = `${getCommunityAuthorName()}님으로 작성`;
  }
}

function renderCommunity() {
  renderCommunityCompose();
  renderCommunityFilters();
  renderCommunityFeed();
  scheduleCommunityTimeRefresh();
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
  const nick = getCommunityAuthorName();
  const type = $("community-type")?.value || "tip";
  const posts = loadUserCommunityPosts();
  const now = new Date();
  posts.unshift({
    id: `user-${now.getTime()}`,
    type,
    author: nick,
    authorId: getCommunityUserId(),
    region: "강원",
    title: text.length > 42 ? `${text.slice(0, 42)}…` : "",
    body: text,
    tags: [],
    likes: 0,
    createdAt: now.toISOString(),
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
  updateCommunityCharCount();
}

/* ==================== Saved trips (login required) ==================== */
const TRIPS_LS = "voyageai_saved_trips";

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
    toast("찜하려면 로그인해 주세요.");
    state.pendingView = null;
    openLoginModal();
    return;
  }
  if (!state.steps.length) {
    toast("찜할 코스가 없어요.");
    return;
  }
  saveCurrentTripAsync().catch((err) => {
    console.warn("saveCurrentTrip:", err);
    toast("찜하기에 실패했어요.");
  });
}

async function saveCurrentTripAsync() {
  const auth = loadAuth();
  const stops = destinationSteps(state.steps);
  const payload = {
    query: state.query || "",
    meta: JSON.parse(JSON.stringify(state.meta || {})),
    steps: JSON.parse(JSON.stringify(state.steps)),
    focus_order: state.focusOrder,
    stop_names: stops.map((s) => s.spot.name).join(" → "),
  };

  if (canUseSupabaseCloud()) {
    if (!auth.userId) {
      toast("로그인 정보를 확인할 수 없어요. 다시 로그인해 주세요.");
      return;
    }
    const { error } = await sb.from("saved_trips").insert({
      ...payload,
      user_id: auth.userId,
    });
    if (error) {
      console.warn("Supabase saved_trips insert:", error);
      if (error.code === "42P01" || String(error.message || "").includes("saved_trips")) {
        toast("찜 테이블이 없어요. Supabase SQL Editor에서 supabase_schema.sql을 실행해 주세요.");
      } else if (error.code === "42501" || String(error.message || "").includes("row-level security")) {
        toast("찜 권한 오류예요. 다시 로그인하거나 Supabase RLS 정책을 확인해 주세요.");
      } else {
        toast(`찜하기에 실패했어요. (${error.message || error.code || "unknown"})`);
      }
      throw error;
    }
    toast("찜에 담았어요.");
    return;
  }

  const trip = {
    id: `trip-${Date.now()}`,
    savedAt: new Date().toISOString(),
    query: payload.query,
    meta: payload.meta,
    steps: payload.steps,
    focusOrder: state.focusOrder,
    stopNames: payload.stop_names,
  };
  const trips = loadSavedTripsLocal();
  trips.unshift(trip);
  persistSavedTripsLocal(trips);
  toast("찜 했어요!");
}

function deleteSavedTrip(id) {
  if (!isLoggedIn()) return;
  if (!confirm("찜한 코스를 삭제할까요?")) return;
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
  toast("찜에서 삭제했어요.");
  await renderTrips();
}

async function openSavedTrip(id) {
  if (!isLoggedIn()) return;
  const trips = await loadSavedTripsForUser();
  const trip = trips.find((t) => t.id === id);
  if (!trip) {
    toast("찜한 코스를 찾지 못했어요.");
    return;
  }
  state.query = trip.query || "";
  state.meta = trip.meta || {};
  state.steps = trip.steps || [];
  state.focusOrder = trip.focusOrder || 1;
  resetMapState();
  resetKakaoRouteState();
  show("planner");
  renderPlanner();
}

async function renderTrips() {
  const list = $("trips-list");
  const chip = $("trips-count-chip");
  if (!list) return;
  const auth = loadAuth();
  const trips = await loadSavedTripsForUser();
  if (chip) chip.textContent = `${trips.length}개`;

  if (!auth.loggedIn) {
    list.innerHTML = `<p class="trips-empty">로그인하면 찜 목록을 사용할 수 있어요.</p>`;
    return;
  }

  if (!trips.length) {
    list.innerHTML =
      `<div class="trips-empty">` +
      `<p>아직 찜한 코스가 없어요.</p>` +
      `<p class="trips-empty-hint">AI로 코스를 만든 뒤 <strong>♡ 찜하기</strong>를 눌러 보세요.</p>` +
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
  u.search = "";
  if (u.hash.includes("access_token")) {
    const saved = sessionStorage.getItem(VIEW_LS);
    u.hash = saved && saved !== "explore" ? `#${saved}` : "";
  }
  return u.toString();
}

function loadAuth() {
  try {
    const raw = localStorage.getItem(AUTH_LS);
    if (raw) return { email: "", ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { loggedIn: false, name: "", userId: "", provider: "", email: "" };
}

function providerLabel(provider) {
  if (provider === "google") return "Google 연동";
  if (provider === "kakao") return "카카오 연동";
  if (provider === "local") return "체험 계정";
  return "로그인 전";
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
  saveAuth({ loggedIn: true, name, userId: user.id, provider, email: user.email || "" });
  localStorage.setItem(COMMUNITY_LS.nick, name);
}

function clearStaleOAuthAuth() {
  const auth = loadAuth();
  if (isOAuthProvider(auth.provider)) {
    saveAuth({ loggedIn: false, name: "", userId: "", provider: "", email: "" });
  }
}

function renderAuthUI() {
  const auth = loadAuth();
  const loginBtn = $("auth-login-btn");
  const logoutBtn = $("auth-logout-btn");
  const label = $("auth-label");
  const avatar = $("auth-avatar");
  const hint = $("profile-dropdown-hint");
  const ddName = $("profile-dropdown-name");
  const ddProvider = $("profile-dropdown-provider");
  const ddAvatar = $("profile-dropdown-avatar");
  const settingsBtn = $("profile-account-btn");
  if (!loginBtn || !logoutBtn) return;

  if (auth.loggedIn && auth.name) {
    loginBtn.classList.add("hidden");
    logoutBtn.classList.remove("hidden");
    settingsBtn?.classList.remove("hidden");
    if (label) label.textContent = auth.name;
    if (avatar) avatar.textContent = authInitial(auth.name);
    if (ddName) ddName.textContent = auth.name;
    if (ddProvider) ddProvider.textContent = providerLabel(auth.provider);
    if (ddAvatar) ddAvatar.textContent = authInitial(auth.name);
    if (hint) hint.textContent = `${auth.name}님, 아래 목록을 이용할 수 있어요.`;
  } else {
    loginBtn.classList.remove("hidden");
    logoutBtn.classList.add("hidden");
    settingsBtn?.classList.add("hidden");
    if (label) label.textContent = "로그인";
    if (avatar) avatar.textContent = "Y";
    if (ddName) ddName.textContent = "게스트";
    if (ddProvider) ddProvider.textContent = "로그인 전";
    if (ddAvatar) ddAvatar.textContent = "Y";
    if (hint) hint.textContent = "Google·카카오로 로그인하면 아래 목록을 이용할 수 있어요.";
  }
  if (state.view === "community") renderCommunity();
}

function renderProfileModal() {
  const auth = loadAuth();
  const cardAvatar = $("profile-card-avatar");
  const cardName = $("profile-card-name");
  const cardProvider = $("profile-card-provider");
  const emailEl = $("profile-card-email");
  const localBlock = $("profile-modal-local");
  const nickInput = $("profile-nick-edit");
  const logoutModal = $("profile-modal-logout");
  if (cardAvatar) cardAvatar.textContent = authInitial(auth.name || "Y");
  if (cardName) cardName.textContent = auth.name || "게스트";
  if (cardProvider) cardProvider.textContent = providerLabel(auth.provider);
  if (emailEl) {
    if (auth.email) {
      emailEl.textContent = auth.email;
      emailEl.classList.remove("hidden");
    } else {
      emailEl.textContent = "";
      emailEl.classList.add("hidden");
    }
  }
  if (localBlock && nickInput) {
    if (auth.loggedIn && auth.provider === "local") {
      localBlock.classList.remove("hidden");
      nickInput.value = auth.name || "";
    } else {
      localBlock.classList.add("hidden");
    }
  }
  logoutModal?.classList.toggle("hidden", !auth.loggedIn);
}

function openProfileModal() {
  if (!isLoggedIn()) {
    openLoginModal();
    return;
  }
  closeProfileMenu();
  renderProfileModal();
  const modal = $("profile-modal");
  if (!modal) return;
  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");
  initIcons();
}

function closeProfileModal() {
  const modal = $("profile-modal");
  if (!modal) return;
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
}

function saveProfileNick() {
  const auth = loadAuth();
  if (!auth.loggedIn || auth.provider !== "local") return;
  const nick = String($("profile-nick-edit")?.value || "").trim().slice(0, 12);
  if (nick.length < 2) {
    toast("닉네임은 2자 이상 입력해 주세요.");
    $("profile-nick-edit")?.focus();
    return;
  }
  saveAuth({ ...auth, name: nick, userId: `local:${nick}` });
  localStorage.setItem(COMMUNITY_LS.nick, nick);
  renderAuthUI();
  renderProfileModal();
  toast("프로필 이름을 저장했어요.");
}

const OAUTH_PROVIDERS = {
  google: { label: "Google" },
  kakao: { label: "카카오" },
};

function syncLoginModalMode() {
  const desc = $("login-modal-desc");
  if (desc) {
    desc.textContent = hasSupabase()
      ? "Google·카카오로 로그인하면 찜 목록이 기기 간에 동기화됩니다."
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

function cancelLoginModal() {
  state.pendingView = null;
  sessionStorage.removeItem(PENDING_VIEW_LS);
  closeLoginModal();
}

function resumePendingViewAfterAuth() {
  if (!isLoggedIn()) return;
  const pending = sessionStorage.getItem(PENDING_VIEW_LS);
  if (!pending || !VIEW_IDS.has(pending)) return;
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
    const saved = sessionStorage.getItem(VIEW_LS);
    const clean = window.location.pathname + window.location.search;
    const hash = saved && saved !== "explore" ? `#${saved}` : "";
    window.history.replaceState({ view: saved || "explore" }, document.title, clean + hash);
  }
  if (sessionStorage.getItem(PENDING_VIEW_LS)) {
    resumePendingViewAfterAuth();
  }
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
  sessionStorage.setItem(VIEW_LS, state.view || "explore");
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
  saveAuth({ loggedIn: true, name: nick, userId: `local:${nick}`, provider: "local", email: "" });
  localStorage.setItem(COMMUNITY_LS.nick, nick);
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
  saveAuth({ loggedIn: false, name: "", userId: "", provider: "", email: "" });
  state.pendingView = null;
  sessionStorage.removeItem(PENDING_VIEW_LS);
  renderAuthUI();
  toast("로그아웃했어요.");
}

function initAuth() {
  $("profile-trigger")?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleProfileMenu();
  });
  $("profile-account-btn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!isLoggedIn()) {
      closeProfileMenu();
      openLoginModal();
      return;
    }
    openProfileModal();
  });
  $("profile-modal-close")?.addEventListener("click", closeProfileModal);
  $("profile-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "profile-modal") closeProfileModal();
  });
  $("profile-nick-save")?.addEventListener("click", saveProfileNick);
  $("profile-modal-logout")?.addEventListener("click", () => {
    closeProfileModal();
    logoutAuth().catch((err) => console.warn("logout:", err));
  });
  $("auth-login-btn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    closeProfileMenu();
    openLoginModal();
  });
  $("auth-logout-btn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    closeProfileMenu();
    logoutAuth().catch((err) => console.warn("logout:", err));
  });
  $("login-google")?.addEventListener("click", () => {
    loginWithOAuth("google").catch((err) => console.warn("loginWithOAuth(google):", err));
  });
  $("login-kakao")?.addEventListener("click", () => {
    loginWithOAuth("kakao").catch((err) => console.warn("loginWithOAuth(kakao):", err));
  });
  $("login-submit")?.addEventListener("click", submitLogin);
  $("login-cancel")?.addEventListener("click", cancelLoginModal);
  $("login-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "login-modal") cancelLoginModal();
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

function init() {
  try {
    initIcons();
    const n = String(ENRICHED_SPOTS.length);
    const spotEl = $("spot-count");
    if (spotEl) spotEl.textContent = n;
    const landingSpotEl = $("landing-spot-count");
    if (landingSpotEl) landingSpotEl.textContent = n;
    const spotsTotalEl = $("spots-total");
    if (spotsTotalEl) spotsTotalEl.textContent = n;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute(
        "content",
        `강원 온도(ON道) — 강원도 맞춤 여행 코스, ${n}곳 큐레이션, AI 일정·지도·날씨·축제를 한곳에서.`
      );
    }
    $("weather-refresh")?.addEventListener("click", () => {
      wxCache = null;
      wxCacheAt = 0;
      renderWeather(true).catch((err) => console.warn("renderWeather refresh:", err));
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && state.view === "weather" && !isWeatherCacheFresh()) {
        renderWeather(true).catch((err) => console.warn("renderWeather visibility:", err));
      }
    });
    initImageFallback();
    initSpots();
    initCommunity();
    initTrips();
    initAuth();
    if ($("agent-spin")) $("agent-spin").style.display = "none";
    window.addEventListener("resize", () => {
      state.map?.invalidateSize();
      refreshLandingRegionTipPosition();
    }, { passive: true });
    window.addEventListener("hashchange", () => {
      const next = parseViewFromLocation();
      if (next !== state.view) show(next, { skipHash: true });
    });
    show(parseViewFromLocation());
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
