"""로컬에서 자율형 멀티에이전트 기획을 돌린다: 엔진(걸음.py)을 스레드에서 끝날 때까지 한 걸음씩 부르고, 결과를 runs/ 에 파일로 남긴다."""
import asyncio
import hashlib
import json
import sys
import threading
from datetime import datetime
from pathlib import Path

여기 = Path(__file__).resolve().parent
sys.path[:0] = [str(여기.parent), str(여기)]

from 걸음 import 보이기, 새일, 식사칸, 자동표시, 한걸음, 멈춤  # noqa: E402
from 실행 import 조건_확인  # noqa: E402
from 관리자실행 import 코스시험  # noqa: E402


class 파일저장:
    """기존 관리자 화면과 같은 폴더 모양으로 남긴다 (runs/<실행>/01회차/…)."""

    def __init__(self, 저장소, 폴더):
        self.저장소, self.폴더, self.시험폴더 = 저장소, 폴더, None

    def _쓰기(self, 이름, 값):
        (self.폴더 / 이름).write_text(값 if isinstance(값, str) else json.dumps(값, ensure_ascii=False, indent=2), encoding='utf-8')

    def 단계1(self, 일, 글):
        self._쓰기('1단계_결과.md', 글)
        self._쓰기('1단계_선택.json', {'조건': 일['조건'], '담당자선택': '알림을남기고진행', '입력경로': 자동표시})

    def 단계2(self, 일, 글, 전달):
        self._쓰기('2단계_결과.md', 글)
        self._쓰기('2단계_선택.json', {'담당자선택_E3': '경고를남기고진행', '확정체류기간': 일['조건']['체류기간'], '입력경로': 자동표시})
        self._쓰기('3단계_전달_준비.json', 전달)
        if self.시험폴더:   # 이미 만든 코스가 있으면 그 입력 기록의 요약을 새 것으로 맞춘다 (근거 행 · 경고는 같다)
            옛 = json.loads((self.시험폴더 / '3단계_입력.json').read_text(encoding='utf-8'))
            (self.시험폴더 / '3단계_입력.json').write_text(json.dumps(dict(전달, 코스작성조건=옛['코스작성조건']), ensure_ascii=False, indent=2), encoding='utf-8')
            상태파일 = self.시험폴더 / '통합시험_상태.json'
            기록 = json.loads(상태파일.read_text(encoding='utf-8'))
            기록.update({'원본해시': hashlib.sha256((self.폴더 / '3단계_전달_준비.json').read_bytes()).hexdigest(),
                       '입력해시': hashlib.sha256((self.시험폴더 / '3단계_입력.json').read_bytes()).hexdigest()})
            상태파일.write_text(json.dumps(기록, ensure_ascii=False, indent=2), encoding='utf-8')

    def 코스(self, 일, 코스, 입력3, 검사):
        관리 = 코스시험(self.저장소)
        준비 = 관리.저장(일['id'], 식사칸(일['조건']))
        시험폴더 = self.시험폴더 = self.저장소.루트 / 준비['시험id']
        원문 = json.dumps(코스, ensure_ascii=False, indent=2)
        (시험폴더 / '3단계_결과.md').write_text(원문, encoding='utf-8')
        입력 = json.loads((시험폴더 / '3단계_입력.json').read_text(encoding='utf-8'))
        상태 = 관리._결과검사(준비['시험id'], 입력, 원문, 준비)
        상태['완료시각'] = datetime.now().astimezone().isoformat()
        (시험폴더 / '통합시험_상태.json').write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding='utf-8')

    def 끝(self, 일):
        self._쓰기('에이전트_활동.json', 보이기(일))


class 자율기획:
    def __init__(self, 저장소):
        self.저장소 = 저장소
        self.잠금 = threading.Lock()
        self.작업 = None
        self.일 = None

    def 진행(self):
        return 보이기(self.일) if self.일 else {'상태': '없음'}

    def 시작(self, 값):
        조건 = 조건_확인(값)
        with self.잠금:
            if self.작업 is not None and self.작업.is_alive():
                raise ValueError('다른 기획을 만드는 중입니다. 끝난 뒤 다시 시작해 주세요.')
            실행 = datetime.now().strftime('%Y%m%d_%H%M%S')
            폴더 = self.저장소.루트 / 실행 / '01회차'
            폴더.mkdir(parents=True, exist_ok=False)
            self.일 = 새일(조건, f'{실행}/01회차')
            self.작업 = threading.Thread(target=self._실행, args=(폴더,), daemon=True)
            self.작업.start()
            return self.진행()

    def _실행(self, 폴더):
        일, 저장 = self.일, 파일저장(self.저장소, 폴더)

        async def 돌기():
            for _ in range(30):   # 총괄의 판단과 실행을 번갈아. 한도를 넘으면 멈춘다
                if 일['상태'] != '진행중':
                    return
                await 한걸음(일, 저장)
            멈춤(일, '정해 둔 걸음 수 안에 끝나지 않았습니다. 다시 시작해 주세요.')
            저장.끝(일)

        asyncio.run(돌기())
