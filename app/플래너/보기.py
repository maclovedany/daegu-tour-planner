"""저장된 실행 기록을 기획자 화면용 한 묶음으로 바꾼다. 읽기 전용. AI 호출·웹 조회 없음."""
import csv
import json
import re
import sys
from pathlib import Path

앱 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(앱))

from 장소정보 import _이름, 장소목록  # noqa: E402

자료 = Path(__file__).resolve().parent / '자료'
이동파일 = 앱.parent / 'research' / 'data' / '이동시간_중구동구_데모코스_2026.csv'


def 좌표목록():
    결과 = {}
    with (자료 / '장소좌표.csv').open(encoding='utf-8-sig', newline='') as f:
        for 행 in csv.DictReader(f):
            if 행['위도'] and 행['경도']:
                결과[_이름(행['장소명'])] = {'lat': float(행['위도']), 'lon': float(행['경도']),
                                          '정밀도': 행['정밀도'], '출처': 행['출처'], '확인일': 행['확인일']}
    return 결과


def 이동목록():
    결과 = {}
    with 이동파일.open(encoding='utf-8-sig', newline='') as f:
        for 행 in csv.DictReader(f):
            결과[(_이름(행['출발장소']), _이름(행['도착장소']))] = {
                '도보': 행['도보_분'], '대중교통': 행['대중교통_분'], '노선': 행['이용노선'],
                '기준': f"{행['기준요일']} {행['기준출발시각']} · {행['도구']} · 확인 {행['확인일']}"}
    return 결과


def _첫문장(글):
    글 = re.sub(r'\s*\(적용 근거:[^)]*\)\s*$', '', str(글)).strip()
    return re.split(r'(?<=[다요음]\.)\s', 글, maxsplit=1)[0]


def 최신코스(저장소, 실행id):
    """실행 기록에서 코스가 들어 있는 가장 최근 저장본. 없으면 None."""
    폴더 = 저장소._경로(실행id)
    후보 = []
    for 하위 in 폴더.glob('통합시험_*'):
        파일 = 하위 / '3단계_구조화.json'
        if not 파일.is_file():
            continue
        try:
            값 = json.loads(파일.read_text(encoding='utf-8'))
            상태 = json.loads((하위 / '통합시험_상태.json').read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        if isinstance(값.get('칸목록'), list) and 값['칸목록']:
            후보.append((상태.get('완료시각') or 상태.get('기록시각') or '', 하위, 값, 상태))
    if not 후보:
        return None
    후보.sort(key=lambda r: r[0])
    return 후보[-1]


def 기획목록(저장소):
    결과 = []
    for 요약 in 저장소.목록():
        코스 = 최신코스(저장소, 요약['id'])
        결과.append({'id': 요약['id'], '조건': 요약['조건'], '실행': 요약['실행'],
                   '코스있음': 코스 is not None, '검사상태': 요약['검사상태']})
    return 결과


def 기획보기(저장소, 실행id):
    요약 = 저장소.상세(실행id)
    찾음 = 최신코스(저장소, 실행id)
    if 찾음 is None:
        return {'id': 실행id, '조건': 요약['조건'], '코스있음': False}
    _, 폴더, 코스, 상태 = 찾음
    입력 = json.loads((폴더 / '3단계_입력.json').read_text(encoding='utf-8'))
    근거 = {r['근거ID']: r for r in 입력.get('근거목록', [])}
    경고들 = 코스.get('남은경고', [])
    좌표, 이동, 운영 = 좌표목록(), 이동목록(), {_이름(r['장소명']): r for r in 장소목록()}

    일정 = []
    for 칸 in 코스['칸목록']:
        이름 = _이름(칸.get('장소명', ''))
        ids = [r for r in 칸.get('근거ID', []) if r in 근거]
        주의 = [w for w in 경고들 if w.get('칸ID') == 칸['칸ID'] or set(w.get('적용근거ID', [])) & set(ids)]
        위치 = 좌표.get(이름)
        정보 = 운영.get(이름, {})
        일정.append({
            '칸ID': 칸['칸ID'], '안': 칸.get('안', '공통'), '일차': 칸.get('일차'), '시간칸': 칸.get('시간칸', ''),
            '이름': 이름 if 위치 else 칸.get('장소명', ''), '시각': 칸.get('시각', {}).get('값', ''),
            '시각종류': 칸.get('시각', {}).get('종류', '미정'), '머무는시간': 칸.get('머무는시간'),
            '좌표': 위치,
            '근거': [{'ID': r, '항목': 근거[r].get('원자료항목명') or 근거[r].get('항목', ''),
                    '수치': 근거[r].get('수치_원문', ''), '출처': 근거[r].get('출처', ''), '연도': 근거[r].get('연도', '')} for r in ids],
            '주의': [{'ID': w.get('경고ID', ''), '문구': _첫문장(w.get('문구', ''))} for w in 주의],
            '운영': {'운영시간': 정보.get('운영시간', ''), '정기휴무': 정보.get('정기휴무', ''),
                   '확인상태': 정보.get('상태', ''), '확인일': 정보.get('확인일', '')} if 정보 else None,
        })

    # 지도에 놓을 수 있는 장소끼리만 잇는다. 사이에 장소가 정해지지 않은 일정이 있으면 표시한다.
    구간 = []
    앞, 건너뜀 = None, 0
    for i, 칸 in enumerate(일정):
        if not 칸['좌표']:
            건너뜀 += 1
            continue
        if 앞 is not None:
            기록 = 이동.get((일정[앞]['이름'], 칸['이름']))
            구간.append({'출발': 앞, '도착': i, '이동': 기록, '사이미정': 건너뜀, '일차': 칸['일차']})
        앞, 건너뜀 = i, 0

    큰경고 = sorted(경고들, key=lambda w: -len(w.get('적용근거ID', [])))
    return {
        'id': 실행id, '조건': 요약['조건'], '코스있음': True,
        '저장본': 폴더.relative_to(저장소.루트).as_posix(), '저장시각': 상태.get('완료시각') or 상태.get('기록시각', ''),
        '일정': 일정, '구간': 구간,
        '주의요약': [_첫문장(w.get('문구', '')) for w in 큰경고[:3]], '주의전체': len(경고들),
        '주의목록': [{'ID': w.get('경고ID', ''), '문구': w.get('문구', '')} for w in 경고들],
        '정할것': 상태.get('담당자확인대기', []),
        '상태': '초안' if not 상태.get('담당자확정') else '확정 준비 완료',
    }
