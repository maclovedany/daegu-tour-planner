"""조건 네 가지만 받아 1→2→3단계를 이어서 실행한다 (기획자 화면용).

담당자에게 묻던 중간 선택은 '남기고 진행'으로 자동 처리하고, 자동 처리했다는 사실을 기록에 남긴다.
코스 조건(시작·종료, 식사, 운영 방식)은 모두 미정으로 두고 초안을 만든다. 확정은 하지 않는다.
"""
import asyncio
import json
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

앱 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(앱))

from stages import STAGES  # noqa: E402
from 흐름 import (계절_선택지, 언어권_선택지, 지역_선택지, 확정체류기간_선택지,  # noqa: E402
                조건_문장, 전달_준비, 전달_검사)
from 관리자실행 import 코스시험  # noqa: E402

단계이름 = ['자료 확인', '수요 분석', '코스 짜기']   # 화면 위 진행 표시에 그대로 쓰인다
자동표시 = '기획자 화면 자동 진행 (담당자가 직접 고르지 않음)'


def 조건_확인(값):
    if not isinstance(값, dict):
        raise ValueError('조건을 다시 골라 주세요.')
    계절, 체류 = 값.get('계절'), 값.get('체류기간')
    언어권, 지역 = 값.get('언어권'), 값.get('지역')
    if 계절 not in 계절_선택지:
        raise ValueError('계절을 골라 주세요.')
    if 체류 not in 확정체류기간_선택지:
        raise ValueError('체류 기간을 골라 주세요.')
    for 이름, 목록, 선택지 in [('대상 언어권', 언어권, 언어권_선택지), ('지역', 지역, 지역_선택지)]:
        if not isinstance(목록, list) or not 목록 or any(x not in 선택지 for x in 목록) or len(set(목록)) != len(목록):
            raise ValueError(f'{이름}을 하나 이상 골라 주세요.')
    return {'계절': 계절, '언어권': 언어권, '지역': 지역, '체류기간': 체류}


async def _AI(에이전트, 입력):
    from run_stage import 단계_실행
    return await 단계_실행(에이전트, 입력)


class 자동기획:
    def __init__(self, 저장소, 실행함수=None):
        self.저장소 = 저장소
        self.실행함수 = 실행함수 or _AI
        self.잠금 = threading.Lock()
        self.작업 = None
        self.상태 = {'상태': '없음'}

    def 진행(self):
        return dict(self.상태)

    def 시작(self, 값):
        조건 = 조건_확인(값)
        with self.잠금:
            if self.작업 is not None and self.작업.is_alive():
                raise ValueError('다른 기획을 만드는 중입니다. 끝난 뒤 다시 시작해 주세요.')
            실행 = datetime.now().strftime('%Y%m%d_%H%M%S')
            폴더 = self.저장소.루트 / 실행 / '01회차'
            폴더.mkdir(parents=True, exist_ok=False)
            self.상태 = {'상태': '진행중', '단계': 0, '단계이름': 단계이름, 'id': f'{실행}/01회차',
                       '조건': 조건, '요약': [], '시작시각': datetime.now().astimezone().isoformat()}
            self.작업 = threading.Thread(target=self._실행, args=(폴더, 조건), daemon=True)
            self.작업.start()
            return self.진행()

    def _저장(self, 폴더, 이름, 값):
        글 = 값 if isinstance(값, str) else json.dumps(값, ensure_ascii=False, indent=2)
        (폴더 / 이름).write_text(글, encoding='utf-8')

    def _실행(self, 폴더, 조건):
        try:
            한번 = lambda 에이전트, 입력: asyncio.run(asyncio.wait_for(self.실행함수(에이전트, 입력), timeout=1500))  # noqa: E731
            결과1 = 한번(STAGES[1]['에이전트'], '조건: ' + 조건_문장(조건))
            self._저장(폴더, '1단계_결과.md', 결과1)
            self._저장(폴더, '1단계_선택.json', {'조건': 조건, '담당자선택': '알림을남기고진행', '입력경로': 자동표시})

            알림 = re.search(r'알림[^\n]*?(\d+)\s*건', 결과1)
            self.상태['요약'].append(f'볼 수 있는 자료를 확인했습니다. 알림 {알림[1]}건' if 알림 else '볼 수 있는 자료를 확인했습니다.')
            self.상태['단계'] = 1
            기관 = '기관 데이터: 없음'
            결과2 = 한번(STAGES[2]['에이전트'], '1단계 결과:\n' + 결과1 + '\n\n담당자 선택: 알림을 남기고 진행\n' + 기관)
            self._저장(폴더, '2단계_결과.md', 결과2)
            self._저장(폴더, '2단계_선택.json', {'담당자선택_E3': '경고를남기고진행', '확정체류기간': 조건['체류기간'], '입력경로': 자동표시})
            전달 = 전달_준비(조건, 조건['체류기간'], '경고를남기고진행', 결과2, 기관)
            문제 = 전달_검사(전달)
            전달['검사결과'] = 문제 or ['통과']
            self._저장(폴더, '3단계_전달_준비.json', 전달)
            if 문제:
                self.상태.update({'상태': '멈춤', '안내': '수요 분석 결과의 표 형식이 맞지 않아 코스를 만들지 못했습니다. 같은 조건으로 다시 시작해 주세요.',
                                '문제': 문제[:5]})
                return

            self.상태['요약'].append(f"근거 {len(전달['근거목록'])}건, 주의 {len(전달['경고목록'])}건")
            self.상태['단계'] = 2
            코스 = 코스시험(self.저장소, self.실행함수)
            칸 = [(1, '점심'), (1, '저녁')] + ([(2, '점심')] if 조건['체류기간'] == '1박2일' else [])
            준비 = 코스.저장(self.상태['id'], {'식사목록': [{'일차': 일, '시간칸': 이름} for 일, 이름 in 칸]})
            코스.시작(준비['시험id'])
            코스.작업들[준비['시험id']].join()
            끝 = 코스.상태(준비['시험id'])
            if 끝.get('상태') == '실행실패' or not (self.저장소.루트 / 준비['시험id'] / '3단계_결과.md').is_file():
                self.상태.update({'상태': '멈춤', '안내': '코스를 만드는 중에 AI 연결이 끊겼습니다. 로그인과 네트워크를 확인한 뒤 다시 시작해 주세요.'})
                return
            try:
                칸수 = len(json.loads((self.저장소.루트 / 준비['시험id'] / '3단계_구조화.json').read_text(encoding='utf-8')).get('칸목록', []))
                self.상태['요약'].append(f'일정 {칸수}개로 코스 초안을 만들었습니다.')
            except (ValueError, OSError):
                self.상태['요약'].append('코스 초안을 만들었습니다.')
            self.상태.update({'상태': '완료', '단계': 3})
        except Exception as 오류:  # 원문·키를 화면에 복제하지 않는다
            self.상태.update({'상태': '멈춤', '오류종류': type(오류).__name__,
                            '안내': 'AI를 실행하지 못했습니다. 로그인·네트워크를 확인한 뒤 다시 시작해 주세요.'})
        finally:
            self.상태['끝난시각'] = datetime.now().astimezone().isoformat()
