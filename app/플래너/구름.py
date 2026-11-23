"""배포판(Vercel)에서 기획을 만들고 저장한다. 엔진은 로컬과 같고(걸음.py), 상태와 결과를 Supabase에 둔다.

요청 한 번에 한 걸음만 한다: 화면이 /api/step 을 되풀이해 부른다. 그래서 요청마다 서버가 달라져도 이어진다.
필요한 환경변수: SUPABASE_URL, SUPABASE_ANON_KEY (또는 SUPABASE_SERVICE_ROLE_KEY), GEMINI_API_KEY (GEMINI_MODEL은 선택).
HARUHARU_ACCESS_CODE 를 넣으면 그 코드를 아는 사람만 새 기획을 만들 수 있다.
"""
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

여기 = Path(__file__).resolve().parent
sys.path[:0] = [str(여기.parent), str(여기)]

from 걸음 import 보이기, 새일, 한걸음  # noqa: E402
from 실행 import 조건_확인  # noqa: E402
from 보기 import 보기_만들기  # noqa: E402
from 장소정보 import _이름  # noqa: E402

칸종류 = ('낮', '점심', '낮오후', '저녁', '밤', '숙박', '2일차오전')


class DB:
    """Supabase REST (PostgREST). 표준 라이브러리만 쓴다."""

    def __init__(self):
        self.주소 = os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/'
        self.키 = (os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_ANON_KEY']).strip()

    def _요청(self, 방법, 경로, 본문=None):
        머리 = {'apikey': self.키, 'Authorization': 'Bearer ' + self.키, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        요청 = urllib.request.Request(self.주소 + 경로, data=None if 본문 is None else json.dumps(본문, ensure_ascii=False).encode('utf-8'), headers=머리, method=방법)
        try:
            with urllib.request.urlopen(요청, timeout=20) as 응답:
                글 = 응답.read().decode('utf-8')
                return json.loads(글) if 글 else []
        except urllib.error.HTTPError as 오류:
            # 표가 없거나 접근 규칙에 막히면 여기로 온다. 화면에 원인을 알려 준다 (키는 담기지 않는다)
            raise ConnectionError(f'Supabase {오류.code}: ' + 오류.read().decode('utf-8', 'replace')[:300]) from None

    def 넣기(self, 표, 값):
        return self._요청('POST', 표, 값)

    def 고치기(self, 표, 조건, 값):
        return self._요청('PATCH', f'{표}?{조건}', 값)

    def 찾기(self, 표, 질의):
        return self._요청('GET', f'{표}?{질의}')


db = None


def _db():
    global db
    if db is None:
        db = DB()
    return db


def 준비상태():
    빠진 = [이름 for 이름 in ['SUPABASE_URL'] if not os.environ.get(이름)]
    if not (os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_ANON_KEY')):
        빠진.append('SUPABASE_ANON_KEY')
    if not os.environ.get('GEMINI_API_KEY'):
        빠진.append('GEMINI_API_KEY')
    return 빠진


class DB저장:
    """엔진이 단계 결과를 남길 때 부른다. 판 번호는 상태에 적어 둔다."""

    def _판(self, 일, 열쇠):
        일.setdefault('판', {})[열쇠] = 일.get('판', {}).get(열쇠, 0) + 1
        return 일['판'][열쇠]

    def 단계1(self, 일, 글):
        _db().넣기('stage_results', {'plan_id': 일['id'], 'stage': 1, 'version': self._판(일, '1'), 'raw_text': 글, 'check_result': ['통과']})

    def 단계2(self, 일, 글, 전달):
        _db().넣기('stage_results', {'plan_id': 일['id'], 'stage': 2, 'version': self._판(일, '2'), 'raw_text': 글, 'check_result': 전달['검사결과'],
                                  'data': {k: 전달[k] for k in ['근거목록', '경고목록', '요약', '미확인사항']}})

    def 코스(self, 일, 코스, 입력3, 검사):
        끝 = 코스.get('코스시작종료') or {}
        시각 = lambda v: v if isinstance(v, str) and len(v) == 5 and v[2] == ':' else None  # noqa: E731
        행 = _db().넣기('courses', {
            'plan_id': 일['id'], 'revision': self._판(일, '코스'), 'status': '초안', 'conditions': 입력3['코스작성조건'], 'data': 코스,
            'check_result': 검사['고칠'] or ['통과'], 'pending': 검사['대기'], 'start_place': 끝.get('시작지점'), 'end_place': 끝.get('종료지점'),
            'start_time': 시각(끝.get('시작시각')), 'end_time': 시각(끝.get('종료시각')),
            'operation_mode': 코스.get('운영방식') if 코스.get('운영방식') in ('단체동행형', '개별이동형', '미정') else '미정'})[0]
        칸들 = []
        for i, 칸 in enumerate(코스.get('칸목록', [])):
            if 칸.get('시간칸') not in 칸종류 or 칸.get('일차') not in (1, 2) or not 칸.get('칸ID'):
                continue
            값, 종류 = (칸.get('시각') or {}).get('값'), (칸.get('시각') or {}).get('종류')
            종류 = 종류 if 종류 in ('확정', '가정') and 시각(값) else '미정'
            칸들.append({'course_id': 행['id'], 'variant': 칸.get('안', '공통'), 'slot_code': 칸['칸ID'], 'position': i + 1, 'day': 칸['일차'], 'slot': 칸['시간칸'],
                       'place_name': str(칸.get('장소명', ''))[:300], 'time_value': 시각(값) if 종류 != '미정' else None, 'time_kind': 종류,
                       'stay_min': 칸['머무는시간'] if isinstance(칸.get('머무는시간'), int) and 칸['머무는시간'] >= 0 else None,
                       'evidence_codes': [r for r in 칸.get('근거ID', []) if isinstance(r, str)]})
        if 칸들:
            _db().넣기('course_stops', 칸들)

    def 끝(self, 일):
        pass


def _상태쓰기(일):
    _db().고치기('plans', f"id=eq.{일['id']}", {
        'agent_state': 일, 'activity': 일['활동'], 'current_stage': min(일['단계'], 5), 'notice': 일.get('안내'),
        'status': '진행중' if 일['상태'] == '진행중' else '멈춤' if 일['상태'] == '멈춤' else '초안',
        'summary': 일.get('마무리'), 'left_for_human': 일.get('사람이_정할_것', []), 'unresolved': 일.get('남은_문제', []), 'total_seconds': 일.get('전체초')})


def _상태읽기(실행id):
    행 = _db().찾기('plans', f'id=eq.{quote(실행id)}&select=agent_state')
    if not 행 or not 행[0].get('agent_state'):
        raise ValueError('기획을 찾을 수 없습니다.')
    return 행[0]['agent_state']


def 시작(값):
    빠진 = 준비상태()
    if 빠진:
        raise ValueError('배포 환경변수가 없습니다: ' + ', '.join(빠진))
    코드 = os.environ.get('HARUHARU_ACCESS_CODE', '').strip()
    if 코드 and str(값.get('코드', '')).strip() != 코드:
        raise ValueError('접속 코드가 맞지 않습니다.')
    조건 = 조건_확인(값)
    행 = _db().넣기('plans', {'season': 조건['계절'], 'languages': 조건['언어권'], 'districts': 조건['지역'], 'stay': 조건['체류기간']})[0]
    일 = 새일(조건, 행['id'])
    _상태쓰기(일)
    return 보이기(일)


def 걸음(실행id):
    일 = _상태읽기(실행id)
    if 일['상태'] == '진행중':
        asyncio.run(한걸음(일, DB저장()))
        _상태쓰기(일)
    return 보이기(일)


def 진행(실행id):
    return 보이기(_상태읽기(실행id)) if 실행id else {'상태': '없음'}


def 목록():
    행 = _db().찾기('plans', 'select=id,season,languages,districts,stay,created_at&status=eq.초안&current_stage=eq.3&order=created_at.desc&limit=30')
    return [{'id': r['id'], '조건': {'계절': r['season'], '언어권': r['languages'], '지역': r['districts'], '체류기간': r['stay']},
             '실행': r['created_at'][:19].replace('-', '').replace(':', '').replace('T', '_'), '코스있음': True, '검사상태': '통과'} for r in 행]


def 보기(실행id):
    기획 = _db().찾기('plans', f'id=eq.{quote(실행id)}&select=season,languages,districts,stay')
    코스 = _db().찾기('courses', f'plan_id=eq.{quote(실행id)}&select=id,data,pending,status,created_at&order=revision.desc&limit=1')
    수요 = _db().찾기('stage_results', f'plan_id=eq.{quote(실행id)}&stage=eq.2&select=data&order=version.desc&limit=1')
    if not 기획:
        raise ValueError('기획을 찾을 수 없습니다.')
    r = 기획[0]
    조건 = {'계절': r['season'], '언어권': r['languages'], '지역': r['districts'], '체류기간': r['stay']}
    if not 코스:
        return {'id': 실행id, '조건': 조건, '코스있음': False}
    근거목록 = (수요[0]['data'] or {}).get('근거목록', []) if 수요 else []
    return 보기_만들기(실행id, 조건, 코스[0]['data'], 근거목록, 코스[0]['id'], 코스[0]['created_at'], 코스[0]['pending'] or [], 코스[0]['status'] == '확정')
