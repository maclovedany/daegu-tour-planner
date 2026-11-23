"""홍보 영상(Remotion)에 넣을 자료를 만든다: 코스 초안 + 홍보 문구 초안 + 지도 바탕 → 영상/public/course.json

사용: python 플래너/영상자료.py "<실행id>"   (예: 20261123_141339/01회차)
"""
import json
import shutil
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent
sys.path.insert(0, str(여기.parent))
sys.path.insert(0, str(여기))

from 관리자조회 import 결과저장소  # noqa: E402
from 보기 import 기획보기  # noqa: E402
from 홍보 import 홍보읽기  # noqa: E402

칸이름 = {'낮': '낮', '낮오후': '오후', '2일차오전': '오전', '점심': '점심', '저녁': '저녁', '밤': '밤', '숙박': '숙박'}
칸종류 = {'낮': 'day', '낮오후': 'day', '2일차오전': 'day', '점심': 'meal', '저녁': 'meal', '밤': 'night', '숙박': 'stay'}


def 만들기(저장소, 실행id, 비율=1080 / 1100):
    기획 = 기획보기(저장소, 실행id)
    if not 기획.get('코스있음'):
        raise ValueError('코스 초안이 있는 기획을 골라 주세요.')
    홍보 = (홍보읽기(저장소, 실행id) or {}).get('홍보', {})
    지도 = json.loads((여기 / '화면' / 'map.json').read_text(encoding='utf-8'))
    원점 = 지도['origin']
    문구 = {m['장면ID']: m for m in 홍보.get('문구목록', [])}

    장면, 놓인 = [], {}
    for i, 칸 in enumerate(기획['일정']):
        if not 칸['좌표']:
            continue
        x = (칸['좌표']['lon'] - 원점['lon']) * 원점['kx']
        y = -(칸['좌표']['lat'] - 원점['lat']) * 원점['ky']
        if any(abs(x - s['x']) + abs(y - s['y']) < 110 for s in 장면):   # 같은 곳을 두 번 들르면 살짝 옮긴다
            x, y = x + 90, y + 70
        글 = 문구.get(칸['칸ID'], {})
        깨끗 = lambda t: '' if not t or t == '미정' else t  # noqa: E731
        시각 = (('약 ' if 칸['시각종류'] == '가정' else '') + 칸['시각']) if 칸['시각'] else ''
        놓인[i] = len(장면)
        장면.append({'번호': len(장면) + 1, '이름': 칸['이름'], '종류': 칸종류.get(칸['시간칸'], 'day'), '일차': 칸['일차'],
                   '때': ' '.join(t for t in [f"{칸['일차']}일차", 칸이름.get(칸['시간칸'], ''), 시각] if t),
                   '제목': 깨끗(글.get('제목')) or 칸['이름'], '본문': 깨끗(글.get('본문')), 'x': round(x), 'y': round(y)})
    if not 장면:
        raise ValueError('지도에 놓을 수 있는 장소가 없습니다.')

    구간 = []
    for k, leg in enumerate(기획['구간']):
        a, b = 장면[놓인[leg['출발']]], 장면[놓인[leg['도착']]]
        dx, dy = b['x'] - a['x'], b['y'] - a['y']
        굽음 = 0.24 * (-1 if k % 2 else 1) * (-1 if dx < 0 else 1)
        구간.append({'a': [a['x'], a['y']], 'c': [round((a['x'] + b['x']) / 2 - dy * 굽음), round((a['y'] + b['y']) / 2 + dx * 굽음)],
                   'b': [b['x'], b['y']], '일차': leg['일차'],
                   '이동': f"걸어서 {leg['이동']['도보']}분, 대중교통 {leg['이동']['대중교통']}분" if leg['이동'] else ''})

    xs, ys = [s['x'] for s in 장면], [s['y'] for s in 장면]
    w, h = max(max(xs) - min(xs), 1) * 1.7, max(max(ys) - min(ys), 1) * 1.7
    w, h = max(w, 1500), max(h, 1100)
    w, h = (h * 비율, h) if w / h < 비율 else (w, w / 비율)
    x0, y0 = (max(xs) + min(xs)) / 2 - w / 2, (max(ys) + min(ys)) / 2 - h / 2
    근처 = lambda 선: any(x0 - 300 < x < x0 + w + 300 and y0 - 300 < -y < y0 + h + 300 for x, y in 선)  # noqa: E731
    길 = lambda 키, 닫기='': ''.join('M' + 'L'.join(f'{x},{-y}' for x, y in 선) + 닫기 for 선 in 지도[키] if 근처(선))  # noqa: E731
    조건 = 기획['조건']
    이름 = (홍보.get('코스카드') or {}).get('코스이름', '')
    return {
        '제목': 이름 if 이름 and '미정' not in 이름 else f"{조건['계절']}, 대구 {'·'.join(조건['지역'])}에서 {'1박 2일' if 조건['체류기간'] == '1박2일' else '하루'}",
        '초안': '초안 · 코스 확정 전' if 기획['상태'] == '초안' else '초안',
        '이틀': 조건['체류기간'] == '1박2일',
        '장면': 장면, '구간': 구간, '보기': [round(x0), round(y0), round(w), round(h)],
        '지도': {'경계': 'M' + 'L'.join(f'{x},{-y}' for x, y in 지도['boundary']) + 'Z', '공원': 길('park', 'Z'), '물': 길('water', 'Z'), '강': 길('river'),
               '작은길': 길('minor'), '보행길': 길('walk'), '중간길': 길('mid'), '큰길': 길('major')},
        '출처': '지도 바탕 © OpenStreetMap contributors · 경로선은 순서를 잇는 표시',
    }


if __name__ == '__main__':
    실행id = sys.argv[1]
    값 = 만들기(결과저장소(여기.parent / 'runs'), 실행id)
    공개 = 여기 / '영상' / 'public'
    공개.mkdir(parents=True, exist_ok=True)
    (공개 / 'course.json').write_text(json.dumps(값, ensure_ascii=False), encoding='utf-8')
    for 이름 in ['raccoon_run', 'raccoon_front', 'weasel_run', 'weasel_front']:
        shutil.copyfile(여기 / '화면' / 'img' / f'{이름}.png', 공개 / f'{이름}.png')
    print(f"영상 자료 저장: {공개 / 'course.json'} · 장면 {len(값['장면'])}개")
