/**
 * PickRandomLocation – App Logic
 * Uses Leaflet.js (OpenStreetMap) + Nominatim (reverse geocode) + SheetJS (Excel export)
 */

/* =====================================================================
   STATE
   ===================================================================== */
const state = {
  results: [],
  currentBounds: null,
  currentPolygon: null,
  areaName: '',
  picking: false,
  map: null,
  markers: [],
  polygonLayer: null,
  totalTarget: 0,
  doneCount: 0,
};

/* =====================================================================
   DOM REFS
   ===================================================================== */
const $ = id => document.getElementById(id);
const btnPick          = $('btnPick');
const btnExport        = $('btnExport');
const btnClear         = $('btnClear');
const btnAddArea       = $('btnAddArea');
const areaListEl       = $('areaList');
const totalTargetBadge = $('totalTargetBadge');
const progressWrap     = $('progressWrap');
const progressFill     = $('progressFill');
const progressText     = $('progressText');
const logBox           = $('logBox');
const statPicked       = $('statPicked');
const statArea         = $('statArea');
const resultCountBadge = $('resultCount');
const tbody            = $('resultsBody');
const mapPlaceholder   = $('mapPlaceholder');
const mapZoneChip      = $('mapZoneChip');

let areaRowCounter = 0; // unique id per row

/* =====================================================================
   LOGGING
   ===================================================================== */
function log(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'log-entry' + (type ? ' ' + type : '');
  const now = new Date();
  const ts = now.toTimeString().slice(0,8);
  el.textContent = `[${ts}] ${msg}`;
  logBox.appendChild(el);
  logBox.scrollTop = logBox.scrollHeight;
  // keep max 60 lines
  while (logBox.children.length > 60) logBox.removeChild(logBox.firstChild);
}

/* =====================================================================
   MAP INIT
   ===================================================================== */
function initMap() {
  state.map = L.map('map', {
    center: [16.047, 108.206],
    zoom: 6,
    zoomControl: true,
    attributionControl: true,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(state.map);

  log('Bản đồ đã sẵn sàng', 'success');
}

/* =====================================================================
   AUTOCOMPLETE – Inline admin data (63 tỉnh/TP trước sáp nhập)
   Embedded inline to avoid CORS issue when opened via file:// protocol
   ===================================================================== */
const INLINE_PROVINCES = [
  {code:"01",name:"Thành phố Hà Nội",type:"city",search_name:"Hà Nội"},
  {code:"02",name:"Tỉnh Hà Giang",type:"province",search_name:"Hà Giang"},
  {code:"04",name:"Tỉnh Cao Bằng",type:"province",search_name:"Cao Bằng"},
  {code:"06",name:"Tỉnh Bắc Kạn",type:"province",search_name:"Bắc Kạn"},
  {code:"08",name:"Tỉnh Tuyên Quang",type:"province",search_name:"Tuyên Quang"},
  {code:"10",name:"Tỉnh Lào Cai",type:"province",search_name:"Lào Cai"},
  {code:"11",name:"Tỉnh Điện Biên",type:"province",search_name:"Điện Biên"},
  {code:"12",name:"Tỉnh Lai Châu",type:"province",search_name:"Lai Châu"},
  {code:"14",name:"Tỉnh Sơn La",type:"province",search_name:"Sơn La"},
  {code:"15",name:"Tỉnh Yên Bái",type:"province",search_name:"Yên Bái"},
  {code:"17",name:"Tỉnh Hòa Bình",type:"province",search_name:"Hòa Bình"},
  {code:"19",name:"Tỉnh Thái Nguyên",type:"province",search_name:"Thái Nguyên"},
  {code:"20",name:"Tỉnh Lạng Sơn",type:"province",search_name:"Lạng Sơn"},
  {code:"22",name:"Tỉnh Quảng Ninh",type:"province",search_name:"Quảng Ninh"},
  {code:"24",name:"Tỉnh Bắc Giang",type:"province",search_name:"Bắc Giang"},
  {code:"25",name:"Tỉnh Phú Thọ",type:"province",search_name:"Phú Thọ"},
  {code:"26",name:"Tỉnh Vĩnh Phúc",type:"province",search_name:"Vĩnh Phúc"},
  {code:"27",name:"Tỉnh Bắc Ninh",type:"province",search_name:"Bắc Ninh"},
  {code:"30",name:"Tỉnh Hải Dương",type:"province",search_name:"Hải Dương"},
  {code:"31",name:"Thành phố Hải Phòng",type:"city",search_name:"Hải Phòng"},
  {code:"33",name:"Tỉnh Hưng Yên",type:"province",search_name:"Hưng Yên"},
  {code:"34",name:"Tỉnh Thái Bình",type:"province",search_name:"Thái Bình"},
  {code:"35",name:"Tỉnh Hà Nam",type:"province",search_name:"Hà Nam"},
  {code:"36",name:"Tỉnh Nam Định",type:"province",search_name:"Nam Định"},
  {code:"37",name:"Tỉnh Ninh Bình",type:"province",search_name:"Ninh Bình"},
  {code:"38",name:"Tỉnh Thanh Hóa",type:"province",search_name:"Thanh Hóa"},
  {code:"40",name:"Tỉnh Nghệ An",type:"province",search_name:"Nghệ An"},
  {code:"42",name:"Tỉnh Hà Tĩnh",type:"province",search_name:"Hà Tĩnh"},
  {code:"44",name:"Tỉnh Quảng Bình",type:"province",search_name:"Quảng Bình"},
  {code:"45",name:"Tỉnh Quảng Trị",type:"province",search_name:"Quảng Trị"},
  {code:"46",name:"Tỉnh Thừa Thiên Huế",type:"province",search_name:"Thừa Thiên Huế"},
  {code:"48",name:"Thành phố Đà Nẵng",type:"city",search_name:"Đà Nẵng"},
  {code:"49",name:"Tỉnh Quảng Nam",type:"province",search_name:"Quảng Nam"},
  {code:"51",name:"Tỉnh Quảng Ngãi",type:"province",search_name:"Quảng Ngãi"},
  {code:"52",name:"Tỉnh Bình Định",type:"province",search_name:"Bình Định"},
  {code:"54",name:"Tỉnh Phú Yên",type:"province",search_name:"Phú Yên"},
  {code:"56",name:"Tỉnh Khánh Hòa",type:"province",search_name:"Khánh Hòa"},
  {code:"58",name:"Tỉnh Ninh Thuận",type:"province",search_name:"Ninh Thuận"},
  {code:"60",name:"Tỉnh Bình Thuận",type:"province",search_name:"Bình Thuận"},
  {code:"62",name:"Tỉnh Kon Tum",type:"province",search_name:"Kon Tum"},
  {code:"64",name:"Tỉnh Gia Lai",type:"province",search_name:"Gia Lai"},
  {code:"66",name:"Tỉnh Đắk Lắk",type:"province",search_name:"Đắk Lắk"},
  {code:"67",name:"Tỉnh Đắk Nông",type:"province",search_name:"Đắk Nông"},
  {code:"68",name:"Tỉnh Lâm Đồng",type:"province",search_name:"Lâm Đồng"},
  {code:"70",name:"Tỉnh Bình Phước",type:"province",search_name:"Bình Phước"},
  {code:"72",name:"Tỉnh Tây Ninh",type:"province",search_name:"Tây Ninh"},
  {code:"74",name:"Tỉnh Bình Dương",type:"province",search_name:"Bình Dương"},
  {code:"75",name:"Tỉnh Đồng Nai",type:"province",search_name:"Đồng Nai"},
  {code:"77",name:"Tỉnh Bà Rịa - Vũng Tàu",type:"province",search_name:"Bà Rịa Vũng Tàu"},
  {code:"79",name:"Thành phố Hồ Chí Minh",type:"city",search_name:"Hồ Chí Minh"},
  {code:"80",name:"Tỉnh Long An",type:"province",search_name:"Long An"},
  {code:"82",name:"Tỉnh Tiền Giang",type:"province",search_name:"Tiền Giang"},
  {code:"83",name:"Tỉnh Bến Tre",type:"province",search_name:"Bến Tre"},
  {code:"84",name:"Tỉnh Trà Vinh",type:"province",search_name:"Trà Vinh"},
  {code:"86",name:"Tỉnh Vĩnh Long",type:"province",search_name:"Vĩnh Long"},
  {code:"87",name:"Tỉnh Đồng Tháp",type:"province",search_name:"Đồng Tháp"},
  {code:"89",name:"Tỉnh An Giang",type:"province",search_name:"An Giang"},
  {code:"91",name:"Tỉnh Kiên Giang",type:"province",search_name:"Kiên Giang"},
  {code:"92",name:"Thành phố Cần Thơ",type:"city",search_name:"Cần Thơ"},
  {code:"93",name:"Tỉnh Hậu Giang",type:"province",search_name:"Hậu Giang"},
  {code:"94",name:"Tỉnh Sóc Trăng",type:"province",search_name:"Sóc Trăng"},
  {code:"95",name:"Tỉnh Bạc Liêu",type:"province",search_name:"Bạc Liêu"},
  {code:"96",name:"Tỉnh Cà Mau",type:"province",search_name:"Cà Mau"},
];

let adminData = { provinces: INLINE_PROVINCES };

function loadAdminData() {
  log(`Đã sẵn sàng. Cấu trúc hành chính mới (Tỉnh/TP → Phường/Xã)`, 'success');
}

/* =====================================================================
   MULTI-AREA ROW MANAGEMENT
   ===================================================================== */

function updateTotals() {
  const rows = getAreaRows();
  const total = rows.reduce((s, r) => s + r.qty, 0);
  totalTargetBadge.textContent = `tổng: ${total} điểm`;
  renumberRows();
}

function renumberRows() {
  const nums = areaListEl.querySelectorAll('.area-row-num');
  nums.forEach((el, i) => { el.textContent = i + 1; });
}

function getAreaRows() {
  return [...areaListEl.querySelectorAll('.area-row')].map(row => ({
    el: row,
    query: row.querySelector('.area-row-input').value.trim(),
    qty: Math.max(1, parseInt(row.querySelector('.mini-qty-val').value) || 5),
  }));
}

// Debounce helper
function debounce(fn, delay) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

// Preview bounding box từ Photon extent hoặc Nominatim polygon
function previewAreaOnMap(result) {
  if (!result) return;
  if (state.polygonLayer) state.map.removeLayer(state.polygonLayer);

  // Nếu đã có dữ liệu Nominatim đính kèm (sau khi user chọn)
  if (result._nominatim) {
    const nm = result._nominatim;
    const bbox = nm.boundingbox.map(parseFloat);
    if (nm.geojson) {
      state.polygonLayer = L.geoJSON(nm.geojson, {
        style: { color: '#3b82f6', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.08, dashArray: '5,5' }
      }).addTo(state.map);
    }
    state.map.fitBounds([[bbox[0], bbox[2]], [bbox[1], bbox[3]]], { padding: [20, 20] });
    const label = nm.display_name ? nm.display_name.split(',')[0] : (result.properties.name || '');
    mapZoneChip.innerHTML = `Xem tr&#432;&#7899;c: <span>${label}</span>`;
  } else {
    // Photon result – preview nhanh bằng extent
    const p = result.properties || {};
    const ext = p.extent; // [minLon, maxLat, maxLon, minLat]
    if (ext) {
      state.map.fitBounds([[ext[3], ext[0]], [ext[1], ext[2]]], { padding: [20, 20] });
    } else {
      const [lon, lat] = result.geometry.coordinates;
      state.map.setView([lat, lon], 13);
    }
    mapZoneChip.innerHTML = `Xem tr&#432;&#7899;c: <span>${p.name || ''}</span>`;
  }
  mapPlaceholder.classList.add('hidden');
}

// Nominatim lookup bằng OSM ID để lấy polygon ranh giới
async function fetchNominatimByOsmId(osmType, osmId) {
  const prefix = { node: 'N', way: 'W', relation: 'R' }[(osmType || '').toLowerCase()] || 'R';
  const url = `https://nominatim.openstreetmap.org/lookup?` +
    new URLSearchParams({ osm_ids: `${prefix}${osmId}`, format: 'json', polygon_geojson: 1, addressdetails: 1 });
  const resp = await fetch(url, { headers: { 'Accept-Language': 'vi,en' } });
  const data = await resp.json();
  return data[0] || null;
}

function attachAutocomplete(inputEl, acDropdown) {
  const doSearch = debounce(async () => {
    const q = inputEl.value.trim();
    acDropdown.innerHTML = '';
    if (q.length < 2) { acDropdown.style.display = 'none'; return; }

    const loading = document.createElement('div');
    loading.className = 'ac-item ac-loading';
    loading.textContent = 'Đang tìm...';
    acDropdown.appendChild(loading);
    acDropdown.style.display = 'block';

    try {
      // Photon API – không bị rate-limit như Nominatim
      // lang:'en' để country trả về "Vietnam" nhất quán với filter bên dưới
      const url = `https://photon.komoot.io/api/?` +
        new URLSearchParams({ q: q, limit: 10, lang: 'en', lat: 16.047, lon: 108.206 });
      const resp = await fetch(url);
      const data = await resp.json();

      // Lọc chỉ kết quả ở Việt Nam (country có thể là "Vietnam" hoặc rỗng khi bias đã đủ)
      const results = (data.features || []).filter(f => {
        const country = (f.properties.country || '').toLowerCase()
          .normalize('NFD').replace(/[\u0300-\u036f]/g, ''); // bỏ dấu để so sánh
        return !country || country.includes('viet') || country.includes('vietnam');
      }).slice(0, 7);

      acDropdown.innerHTML = '';
      if (!results.length) {
        const noRes = document.createElement('div');
        noRes.className = 'ac-item ac-no-result';
        noRes.textContent = 'Không tìm thấy kết quả';
        acDropdown.appendChild(noRes);
        acDropdown.style.display = 'block';
        return;
      }

      results.forEach(r => {
        const p = r.properties;
        const mainName = p.name || p.city || p.state || '';
        const subParts = [p.city, p.county, p.state].filter(x => x && x !== mainName);
        const subName = subParts.slice(0, 2).join(', ');

        const item = document.createElement('div');
        item.className = 'ac-item';
        item.innerHTML = `<span class="ac-icon">📍</span><span class="ac-main">${mainName}</span><span class="ac-type">${subName}</span>`;

        // Hover → preview nhanh bằng extent (không tốn API call)
        item.addEventListener('mouseenter', () => previewAreaOnMap(r));

        // Click → chọn địa điểm, rồi tải polygon từ Nominatim
        item.addEventListener('mousedown', async e => {
          e.preventDefault();
          inputEl.value = mainName;
          acDropdown.style.display = 'none';
          updateTotals();
          previewAreaOnMap(r); // preview nhanh trước

          // Gọi Nominatim 1 lần bằng OSM ID để lấy polygon ranh giới
          if (p.osm_id) {
            try {
              const nm = await fetchNominatimByOsmId(p.osm_type, p.osm_id);
              if (nm) { r._nominatim = nm; previewAreaOnMap(r); }
            } catch (_) { /* giữ preview bằng extent */ }
          }
        });
        acDropdown.appendChild(item);
      });
      acDropdown.style.display = 'block';
    } catch (err) {
      acDropdown.innerHTML = '';
      const errEl = document.createElement('div');
      errEl.className = 'ac-item ac-no-result';
      errEl.textContent = 'Lỗi kết nối – kiểm tra mạng';
      acDropdown.appendChild(errEl);
      acDropdown.style.display = 'block';
    }
  }, 500);

  inputEl.addEventListener('input', doSearch);
  inputEl.addEventListener('blur', () => {
    setTimeout(() => { acDropdown.style.display = 'none'; }, 200);
  });
}

function addAreaRow(defaultQuery = '', defaultQty = 5) {
  const id = ++areaRowCounter;
  const row = document.createElement('div');
  row.className = 'area-row';
  row.dataset.id = id;
  row.innerHTML = `
    <div class="area-row-top">
      <span class="area-row-num">${areaListEl.children.length + 1}</span>
      <div class="area-row-input-wrap">
        <input class="area-row-input" type="text" placeholder="Nhập tỉnh, quận, phường..." autocomplete="off" value="${defaultQuery}" />
        <div class="row-ac" style="display:none"></div>
      </div>
      <button class="area-row-remove" title="Xóa">×</button>
    </div>
    <div class="area-row-bottom">
      <span class="area-row-label">🎯 Số điểm ngẫu nhiên: </span>
      <div class="mini-qty">
        <button class="mini-qty-btn" data-action="minus">−</button>
        <input class="mini-qty-val" type="number" value="${defaultQty}" min="1" max="3000" />
        <button class="mini-qty-btn" data-action="plus">+</button>
      </div>
    </div>
  `;
  areaListEl.appendChild(row);

  const inputEl   = row.querySelector('.area-row-input');
  const acDrop    = row.querySelector('.row-ac');
  const qtyVal    = row.querySelector('.mini-qty-val');
  const removeBtn = row.querySelector('.area-row-remove');
  const qtyBtns   = row.querySelectorAll('.mini-qty-btn');

  attachAutocomplete(inputEl, acDrop);
  inputEl.addEventListener('input', updateTotals);

  qtyBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      let v = parseInt(qtyVal.value) || 5;
      if (btn.dataset.action === 'minus') v = Math.max(1, v - 1);
      else v = Math.min(3000, v + 1);
      qtyVal.value = v;
      updateTotals();
    });
  });
  qtyVal.addEventListener('change', () => {
    let v = parseInt(qtyVal.value) || 1;
    qtyVal.value = Math.max(1, Math.min(3000, v));
    updateTotals();
  });

  removeBtn.addEventListener('click', () => {
    if (areaListEl.children.length <= 1) return; // keep at least 1
    row.remove();
    updateTotals();
  });

  updateTotals();
  return row;
}

btnAddArea.addEventListener('click', () => addAreaRow());

document.addEventListener('click', e => {
  if (!e.target.closest('.area-row-input-wrap')) {
    document.querySelectorAll('.row-ac').forEach(d => d.style.display = 'none');
  }
});

/* =====================================================================
   NOMINATIM AREA SEARCH
   ===================================================================== */
async function searchArea(query) {
  log(`Đang tìm khu vực: "${query}"...`, 'info');
  const url = `https://nominatim.openstreetmap.org/search?` +
    new URLSearchParams({
      q: query + ', Vietnam',
      format: 'json',
      addressdetails: 1,
      polygon_geojson: 1,
      limit: 1,
    });
  const resp = await fetch(url, { headers: { 'Accept-Language': 'vi,en' } });
  if (!resp.ok) throw new Error('Nominatim search failed: ' + resp.status);
  const data = await resp.json();
  if (!data.length) throw new Error(`Không tìm thấy khu vực: "${query}"`);
  return data[0];
}

/* =====================================================================
   OVERPASS API – Fetch real address points
   Query for nodes/ways that have addr:housenumber + addr:street
   ===================================================================== */
async function fetchAddressPoints(bbox) {
  // bbox: [south, north, west, east]
  const [s, n, w, e] = bbox;
  const bboxStr = `${s},${w},${n},${e}`;

  const query = `
[out:json][timeout:60];
(
  node["addr:housenumber"]["addr:street"](${bboxStr});
  way["addr:housenumber"]["addr:street"](${bboxStr});
);
out center 3000;
`.trim();

  log('Đang truy vấn Overpass API để lấy địa chỉ thực...', 'info');

  const resp = await fetch('https://overpass-api.de/api/interpreter', {
    method: 'POST',
    body: 'data=' + encodeURIComponent(query),
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  if (!resp.ok) throw new Error('Overpass API error: ' + resp.status);
  const data = await resp.json();
  const elements = data.elements || [];

  // Normalize: extract lat/lng and address tags
  const points = elements.map(el => {
    const lat = el.lat ?? el.center?.lat;
    const lng = el.lon ?? el.center?.lon;
    const tags = el.tags || {};
    return {
      lat,
      lng,
      houseNumber: tags['addr:housenumber'] || '',
      street:      tags['addr:street'] || '',
      ward:        tags['addr:subdistrict'] || tags['addr:quarter'] || tags['addr:suburb'] || '',
      district:    tags['addr:district'] || tags['addr:city_district'] || '',
      province:    tags['addr:province'] || tags['addr:state'] || tags['addr:city'] || '',
    };
  }).filter(p => p.lat && p.lng && p.street);

  return points;
}

/* Shuffle array in-place (Fisher-Yates) */
function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/* =====================================================================
   NOMINATIM REVERSE GEOCODE
   ===================================================================== */
async function reverseGeocode(lat, lng) {
  const url = `https://nominatim.openstreetmap.org/reverse?` +
    new URLSearchParams({
      lat, lon: lng,
      format: 'json',
      addressdetails: 1,
      zoom: 18,
    });
  const resp = await fetch(url, { headers: { 'Accept-Language': 'vi,en' } });
  if (!resp.ok) throw new Error('Nominatim reverse failed: ' + resp.status);
  return resp.json();
}

/* =====================================================================
   ADDRESS PARSING (cấu trúc hành chính mới: Tỉnh/TP → Phường/Xã)
   ===================================================================== */

/**
 * Các thành phố trực thuộc trung ương – để thêm prefix "Thành phố" đúng.
 * Theo cấu trúc mới sau sáp nhập 2025.
 */
const DIRECT_CITIES = new Set([
  'hà nội', 'hồ chí minh', 'hải phòng', 'đà nẵng', 'cần thơ',
]);

/**
 * Format province name: đảm bảo có prefix đúng (Thành phố / Tỉnh).
 * Không remap tên cũ – chấp nhận tên mới từ OSM/Nominatim.
 */
function normalizeProvince(raw) {
  if (!raw) return '';
  // Already has correct prefix
  if (/^(Thành phố|Tỉnh|TP\.)\s/i.test(raw)) return raw;
  const key = raw.trim().toLowerCase();
  if (DIRECT_CITIES.has(key)) return 'Thành phố ' + raw.trim();
  return 'Tỉnh ' + raw.trim();
}

function parseAddress(nominatimResult) {
  const a = nominatimResult.address || {};
  const display = nominatimResult.display_name || '';

  // --- Specific Address (number + street) ---
  const houseNumber = a.house_number || '';
  const road = a.road || a.pedestrian || a.path || a.cycleway || '';
  let specificAddress = [houseNumber, road].filter(Boolean).join(' ');
  if (!specificAddress) {
    // Try quarter or neighbourhood as specific fallback
    specificAddress = a.quarter || a.neighbourhood || a.hamlet || '';
  }

  // --- Province/City ---
  // Nominatim keys (in priority): state > city (for centrally-run cities)
  const rawProvince = a.state || a.city || a['ISO3166-2-lvl4'] || '';
  const province = normalizeProvince(rawProvince);

  // --- District --- (kept internally, not displayed)
  const district =
    a.county ||
    a.city_district ||
    a.district ||
    a.borough || '';

  // --- Ward (Phường/Xã) ---
  // Trong Nominatim Việt Nam:
  //   suburb      = Phường X   (cấp phường – đúng)
  //   quarter     = Khu phố X  (tiểu khu bên trong phường – KHÔNG dùng)
  const ward =
    a.suburb ||
    a.neighbourhood ||
    a.village ||
    a.hamlet ||
    a.municipality ||
    a.town || '';

  return { specificAddress, province, district, ward };
}

/* =====================================================================
   MARKER CREATION
   ===================================================================== */
function createMarker(lat, lng, index, addrObj) {
  const icon = L.divIcon({
    className: '',
    html: `<div class="custom-marker-icon"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

  const popup = `
    <div>
      <div class="popup-label">Điểm #${index}</div>
      <div class="popup-val">${addrObj.specificAddress || '(Không xác định đường)'}</div>
      <div style="margin-top:6px">
        <div class="popup-label">Phường/Xã</div>
        <div class="popup-val">${addrObj.ward || '-'}</div>
      </div>
      <div>
        <div class="popup-label">Tỉnh/TP</div>
        <div class="popup-val">${addrObj.province || '-'}</div>
      </div>
      <div style="margin-top:6px" class="popup-coord">${lat.toFixed(6)}, ${lng.toFixed(6)}</div>
    </div>`;

  const marker = L.marker([lat, lng], { icon })
    .addTo(state.map)
    .bindPopup(popup);
  state.markers.push(marker);
  return marker;
}

/* =====================================================================
   TABLE ROW
   ===================================================================== */
function addTableRow(index, lat, lng, addr) {
  // Remove empty state
  const emptyRow = tbody.querySelector('.empty-table-row');
  if (emptyRow) emptyRow.remove();

  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td class="stt-cell">${index}</td>
    <td title="${addr.specificAddress}">${addr.specificAddress || '—'}</td>
    <td class="province-cell" title="${addr.province}">${addr.province || '—'}</td>
    <td title="${addr.ward}">${addr.ward || '—'}</td>
    <td class="coord-cell">${lat.toFixed(6)}</td>
    <td class="coord-cell">${lng.toFixed(6)}</td>
  `;
  tr.addEventListener('click', () => {
    state.map.setView([lat, lng], 16);
    state.markers[index - 1]?.openPopup();
  });
  tbody.appendChild(tr);
}

/* =====================================================================
   PROGRESS
   ===================================================================== */
function setProgress(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  progressFill.style.width = pct + '%';
  progressText.textContent = `Đang xử lý ${done}/${total} điểm...`;
}

/* =====================================================================
   SLEEP HELPER (rate limit respect)
   ===================================================================== */
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* =====================================================================
   CLEAR
   ===================================================================== */
function clearAll() {
  state.results = [];
  state.markers.forEach(m => state.map.removeLayer(m));
  state.markers = [];
  tbody.innerHTML = '';
  const emptyTr = document.createElement('tr');
  emptyTr.className = 'empty-table-row';
  emptyTr.innerHTML = '<td colspan="6" class="empty-table">Chưa có dữ liệu. Hãy pick ngẫu nhiên để bắt đầu.</td>';
  tbody.appendChild(emptyTr);
  statPicked.textContent = '0';
  resultCountBadge.textContent = '0';
  log('Đã xoá tất cả kết quả');
}

btnClear.addEventListener('click', clearAll);

/* =====================================================================
   MAIN PICK FLOW (multi-area)
   ===================================================================== */
btnPick.addEventListener('click', async () => {
  const areaRows = getAreaRows();
  const validRows = areaRows.filter(r => r.query);
  if (!validRows.length) { log('Vui lòng nhập ít nhất 1 khu vực', 'error'); return; }

  const totalQty = validRows.reduce((s, r) => s + r.qty, 0);

  // Lock UI
  state.picking = true;
  btnPick.disabled = true;
  btnPick.innerHTML = `<span class="spinner"></span> Đang xử lý...`;
  progressWrap.classList.add('active');
  setProgress(0, totalQty);
  statArea.textContent = totalQty;

  let globalPicked = 0;

  try {
    for (let ri = 0; ri < validRows.length; ri++) {
      const { query, qty } = validRows[ri];
      log(`── [Đợt ${ri+1}/${validRows.length}] ${query} – ${qty} điểm ──`, 'info');

      // Step 1: Find area
      let areaResult;
      try {
        areaResult = await searchArea(query);
      } catch (e) {
        log(`Không tìm thấy khu vực "${query}": ${e.message}`, 'error');
        globalPicked += 0;
        continue;
      }

      const bbox_raw = areaResult.boundingbox;
      const bbox = [
        parseFloat(bbox_raw[0]),
        parseFloat(bbox_raw[1]),
        parseFloat(bbox_raw[2]),
        parseFloat(bbox_raw[3]),
      ];
      const geojson = areaResult.geojson;

      state.currentBounds = bbox;
      state.areaName = areaResult.display_name;

      log(`Tìm thấy: ${areaResult.display_name}`, 'success');

      // Draw area on map (overlay each area)
      if (state.polygonLayer) state.map.removeLayer(state.polygonLayer);
      if (geojson) {
        state.polygonLayer = L.geoJSON(geojson, {
          style: {
            color: '#3b82f6',
            weight: 2,
            fillColor: '#3b82f6',
            fillOpacity: 0.08,
            dashArray: '5,5',
          }
        }).addTo(state.map);
      }
      state.map.fitBounds([[bbox[0], bbox[2]], [bbox[1], bbox[3]]], { padding: [20, 20] });
      mapPlaceholder.classList.add('hidden');
      mapZoneChip.innerHTML = `Khu vực: <span>${query}</span>`;

      // Step 2: Fetch address points via Overpass
      progressText.textContent = `[${query}] Đang tải địa chỉ...`;
      let addressPool = [];
      try {
        addressPool = await fetchAddressPoints(bbox);
        log(`Tìm thấy ${addressPool.length} địa chỉ có số nhà`, 'success');
      } catch (e) {
        log('Lỗi Overpass: ' + e.message, 'error');
      }

      if (addressPool.length === 0) {
        log(`⚠️ Khu vực "${query}" không có dữ liệu OSM đầy đủ.`, 'error');
        continue;
      }

      // Step 3: Reverse geocode center for province/district
      const centerLat = (bbox[0] + bbox[1]) / 2;
      const centerLng = (bbox[2] + bbox[3]) / 2;
      let areaAddr = { province: '', district: '', ward: '' };
      try {
        await sleep(600);
        const revCenter = await reverseGeocode(centerLat, centerLng);
        areaAddr = parseAddress(revCenter);
        log(`Tỉnh/TP: ${areaAddr.province}`, 'success');
      } catch (e) { /* ignore */ }

      // Step 4: Randomly pick qty addresses
      const pool = shuffleArray([...addressPool]);
      const picks = pool.slice(0, qty);

      for (let i = 0; i < picks.length; i++) {
        const pt = picks[i];
        const { lat, lng, houseNumber, street } = pt;
        const specificAddress = houseNumber ? `${houseNumber} ${street}` : street;
        const province = normalizeProvince(pt.province || areaAddr.province);
        let district = pt.district || areaAddr.district;
        let ward = pt.ward || '';

        if (!ward) {
          try {
            await sleep(800);
            const rev = await reverseGeocode(lat, lng);
            const parsed = parseAddress(rev);
            ward = parsed.ward || '';
            if (!district) district = parsed.district || areaAddr.district;
          } catch (e) { /* skip */ }
        }

        log(`#${globalPicked+1} → ${specificAddress}, ${ward || district}, ${province}`, 'success');

        const record = {
          stt: state.results.length + 1,
          specificAddress,
          province,
          district,
          ward,
          latitude: lat,
          longitude: lng,
        };
        state.results.push(record);
        createMarker(lat, lng, state.results.length, { specificAddress, province, district, ward });
        addTableRow(state.results.length, lat, lng, { specificAddress, province, district, ward });

        globalPicked++;
        statPicked.textContent = state.results.length;
        resultCountBadge.textContent = state.results.length;
        setProgress(globalPicked, totalQty);
      }

      if (picks.length < qty) {
        log(`⚠️ Chỉ tìm được ${picks.length}/${qty} địa chỉ trong "${query}"`, 'info');
      }
    } // end area loop

    log(`Hoàn tất! Đã pick ${globalPicked}/${totalQty} điểm từ ${validRows.length} khu vực.`, 'success');
    if (state.results.length > 0) btnExport.disabled = false;

  } catch (err) {
    log(`Lỗi: ${err.message}`, 'error');
  } finally {
    state.picking = false;
    btnPick.disabled = false;
    btnPick.innerHTML = `<span>🎲</span> Pick Ngẫu Nhiên`;
    progressWrap.classList.remove('active');
  }
});

/* =====================================================================
   EXCEL EXPORT (SheetJS)
   ===================================================================== */
btnExport.addEventListener('click', () => {
  if (!state.results.length) return;

  const headers = ['STT', 'Địa chỉ cụ thể', 'Tỉnh/Thành phố', 'Phường/Xã', 'Latitude', 'Longitude'];
  const rows = state.results.map(r => [
    r.stt,
    r.specificAddress || '',
    r.province || '',
    r.ward || '',
    r.latitude,
    r.longitude,
  ]);

  const wsData = [headers, ...rows];
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(wsData);

  // Column widths
  ws['!cols'] = [
    { wch: 5 },
    { wch: 36 },
    { wch: 24 },
    { wch: 22 },
    { wch: 14 },
    { wch: 14 },
  ];

  // Style header row (SheetJS CE supports basic cell objects)
  headers.forEach((_, ci) => {
    const cellAddr = XLSX.utils.encode_cell({ r: 0, c: ci });
    if (ws[cellAddr]) {
      ws[cellAddr].s = {
        font: { bold: true, color: { rgb: 'FFFFFF' } },
        fill: { fgColor: { rgb: '1D4ED8' } },
        alignment: { horizontal: 'center' },
      };
    }
  });

  XLSX.utils.book_append_sheet(wb, ws, 'Locations');

  // Generate filename with timestamp
  const now = new Date();
  const ts = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`;
  const safeName = (state.areaName.split(',')[0] || 'Vietnam').replace(/[^\w\sÀ-ỹ]/g, '').trim().replace(/\s+/g, '_');
  const filename = `locations_${safeName}_${ts}.xlsx`;

  XLSX.writeFile(wb, filename);
  log(`Xuất Excel thành công: ${filename}`, 'success');
});

/* =====================================================================
   INIT
   ===================================================================== */
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  loadAdminData();
  btnExport.disabled = true;

  // Add one default area row
  addAreaRow();

  // Add empty table row
  const emptyTr = document.createElement('tr');
  emptyTr.className = 'empty-table-row';
  emptyTr.innerHTML = '<td colspan="6" class="empty-table">Chưa có dữ liệu. Hãy pick ngẫu nhiên để bắt đầu.</td>';
  tbody.appendChild(emptyTr);
});
