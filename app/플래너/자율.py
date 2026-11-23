"""자율형 멀티에이전트 기획: 총괄 에이전트가 단계 에이전트와 검증 에이전트를 스스로 부른다.

- 총괄 에이전트: 무엇을 언제 부를지, 검증에서 걸린 단계를 어떤 지시로 다시 돌릴지 정한다.
- 단계 에이전트: 자료 확인(코드) · 수요 분석 · 코스 짜기. 한 번 부르면 한 단계가 1분 안에 끝나게 만들었다 (단계.py).
- 검증 에이전트: 만든 쪽과 따로, 결과가 자료 · 규칙과 맞는지 본다.
총괄은 담당자만 정할 수 있는 것(시작 · 종료, 식사, 확정)을 대신 정하지 못한다. 도구가 그런 값을 받지 않는다.
"""
import asyncio
import hashlib
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

여기 = Path(__file__).resolve().parent
sys.path.insert(0, str(여기.parent))
sys.path.insert(0, str(여기))

import 에이전트  # noqa: E402
from 단계 import 자료_확인, 수요_분석, 코스_짜기, 자료  # noqa: E402
from 실행 import 조건_확인, 자동표시  # noqa: E402
from 관리자실행 import 코스시험  # noqa: E402
from 흐름 import 전달_검사, 전달_준비  # noqa: E402

단계이름 = ['자료 확인', '수요 분석', '코스 짜기']
한도 = {'analyze_demand': 2, 'plan_course': 2, 'review': 3}   # 같은 일을 끝없이 되풀이하지 않게

총괄_지시 = '''너는 대구 체류 여행 코스 기획의 총괄 에이전트다. 도구로 단계 에이전트와 검증 에이전트를 불러 "검증을 통과한 코스 초안"을 만든다.

순서와 판단 (빠르게 끝내는 것이 중요하다):
1. collect_data → analyze_demand 순서로 부른다.
2. 수요 분석이 나오면 review(target="demand")와 plan_course를 같은 차례에 함께 부른다. 코스가 나오면 review(target="course")를 부른다.
3. 도구 결과의 "고칠_점"이나 검증의 "문제"가 있으면, 무엇을 어떻게 고칠지 한두 문장으로 적어 그 단계를 한 번만 다시 부른다. 다시 한 결과는 다시 검증하지 않고 받아들인다.
4. 수요 분석 요약만 고친 경우 코스는 다시 짜지 않는다. 근거 행과 경고는 그대로이기 때문이다.
5. "담당자_확인_대기"는 사람이 정할 일이다. 고치려 하지 말고 finish의 left_for_human에 그대로 넘긴다.
6. 다시 해도 남은 문제는 finish의 unresolved에 적는다. 끝나면 반드시 finish를 부른다. 도구 호출 사이에 설명을 쓰지 않는다.'''


class 자율기획:
    def __init__(self, 저장소):
        self.저장소 = 저장소
        self.잠금 = threading.Lock()
        self.작업 = None
        self.상태 = {'상태': '없음'}

    def 진행(self):
        return json.loads(json.dumps(self.상태, ensure_ascii=False))

    def 시작(self, 값):
        조건 = 조건_확인(값)
        with self.잠금:
            if self.작업 is not None and self.작업.is_alive():
                raise ValueError('다른 기획을 만드는 중입니다. 끝난 뒤 다시 시작해 주세요.')
            실행 = datetime.now().strftime('%Y%m%d_%H%M%S')
            폴더 = self.저장소.루트 / 실행 / '01회차'
            폴더.mkdir(parents=True, exist_ok=False)
            self.상태 = {'상태': '진행중', '단계': 0, '단계이름': 단계이름, 'id': f'{실행}/01회차', '조건': 조건, '요약': [], '활동': [],
                       '시작시각': datetime.now().astimezone().isoformat()}
            self.작업 = threading.Thread(target=self._실행, args=(폴더, 조건), daemon=True)
            self.작업.start()
            return self.진행()

    def _기록(self, 누가, 내용, 초=None):
        self.상태['활동'].append({'누가': 누가, '내용': 내용, '초': 초, '시각': datetime.now().strftime('%H:%M:%S')})

    def _실행(self, 폴더, 조건):
        시작 = time.monotonic()
        try:
            asyncio.run(총괄(self, 폴더, 조건))
            if self.상태['상태'] == '진행중':
                self.상태.update({'상태': '멈춤', '안내': '총괄 에이전트가 마무리하지 않고 끝났습니다. 다시 시작해 주세요.'})
        except Exception as 오류:
            self._기록('앱', f'멈춤: {type(오류).__name__}')
            self.상태.update({'상태': '멈춤', '오류종류': type(오류).__name__, '안내': 'AI를 실행하지 못했습니다. 로그인 · 네트워크를 확인한 뒤 다시 시작해 주세요.'})
        finally:
            self.상태['전체초'] = round(time.monotonic() - 시작, 1)
            self.상태['끝난시각'] = datetime.now().astimezone().isoformat()
            try:
                (폴더 / '에이전트_활동.json').write_text(json.dumps(self.진행(), ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError:
                pass


async def 총괄(기획, 폴더, 조건):
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool
    s = {'근거': None, '수요': None, '전달': None, '코스': None, '시험id': None, '입력3': None, '횟수': {}}
    답 = lambda 값: {'content': [{'type': 'text', 'text': json.dumps(값, ensure_ascii=False)}]}  # noqa: E731

    def 넘침(이름):
        s['횟수'][이름] = s['횟수'].get(이름, 0) + 1
        return s['횟수'][이름] > 한도.get(이름, 99)

    def 저장(이름, 값):
        (폴더 / 이름).write_text(값 if isinstance(값, str) else json.dumps(값, ensure_ascii=False, indent=2), encoding='utf-8')

    async def 시간안에(일, 이름):
        try:
            return await 일
        except asyncio.TimeoutError:
            기획._기록(이름, '정해 둔 시간 안에 끝나지 않아 끊었습니다')
            return None

    @tool('collect_data', '1단계 자료 확인. 조건에 맞는 근거 행과 경고를 원자료에서 뽑는다 (코드, 즉시).', {})
    async def collect_data(_):
        t = time.monotonic()
        s['근거'], 글 = 자료_확인(조건)
        저장('1단계_결과.md', 글)
        저장('1단계_선택.json', {'조건': 조건, '담당자선택': '알림을남기고진행', '입력경로': 자동표시})
        요약 = f"근거 {len(s['근거']['행'])}행, 경고 {len(s['근거']['경고'])}건, 알림 {len(s['근거']['알림'])}건"
        기획._기록('자료 확인', 요약, round(time.monotonic() - t, 2))
        기획.상태['요약'].append('조건에 맞는 자료에서 ' + 요약 + '을 뽑았습니다.')
        기획.상태['단계'] = 1
        return 답({'결과': 요약, '자료_없음': s['근거']['미확인'][:5]})

    @tool('analyze_demand', '2단계 수요 분석 에이전트를 부른다. 근거표를 보고 요약과 해석을 쓴다. instruction에는 다시 할 때 고칠 점을 적는다 (처음엔 빈 문자열).', {'instruction': str})
    async def analyze_demand(args):
        if s['근거'] is None:
            return 답({'오류': 'collect_data를 먼저 부르세요.'})
        if 넘침('analyze_demand'):
            return 답({'오류': '수요 분석을 더 다시 할 수 없습니다. finish로 마무리하세요.'})
        r = await 시간안에(수요_분석(조건, s['근거'], args.get('instruction', '')), '수요 분석')
        if r is None:
            return 답({'오류': '시간 초과. 한 번 더 부르거나 finish로 마무리하세요.'})
        s['수요'] = r
        저장('2단계_결과.md', r['글'])
        저장('2단계_선택.json', {'담당자선택_E3': '경고를남기고진행', '확정체류기간': 조건['체류기간'], '입력경로': 자동표시})
        전달 = 전달_준비(조건, 조건['체류기간'], '경고를남기고진행', r['글'], '기관 데이터: 없음')
        형식 = 전달_검사(전달)
        전달['검사결과'] = 형식 or ['통과']
        저장('3단계_전달_준비.json', 전달)
        s['전달'] = 전달 if not 형식 else None
        if s['시험id'] and not 형식:   # 이미 만든 코스가 있으면 그 입력 기록의 요약을 새 것으로 맞춘다 (근거 행 · 경고는 같다)
            시험폴더 = 기획.저장소.루트 / s['시험id']
            입력3 = dict(전달, 코스작성조건=s['입력3']['코스작성조건'])
            (시험폴더 / '3단계_입력.json').write_text(json.dumps(입력3, ensure_ascii=False, indent=2), encoding='utf-8')
            상태파일 = 시험폴더 / '통합시험_상태.json'
            기록 = json.loads(상태파일.read_text(encoding='utf-8'))
            기록.update({'원본해시': hashlib.sha256((폴더 / '3단계_전달_준비.json').read_bytes()).hexdigest(),
                       '입력해시': hashlib.sha256((시험폴더 / '3단계_입력.json').read_bytes()).hexdigest()})
            상태파일.write_text(json.dumps(기록, ensure_ascii=False, indent=2), encoding='utf-8')
            s['입력3'] = 입력3
        기획._기록('수요 분석', f"요약 {len(r['요약'])}문장" + (f", 고칠 점 {len(r['문제'] + 형식)}건" if r['문제'] or 형식 else ''), r['초'])
        if not (r['문제'] or 형식):
            기획.상태['요약'] = 기획.상태['요약'][:1] + [f"근거 {len(전달['근거목록'])}건과 주의 {len(전달['경고목록'])}건을 요약 {len(r['요약'])}문장으로 정리했습니다."]
            기획.상태['단계'] = max(기획.상태['단계'], 2)
        return 답({'요약': [x['문장'] for x in r['요약']], '해석': r['해석'], '고칠_점': r['문제'] + 형식[:5]})

    @tool('plan_course', '3단계 코스 짜기 에이전트를 부른다. instruction에는 다시 할 때 고칠 점을 적는다 (처음엔 빈 문자열).', {'instruction': str})
    async def plan_course(args):
        if s['전달'] is None:
            return 답({'오류': 'analyze_demand가 문제 없이 끝나야 코스를 짤 수 있습니다.'})
        if 넘침('plan_course'):
            return 답({'오류': '코스를 더 다시 짤 수 없습니다. finish로 마무리하세요.'})
        코스관리 = 코스시험(기획.저장소)
        칸 = [(1, '점심'), (1, '저녁')] + ([(2, '점심')] if 조건['체류기간'] == '1박2일' else [])
        준비 = 코스관리.저장(기획.상태['id'], {'식사목록': [{'일차': 일, '시간칸': 이름} for 일, 이름 in 칸]})   # 담당자 선택은 모두 미정
        시험폴더 = 기획.저장소.루트 / 준비['시험id']
        입력3 = json.loads((시험폴더 / '3단계_입력.json').read_text(encoding='utf-8'))
        r = await 시간안에(코스_짜기(입력3, args.get('instruction', '')), '코스 짜기')
        if r is None:
            return 답({'오류': '시간 초과. 한 번 더 부르거나 finish로 마무리하세요.'})
        원문 = json.dumps(r['코스'], ensure_ascii=False, indent=2)
        (시험폴더 / '3단계_결과.md').write_text(원문, encoding='utf-8')
        상태 = 코스관리._결과검사(준비['시험id'], 입력3, 원문, 준비)
        상태['완료시각'] = datetime.now().astimezone().isoformat()
        (시험폴더 / '통합시험_상태.json').write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding='utf-8')
        # 담당자가 아직 정하지 않아 생기는 항목은 '고칠 점'이 아니라 사람에게 넘길 일이다
        사람몫 = ('확정조건 미충족', '2일차 오전은 담당자가', '미확정', '시각 형식 오류')
        제몫 = lambda p: any(k in p for k in 사람몫)  # noqa: E731
        고칠 = [p for p in 상태.get('문제', []) if not 제몫(p)]
        s['코스'], s['시험id'], s['입력3'] = r['코스'], 준비['시험id'], 입력3
        s['대기'] = list(dict.fromkeys(상태.get('담당자확인대기', []) + [p for p in 상태.get('문제', []) if 제몫(p)]))
        칸들 = [f"{k.get('일차')}일차 {k.get('시간칸')} {k.get('장소명')} {k.get('시각', {}).get('값') or '시각 미정'}" for k in r['코스'].get('칸목록', [])]
        기획._기록('코스 짜기', f'일정 {len(칸들)}개' + (f', 고칠 점 {len(고칠)}건' if 고칠 else ''), r['초'])
        if not 고칠:
            기획.상태['요약'] = 기획.상태['요약'][:2] + [f'일정 {len(칸들)}개로 코스 초안을 만들었습니다.']
        return 답({'일정': 칸들, '고칠_점': 고칠[:6], '시간_충돌': 상태.get('시간표검사', {}).get('충돌', [])[:5], '담당자_확인_대기': s['대기'][:8]})

    @tool('review', '검증 에이전트를 부른다. target은 "demand"(수요 분석 요약) 또는 "course"(코스 초안). 만든 에이전트와 따로 자료 · 규칙과 대조한다.', {'target': str})
    async def review(args):
        대상 = args.get('target')
        if 대상 not in ('demand', 'course') or (대상 == 'demand' and not s['수요']) or (대상 == 'course' and not s['코스']):
            return 답({'오류': '검증할 결과가 아직 없습니다.'})
        if 넘침('review'):
            return 답({'오류': '검증을 더 부를 수 없습니다. finish로 마무리하세요.'})
        r = await 시간안에(검증(대상, 조건, s), '검증')
        if r is None:
            return 답({'오류': '시간 초과'})
        이름 = '수요 분석' if 대상 == 'demand' else '코스'
        기획._기록('검증', f"{이름}: " + ('통과' if r['통과'] else f"문제 {len(r['문제'])}건 — " + r['문제'][0][:60]), r['초'])
        if 대상 == 'course':
            s['코스검증'] = r
        return 답({'통과': r['통과'], '문제': r['문제']})

    @tool('finish', '기획을 마무리한다. summary는 결과 한두 문장, left_for_human은 사람이 정하거나 확인할 일 목록, unresolved는 고치지 못한 문제 목록.',
          {'type': 'object', 'required': ['summary'], 'properties': {
              'summary': {'type': 'string'}, 'left_for_human': {'type': 'array', 'items': {'type': 'string'}},
              'unresolved': {'type': 'array', 'items': {'type': 'string'}}}})
    async def finish(args):
        남은 = [str(x) for x in args.get('unresolved') or []]
        if s['코스'] is None:
            기획.상태.update({'상태': '멈춤', '안내': '코스 초안을 만들지 못했습니다. ' + ' '.join(남은)[:200]})
        else:
            기획.상태.update({'상태': '완료', '단계': 3, '마무리': str(args.get('summary', ''))[:400],
                            '사람이_정할_것': [str(x) for x in args.get('left_for_human') or []][:10], '남은_문제': 남은[:6]})
        기획._기록('총괄', '마무리: ' + str(args.get('summary', ''))[:120])
        return 답({'확인': '끝'})

    도구 = [collect_data, analyze_demand, plan_course, review, finish]
    옵션 = ClaudeAgentOptions(
        model=(에이전트.설정_읽기(에이전트.저장소).get('CLAUDE_MODEL') or 'claude-sonnet-5-5').strip(),
        system_prompt=총괄_지시, tools=[], mcp_servers={'plan': create_sdk_mcp_server('plan', tools=도구)},
        allowed_tools=[f'mcp__plan__{t.name}' for t in 도구], cwd=str(에이전트.저장소), max_turns=24, setting_sources=[],
        thinking={'type': 'disabled'}, effort='low', env={'MCP_TOOL_TIMEOUT': '180000'},
    )
    기획._기록('총괄', '기획을 시작합니다')
    async with ClaudeSDKClient(options=옵션) as 창:
        await 창.query('조건: ' + json.dumps(조건, ensure_ascii=False) + '\n이 조건으로 코스 초안을 만들어 주세요.')
        async for _ in 창.receive_response():
            if 기획.상태['상태'] != '진행중':
                break


async def 검증(대상, 조건, s):
    """만든 에이전트와 따로 부르는 검증 에이전트. {'통과', '문제', '초'}"""
    if 대상 == 'demand':
        시스템 = ('너는 수요 분석 요약을 검증하는 에이전트다. 요약을 쓴 에이전트와 따로 본다. 근거표 전체가 주어진다.\n'
               '뚜렷한 오류만 찾는다: 근거표의 값과 다른 수치, 근거표 어디에도 없는 수치, 조사시기 값과 거주국가 값을 합쳐 교차값처럼 쓴 문장, '
               '기간 · 대상이 다른 두 자료를 한 문장에서 비교한 것, 코스나 장소를 고르거나 막는 말.\n'
               '문제로 삼지 않는 것: 문장이 가리킨 ID 밖의 행에 있는 값을 쓴 것, 같은 뜻의 다른 말(무박 = 당일), 표현 · 어순 · 문체, 더 자세히 쓸 수 있었다는 지적.\n'
               '확실하지 않으면 통과시킨다. 출력은 JSON 하나만: {"통과": true|false, "문제": ["어느 문장이 왜 틀렸고 어떻게 고칠지 한 문장", …]} (문제는 2개 이하).')
        입력 = ('조건: ' + json.dumps(조건, ensure_ascii=False) + '\n\n요약:\n' + '\n'.join(f"- {x['문장']} [{' · '.join(x.get('근거', []))}]" for x in s['수요']['요약'])
              + f"\n해석: {s['수요']['해석']}\n\n근거표 (ID|원자료 항목명|수치|출처 연도|표본):\n"
              + '\n'.join(f"{x['ID']}|{x['원자료 항목명']}|{x['수치']}|{x['출처']} {x['연도']}|{x['표본 · 대상']}" for x in s['근거']['행']))
    else:
        코스 = s['코스']
        시스템 = ('너는 코스 초안을 검증하는 에이전트다. 코스를 짠 에이전트와 따로 본다. 아래 자료에 비추어 틀린 것만 찾는다.\n'
               '찾을 것: 운영 시간 · 정기 휴무와 일정 시각이 부딪히는데 경고나 대체안이 없는 칸, 자료에 있는 이동 시간보다 짧게 잡힌 연결, '
               '담당자가 미정으로 둔 식사 방식 · 식당 · 시작 · 종료를 확정한 것처럼 쓴 것, 가족 · 술 관련 규칙 위반, 수요 근거가 없는데 경고가 없는 관광 칸, 같은 장소 중복.\n'
               '시각이 "가정"이거나 담당자 확인 대기인 것, 미정으로 남은 것 자체는 문제가 아니다. 표현 · 문체도 문제로 삼지 않는다. 확실하지 않으면 통과시킨다.\n'
               '출력은 JSON 하나만: {"통과": true|false, "문제": ["어느 칸이 왜 틀렸고 어떻게 고칠지 한 문장", …]} (문제는 2개 이하).\n\n'
               + 에이전트.지침('지침/3_코스검토/4_충돌_대체.md', '지침/3_코스검토/12_코스_체크리스트.md')
               + '\n\n===== 장소 운영 정보 =====\n' + (자료 / '장소운영정보_중구동구_데모코스_2026.csv').read_text(encoding='utf-8-sig')
               + '\n===== 이동 시간 =====\n' + (자료 / '이동시간_중구동구_데모코스_2026.csv').read_text(encoding='utf-8-sig'))
        짧은 = {k: 코스.get(k) for k in ['칸목록', '식사목록', '코스시작종료', '운영방식', '2일차오전구성', '대체이력', '미확인사항']}
        짧은['3단계가_붙인_경고'] = [w for w in 코스.get('남은경고', []) if not str(w.get('경고ID', '')).startswith('W')]
        입력 = ('조건: ' + json.dumps(조건, ensure_ascii=False) + '\n담당자 선택: ' + json.dumps({k: v for k, v in s['입력3']['코스작성조건'].items() if k != '결정기록'}, ensure_ascii=False)
              + '\n\n코스 초안:\n' + json.dumps(짧은, ensure_ascii=False))
    답, 초 = await 에이전트.부르기(시스템, 입력)
    값 = 에이전트.JSON_꺼내기(답)
    문제 = [str(x) for x in 값.get('문제', []) if x][:3]
    return {'통과': bool(값.get('통과')) and not 문제, '문제': 문제, '초': 초}
