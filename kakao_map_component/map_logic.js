// Clean Leaflet map (CartoDB tiles) — works everywhere, no API key/domain needed.
let mapReady = false;

function hideLoading() {
  const el = document.getElementById('map-loading');
  if (el) el.style.display = 'none';
}

function setLabel(title, focus) {
  const t = document.getElementById('map-label');
  const f = document.getElementById('map-focus-badge');
  if (t) t.textContent = title || 'Live Map';
  if (f) f.textContent = focus ? ('📍 ' + focus) : '정거장을 선택하세요';
}

function popupHtml(spot, showNumbers) {
  const stay = spot.stay_minutes ? ('약 ' + spot.stay_minutes + '분') : '';
  const meta = [spot.region, spot.theme, stay].filter(Boolean).join(' · ');
  return '<div style="min-width:190px;line-height:1.55;font-size:13px;font-family:Inter,sans-serif;">'
    + '<strong style="font-size:13.5px;color:#171d1c;">'
    + (showNumbers && spot.order ? spot.order + '. ' : '') + spot.name + '</strong><br/>'
    + '<span style="color:#3e4947;">' + meta + '</span>'
    + (spot.why ? '<br/><span style="color:#3e4947;">' + spot.why + '</span>' : '')
    + '</div>';
}

function isFocused(spot, focusOrder) {
  return focusOrder > 0 && spot.order === focusOrder;
}

function initLeaflet(cfg) {
  const container = document.getElementById('map');
  container.innerHTML = '';
  container.style.height = cfg.height + 'px';

  const map = L.map(container, { zoomControl: true, attributionControl: true })
    .setView([cfg.center_lat, cfg.center_lng], 9);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap © CARTO',
    subdomains: 'abcd'
  }).addTo(map);

  const latlngs = [];
  let focusSpot = null;

  cfg.markers.forEach(function (spot) {
    const ll = [spot.lat, spot.lng];
    latlngs.push(ll);
    const focused = isFocused(spot, cfg.focus_order);
    if (focused) focusSpot = spot;
    const label = cfg.show_numbers && spot.order ? spot.order : '';
    const icon = L.divIcon({
      html: '<div class="order-pin' + (focused ? ' focus' : '') + '">' + label + '</div>',
      className: '',
      iconSize: focused ? [34, 34] : [28, 28],
      iconAnchor: focused ? [17, 17] : [14, 14]
    });
    const m = L.marker(ll, { icon: icon }).addTo(map);
    m.bindPopup(popupHtml(spot, cfg.show_numbers));
    if (focused) { map.setView(ll, 12); m.openPopup(); }
  });

  if (cfg.show_route && latlngs.length > 1) {
    L.polyline(latlngs, {
      color: '#006a61', weight: 4, opacity: 0.85, dashArray: '1 8', lineCap: 'round'
    }).addTo(map);
  }
  if (!focusSpot && latlngs.length > 1) {
    map.fitBounds(latlngs, { padding: [44, 44] });
  } else if (!focusSpot && latlngs.length === 1) {
    map.setView(latlngs[0], 11);
  }

  mapReady = true;
  hideLoading();
  setTimeout(function () { map.invalidateSize(); }, 150);
  setTimeout(function () { map.invalidateSize(); }, 600);
}

function bootMap(cfg) {
  setLabel(cfg.title, cfg.focus_label);
  if (typeof L === 'undefined') {
    const s = document.createElement('script');
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    s.onload = function () { initLeaflet(cfg); };
    document.head.appendChild(s);
  } else {
    initLeaflet(cfg);
  }
}
