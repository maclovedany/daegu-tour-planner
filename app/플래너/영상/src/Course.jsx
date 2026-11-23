import React from 'react';
import { AbsoluteFill, Easing, Img, interpolate, interpolateColors, spring, staticFile, useCurrentFrame } from 'remotion';

export const FPS = 30;
const INTRO = 90, HOLD = 110, MOVE = 50, OUTRO = 130;
export const durationOf = (d) => INTRO + d.장면.length * HOLD + Math.max(0, d.장면.length - 1) * MOVE + OUTRO;

const FONT = '"Pretendard", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif';
const PIN = { day: '#E8962E', meal: '#D9542B', night: '#4B46B8', stay: '#7A8699' };
const DAY = { 1: '#2F7DE1', 2: '#D9362E' };   // 1일차 파랑, 2일차 빨강
const INK = '#3A2416';
const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' };

const bez = (l, t) => [0, 1].map((i) => (1 - t) ** 2 * l.a[i] + 2 * (1 - t) * t * l.c[i] + t * t * l.b[i]);
// 곡선의 앞부분만: 그려지는 중인 구간에 쓴다
const part = (l, t) => { const p = bez(l, t), c = [0, 1].map((i) => l.a[i] + (l.c[i] - l.a[i]) * t); return `M${l.a[0]},${l.a[1]} Q${c[0]},${c[1]} ${p[0]},${p[1]}`; };

/** 프레임 → 지금 어느 장소에 있는지, 다음 장소로 얼마나 갔는지 */
function where(d, frame) {
  const n = d.장면.length, f = frame - INTRO;
  if (f < 0) return { stop: 0, move: 0, phase: 'intro', local: frame };
  const span = HOLD + MOVE, i = Math.min(n - 1, Math.floor(f / span)), local = f - i * span;
  if (i === n - 1 && local >= HOLD) return { stop: n - 1, move: 0, phase: 'outro', local: local - HOLD };
  if (local < HOLD) return { stop: i, move: 0, phase: 'hold', local };
  return { stop: i, move: Easing.inOut(Easing.cubic)((local - HOLD) / MOVE), phase: 'move', local: local - HOLD };
}

const Map = ({ d, at, frame }) => {
  const [x0, y0, w, h] = d.보기, u = w / 1000;
  const here = at.phase === 'move' ? bez(d.구간[at.stop], at.move) : [d.장면[at.stop].x, d.장면[at.stop].y];
  // 걷는 동안에는 캐릭터 쪽으로 조금 다가가고, 시작과 끝에는 전체를 보여 준다
  const zoomIn = at.phase === 'intro' ? interpolate(at.local, [40, INTRO], [0, 1], clamp) : at.phase === 'outro' ? interpolate(at.local, [0, 40], [1, 0], clamp) : 1;
  const vw = w * (1 - 0.3 * zoomIn), vh = h * (1 - 0.3 * zoomIn);
  const cx = x0 + w / 2 + (here[0] - x0 - w / 2) * 0.6 * zoomIn, cy = y0 + h / 2 + (here[1] - y0 - h / 2) * 0.6 * zoomIn;
  const moving = at.phase === 'move';
  const right = moving && d.구간[at.stop].b[0] > d.구간[at.stop].a[0];
  const bob = moving ? Math.abs(Math.sin(frame / 2.6)) * 12 * u : 0;
  const size = 120 * u;
  const char = (name, dx, k) => {
    const file = `${name}_${moving ? 'run' : 'front'}.png`, s = size * k;
    const x = here[0] + dx * u, y = here[1] - s * 0.92 - bob * (name === 'weasel' ? 1 : 0.8);
    return <image key={name} href={staticFile(file)} x={x} y={y} width={s} height={s} transform={right ? `translate(${2 * x + s} 0) scale(-1 1)` : undefined} />;
  };
  return (
    <svg viewBox={`${cx - vw / 2} ${cy - vh / 2} ${vw} ${vh}`} width={1080} height={1100} style={{ display: 'block', fontFamily: FONT }} preserveAspectRatio="xMidYMid slice">
      <rect x={x0 - w} y={y0 - h} width={w * 3} height={h * 3} fill="#EFE3C8" />
      <path d={d.지도.경계} fill="#FAF3E1" stroke="#C99A62" strokeWidth={2.2 * u} strokeDasharray={`${8 * u} ${7 * u}`} />
      <path d={d.지도.공원} fill="#CDE2B4" /><path d={d.지도.물} fill="#A9D6E5" />
      {[['강', 9, '#A9D6E5'], ['작은길', 2.2, '#fff'], ['보행길', 3, '#F6D9A0'], ['중간길', 4.2, '#fff'], ['큰길', 7, '#fff']].map(([k, sw, c]) => (
        <path key={k} d={d.지도[k]} fill="none" stroke={c} strokeWidth={sw * u} strokeLinecap="round" strokeLinejoin="round" />))}
      {d.구간.map((l, k) => {
        const t = at.phase === 'outro' || k < at.stop ? 1 : k === at.stop ? at.move : 0;
        if (t <= 0) return null;
        const path = part(l, t), two = l.일차 === 2;
        return (<g key={k}><path d={path} fill="none" stroke="#fff" strokeWidth={14 * u} strokeLinecap="round" />
          <path d={path} fill="none" stroke={DAY[two ? 2 : 1]} strokeWidth={8 * u} strokeLinecap="round" strokeDasharray={two ? `${16 * u} ${13 * u}` : undefined} /></g>);
      })}
      {d.장면.map((s, i) => {
        const seen = at.phase === 'outro' || i <= at.stop || (i === at.stop + 1 && at.move > 0.9);
        const arrive = i === at.stop && at.phase === 'hold' ? spring({ frame: at.local, fps: FPS, config: { damping: 9 } }) : 1;
        const k = u * (seen ? 1.25 * (0.75 + 0.25 * arrive) : 0.9), col = seen ? PIN[s.종류] : '#B9AE9C';
        return (<g key={i} transform={`translate(${s.x} ${s.y}) scale(${k})`}>
          <ellipse cx="0" cy="2" rx="13" ry="5" fill="#000" opacity=".18" />
          <path d="M0,0C-12,-17 -19,-27 -19,-37A19,19 0 1 1 19,-37C19,-27 12,-17 0,0Z" fill={col} stroke="#fff" strokeWidth="2.5" />
          <circle cx="0" cy="-37" r="11.5" fill="#fff" /><text x="0" y="-31" textAnchor="middle" fontSize="17" fontWeight="800" fill={col}>{s.번호}</text>
          {seen && <text x="26" y="-30" fontSize="21" fontWeight="800" fill={INK} stroke="#fff" strokeWidth="6" paintOrder="stroke" strokeLinejoin="round">{s.이름}</text>}
        </g>);
      })}
      {char('raccoon', -205, 0.98)}{char('weasel', -138, 0.9)}
    </svg>
  );
};

export const Course = (d) => {
  const frame = useCurrentFrame();
  const at = where(d, frame), stop = d.장면[at.stop], total = durationOf(d);
  // 밤 장면에 가까워질수록 배경이 낮에서 밤으로 바뀐다
  const nightOf = (i) => (d.장면[i].종류 === 'night' ? 1 : d.장면[i].종류 === 'meal' && d.장면[i].때.includes('저녁') ? 0.5 : 0);
  const nextNight = at.stop + 1 < d.장면.length ? nightOf(at.stop + 1) : nightOf(at.stop);
  const night = at.phase === 'intro' ? 0 : nightOf(at.stop) + (nextNight - nightOf(at.stop)) * at.move;
  const top = interpolateColors(night, [0, 0.5, 1], ['#FFE7B8', '#F6B877', '#2B2F6B']);
  const bottom = interpolateColors(night, [0, 0.5, 1], ['#FBF1DC', '#F3C9A0', '#1B1F4A']);
  const ink = interpolateColors(night, [0, 0.6, 1], [INK, INK, '#FFFFFF']);
  const intro = interpolate(frame, [0, 18, INTRO - 22, INTRO], [0, 1, 1, 0], clamp);
  const body = interpolate(frame, [INTRO - 22, INTRO], [0, 1], clamp);
  const cardIn = at.phase === 'hold' ? spring({ frame: at.local, fps: FPS, config: { damping: 14 } }) : at.phase === 'move' ? interpolate(at.local, [0, 10], [1, 0], clamp) : 0;
  const leg = at.phase === 'move' ? d.구간[at.stop] : null;
  const end = at.phase === 'outro' ? interpolate(at.local, [10, 34], [0, 1], clamp) : 0;
  const fadeOut = interpolate(frame, [total - 14, total], [1, 0], clamp);

  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${top}, ${bottom})`, fontFamily: FONT, color: ink, opacity: fadeOut }}>
      {/* 여는 장면 */}
      <AbsoluteFill style={{ opacity: intro, padding: '250px 84px 0', display: intro > 0 ? 'flex' : 'none', flexDirection: 'column' }}>
        <div style={{ fontSize: 44, fontWeight: 800, color: '#B5672A' }}>낮에서 밤까지, 대구에서 머무는 여행</div>
        <div style={{ fontSize: 124, fontWeight: 900, lineHeight: 1.12, letterSpacing: '-0.04em', marginTop: 30, wordBreak: 'keep-all', transform: `translateY(${(1 - spring({ frame, fps: FPS, config: { damping: 16 } })) * 60}px)` }}>{d.제목}</div>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-end', marginTop: 'auto', marginBottom: 210, transform: `scale(${0.85 + 0.15 * spring({ frame: frame - 8, fps: FPS, config: { damping: 10 } })})` }}>
          <Img src={staticFile('raccoon_front.png')} style={{ height: 500 }} />
          <Img src={staticFile('weasel_front.png')} style={{ height: 520, marginLeft: -40 }} />
        </div>
      </AbsoluteFill>

      {/* 지도와 장면 문구 */}
      <AbsoluteFill style={{ opacity: body }}>
        <div style={{ padding: '96px 72px 0', height: 300 }}>
          <div style={{ fontSize: 58, fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.15, wordBreak: 'keep-all' }}>{d.제목}</div>
          <div style={{ display: 'flex', gap: 28, marginTop: 18, fontSize: 32, fontWeight: 800 }}>
            <span style={{ color: DAY[1], background: '#fff', borderRadius: 40, padding: '6px 22px' }}>━ 1일차</span>
            {d.이틀 && <span style={{ color: DAY[2], background: '#fff', borderRadius: 40, padding: '6px 22px' }}>┅ 2일차</span>}
          </div>
        </div>
        <div style={{ margin: '0 40px', borderRadius: 48, overflow: 'hidden', border: '10px solid #fff', boxShadow: '0 20px 60px rgba(43,47,107,.3)', width: 1000, height: 1020 }}>
          <div style={{ marginLeft: -40, marginTop: -40 }}><Map d={d} at={at} frame={frame} /></div>
        </div>

        <div style={{ position: 'absolute', left: 56, right: 56, top: 1400, minHeight: 330, background: '#fff', color: INK, borderRadius: 44, padding: '40px 48px', boxShadow: '0 16px 48px rgba(43,47,107,.25)', opacity: cardIn, transform: `translateY(${(1 - cardIn) * 50}px)` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, fontSize: 36, fontWeight: 800, color: '#7A5A44' }}>
            <span style={{ width: 72, height: 72, borderRadius: 36, background: PIN[stop.종류], color: '#fff', display: 'grid', placeItems: 'center', fontSize: 40 }}>{stop.번호}</span>{stop.때}
          </div>
          <div style={{ fontSize: 66, fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.2, marginTop: 20, wordBreak: 'keep-all' }}>{stop.제목}</div>
          {stop.본문 && <div style={{ fontSize: 38, lineHeight: 1.5, marginTop: 16, wordBreak: 'keep-all' }}>{stop.본문}</div>}
        </div>
        {leg && leg.이동 && (
          <div style={{ position: 'absolute', left: 0, right: 0, top: 1500, textAlign: 'center', fontSize: 46, fontWeight: 800, opacity: interpolate(at.local, [8, 18, MOVE - 8, MOVE], [0, 1, 1, 0], clamp) }}>{leg.이동}</div>)}

        {/* 닫는 장면: 들른 곳 모아 보기 */}
        <div style={{ position: 'absolute', left: 56, right: 56, top: 1400, opacity: end, display: 'flex', flexWrap: 'wrap', gap: '18px 22px' }}>
          {d.장면.map((s) => (
            <span key={s.번호} style={{ display: 'flex', alignItems: 'center', gap: 14, background: '#fff', color: INK, borderRadius: 50, padding: '12px 28px 12px 12px', fontSize: 40, fontWeight: 800 }}>
              <b style={{ width: 60, height: 60, borderRadius: 30, background: PIN[s.종류], color: '#fff', display: 'grid', placeItems: 'center', fontSize: 34 }}>{s.번호}</b>{s.이름}
            </span>))}
        </div>
        <div style={{ position: 'absolute', left: 56, right: 56, bottom: 44, display: 'flex', justifyContent: 'space-between', fontSize: 22, fontWeight: 600, opacity: 0.75 }}>
          <span>{d.출처}</span><span>{d.초안}</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
