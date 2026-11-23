// 코스 초안과 홍보 문구 초안으로 홍보물 시안을 그린다. 인쇄는 브라우저의 "PDF로 저장"을 쓴다.
const $ = (id) => document.getElementById(id);
const KINDS = [['map', '관광 지도'], ['leaflet', '리플릿'], ['poster', '포스터'], ['cards', 'SNS 카드뉴스'], ['stamp', '스탬프 투어 북'], ['mockup', '적용 예시']];
const SIZE = { map: [420, 297], leaflet: [297, 210], poster: [420, 594], cards: [285.75, 357.19], stamp: [105, 148], mockup: [420, 297] }; // mm
const SLOT = { '낮': 'day', '낮오후': 'day', '2일차오전': 'day', '점심': 'meal', '저녁': 'meal', '밤': 'night', '숙박': 'stay' };
const COLOR = { day: '#E8962E', meal: '#D9542B', night: '#4B46B8', stay: '#7A8699' };
const SLOTNAME = { '낮': '낮', '낮오후': '오후', '2일차오전': '오전', '점심': '점심', '저녁': '저녁', '밤': '밤', '숙박': '숙박' };
const params = new URLSearchParams(location.search);
const state = { kind: params.get('kind') || 'map', lang: '한국어', plan: null, map: null, promo: null, id: '' };

const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const get = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(url); return r.json(); };

// ---------- 내용 ----------
function title() {
  const c = state.plan.조건;
  const name = state.promo?.홍보?.코스카드?.코스이름;
  if (name && !/미정/.test(name)) return name;
  return `${c.계절}, 대구 ${(c.지역 || []).join('·')}에서 ${c.체류기간 === '1박2일' ? '1박 2일' : '하루'}`;
}
function timeText(s) { return s.시각 ? (s.시각종류 === '가정' ? '약 ' : '') + s.시각 : ''; }
function scene(s) {
  // 장면 문구: 한국어는 문구목록, 다른 언어는 번역목록(AI 초안). 없으면 빈 값.
  const p = state.promo?.홍보;
  if (!p) return { 제목: '', 본문: '' };
  if (state.lang === '한국어') {
    const m = (p.문구목록 || []).find((x) => x.장면ID === s.칸ID);
    const clean = (t) => (!t || t === '미정' ? '' : t);
    return { 제목: clean(m?.제목), 본문: clean(m?.본문) };
  }
  const t = (p.번역목록 || []).find((x) => x.장면ID === s.칸ID && x.언어 === state.lang);
  const v = t?.번역;
  if (!v) return { 제목: '', 본문: '' };
  if (typeof v === 'object') return { 제목: v.제목 || '', 본문: v.본문 || '' };
  const m = String(v).match(/^제목:\s*(.*?)\s*\/\s*본문:\s*(.*)$/s);
  if (m) return { 제목: m[1], 본문: m[2] };
  const [first, ...rest] = String(v).split(/\n+|(?<=[.!?。！？])\s+/);
  return rest.length ? { 제목: first, 본문: rest.join(' ') } : { 제목: '', 본문: first };
}
const placed = () => state.plan.일정.filter((s) => s.좌표);
const draftTag = () => `<span class="draft">초안 · ${state.plan.상태 === '초안' ? '코스 확정 전' : '검토 전'}${state.lang === '한국어' ? '' : ' · 번역 AI 초안'}</span>`;
const chars = (cls = '') => `<div class="duo ${cls}"><img src="/img/raccoon_front.png" alt="너구리"><img src="/img/weasel_front.png" alt="족제비"></div>`;

// ---------- 지도 그림 (SVG) ----------
function mapSvg(ratio, opt = {}) {
  const { origin } = state.map;
  const xy = (c) => [(c.lon - origin.lon) * origin.kx, -(c.lat - origin.lat) * origin.ky];
  const stops = placed().map((s, i) => ({ s, no: i + 1, p: xy(s.좌표) }));
  stops.forEach((a, i) => { for (const b of stops.slice(0, i)) if (Math.hypot(a.p[0] - b.p[0], a.p[1] - b.p[1]) < 80) a.p = [a.p[0] + 90, a.p[1] + 70]; });
  const xs = stops.map((a) => a.p[0]), ys = stops.map((a) => a.p[1]);
  let w = Math.max(...xs) - Math.min(...xs), h = Math.max(...ys) - Math.min(...ys);
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  w = Math.max(w * (opt.zoom || 1.7), 1500); h = Math.max(h * (opt.zoom || 1.7), 1100);
  if (w / h < ratio) w = h * ratio; else h = w / ratio;
  const x0 = cx - w / 2, y0 = cy - h / 2, u = w / 1000;
  const path = (pts) => 'M' + pts.map(([x, y]) => `${x},${-y}`).join('L');
  const near = (pts) => pts.some(([x, y]) => x > x0 - 200 && x < x0 + w + 200 && -y > y0 - 200 && -y < y0 + h + 200);
  const roads = (key, width, color) => `<path d="${state.map[key].filter(near).map(path).join('')}" fill="none" stroke="${color}" stroke-width="${width * u}" stroke-linecap="round" stroke-linejoin="round"/>`;
  const fills = (key, color) => `<path d="${state.map[key].filter(near).map((p) => path(p) + 'Z').join('')}" fill="${color}"/>`;
  let out = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${y0} ${w} ${h}" preserveAspectRatio="xMidYMid slice" class="mapsvg">
    <rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="#EFE3C8"/>
    <path d="${path(state.map.boundary)}Z" fill="#FAF3E1" stroke="#C99A62" stroke-width="${2.2 * u}" stroke-dasharray="${8 * u} ${7 * u}"/>
    ${fills('park', '#CDE2B4')}${fills('water', '#A9D6E5')}${roads('river', 9, '#A9D6E5')}
    ${roads('minor', 2.2, '#FFFFFF')}${roads('walk', 3, '#F6D9A0')}${roads('mid', 4.2, '#FFFFFF')}${roads('major', 7, '#FFFFFF')}`;
  // 순서를 잇는 선 (실제 이동 경로 아님)
  state.plan.구간.forEach((leg, k) => {
    const a = stops.find((x) => x.s === state.plan.일정[leg.출발]).p, b = stops.find((x) => x.s === state.plan.일정[leg.도착]).p;
    const dx = b[0] - a[0], dy = b[1] - a[1], bend = 0.24 * (k % 2 ? -1 : 1) * (dx < 0 ? -1 : 1);
    const c = [(a[0] + b[0]) / 2 - dy * bend, (a[1] + b[1]) / 2 + dx * bend];
    const d = `M${a[0]},${a[1]} Q${c[0]},${c[1]} ${b[0]},${b[1]}`;
    const day2 = leg.일차 === 2;   // 1일차 파란 실선, 2일차 빨간 점선
    const dash = day2 ? ` stroke-dasharray="${16 * u} ${12 * u}"` : '';
    out += `<path d="${d}" fill="none" stroke="#FFFFFF" stroke-width="${13 * u}" stroke-linecap="round"/><path d="${d}" fill="none" stroke="${day2 ? '#D9362E' : '#2F7DE1'}" stroke-width="${7.5 * u}" stroke-linecap="round"${dash}/>`;
  });
  for (const { s, no, p } of stops) {
    const col = COLOR[SLOT[s.시간칸] || 'day'], k = (opt.pin || 1) * u;
    out += `<g transform="translate(${p[0]} ${p[1]}) scale(${k})"><ellipse cx="0" cy="2" rx="13" ry="5" fill="#000" opacity=".18"/>
      <path d="M0,0C-12,-17 -19,-27 -19,-37A19,19 0 1 1 19,-37C19,-27 12,-17 0,0Z" fill="${col}" stroke="#fff" stroke-width="2.5"/>
      <circle cx="0" cy="-37" r="11.5" fill="#fff"/><text x="0" y="-31.5" text-anchor="middle" font-size="17" font-weight="800" fill="${col}">${no}</text>
      ${opt.labels === false ? '' : `<text x="25" y="-30" font-size="19" font-weight="800" fill="#3A2416" stroke="#fff" stroke-width="5" paint-order="stroke" stroke-linejoin="round">${esc(s.이름)}</text>`}</g>`;
  }
  if (opt.legend !== false) {   // 범례: 일차별 선 구분
    const two = state.plan.조건.체류기간 === '1박2일', lw = (two ? 250 : 135) * u, lx = x0 + w - lw - 22 * u, ly = y0 + h - 62 * u;
    out += `<g font-size="${17 * u}" font-weight="800"><rect x="${lx}" y="${ly}" width="${lw}" height="${40 * u}" rx="${10 * u}" fill="#fff" opacity=".94"/>
      <path d="M${lx + 16 * u},${ly + 20 * u}h${46 * u}" stroke="#2F7DE1" stroke-width="${6 * u}" stroke-linecap="round"/><text x="${lx + 72 * u}" y="${ly + 26 * u}" fill="#2F7DE1">1일차</text>
      ${two ? `<path d="M${lx + 132 * u},${ly + 20 * u}h${46 * u}" stroke="#D9362E" stroke-width="${6 * u}" stroke-dasharray="${9 * u} ${8 * u}"/><text x="${lx + 188 * u}" y="${ly + 26 * u}" fill="#D9362E">2일차</text>` : ''}</g>`;
  }
  if (opt.chars !== false && stops.length) {
    const [x, y] = stops[0].p, k = (opt.charSize || 105) * u;
    out += `<image href="/img/raccoon_run.png" x="${x - k * 1.95}" y="${y - k * 0.55}" width="${k}" height="${k}"/><image href="/img/weasel_run.png" x="${x - k * 1.15}" y="${y - k * 0.75}" width="${k * 0.82}" height="${k * 1.03}"/>`;
  }
  return out + '</svg>';
}

// ---------- 홍보물 ----------
function stopList(withText) {
  let day = 0, n = 0, out = '';
  for (const s of state.plan.일정) {
    if (s.일차 !== day) { day = s.일차; out += `<li class="dayhead">${day}일차</li>`; }
    const sc = scene(s), no = s.좌표 ? ++n : '';
    const sub = [SLOTNAME[s.시간칸] || s.시간칸, timeText(s)].filter(Boolean).join(' ');
    const hours = s.운영?.운영시간 ? `<small>운영 ${esc(s.운영.운영시간)}${s.운영.정기휴무 ? ` · 쉬는 날 ${esc(s.운영.정기휴무)}` : ''}</small>` : '';
    out += `<li class="${s.좌표 ? '' : 'open'}"><b class="no ${SLOT[s.시간칸] || 'day'}">${no}</b><div><em>${esc(sub)}</em><strong>${esc(s.좌표 ? s.이름 : sc.제목 || openName(s))}</strong>${withText && sc.본문 ? `<p>${esc(sc.본문)}</p>` : ''}${hours}</div></li>`;
  }
  return out;
}
function legRows() {
  return state.plan.구간.filter((l) => l.이동).map((l) => `<tr><td>${esc(state.plan.일정[l.출발].이름)} → ${esc(state.plan.일정[l.도착].이름)}</td><td>걸어서 ${l.이동.도보}분</td><td>대중교통 ${l.이동.대중교통}분</td></tr>`).join('');
}
function card() {
  const c = { ...(state.promo?.홍보?.코스카드 || {}) };
  if (c.대상문장) c.대상문장 = c.대상문장.replace(/\s*→\s*\[?코스 이름 미정\]?\s*$/, '');   // 이름이 없으면 화살표 뒤를 싣지 않는다
  return c;
}
// 장소가 정해지지 않은 칸은 안쪽 메모(괄호)를 빼고 '미정'으로만 알린다
const openName = (s) => `${s.이름.replace(/\s*\([^)]*\)/g, '').replace(/\s*칸$/, '')} (미정)`;
function cautionLine() {
  // 홍보물에는 가장 넓게 걸리는 주의 두 가지만 싣고, 나머지는 건수로 알린다
  const w = card().남은경고;
  const list = (Array.isArray(w) ? w : w ? [w] : []).map((x) => (typeof x === 'string' ? x : x.문구 || '')).filter(Boolean)
    .map((t) => t.replace(/\s*\(적용 근거:[^)]*\)\s*$/, '').split(/(?<=[다요음]\.)\s/)[0]);
  if (!list.length) return '';
  return `<p class="fine">${esc(list.slice(0, 2).join(' '))}${list.length > 2 ? ` 이 밖에 확인할 점이 ${list.length - 2}건 더 있습니다.` : ''}</p>`;
}
const credit = '<p class="fine">지도 바탕 © OpenStreetMap contributors. 경로선은 순서를 잇는 표시이며 실제 이동 경로가 아닙니다.</p>';

const render = {
  map() {
    const legs = legRows();
    return [el('section', 'sheet s-map', `<div class="mapwrap">${mapSvg(280 / 297)}</div>
      <aside><h1>${esc(title())}</h1>${card().대상문장 ? `<p class="lead">${esc(card().대상문장)}</p>` : ''}
      <ol class="stops">${stopList(false)}</ol>
      ${legs ? `<h2>이동 시간</h2><table>${legs}</table>` : ''}
      <footer>${cautionLine()}${credit}${draftTag()}</footer></aside>`)];
  },
  leaflet() {
    const c = card();
    const outside = el('section', 'sheet s-leaflet', `
      <div class="panel flap"><h2>이런 분께 권합니다</h2><p class="lead">${esc(c.대상문장 || '코스 카드 문구가 아직 없습니다.')}</p>
        ${c.한눈에 ? `<h2>코스 한눈에</h2><p>${esc(c.한눈에)}</p>` : ''}${c.식사안내 ? `<h2>식사 안내</h2><p>${esc(Array.isArray(c.식사안내) ? c.식사안내.join(' ') : c.식사안내.카드표시 || (typeof c.식사안내 === 'string' ? c.식사안내 : ''))}</p>` : ''}</div>
      <div class="panel backp"><h2>알아 두세요</h2>${cautionLine() || '<p class="fine">남은 주의 사항이 없습니다.</p>'}${credit}${draftTag()}</div>
      <div class="panel cover"><p class="kicker">대구 체류 여행</p><h1>${esc(title())}</h1>${chars()}</div>`);
    const inside = el('section', 'sheet s-leaflet inside', `<ol class="stops flow">${stopList(true)}</ol><div class="minimap">${mapSvg(99 / 210, { zoom: 1.5, pin: 1.6, charSize: 170 })}</div>`);
    return [outside, inside];
  },
  poster() {
    const names = placed().map((s, i) => `<li class="${SLOT[s.시간칸] || 'day'}"><b>${i + 1}</b>${esc(s.이름)}</li>`).join('');
    return [el('section', 'sheet s-poster', `<header><p class="kicker">낮에서 밤까지, 대구에서 머무는 여행</p><h1>${esc(title())}</h1></header>
      <div class="mapwrap">${mapSvg(364 / 336, { zoom: 1.45, pin: 1.25, charSize: 150 })}</div>
      <ol class="strip">${names}</ol><footer>${credit}${draftTag()}</footer>`)];
  },
  cards() {
    const sheets = [el('section', 'sheet s-card cover', `<p class="kicker">대구 체류 여행</p><h1>${esc(title())}</h1>${chars()}${draftTag()}`)];
    let n = 0;
    for (const s of state.plan.일정) {
      if (!s.좌표) continue;
      n += 1;
      const sc = scene(s), slot = SLOT[s.시간칸] || 'day';
      sheets.push(el('section', `sheet s-card ${slot}`, `<p class="step"><b>${n}</b>${esc([`${s.일차}일차`, SLOTNAME[s.시간칸], timeText(s)].filter(Boolean).join(' '))}</p>
        <h1>${esc(sc.제목 || s.이름)}</h1>${sc.본문 ? `<p class="body">${esc(sc.본문)}</p>` : ''}<p class="place">${esc(s.이름)}</p>
        <img class="mascot" src="/img/${n % 2 ? 'weasel' : 'raccoon'}_run.png" alt="">${draftTag()}`));
    }
    sheets.push(el('section', 'sheet s-card last', `<h1>오늘의 길</h1><div class="mapwrap">${mapSvg(1, { zoom: 1.5, pin: 1.3, charSize: 130 })}</div>${draftTag()}`));
    return sheets;
  },
  stamp() {
    const sheets = [el('section', 'sheet s-stamp cover', `<p class="kicker">스탬프 투어</p><h1>${esc(title())}</h1>${chars()}<p class="fine">장소마다 도장을 모아 보세요.</p>${draftTag()}`)];
    placed().forEach((s, i) => {
      const sc = scene(s);
      sheets.push(el('section', 'sheet s-stamp', `<p class="step"><b class="no ${SLOT[s.시간칸] || 'day'}">${i + 1}</b>${esc(SLOTNAME[s.시간칸] || '')}</p><h1>${esc(s.이름)}</h1>
        ${sc.제목 ? `<p class="body">${esc(sc.제목)}</p>` : ''}<div class="ring"><span>도장 찍는 곳</span></div>${draftTag()}`));
    });
    sheets.push(el('section', 'sheet s-stamp last', `<h1>모두 모았어요</h1><div class="mapwrap">${mapSvg(105 / 85, { zoom: 1.5, pin: 1.5, labels: false, charSize: 150, legend: false })}</div>
      <p class="fine">도장 보상과 운영 방법은 아직 정해지지 않았습니다.</p>${draftTag()}`));
    return sheets;
  },
  mockup() {
    const kv = (cls) => `<div class="kv ${cls}"><div><p class="kicker">대구 체류 여행</p><strong>${esc(title())}</strong></div>${chars()}</div>`;
    const item = (name, body) => `<figure><div class="mock">${body}</div><figcaption>${name}</figcaption></figure>`;
    return [el('section', 'sheet s-mock', `<h1>다른 매체에 얹어 본 모습</h1><p class="lead">같은 그림을 현수막·전광판·교통수단·기념품에 올린 예시입니다. 실제 제작 규격과 문안은 따로 정해야 합니다.</p>
      <div class="grid">
        ${item('현수막', `<div class="banner">${kv('wide')}</div>`)}
        ${item('전광판 (가로)', `<div class="screen">${kv('')}</div>`)}
        ${item('세로형 디지털 안내판', `<div class="totem">${kv('tall')}</div>`)}
        ${item('버스 옆면', `<div class="bus"><div class="win"></div>${kv('wide')}<i></i><i></i></div>`)}
        ${item('엽서', `<div class="postcard">${kv('')}</div>`)}
        ${item('자석', `<div class="magnet">${chars()}</div>`)}
        ${item('에코백', `<div class="tote"><span></span>${kv('tall')}</div>`)}
        ${item('열쇠고리', `<div class="keyring"><span></span><img src="/img/raccoon_front.png" alt=""></div>`)}
      </div><footer>${draftTag()}</footer>`)];
  },
};

// ---------- 화면 ----------
function fit() {
  const [w] = SIZE[state.kind];
  const px = w * 96 / 25.4, room = Math.min(innerWidth - 48, state.kind === 'stamp' ? 420 : state.kind === 'cards' ? 520 : 1180);
  document.querySelectorAll('.frame').forEach((f) => {
    const k = Math.min(1, room / px), sheet = f.firstElementChild;
    sheet.style.transform = `scale(${k})`;
    f.style.setProperty('--ph', `${SIZE[state.kind][1]}mm`);   // 인쇄할 때 쪽 높이
    f.style.width = `${px * k}px`; f.style.height = `${SIZE[state.kind][1] * 96 / 25.4 * k}px`;
  });
}
function draw() {
  $('pageSize').href = `/page/${state.kind}.css`;
  document.body.dataset.kind = state.kind;
  document.querySelectorAll('#kinds button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.kind === state.kind)));
  const stage = $('stage');
  stage.replaceChildren(...render[state.kind]().map((sheet) => { const f = el('div', 'frame'); f.append(sheet); return f; }));
  fit();
}
function statusLine() {
  const st = $('status');
  st.replaceChildren();
  if (state.promo) {
    const bad = (state.promo.검사 || []).filter((x) => x !== '통과');
    st.textContent = `문구는 AI가 쓴 초안이고 번역은 검토 전입니다.${bad.length ? ` 형식 검사에서 확인할 점이 ${bad.length}건 있습니다.` : ''}`;
    return;
  }
  st.append('홍보 문구를 아직 만들지 않아 장소 이름만 넣었습니다. ');
  const b = el('button', 'link', '홍보 문구 만들기');
  b.type = 'button';
  b.onclick = async () => {
    b.disabled = true;
    const r = await fetch('/api/promo/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: state.id }) });
    if (!r.ok) { st.textContent = (await r.json()).오류 || '시작하지 못했습니다.'; return; }
    poll();
  };
  st.append(b, ' (10분쯤 걸리고 AI 사용량이 듭니다)');
}
async function poll() {
  const r = await get('/api/promo?id=' + encodeURIComponent(state.id));
  if (r.진행.상태 === '진행중' && r.진행.id === state.id) { $('status').textContent = '홍보 문구를 만드는 중입니다. 끝나면 자동으로 바뀝니다.'; setTimeout(poll, 5000); return; }
  if (r.진행.상태 === '멈춤' && r.진행.id === state.id && !r.결과) { $('status').textContent = r.진행.안내; return; }
  state.promo = r.결과; langs(); statusLine(); draw();
}
function langs() {
  const set = ['한국어', ...new Set((state.promo?.홍보?.번역목록 || []).map((t) => t.언어))];
  $('lang').replaceChildren(...set.map((l) => new Option(l === '한국어' ? l : `${l} (AI 초안)`, l, false, l === state.lang)));
  $('lang').hidden = set.length < 2;
}

async function start() {
  for (const [k, name] of KINDS) { const b = el('button', '', name); b.type = 'button'; b.dataset.kind = k; b.onclick = () => { state.kind = k; draw(); }; $('kinds').append(b); }
  try {
    const plans = await get('/api/plans');
    const pick = plans.find((p) => p.id === params.get('id')) || plans.find((p) => p.코스있음);
    if (!pick || !pick.코스있음) { $('status').textContent = '코스 초안이 있는 기획이 없습니다. 코스를 먼저 만들어 주세요.'; return; }
    state.id = pick.id;
    $('back').href = '/?id=' + encodeURIComponent(pick.id);
    [state.plan, state.map] = await Promise.all([get('/api/plan?id=' + encodeURIComponent(pick.id)), get('/map.json')]);
    if (params.get('lang')) state.lang = params.get('lang');
    $('lang').onchange = () => { state.lang = $('lang').value; draw(); };
    $('print').onclick = () => print();
    addEventListener('resize', fit);
    draw();
    await poll().catch(() => statusLine());
    document.body.dataset.ready = '1';
  } catch (e) { $('status').textContent = '홍보물을 불러오지 못했습니다. 서버가 켜져 있는지 확인해 주세요.'; console.error(e); }
}
start();
