const fs = require("fs");
const path = require("path");

const svgPath = path.join(__dirname, "../docs/assets/gangwon-hero.svg");
let svg = fs.readFileSync(svgPath, "utf8");

const regions = [
  "강릉시",
  "고성군",
  "동해시",
  "삼척시",
  "속초시",
  "양구군",
  "양양군",
  "영월군",
  "원주시",
  "인제군",
  "정선군",
  "철원군",
  "춘천시",
  "태백시",
  "평창군",
  "홍천군",
  "화천군",
  "횡성군",
];

const labels = [
  "강릉",
  "고성",
  "동해",
  "삼척",
  "속초",
  "양구",
  "양양",
  "영월",
  "원주",
  "인제",
  "정선",
  "철원",
  "춘천",
  "태백",
  "평창",
  "홍천",
  "화천",
  "횡성",
];

const surfaceMatch = svg.match(/<g class="gw-surface"[^>]*>([\s\S]*?)<\/g>\s*<g class="gw-labels">/);
if (!surfaceMatch) {
  console.error("gw-surface block not found");
  process.exit(1);
}

const paths = [...surfaceMatch[1].matchAll(/<path d="([^"]+)"[^>]*\/?>/g)].map((m) => m[1]);
if (paths.length !== regions.length) {
  console.error(`Expected ${regions.length} paths, found ${paths.length}`);
  process.exit(1);
}

const surfacePaths = paths
  .map((d, i) => `      <path d="${d}" data-region="${regions[i]}"/>`)
  .join("\n");

const labelCoords = [
  [600, 412],
  [452, 113],
  [682, 490],
  [699, 592],
  [494, 195],
  [319, 202],
  [519, 275],
  [493, 627],
  [304, 582],
  [404, 233],
  [584, 543],
  [128, 168],
  [226, 322],
  [661, 633],
  [489, 477],
  [334, 387],
  [199, 219],
  [331, 499],
];

const labelTexts = labelCoords
  .map(([x, y], i) => `      <text x="${x}" y="${y}" text-anchor="middle">${labels[i]}</text>`)
  .join("\n");

svg = svg.replace(
  /<g class="gw-surface"[^>]*>[\s\S]*?<\/g>\s*<g class="gw-labels">[\s\S]*?<\/g>/,
  `<g class="gw-surface" filter="url(#gw-soft)">\n${surfacePaths}\n    </g>\n    <g class="gw-labels">\n${labelTexts}\n    </g>`
);

svg = svg.replace(
  /aria-label="[^"]*"/,
  'aria-label="강원도 행정구역 지도"'
);

fs.writeFileSync(svgPath, svg, "utf8");
console.log("Fixed gangwon-hero.svg with UTF-8 region names");
