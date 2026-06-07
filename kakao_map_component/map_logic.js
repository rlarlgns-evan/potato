// Kakao Maps primary; clean Leaflet (CartoDB) fallback. No alarming warnings.
let mapEngine = '';
let settled = false;

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
  return '<div style="min-width:190px;line-height:1.55;font-size:13px;font-family:Inter,sans-serif;padding:2px 2px;">'
    + '<strong style="font-size:13.5px;color:#171d1c;">'
    + (showNumbers && spot.order ? spot.order + '. ' : '') + spot.name + '</strong><br/>'
    + '<span style="color:#3e4947;">' + meta + '</span>'
    + (spot.why ? '<br/><span style="color:#3e4947;">' + spot.why + '</span>' : '')
    + '</div>';
}

function pinDiv(label, focused) {
  return '<div class="order-pin' + (focused ? ' focus' : '') + '">' + (label || '') + '</div>';
}

function isFocused(spot, focusOrder) {
  return focusOrder > 0 && spot.order === focusOrder;
}

// ---------- Kakao ----------
function initKakao(cfg) {
  mapEngine = 'kakao';
  const container = document.getElementById('map');
  container.innerHTML = '';
  container.style.height = cfg.height + 'px';

  const map = new kakao.maps.Map(container, {
    center: new kakao.maps.LatLng(cfg.center_lat, cfg.center_lng),
    level: 8
  });
  map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.LEFT);

  const bounds = new kakao.maps.LatLngBounds();
  const path = [];
  let focusSpot = null;
  let openIw = null;

  cfg.markers.forEach(function (spot) {
    const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
    bounds.extend(pos);
    path.push(pos);
    const focused = isFocused(spot, cfg.focus_order);
    if (focused) focusSpot = spot;

    const label = cfg.show_numbers && spot.order ? spot.order : '';
    const el = document.createElement('div');
    el.innerHTML = pinDiv(label, focused);
    const overlay = new kakao.maps.CustomOverlay({
      position: pos, content: el, yAnchor: 0.5, xAnchor: 0.5,
      zIndex: focused ? 10 : 1
    });
    overlay.setMap(map);

    const iw = new kakao.maps.InfoWindow({
      position: pos, removable: true,
      content: '<div style="padding:8px 10px;">' + popupHtml(spot, cfg.show_numbers) + '</div>'
    });
    el.style.cursor = 'pointer';
    el.addEventListener('click', function () {
      if (openIw) openIw.close();
      iw.open(map);
      openIw = iw;
    });
    if (focused) { iw.open(map); openIw = iw; }
  });

  if (cfg.show_route && path.length > 1) {
    new kakao.maps.Polyline({
      path: path, strokeWeight: 4, strokeColor: '#006a61',
      strokeOpacity: 0.85, strokeStyle: 'shortdash'
    }).setMap(map);
  }

  if (focusSpot) {
    map.setCenter(new kakao.maps.LatLng(focusSpot.lat, focusSpot.lng));
    map.setLevel(6);
  } else if (cfg.markers.length > 1) {
    map.setBounds(bounds);
  } else if (cfg.markers.length === 1) {
    map.setCenter(new kakao.maps.LatLng(cfg.markers[0].lat, cfg.markers[0].lng));
    map.setLevel(7);
  }

  hideLoading();
  setTimeout(function () { map.relayout(); }, 150);
  setTimeout(function () { map.relayout(); }, 600);
}

// ---------- Leaflet fallback ----------
function initLeaflet(cfg) {
  if (mapEngine === 'kakao') return;
  mapEngine = 'leaflet';
  const container = document.getElementById('map');
  container.innerHTML = '';
  container.style.height = cfg.height + 'px';

  const map = L.map(container, { zoomControl: true, attributionControl: true })
    .setView([cfg.center_lat, cfg.center_lng], 9);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap © CARTO', subdomains: 'abcd'
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
      html: pinDiv(label, focused), className: '',
      iconSize: focused ? [34, 34] : [28, 28],
      iconAnchor: focused ? [17, 17] : [14, 14]
    });
    const m = L.marker(ll, { icon: icon }).addTo(map);
    m.bindPopup(popupHtml(spot, cfg.show_numbers));
    if (focused) { map.setView(ll, 12); m.openPopup(); }
  });

  if (cfg.show_route && latlngs.length > 1) {
    L.polyline(latlngs, { color: '#006a61', weight: 4, opacity: 0.85, dashArray: '1 8', lineCap: 'round' }).addTo(map);
  }
  if (!focusSpot && latlngs.length > 1) map.fitBounds(latlngs, { padding: [44, 44] });
  else if (!focusSpot && latlngs.length === 1) map.setView(latlngs[0], 11);

  hideLoading();
  setTimeout(function () { map.invalidateSize(); }, 150);
  setTimeout(function () { map.invalidateSize(); }, 600);
}

function fallback(cfg) {
  if (settled || mapEngine === 'kakao') return;
  settled = true;
  if (typeof L === 'undefined') {
    const s = document.createElement('script');
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    s.onload = function () { initLeaflet(cfg); };
    document.head.appendChild(s);
  } else {
    initLeaflet(cfg);
  }
}

function bootMap(cfg) {
  mapEngine = '';
  settled = false;
  setLabel(cfg.title, cfg.focus_label);

  if (!cfg.appkey) { fallback(cfg); return; }

  // Fall back to Leaflet if Kakao doesn't initialize in time (domain/key issue).
  const timer = setTimeout(function () { fallback(cfg); }, 4500);

  function run() {
    try {
      kakao.maps.load(function () {
        try {
          initKakao(cfg);
          settled = true;
          clearTimeout(timer);
        } catch (e) {
          clearTimeout(timer);
          fallback(cfg);
        }
      });
    } catch (e) {
      clearTimeout(timer);
      fallback(cfg);
    }
  }

  if (typeof kakao !== 'undefined' && kakao.maps && kakao.maps.load) { run(); return; }

  const sdk = document.createElement('script');
  sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey='
    + encodeURIComponent(cfg.appkey) + '&autoload=false';
  sdk.onload = function () { run(); };
  sdk.onerror = function () { clearTimeout(timer); fallback(cfg); };
  document.head.appendChild(sdk);
}
