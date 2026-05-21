let mapEngine = '';
let mapReady = false;

function showWarn(msg) {
  const el = document.getElementById('map-error');
  el.style.display = 'block';
  el.innerHTML = msg;
}

function hideLoading() {
  const el = document.getElementById('map-loading');
  if (el) el.style.display = 'none';
}

function setLabel(title, focus) {
  document.getElementById('map-label').textContent = title || 'Live Kakao Map';
  document.getElementById('map-focus-badge').textContent =
    focus ? ('📍 ' + focus) : '일정 카드를 클릭하세요';
}

function popupHtml(spot, showNumbers, focused) {
  const stay = spot.stay_minutes ? ('약 ' + spot.stay_minutes + '분') : '';
  return '<div style="min-width:200px;line-height:1.5;font-size:13px;">'
    + '<strong>' + (showNumbers && spot.order ? spot.order + '. ' : '') + spot.name + '</strong><br/>'
    + (spot.region || '') + (spot.theme ? ' · ' + spot.theme : '') + (stay ? ' · ' + stay : '') + '<br/>'
    + (spot.why || '') + '<br/><span style="color:#94A3B8;font-size:11px;">'
    + spot.lat.toFixed(5) + ', ' + spot.lng.toFixed(5) + '</span></div>';
}

function isFocused(spot, focusOrder) {
  return focusOrder > 0 && spot.order === focusOrder;
}

function initLeaflet(cfg) {
  if (mapEngine === 'kakao') return;
  mapEngine = 'leaflet';
  const container = document.getElementById('map');
  container.innerHTML = '';
  container.style.height = cfg.height + 'px';

  const map = L.map(container).setView([cfg.center_lat, cfg.center_lng], 9);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18, attribution: '© OpenStreetMap'
  }).addTo(map);

  const latlngs = [];
  let focusSpot = null;
  cfg.markers.forEach(function(spot) {
    const ll = [spot.lat, spot.lng];
    latlngs.push(ll);
    const focused = isFocused(spot, cfg.focus_order);
    if (focused) focusSpot = spot;
    const icon = L.divIcon({
      html: '<div class="order-pin' + (focused ? ' focus' : '') + '">' + (cfg.show_numbers ? spot.order : '') + '</div>',
      className: '', iconSize: focused ? [32, 32] : [26, 26], iconAnchor: focused ? [16, 16] : [13, 13]
    });
    const m = L.marker(ll, { icon: icon }).addTo(map);
    m.bindPopup(popupHtml(spot, cfg.show_numbers, focused));
    if (focused) { map.setView(ll, 12); m.openPopup(); }
  });

  if (cfg.show_route && latlngs.length > 1) {
    L.polyline(latlngs, { color: '#14B8A6', weight: 4, opacity: 0.85 }).addTo(map);
  }
  if (!focusSpot && latlngs.length > 1) map.fitBounds(latlngs, { padding: [40, 40] });

  mapReady = true;
  hideLoading();
  setTimeout(function() { map.invalidateSize(); }, 200);
  setTimeout(function() { map.invalidateSize(); }, 600);
}

function initKakao(cfg) {
  mapEngine = 'kakao';
  const container = document.getElementById('map');
  container.innerHTML = '';
  container.style.height = cfg.height + 'px';

  const map = new kakao.maps.Map(container, {
    center: new kakao.maps.LatLng(cfg.center_lat, cfg.center_lng),
    level: 8
  });

  const bounds = new kakao.maps.LatLngBounds();
  const path = [];
  let focusSpot = null;

  cfg.markers.forEach(function(spot) {
    const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
    bounds.extend(pos);
    path.push(pos);
    const focused = isFocused(spot, cfg.focus_order);
    if (focused) focusSpot = spot;

    const marker = new kakao.maps.Marker({ position: pos });
    marker.setMap(map);

    if (cfg.show_numbers && spot.order > 0) {
      const bg = focused ? '#E85D04' : '#14B8A6';
      const label = '<div style="padding:4px 9px;background:' + bg + ';color:#fff;border-radius:6px;font-size:12px;font-weight:700;">' + spot.order + '</div>';
      new kakao.maps.CustomOverlay({ position: pos, content: label, yAnchor: 1.45 }).setMap(map);
    }

    const iw = new kakao.maps.InfoWindow({ content: popupHtml(spot, cfg.show_numbers, focused) });
    kakao.maps.event.addListener(marker, 'click', function() { iw.open(map, marker); });
    if (focused) { iw.open(map, marker); map.setCenter(pos); map.setLevel(5); }
  });

  if (cfg.show_route && path.length > 1) {
    new kakao.maps.Polyline({
      path: path, strokeWeight: 4, strokeColor: '#14B8A6',
      strokeOpacity: 0.85, strokeStyle: 'solid'
    }).setMap(map);
  }
  if (!focusSpot && cfg.markers.length > 1) map.setBounds(bounds);
  else if (!focusSpot && cfg.markers.length === 1) {
    map.setCenter(new kakao.maps.LatLng(cfg.markers[0].lat, cfg.markers[0].lng));
    map.setLevel(7);
  }

  mapReady = true;
  hideLoading();
  function relayout() { map.relayout(); }
  setTimeout(relayout, 100);
  setTimeout(relayout, 500);
}

function useOsm(cfg, msg) {
  showWarn(msg + '<br/><small>도메인: https://kangwon-potato.streamlit.app · http://localhost:8501</small>');
  setLabel('OpenStreetMap (대체)', cfg.focus_label);
  if (typeof L === 'undefined') {
    const s = document.createElement('script');
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    s.onload = function() { initLeaflet(cfg); };
    document.head.appendChild(s);
  } else {
    initLeaflet(cfg);
  }
}

function bootMap(cfg) {
  mapReady = false;
  mapEngine = '';
  document.getElementById('map-error').style.display = 'none';
  document.getElementById('map-loading').style.display = 'flex';
  setLabel(cfg.title, cfg.focus_label);

  if (!cfg.appkey) {
    useOsm(cfg, 'KAKAO_MAP_APP_KEY가 없습니다.');
    return;
  }

  let settled = false;
  const timer = setTimeout(function() {
    if (!settled) {
      settled = true;
      useOsm(cfg, '카카오 지도 연결 실패. SDK 도메인·키를 확인하세요.');
    }
  }, 6000);

  function ok() {
    settled = true;
    clearTimeout(timer);
    setLabel('Kakao Map', cfg.focus_label);
  }

  function fail(msg) {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    useOsm(cfg, msg);
  }

  function run() {
    kakao.maps.load(function() {
      try {
        initKakao(cfg);
        ok();
      } catch (e) {
        fail('카카오 오류: ' + e.message);
      }
    });
  }

  if (typeof kakao !== 'undefined' && kakao.maps && kakao.maps.load) {
    run();
    return;
  }

  const sdk = document.createElement('script');
  sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey='
    + encodeURIComponent(cfg.appkey) + '&autoload=false';
  sdk.onload = function() { run(); };
  sdk.onerror = function() { fail('카카오 SDK 로드 실패'); };
  document.head.appendChild(sdk);
}
