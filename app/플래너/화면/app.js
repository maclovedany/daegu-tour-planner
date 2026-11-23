import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';

const $ = (id) => document.getElementById(id);
const U = 0.1;                       // 1 단위 = 10 m
const BOUND = { x: 330, z: 245 };    // 지도 판 크기 (단위)
const SLOT = {
  '낮': 'day', '낮오후': 'day', '2일차오전': 'day', '점심': 'meal', '저녁': 'meal', '밤': 'night', '숙박': 'stay',
};
const COLOR = { day: '#f0a030', meal: '#e2603c', night: '#5a55c8', stay: '#7a8699' };
const DUSK = { '저녁': 0.55, '밤': 1, '숙박': 1 };
const SLOTNAME = { '낮': '낮', '낮오후': '오후', '2일차오전': '오전', '점심': '점심', '저녁': '저녁', '밤': '밤', '숙박': '숙박' };
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- 장면 ----------
const canvas = $('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
const SKY = [new THREE.Color('#cfe6f2'), new THREE.Color('#f2b78c'), new THREE.Color('#1b2348')];
scene.background = SKY[0].clone();
scene.fog = new THREE.Fog(scene.background, 700, 1900);
const camera = new THREE.PerspectiveCamera(36, 1, 1, 4000);
camera.position.set(0, 520, 560);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.46;
controls.minDistance = 60;
controls.maxDistance = 1100;

const hemi = new THREE.HemisphereLight('#ffffff', '#d8cfc0', 1.5);
const sun = new THREE.DirectionalLight('#fff3df', 1.6);
sun.position.set(-300, 500, 200);
scene.add(hemi, sun);

const flat = (color, extra = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
const mats = {
  base: flat('#b9c7b0'), land: flat('#e6ecdd'), core: flat('#f6f4ea'), major: flat('#ffffff'), mid: flat('#ffffff'),
  minor: flat('#fbfaf5'), walk: flat('#f3d9a8'), rail: flat('#b5afa5'), water: flat('#9ccfe2'), park: flat('#c2dfb2'),
  edge: flat('#8fa58a'), routeEdge: flat('#ffffff'),
  // 동선은 일차별로 색을 나눈다: 1일차 파랑(실선), 2일차 빨강(점선)
  route: { 1: flat('#2f7de1', { emissive: '#2f7de1', emissiveIntensity: 0 }), 2: flat('#d9362e', { emissive: '#d9362e', emissiveIntensity: 0 }) },
  paw: new THREE.MeshBasicMaterial({ color: '#3b3f4a', transparent: true, opacity: 0.75 }),
};

function inside(p) { return Math.abs(p[0] * U) <= BOUND.x && Math.abs(p[1] * U) <= BOUND.z; }

/** 꺾은선 여러 개를 폭이 있는 띠 하나로 만든다. pts는 [x, z] (단위). */
function ribbon(lines, width, y, material, dash = 0) {
  const pos = [];
  const h = width / 2;
  for (const pts of lines) {
    for (let i = 0; i < pts.length - 1; i++) {
      if (dash && i % (dash * 2) >= dash) continue;
      const [ax, az] = pts[i], [bx, bz] = pts[i + 1];
      const dx = bx - ax, dz = bz - az, len = Math.hypot(dx, dz);
      if (!len) continue;
      const nx = (-dz / len) * h, nz = (dx / len) * h;
      pos.push(ax + nx, y, az + nz, bx + nx, y, bz + nz, ax - nx, y, az - nz,
        bx + nx, y, bz + nz, bx - nx, y, bz - nz, ax - nx, y, az - nz);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const n = new Float32Array(pos.length);
  for (let i = 1; i < n.length; i += 3) n[i] = 1;
  g.setAttribute('normal', new THREE.BufferAttribute(n, 3));
  const mesh = new THREE.Mesh(g, material);
  material.side = THREE.DoubleSide;
  return mesh;
}

function area(pts, y, material) {
  const shape = new THREE.Shape(pts.map(([x, z]) => new THREE.Vector2(x, -z)));
  const g = new THREE.ShapeGeometry(shape);
  g.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(g, material);
  m.position.y = y;
  return m;
}

function buildMap(map) {
  const conv = (line) => line.filter(inside).map(([x, y]) => [x * U, -y * U]);
  const lines = (key) => map[key].map(conv).filter((l) => l.length > 1);
  const slab = new THREE.Mesh(new THREE.BoxGeometry(BOUND.x * 2 + 30, 14, BOUND.z * 2 + 30), [mats.base, mats.base, mats.land, mats.base, mats.base, mats.base]);
  slab.position.y = -7;
  scene.add(slab);
  if (map.boundary.length > 3) {
    const ring = map.boundary.map(([x, y]) => [Math.max(-BOUND.x, Math.min(BOUND.x, x * U)), Math.max(-BOUND.z, Math.min(BOUND.z, -y * U))]);
    scene.add(area(ring, 0.04, mats.core));
    scene.add(ribbon([ring], 1.6, 0.07, mats.edge, 1));
  }
  for (const poly of map.park) if (poly.every(inside) && poly.length > 3) scene.add(area(poly.map(([x, y]) => [x * U, -y * U]), 0.1, mats.park));
  for (const poly of map.water) if (poly.every(inside) && poly.length > 3) scene.add(area(poly.map(([x, y]) => [x * U, -y * U]), 0.12, mats.water));
  scene.add(ribbon(lines('river'), 4, 0.11, mats.water));
  scene.add(ribbon(lines('rail'), 0.9, 0.14, mats.rail, 1));
  scene.add(ribbon(lines('minor'), 0.7, 0.16, mats.minor));
  scene.add(ribbon(lines('walk'), 1.0, 0.17, mats.walk));
  scene.add(ribbon(lines('mid'), 1.5, 0.18, mats.mid));
  scene.add(ribbon(lines('major'), 2.6, 0.2, mats.major));
  return (lat, lon) => new THREE.Vector3((lon - map.origin.lon) * map.origin.kx * U, 0, -(lat - map.origin.lat) * map.origin.ky * U);
}

// 밤하늘 별
const stars = (() => {
  const pos = [];
  for (let i = 0; i < 260; i++) {
    const a = Math.random() * Math.PI * 2, e = 0.12 + Math.random() * 0.9;
    pos.push(Math.cos(a) * Math.cos(e) * 1500, Math.sin(e) * 1500, Math.sin(a) * Math.cos(e) * 1500);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color: '#fff7d6', size: 3, sizeAttenuation: false, transparent: true, opacity: 0, fog: false }));
  scene.add(p);
  return p;
})();

// ---------- 코스 ----------
const state = {
  plan: null, stops: [], legs: [], selected: -1, view: 'whole',
  mode: 'idle', leg: 0, t: 0, pause: 0, dusk: 0, duskGoal: 0, lead: new THREE.Vector3(), dir: new THREE.Vector3(1, 0, 0),
  glide: null, paws: null, pawMarks: [],
};
const labels = [];
const chars = [];

function addLabel(el, pos) { $('labels').appendChild(el); labels.push({ el, pos }); return el; }

function buildCourse(plan, project) {
  const placed = [];
  let n = 0;
  plan.일정.forEach((s, i) => {
    s.slot = SLOT[s.시간칸] || 'day';
    if (!s.좌표) return;
    s.pos = project(s.좌표.lat, s.좌표.lon);
    for (const other of placed) if (other.pos.distanceTo(s.pos) < 8) s.pos.add(new THREE.Vector3(9, 0, 7));  // 같은 곳을 두 번 들르면 핀을 살짝 옮겨 겹치지 않게
    s.no = ++n;
    placed.push(s);
    const color = COLOR[s.slot];
    const pin = new THREE.Group();
    const headMat = flat(color, { emissive: color, emissiveIntensity: 0 });
    const cone = new THREE.Mesh(new THREE.ConeGeometry(3.4, 10, 20), headMat);
    cone.rotation.x = Math.PI; cone.position.y = 5;
    const head = new THREE.Mesh(new THREE.SphereGeometry(4.6, 24, 16), headMat);
    head.position.y = 12;
    const dot = new THREE.Mesh(new THREE.SphereGeometry(2, 16, 12), flat('#ffffff'));
    dot.position.y = 12; dot.scale.set(1.36, 1.36, 1.36);
    const blob = new THREE.Mesh(new THREE.CircleGeometry(5, 24), new THREE.MeshBasicMaterial({ color: '#1f2a44', transparent: true, opacity: 0.18 }));
    blob.rotation.x = -Math.PI / 2; blob.position.y = 0.3;
    head.scale.set(1, 1, 0.82);
    pin.add(cone, head, dot, blob);
    pin.position.copy(s.pos);
    scene.add(pin);
    s.pin = pin; s.headMat = headMat;
    const el = document.createElement('button');
    el.type = 'button'; el.className = 'pinlabel'; el.style.setProperty('--c', color);
    el.innerHTML = `<b>${s.no}</b>`; el.append(s.이름);
    el.addEventListener('click', () => select(i, true));
    s.label = addLabel(el, s.pos.clone().setY(19));
  });
  state.stops = plan.일정;

  // 장소를 잇는 선: 실제 길이 아니라 순서를 보여 주는 곡선
  const pawPos = [];
  plan.구간.forEach((leg, k) => {
    const a = plan.일정[leg.출발].pos, b = plan.일정[leg.도착].pos;
    const mid = a.clone().add(b).multiplyScalar(0.5);
    const d = b.clone().sub(a), len = d.length();
    // 같은 두 곳을 오갈 때 가는 선과 오는 선이 겹치지 않도록, 굽는 쪽을 진행 방향이 아니라 지도 방향 기준으로 번갈아 잡는다
    const perp = new THREE.Vector3(-d.z, 0, d.x).normalize().multiplyScalar(len * 0.24 * (k % 2 ? -1 : 1) * (d.x < 0 ? -1 : 1));
    const curve = new THREE.QuadraticBezierCurve3(a, mid.add(perp), b);
    const pts = curve.getPoints(48).map((p) => [p.x, p.z]);
    const unsure = leg.사이미정 > 0, day2 = leg.일차 === 2;
    scene.add(ribbon([pts], 4.2, 0.3, mats.routeEdge, day2 ? 2 : 0));
    scene.add(ribbon([pts], 2.6, 0.34, mats.route[day2 ? 2 : 1], day2 ? 2 : 0));
    const steps = Math.max(4, Math.floor(curve.getLength() / 7));
    for (let j = 1; j < steps; j++) {
      const t = j / steps, p = curve.getPoint(t), tan = curve.getTangent(t);
      const side = new THREE.Vector3(-tan.z, 0, tan.x).multiplyScalar(j % 2 ? 4.6 : 6.2);
      pawPos.push({ leg: k, t, p: p.add(side), rot: Math.atan2(tan.x, tan.z) });
    }
    const el = document.createElement('div');
    el.className = 'leglabel' + (leg.이동 ? '' : ' unknown') + (day2 ? ' d2' : '');
    el.textContent = leg.이동 ? `걸어서 ${leg.이동.도보}분, 대중교통 ${leg.이동.대중교통}분`
      : unsure ? `사이에 장소가 정해지지 않은 일정 ${leg.사이미정}개` : '이동 시간 기록 없음';
    addLabel(el, curve.getPoint(0.5).setY(2));
    state.legs.push({ curve, ...leg });
  });

  // 발자국: 지나간 만큼만 보인다
  const paws = new THREE.InstancedMesh(new THREE.CircleGeometry(1, 12), mats.paw, Math.max(1, pawPos.length));
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  pawPos.forEach((w, i) => {
    e.set(-Math.PI / 2, 0, -w.rot, 'YXZ'); q.setFromEuler(e);
    m.compose(w.p.setY(0.42), q, new THREE.Vector3(1.1, 1.7, 1));
    paws.setMatrixAt(i, m);
  });
  paws.count = 0;
  paws.frustumCulled = false;   // 인스턴스가 지도 전체에 흩어져 있어 기본 가림 판정이 맞지 않는다
  scene.add(paws);
  state.paws = paws; state.pawMarks = pawPos;

  if (placed.length) state.lead.copy(placed[0].pos);
  if (state.legs.length) state.dir.copy(state.legs[0].curve.getTangent(0));
}

function loadChar(name, height, lag) {
  const make = (file) => {
    const tex = new THREE.TextureLoader().load(`/img/${file}.png`, (t) => { t.userData.ratio = t.image.width / t.image.height; });
    tex.colorSpace = THREE.SRGBColorSpace; tex.wrapS = THREE.RepeatWrapping;
    return tex;
  };
  const run = make(`${name}_run`), front = make(`${name}_front`);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: front, transparent: true, alphaTest: 0.05 }));
  sprite.center.set(0.5, 0.02);
  scene.add(sprite);
  chars.push({ sprite, run, front, height, lag, pos: new THREE.Vector3(), phase: Math.random() * 6 });
}

function pathPoint(leg, t, out) {
  // 뒤따르는 캐릭터는 t가 0보다 작아질 수 있다: 앞 구간으로 넘긴다
  while (t < 0 && leg > 0) { leg -= 1; t += 1; }
  return state.legs[leg].curve.getPoint(Math.max(0, Math.min(1, t)), out);
}

// ---------- 화면 ----------
function slotLabel(s) {
  const when = s.시각 ? `${s.시각}${s.시각종류 === '가정' ? ' (가정)' : ''}` : '시각 미정';
  const stay = typeof s.머무는시간 === 'number' ? `, ${s.머무는시간}분` : '';
  return `${SLOTNAME[s.시간칸] || s.시간칸} ${when}${stay}`;
}

function renderSide(plan) {
  const c = plan.조건;
  $('title').textContent = `${c.계절 || ''}, ${(c.지역 || []).join('·')}에서 보내는 ${c.체류기간 === '1박2일' ? '1박 2일' : '하루'}`;
  $('subtitle').textContent = `${(c.언어권 || []).join('·')} 방문객을 위한 코스 ${plan.상태}입니다.`;
  const list = $('timeline');
  let day = 0;
  plan.일정.forEach((s, i) => {
    if (s.일차 !== day) {
      day = s.일차;
      const h = document.createElement('li'); h.className = 'day-head'; h.textContent = `${day}일차`; list.appendChild(h);
    }
    const li = document.createElement('li');
    li.tabIndex = 0; li.dataset.i = i; li.style.setProperty('--c', COLOR[s.slot]);
    if (!s.좌표) li.classList.add('unplaced');
    const tags = [];
    if (s.근거.length) tags.push(`<span class="tag ev">근거 ${s.근거.length}</span>`);
    if (s.주의.length) tags.push(`<span class="tag warn">주의 ${s.주의.length}</span>`);
    if (!s.좌표) tags.push('<span class="tag open">장소 미정</span>');
    li.innerHTML = `<span class="dot">${s.no || '?'}</span><div class="when"></div><div class="name"></div><div class="tags">${tags.join('')}</div>`;
    li.querySelector('.when').textContent = slotLabel(s);
    li.querySelector('.name').textContent = s.이름;
    const open = () => select(i, true);
    li.addEventListener('click', open);
    li.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(); } });
    list.appendChild(li);
  });
  if (plan.정할것.length) {
    $('todo').hidden = false;
    for (const t of plan.정할것) { const li = document.createElement('li'); li.textContent = t; $('todoList').appendChild(li); }
  }
  if (plan.주의전체) {
    $('caution').hidden = false;
    const draw = (all) => {
      $('cautionList').replaceChildren(...(all ? plan.주의목록.map((w) => w.문구) : plan.주의요약).map((t) => { const li = document.createElement('li'); li.textContent = t; return li; }));
      const rest = plan.주의전체 - plan.주의요약.length;
      $('cautionMore').hidden = rest <= 0;
      $('cautionMore').textContent = all ? '세 가지만 보기' : `나머지 ${rest}건 보기`;
      $('cautionMore').onclick = () => draw(!all);
    };
    draw(false);
  }
}

function esc(t) { const d = document.createElement('div'); d.textContent = t ?? ''; return d.innerHTML; }

function select(i, focus) {
  state.selected = i;
  const s = state.stops[i];
  document.querySelectorAll('#timeline li').forEach((li) => li.classList.toggle('on', Number(li.dataset.i) === i));
  state.stops.forEach((x, k) => x.label && x.label.classList.toggle('on', k === i));
  const card = $('card');
  if (!s) { card.hidden = true; return; }
  const op = s.운영;
  const facts = op && (op.운영시간 || op.정기휴무)
    ? `<dl><dt>운영 시간</dt><dd>${esc(op.운영시간 || '기록 없음')}</dd><dt>쉬는 날</dt><dd>${esc(op.정기휴무 || '기록 없음')}</dd><dt>확인한 날</dt><dd>${esc(op.확인일 || '기록 없음')}</dd></dl>`
    : '<p class="meta">운영 시간과 쉬는 날이 아직 자료에 없습니다.</p>';
  const ev = (r) => `<li>${esc(r.항목)} <b>${esc(r.수치)}</b><small>${esc(r.출처)} ${esc(r.연도)}</small></li>`;
  card.innerHTML = `<button class="close" type="button" aria-label="닫기">×</button>
    <h2>${esc(s.이름)}</h2><p class="meta">${s.일차}일차 ${esc(slotLabel(s))}</p>
    ${s.좌표 ? `<h3>운영 정보</h3>${facts}<p class="meta gap">지도 위치는 ${esc(s.좌표.정밀도)} 기준입니다.</p>` : '<p class="meta gap">장소가 정해지면 지도에 표시됩니다.</p>'}
    ${s.주의.length ? `<h3>주의 ${s.주의.length}건</h3><ul>${s.주의.map((w) => `<li>${esc(w.문구)}</li>`).join('')}</ul>` : ''}
    ${s.근거.length ? `<h3>이 장소를 넣은 근거 ${s.근거.length}건</h3><ul>${s.근거.slice(0, 3).map(ev).join('')}</ul>
      ${s.근거.length > 3 ? `<details><summary>나머지 ${s.근거.length - 3}건</summary><ul>${s.근거.slice(3).map(ev).join('')}</ul></details>` : ''}` : ''}`;
  card.hidden = false;
  card.querySelector('.close').onclick = () => select(-1);
  if (focus && s.pos && state.mode === 'idle') {
    if (state.view !== 'whole') setView('whole', true);
    glideTo(s.pos.clone(), 230);
  }
}

function glideTo(target, distance) {
  const dirv = camera.position.clone().sub(controls.target).normalize();
  const to = target.clone().add(dirv.multiplyScalar(distance));
  if (still) { controls.target.copy(target); camera.position.copy(to); return; }
  state.glide = { t: 0, fromT: controls.target.clone(), toT: target, fromP: camera.position.clone(), toP: to };
}

function wholeView() {
  const pts = state.stops.filter((s) => s.pos).map((s) => s.pos);
  const box = new THREE.Box3().setFromPoints(pts.length ? pts : [new THREE.Vector3()]);
  const center = box.getCenter(new THREE.Vector3());
  const size = Math.max(box.getSize(new THREE.Vector3()).length(), 160) * 1.25;
  const to = center.clone().add(new THREE.Vector3(size * 0.25, size * 0.95, size * 1.15));
  if (still) { controls.target.copy(center); camera.position.copy(to); return; }
  state.glide = { t: 0, fromT: controls.target.clone(), toT: center, fromP: camera.position.clone(), toP: to };
}

function setView(view, quiet) {
  state.view = view;
  document.querySelectorAll('.seg button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
  controls.enabled = view !== 'walk';
  state.glide = null;
  if (view === 'whole' && !quiet) wholeView();
  if (view === 'follow') glideTo(state.lead.clone(), 190);
}

function play() {
  if (!state.legs.length) return;
  if (state.mode !== 'idle') { state.mode = 'idle'; $('play').textContent = '이어서 걷기'; return; }
  if (state.leg >= state.legs.length) { state.leg = 0; state.t = 0; state.paws.count = 0; state.duskGoal = 0; }
  if (state.leg === 0 && state.t === 0) select(state.legs[0].출발);
  state.mode = 'walk';
  $('play').textContent = '잠시 멈추기';
  if (state.view === 'whole') setView('follow');
}

// ---------- 매 프레임 ----------
const clock = new THREE.Clock();
const tmp = new THREE.Vector3(), tmp2 = new THREE.Vector3();

function tick() {
  const dt = Math.min(clock.getDelta(), 0.05), now = clock.elapsedTime;
  const before = state.lead.clone();

  if (state.mode === 'walk') {
    const leg = state.legs[state.leg];
    state.t += (17 * dt) / leg.curve.getLength();
    if (state.t >= 1) {
      state.t = 1; state.mode = 'pause'; state.pause = 2.4;
      select(leg.도착);
      state.duskGoal = DUSK[state.stops[leg.도착].시간칸] || 0;
    }
    leg.curve.getPoint(state.t, state.lead);
    leg.curve.getTangent(state.t, state.dir);
    let shown = 0;
    for (const w of state.pawMarks) if (w.leg < state.leg || (w.leg === state.leg && w.t < state.t - 0.04)) shown++;
    state.paws.count = shown;
  } else if (state.mode === 'pause') {
    state.pause -= dt;
    if (state.pause <= 0) {
      state.leg += 1; state.t = 0;
      if (state.leg >= state.legs.length) { state.mode = 'idle'; $('play').textContent = '처음부터 다시 걷기'; }
      else state.mode = 'walk';
    }
  }

  // 캐릭터
  const moving = state.mode === 'walk';
  chars.forEach((c, i) => {
    if (state.legs.length) pathPoint(Math.min(state.leg, state.legs.length - 1), state.t - c.lag / state.legs[Math.min(state.leg, state.legs.length - 1)].curve.getLength(), c.pos);
    else c.pos.copy(state.lead).x += i * 10;
    if (!moving) { tmp.set(-state.dir.z, 0, state.dir.x).multiplyScalar(i ? -7 : 7); c.pos.copy(state.lead).add(tmp); }
    const tex = moving ? c.run : c.front;
    if (c.sprite.material.map !== tex) { c.sprite.material.map = tex; }
    const ratio = tex.userData.ratio || 1;
    c.sprite.scale.set(c.height * ratio, c.height, 1);
    c.sprite.position.copy(c.pos);
    c.sprite.position.y = 0.4 + (moving ? Math.abs(Math.sin(now * 9 + c.phase)) * 2.2 : Math.sin(now * 2 + c.phase) * 0.25 + 0.25);
    if (moving) {   // 그림은 왼쪽을 보고 달린다: 화면에서 오른쪽으로 갈 때 뒤집는다
      const a = tmp.copy(c.pos).project(camera).x, b = tmp2.copy(c.pos).addScaledVector(state.dir, 5).project(camera).x;
      const flip = b > a;
      tex.repeat.x = flip ? -1 : 1; tex.offset.x = flip ? 1 : 0;
    }
  });

  // 낮에서 밤으로
  state.dusk += (state.duskGoal - state.dusk) * Math.min(1, dt * 1.2);
  const k = state.dusk;
  const sky = k < 0.55 ? SKY[0].clone().lerp(SKY[1], k / 0.55) : SKY[1].clone().lerp(SKY[2], (k - 0.55) / 0.45);
  scene.background.copy(sky); scene.fog.color.copy(sky);
  hemi.intensity = 1.5 - k * 1.05; sun.intensity = 1.6 - k * 1.35;
  hemi.color.set('#ffffff').lerp(new THREE.Color('#7f8fd6'), k);
  stars.material.opacity = Math.max(0, (k - 0.6) / 0.4);
  mats.route[1].emissiveIntensity = mats.route[2].emissiveIntensity = k * 0.9;
  for (const s of state.stops) if (s.headMat) s.headMat.emissiveIntensity = k * 0.8;
  document.body.classList.toggle('dark', k > 0.5);

  // 카메라
  if (state.glide) {
    const g = state.glide; g.t = Math.min(1, g.t + dt / 1.1);
    const e = g.t * g.t * (3 - 2 * g.t);
    controls.target.lerpVectors(g.fromT, g.toT, e); camera.position.lerpVectors(g.fromP, g.toP, e);
    if (g.t >= 1) state.glide = null;
  } else if (state.view === 'follow') {
    tmp.copy(state.lead).sub(before);
    controls.target.add(tmp); camera.position.add(tmp);
    controls.target.lerp(state.lead, Math.min(1, dt * 2));
  }
  if (state.view === 'walk') {
    tmp.copy(state.lead).addScaledVector(state.dir, -105).setY(46);
    camera.position.lerp(tmp, Math.min(1, dt * 2.5));
    tmp2.copy(state.lead).addScaledVector(state.dir, 45).setY(4);
    controls.target.lerp(tmp2, Math.min(1, dt * 3));
    camera.lookAt(controls.target);
  } else controls.update();

  // 이름표
  const w = canvas.clientWidth, h = canvas.clientHeight;
  for (const l of labels) {
    tmp.copy(l.pos).project(camera);
    const hide = tmp.z > 1 || Math.abs(tmp.x) > 1.1 || Math.abs(tmp.y) > 1.1;
    l.el.style.display = hide ? 'none' : '';
    if (!hide) { l.el.style.left = `${(tmp.x * 0.5 + 0.5) * w}px`; l.el.style.top = `${(-tmp.y * 0.5 + 0.5) * h}px`; }
  }
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  // 왼쪽 일정 패널만큼 지도의 중심을 오른쪽으로 민다
  if (w > 900) camera.setViewOffset(w, h, -177, 0, w, h); else camera.clearViewOffset();
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);

async function start() {
  resize();
  const get = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(url); return r.json(); };
  try {
    const [map, plans] = await Promise.all([get('/map.json'), get('/api/plans')]);
    const project = buildMap(map);
    const want = new URLSearchParams(location.search).get('id');
    if (!want) { document.body.classList.add('home'); return; }   // 주소에 기획이 없으면 시작 화면 (start.js)
    const pick = plans.find((p) => p.id === want && p.코스있음);
    if (!pick) {
      $('empty').hidden = false;
      $('empty').textContent = '이 기획에는 아직 코스가 없습니다. 주소를 확인하거나 처음 화면에서 다시 골라 주세요.';
      $('title').textContent = '코스 지도';
      requestAnimationFrame(tick);
      return;
    }
    const plan = await get('/api/plan?id=' + encodeURIComponent(pick.id));
    state.plan = plan;
    buildCourse(plan, project);
    renderSide(plan);
    $('promoLink').href = '/promo.html?id=' + encodeURIComponent(pick.id);
    const days = [['1일차', '#2f7de1', '']].concat(plan.조건.체류기간 === '1박2일' ? [['2일차', '#d9362e', 'dash']] : []);
    $('legend').replaceChildren(...days.map(([name, c, cls]) => { const li = document.createElement('li'); li.className = cls; li.style.setProperty('--c', c); li.append(document.createElement('i'), name); return li; }));
    loadChar('weasel', 18, 0);
    loadChar('raccoon', 16, 10);
    wholeView();
    $('play').addEventListener('click', play);
    document.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
    window.__course = state;
  } catch (e) {
    $('empty').hidden = false;
    $('empty').textContent = '지도를 불러오지 못했습니다. 서버가 켜져 있는지 확인한 뒤 새로고침해 주세요.';
    console.error(e);
  }
  requestAnimationFrame(tick);
}
start();
