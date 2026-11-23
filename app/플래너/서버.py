"""기획자 화면 서버 (로컬 전용). 기존 관리자 화면과 따로 띄운다: python 플래너/서버.py --port 8770"""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

여기 = Path(__file__).resolve().parent
sys.path.insert(0, str(여기.parent))
sys.path.insert(0, str(여기))

from 관리자조회 import 결과저장소  # noqa: E402
from 보기 import 기획목록, 기획보기  # noqa: E402
from 자율 import 자율기획  # noqa: E402
from 홍보 import 홍보초안, 홍보읽기  # noqa: E402
from 흐름 import 계절_선택지, 언어권_선택지, 지역_선택지, 확정체류기간_선택지  # noqa: E402

화면 = 여기 / '화면'
형식 = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
      '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml'}


def 핸들러(저장소, 기획=None):
    기획 = 기획 or 자율기획(저장소)
    홍보 = 홍보초안(저장소)

    class Handler(BaseHTTPRequestHandler):
        def 응답(self, 상태, 본문, 타입='application/json; charset=utf-8'):
            데이터 = 본문 if isinstance(본문, bytes) else json.dumps(본문, ensure_ascii=False).encode('utf-8')
            self.send_response(상태)
            self.send_header('Content-Type', 타입)
            self.send_header('Content-Length', str(len(데이터)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data: blob:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(데이터)

        def do_GET(self):
            if self.headers.get('Host') not in [f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}']:
                return self.응답(403, {'오류': '로컬 주소로 접속하세요.'})
            경로 = urlsplit(self.path)
            인자 = parse_qs(경로.query)
            try:
                if 경로.path == '/api/plans':
                    return self.응답(200, 기획목록(저장소))
                if 경로.path == '/api/options':
                    return self.응답(200, {'계절': 계절_선택지, '언어권': 언어권_선택지, '지역': 지역_선택지, '체류기간': 확정체류기간_선택지})
                if 경로.path == '/api/progress':
                    return self.응답(200, 기획.진행())
                if 경로.path == '/api/promo':
                    return self.응답(200, {'진행': 홍보.진행(), '결과': 홍보읽기(저장소, 인자.get('id', [''])[0])})
                if 경로.path == '/api/plan':
                    return self.응답(200, 기획보기(저장소, 인자.get('id', [''])[0]))
                이름 = 'index.html' if 경로.path in ['/', ''] else 경로.path.lstrip('/')
                파일 = (화면 / 이름).resolve()
                if 파일.is_relative_to(화면) and 파일.is_file() and 파일.suffix in 형식:
                    return self.응답(200, 파일.read_bytes(), 형식[파일.suffix])
                return self.응답(404, {'오류': '없는 페이지'})
            except (ValueError, OSError, KeyError):
                return self.응답(404, {'오류': '기획 기록을 읽을 수 없습니다.'})

        def do_POST(self):
            호스트 = self.headers.get('Host', '')
            if 호스트 not in [f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'] \
                    or self.headers.get('Origin') != 'http://' + 호스트 \
                    or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.응답(403, {'오류': '이 화면에서 요청해 주세요.'})
            try:
                크기 = int(self.headers.get('Content-Length', '0'))
                if not 0 < 크기 <= 4096:
                    return self.응답(413, {'오류': '입력을 확인해 주세요.'})
                값 = json.loads(self.rfile.read(크기).decode('utf-8'))
                if self.path == '/api/start':
                    return self.응답(202, 기획.시작(값))
                if self.path == '/api/promo/start':
                    return self.응답(202, 홍보.시작(값.get('id', '')))
                return self.응답(404, {'오류': '없는 요청입니다.'})
            except ValueError as 오류:
                return self.응답(400, {'오류': str(오류) if not isinstance(오류, json.JSONDecodeError) else '입력을 확인해 주세요.'})
            except OSError:
                return self.응답(400, {'오류': '기획을 저장하지 못했습니다.'})

        def log_message(self, *인자):
            pass

    return Handler


def main():
    p = argparse.ArgumentParser(description='기획자 화면 (3D 코스 지도)')
    p.add_argument('--port', type=int, default=8770)
    p.add_argument('--runs', type=Path, default=여기.parent / 'runs')
    a = p.parse_args()
    서버 = ThreadingHTTPServer(('127.0.0.1', a.port), 핸들러(결과저장소(a.runs)))
    print(f'기획자 화면: http://127.0.0.1:{a.port}/', flush=True)
    try:
        서버.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        서버.server_close()


if __name__ == '__main__':
    main()
