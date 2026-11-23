"""Vercel 진입점 (WSGI). 기획자 화면과 저장해 둔 견본 기획을 보여 준다.

Vercel에서는 새 기획을 만들지 않는다. 지금 AI 실행은 로컬의 Claude Code 로그인과 파일 저장에 기대고 있어서,
배포판에서 만들려면 Anthropic API 키로 직접 부르고 결과를 Supabase에 저장하도록 옮겨야 한다 (supabase/ 의 SQL이 그 자리다).
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

화면 = 앱 / '플래너' / '화면'
저장소 = 결과저장소(견본)
형식 = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
      '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml'}
안내 = '배포판은 저장해 둔 기획을 보여 주기만 합니다. 새 기획과 홍보 문구는 로컬에서 만들어 주세요.'


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
        if environ.get('REQUEST_METHOD') == 'POST':
            return 응답('503 Service Unavailable', {'오류': 안내})
        if 경로 == '/api/plans':
            return 응답('200 OK', 기획목록(저장소))
        if 경로 == '/api/plan':
            return 응답('200 OK', 기획보기(저장소, 실행id))
        if 경로 == '/api/promo':
            return 응답('200 OK', {'진행': {'상태': '없음'}, '결과': 홍보읽기(저장소, 실행id)})
        if 경로 == '/api/options':
            return 응답('200 OK', {'계절': 계절_선택지, '언어권': 언어권_선택지, '지역': 지역_선택지, '체류기간': 확정체류기간_선택지})
        if 경로 == '/api/progress':
            return 응답('200 OK', {'상태': '없음'})
        파일 = (화면 / ('index.html' if 경로 == '/' else 경로.lstrip('/'))).resolve()
        if 파일.is_relative_to(화면) and 파일.is_file() and 파일.suffix in 형식:
            return 응답('200 OK', 파일.read_bytes(), 형식[파일.suffix], 'public, max-age=300')
        return 응답('404 Not Found', {'오류': '없는 페이지'})
    except (ValueError, OSError, KeyError):
        return 응답('404 Not Found', {'오류': '기획 기록을 읽을 수 없습니다.'})


app = _앱   # Vercel이 찾는 WSGI 진입점 이름
