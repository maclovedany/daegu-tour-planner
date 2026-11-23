// 시작 화면: 조건 네 가지 → 자동 진행(위쪽 단계 표시) → 끝나면 코스 지도로 이동
const $ = (id) => document.getElementById(id);
const get = async (url) => (await fetch(url)).json();
const FIELDS = [['계절', '계절', 'radio'], ['언어권', '대상 언어권 (여러 개 가능)', 'checkbox'], ['지역', '지역 (여러 개 가능)', 'checkbox'], ['체류기간', '체류 기간', 'radio']];
const HELP = ['이 조건으로 볼 수 있는 자료가 있는지 확인합니다.', '자료의 수치를 읽어 근거와 주의할 점을 정리합니다.', '낮, 저녁, 숙박을 잇는 코스 초안을 만듭니다.'];
let timer = 0;

const days = (v) => (v === '1박2일' ? '1박 2일' : v);
const label = (c) => `${c.계절}, ${(c.지역 || []).join('·')}, ${(c.언어권 || []).join('·')}, ${days(c.체류기간)}`;
const node = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

async function setup() {
  if (new URLSearchParams(location.search).get('id')) return;   // 코스 지도를 보는 중
  document.body.classList.add('home');
  $('landing').hidden = false;
  const [options, plans, progress] = await Promise.all([get('/api/options'), get('/api/plans'), get('/api/progress')]);
  for (const [key, title, type] of FIELDS) {
    const fs = node('fieldset'), chips = node('div', 'chips');
    fs.append(node('legend', '', title), chips);
    for (const value of options[key]) {
      const l = node('label');
      l.append(Object.assign(node('input'), { type, name: key, value }), node('span', '', days(value)));
      chips.append(l);
    }
    $('newFields').append(fs);
  }
  const ready = plans.filter((p) => p.코스있음);
  if (ready.length) {
    $('saved').hidden = false;
    for (const p of ready) {
      const a = node('a', '', label(p.조건));
      a.href = '/?id=' + encodeURIComponent(p.id);
      a.append(node('small', '', `${p.실행.slice(4, 6)}월 ${p.실행.slice(6, 8)}일 ${p.실행.slice(9, 11)}:${p.실행.slice(11, 13)}`));
      const li = node('li'); li.append(a); $('savedList').append(li);
    }
  }
  $('newForm').addEventListener('submit', submit);
  $('stepAgain').addEventListener('click', () => { $('stepper').hidden = true; $('newForm').hidden = false; });
  if (progress.상태 === '진행중') watch();
}

async function submit(ev) {
  ev.preventDefault();
  const data = new FormData($('newForm'));
  const body = { 계절: data.get('계절'), 언어권: data.getAll('언어권'), 지역: data.getAll('지역'), 체류기간: data.get('체류기간') };
  const r = await fetch('/api/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const result = await r.json();
  if (!r.ok) { $('newError').textContent = result.오류 || '시작하지 못했습니다. 다시 시도해 주세요.'; return; }
  $('newError').textContent = '';
  watch();
}

function drawSteps(p) {
  // 첫 단계 '조건 고르기'는 이미 끝난 일이고, 나머지 셋이 서버 진행 단계다
  const names = ['조건 고르기', ...p.단계이름];
  const at = p.단계 + 1, running = p.상태 === '진행중', finished = p.상태 === '완료';
  const cls = (i) => (i < at || finished ? 'done' : i === at ? (running ? 'now' : 'stopped') : 'wait');
  $('steps').replaceChildren(...names.map((n, i) => node('li', cls(i), n)));
  $('stepCards').replaceChildren(...names.map((n, i) => {
    const c = cls(i), box = node('div', c);
    if (c === 'now') { box.append(node('span'), node('span'), node('span')); return box; }
    if (c === 'wait') return box;
    box.append(node('h3', '', i === 0 ? '고른 조건' : n));
    if (i === 0) box.append(node('p', '', label(p.조건)));
    else if (c === 'stopped') box.append(node('p', '', p.안내 || '여기서 멈췄습니다.'));
    else box.append(node('p', '', (p.요약 || [])[i - 1] || HELP[i - 1]));
    if (finished && i === names.length - 1) { const a = node('a', 'primary', '코스 지도 보기'); a.href = '/?id=' + encodeURIComponent(p.id); box.append(a); }
    return box;
  }));
  // 에이전트 활동 기록: 누가 무엇을 했고 몇 초 걸렸는지
  $('agentLogList').replaceChildren(...(p.활동 || []).map((a) => {
    const li = node('li');
    li.append(node('b', '', a.누가), node('span', '', a.내용));
    if (a.초 != null) li.append(node('em', '', `${a.초}초`));
    return li;
  }));
  $('agentLog').hidden = !(p.활동 || []).length;
  const seconds = Math.max(0, Math.round((Date.now() - new Date(p.시작시각)) / 1000));
  $('stepNote').textContent = running ? `${HELP[p.단계] || '결과를 검증하고 있습니다.'} 시작한 지 ${seconds}초 지났습니다.`
    : finished ? (p.마무리 || '코스 초안이 준비됐습니다.') + (p.전체초 ? ` (${Math.round(p.전체초)}초)` : '') : '기획을 끝까지 만들지 못했습니다.';
  $('stepAgain').hidden = running;
}

async function watch() {
  clearTimeout(timer);
  const p = await get('/api/progress');
  if (p.상태 === '없음') return;
  $('stepper').hidden = false;
  $('newForm').hidden = true;
  drawSteps(p);
  if (p.상태 === '진행중') timer = setTimeout(watch, 1000);
}

setup();
