import fs from "fs";
import vm from "vm";

const code = fs.readFileSync(new URL("../docs/data.js", import.meta.url), "utf8");
const sandbox = { module: {}, exports: {} };
vm.runInThisContext(
  code.replace('"use strict";', "") +
    "\nthis.__out = { SPOTS, GANGWON_CITIES, FESTIVALS, HIGHLIGHTS, SUGGESTIONS, THEME_META, SPOT_OVERRIDES, FESTIVAL_ICONS, WEATHER_ICONS, THEME_BADGE, THEME_IMAGE, DEFAULT_IMAGE, REGION_INTRO, GEMINI_MODEL };"
);
const o = globalThis.__out;
const catalog = {
  festivals: o.FESTIVALS,
  cities: o.GANGWON_CITIES,
  highlights: o.HIGHLIGHTS.map((h) => ({ ...h, thumb_bg: h.bg })),
  suggestions: o.SUGGESTIONS,
  theme_meta: o.THEME_META,
  spot_overrides: o.SPOT_OVERRIDES,
  festival_icons: o.FESTIVAL_ICONS,
  weather_icons: Object.fromEntries(
    Object.entries(o.WEATHER_ICONS).map(([k, v]) => [k, { ...v, thumb_bg: v.bg }])
  ),
  theme_badge: o.THEME_BADGE,
  theme_image: o.THEME_IMAGE,
  default_image: o.DEFAULT_IMAGE,
  region_intro_html: o.REGION_INTRO,
  region_intro_md: o.REGION_INTRO.replace(/<b>/g, "**").replace(/<\/b>/g, "**"),
  gemini_model: o.GEMINI_MODEL,
};
fs.mkdirSync(new URL("../data", import.meta.url), { recursive: true });
fs.writeFileSync(new URL("../data/spots.json", import.meta.url), JSON.stringify(o.SPOTS, null, 2));
fs.writeFileSync(new URL("../data/catalog.json", import.meta.url), JSON.stringify(catalog, null, 2));
console.log("ok", o.SPOTS.length);
