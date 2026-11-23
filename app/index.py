"""Vercel 진입점 (WSGI). 기획자 화면, 저장해 둔 견본 기획, 그리고 배포판에서 새로 만드는 기획을 다룬다.

새 기획은 플래너/구름.py 가 만든다: 화면이 /api/step 을 되풀이해 부르고, 요청 한 번에 엔진이 한 걸음씩 나아간다.
AI는 Gemini(GEMINI_API_KEY), 저장은 Supabase(SUPABASE_URL · SUPABASE_ANON_KEY)를 쓴다. 견본 기획은 환경변수 없이도 보인다.
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs

앱 = Path(__file__).resolve().parent          # Vercel 프로젝트의 Root Directory가 app 이다
견본 = 앱 / '플래너' / '견본'
os.environ.setdefault('HARUHARU_DATA_DIR', str(견본 / '자료'))   # 배포판은 app/ 밖의 research/data 를 볼 수 없다
sys.path[:0] = [str(앱), str(앱 / '플래너')]

from 관리자조회 import 결과저장소  # noqa: E402
from 보기 import 기획목록, 기획보기  # noqa: E402
from 홍보 import 홍보읽기  # noqa: E402
from 흐름 import 계절_선택지, 언어권_선택지, 지역_선택지, 확정체류기간_선택지  # noqa: E402
import 구름  # noqa: E402

화면 = 앱 / '플래너' / '화면'
저장소 = 결과저장소(견본)
형식 = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
      '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml'}
안내 = '배포판에서는 아직 홍보 문구를 새로 만들지 않습니다. 로컬에서 만들어 주세요.'


def _앱(environ, start_response):
    def 응답(상태, 본문, 타입='application/json; charset=utf-8', 보관='no-store'):
        데이터 = 본문 if isinstance(본문, bytes) else json.dumps(본문, ensure_ascii=False).encode('utf-8')
        start_response(상태, [('Content-Type', 타입), ('Content-Length', str(len(데이터))), ('Cache-Control', 보관),
                            ('X-Content-Type-Options', 'nosniff')])
        return [데이터]

    경로 = environ.get('PATH_INFO', '/') or '/'
    인자 = parse_qs(environ.get('QUERY_STRING', ''))
    실행id = 인자.get('id', [''])[0]
    try:
        견본인가 = '/' in 실행id      # 견본은 '날짜_시각/회차', 배포판에서 만든 기획은 Supabase의 uuid
        if environ.get('REQUEST_METHOD') == 'POST':
            길이 = int(environ.get('CONTENT_LENGTH') or 0)
            if not 0 < 길이 <= 4096 or (environ.get('CONTENT_TYPE') or '').split(';')[0] != 'application/json':
                return 응답('400 Bad Request', {'오류': '입력을 확인해 주세요.'})
            값 = json.loads(environ['wsgi.input'].read(길이).decode('utf-8'))
            if 경로 == '/api/start':
                return 응답('202 Accepted', 구름.시작(값))
            if 경로 == '/api/step':
                return 응답('200 OK', 구름.걸음(str(값.get('id', ''))))
            return 응답('503 Service Unavailable', {'오류': 안내})
        if 경로 == '/api/plans':
            만든 = 구름.목록() if not 구름.준비상태() else []
            return 응답('200 OK', 만든 + 기획목록(저장소))
        if 경로 == '/api/plan':
            return 응답('200 OK', 기획보기(저장소, 실행id) if 견본인가 else 구름.보기(실행id))
        if 경로 == '/api/promo':
            return 응답('200 OK', {'진행': {'상태': '없음'}, '결과': 홍보읽기(저장소, 실행id) if 견본인가 else None})
        if 경로 == '/api/options':
            return 응답('200 OK', {'계절': 계절_선택지, '언어권': 언어권_선택지, '지역': 지역_선택지, '체류기간': 확정체류기간_선택지,
                                '구름': True, '코드필요': bool(os.environ.get('HARUHARU_ACCESS_CODE', '').strip())})
        if 경로 == '/api/progress':
            return 응답('200 OK', 구름.진행(실행id) if 실행id and not 견본인가 else {'상태': '없음'})
        파일 = (화면 / ('index.html' if 경로 == '/' else 경로.lstrip('/'))).resolve()
        if 파일.is_relative_to(화면) and 파일.is_file() and 파일.suffix in 형식:
            return 응답('200 OK', 파일.read_bytes(), 형식[파일.suffix], 'public, max-age=300')
        return 응답('404 Not Found', {'오류': '없는 페이지'})
    except ConnectionError as 오류:   # Supabase 쪽 문제: 표가 없거나 접근 규칙에 막힘
        return 응답('502 Bad Gateway', {'오류': '저장소(Supabase)에 닿지 못했습니다. SQL을 실행했는지 확인해 주세요. ' + str(오류)[:200]})
    except ValueError as 오류:
        return 응답('400 Bad Request', {'오류': str(오류)[:200] or '입력을 확인해 주세요.'})
    except (OSError, KeyError):
        return 응답('404 Not Found', {'오류': '기획 기록을 읽을 수 없습니다.'})


app = _앱   # Vercel이 찾는 WSGI 진입점 이름
