"""자율형 멀티에이전트 엔진. 한 번 부르면 '총괄의 판단 한 번' 또는 '고른 에이전트들의 실행 한 번'만 한다.

- 상태(일)는 JSON으로 저장할 수 있는 dict 하나다. 그래서 로컬(스레드가 계속 돌림)과 배포판(요청마다 한 걸음, 상태는 DB)이 같은 엔진을 쓴다.
- 총괄 에이전트: 무엇을 부를지, 검증에서 걸린 단계를 어떤 지시로 다시 돌릴지 정한다. 할 수 있는 일이 하나뿐일 때는 묻지 않고 진행한다.
- 총괄은 담당자만 정할 수 있는 것(시작 · 종료, 식사, 확정)을 정하지 못한다. 그런 값을 받는 도구가 없다.
"""
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

여기 = Path(__file__).resolve().parent
sys.path[:0] = [str(여기.parent), str(여기)]

from 에이전트 import JSON_꺼내기, 부르기  # noqa: E402
from 단계 import 검증, 수요_글, 수요_분석, 자료_확인, 코스_짜기  # noqa: E402
from 단계연결 import 코스_검사  # noqa: E402
from 시간표검사 import 시간표_검사  # noqa: E402
from 관리자실행 import 조건_검사  # noqa: E402
from 흐름 import 전달_검사, 전달_준비  # noqa: E402

단계이름 = ['자료 확인', '수요 분석', '코스 짜기']
한도 = {'analyze_demand': 2, 'plan_course': 2, 'review_demand': 2, 'review_course': 1}   # 같은 일을 끝없이 되풀이하지 않게
누구 = {'collect_data': '자료 확인', 'analyze_demand': '수요 분석', 'plan_course': '코스 짜기', 'review_demand': '검증', 'review_course': '검증'}
자동표시 = '기획자 화면 자동 진행 (담당자가 직접 고르지 않음)'
사람몫 = ('확정조건 미충족', '2일차 오전은 담당자가', '미확정', '시각 형식 오류')

총괄_지시 = '''너는 대구 체류 여행 코스 기획의 총괄 에이전트다. 단계 에이전트와 검증 에이전트를 불러 "검증을 통과한 코스 초안"을 만든다. 지금까지의 기록을 보고 다음에 할 일을 정한다.

부를 수 있는 일:
- analyze_demand: 수요 분석 에이전트 (근거표를 요약 · 해석). 다시 시킬 때는 "지시"에 고칠 점을 적는다.
- plan_course: 코스 짜기 에이전트. 다시 시킬 때는 "지시"에 고칠 점을 적는다.
- review_demand: 검증 에이전트가 수요 분석 요약을 자료와 대조한다.
- review_course: 검증 에이전트가 코스 초안을 운영 정보 · 이동 시간과 대조한다.
- finish: 마무리한다.

판단 규칙 (빠르게 끝내는 것이 중요하다):
1. 수요 분석이 나오면 review_demand와 plan_course를 한꺼번에 부른다. 코스가 나오면 review_course를 부른다.
2. 결과의 "고칠 점"이나 검증의 "문제"가 있으면, 무엇을 어떻게 고칠지 한두 문장으로 "지시"에 적어 그 단계를 한 번만 다시 부른다. 다시 한 결과는 다시 검증하지 않고 받아들인다.
3. 수요 분석 요약만 고친 경우 코스는 다시 짜지 않는다. 근거 행과 경고는 그대로이기 때문이다.
4. "담당자 확인 대기"는 사람이 정할 일이다. 고치려 하지 말고 finish의 "사람이_정할_것"에 넘긴다.
5. "남은 횟수"가 0인 일은 부르지 않는다. 더 할 일이 없거나 다시 해도 문제가 남으면 finish로 끝낸다.

출력은 JSON 객체 하나만 쓴다:
{"행동": [{"도구": "analyze_demand|plan_course|review_demand|review_course", "지시": ""}]}
또는
{"행동": [{"도구": "finish", "요약": "결과 한두 문장", "사람이_정할_것": ["…"], "남은_문제": ["…"]}]}'''


def 새일(조건, 실행id):
    return {'상태': '진행중', '단계': 0, '단계이름': 단계이름, 'id': 실행id, '조건': 조건, '요약': [], '활동': [], '일하는중': ['총괄'],
            '시작시각': datetime.now().astimezone().isoformat(), '할일': [], '횟수': {}, '기록': [], '수요': None, '코스': None, '코스조건': None,
            '자료확인': False, '전달통과': False}


def 보이기(일):
    """화면에 줄 것만. 코스 전문 같은 큰 값은 뺀다."""
    열쇠 = ['상태', '단계', '단계이름', 'id', '조건', '요약', '활동', '일하는중', '시작시각', '전체초', '마무리', '사람이_정할_것', '남은_문제', '안내', '오류종류']
    return json.loads(json.dumps({k: 일[k] for k in 열쇠 if k in 일}, ensure_ascii=False))


def _기록(일, 이름, 내용, 초=None):
    일['활동'].append({'누가': 이름, '내용': 내용, '초': 초, '시각': datetime.now().strftime('%H:%M:%S')})


def 멈춤(일, 안내, 오류=None):
    일.update({'상태': '멈춤', '안내': 안내, '일하는중': [], '할일': []})
    if 오류:
        일['오류종류'] = 오류
    _마침(일)


def _마침(일):
    일['일하는중'] = []
    일['전체초'] = round((datetime.now().astimezone() - datetime.fromisoformat(일['시작시각'])).total_seconds(), 1)
    일['끝난시각'] = datetime.now().astimezone().isoformat()


def 식사칸(조건):
    칸 = [(1, '점심'), (1, '저녁')] + ([(2, '점심')] if 조건['체류기간'] == '1박2일' else [])
    return {'식사목록': [{'일차': 일, '시간칸': 이름} for 일, 이름 in 칸]}   # 담당자 선택은 모두 미정으로 둔다


def 전달_만들기(조건, 근거, 수요):
    글 = 수요_글(근거, 수요['요약'], 수요['해석'])
    전달 = 전달_준비(조건, 조건['체류기간'], '경고를남기고진행', 글, '기관 데이터: 없음')
    전달['검사결과'] = 전달_검사(전달) or ['통과']
    return 글, 전달


def 코스검사(코스, 입력3):
    """형식 · 참조 · 시간표 검사. 담당자가 아직 정하지 않아 생기는 항목은 '고칠 점'이 아니라 사람에게 넘길 일이다."""
    try:
        문제 = 코스_검사(코스, 입력3)
        시간 = 시간표_검사(코스, 입력3['코스작성조건'], 입력3['확정체류기간'])
    except (TypeError, ValueError, KeyError, AttributeError):
        return {'고칠': ['코스 JSON의 필수 필드 형식이 맞지 않습니다. 형식대로 다시 써야 합니다.'], '대기': [], '충돌': []}
    제몫 = lambda p: any(k in p for k in 사람몫)  # noqa: E731
    return {'고칠': [p for p in 문제 if not 제몫(p)], '대기': list(dict.fromkeys([p for p in 문제 if 제몫(p)] + 시간['확인대기'])), '충돌': 시간['충돌']}


async def 한걸음(일, 저장):
    """총괄의 판단 한 번, 또는 고른 일들의 실행 한 번."""
    if 일['상태'] != '진행중':
        return 일
    try:
        if 일['할일']:
            await _실행(일, 저장)
        else:
            await _판단(일, 저장)
    except Exception as 오류:   # 원문 · 키를 화면에 복제하지 않는다
        _기록(일, '앱', f'멈춤: {type(오류).__name__}')
        멈춤(일, 'AI를 실행하지 못했습니다. 키 · 로그인 · 네트워크를 확인한 뒤 다시 시작해 주세요.', type(오류).__name__)
        저장.끝(일)
    return 일


async def _판단(일, 저장):
    남은 = {k: v - 일['횟수'].get(k, 0) for k, v in 한도.items()}
    if not 일['자료확인']:
        행동 = [{'도구': 'collect_data'}]            # 할 수 있는 일이 하나뿐이면 총괄을 부르지 않는다
    elif 일['수요'] is None and 남은['analyze_demand'] == 한도['analyze_demand']:
        행동 = [{'도구': 'analyze_demand', '지시': ''}]
    else:
        입력 = ('조건: ' + json.dumps(일['조건'], ensure_ascii=False) + '\n\n지금까지의 기록:\n' + '\n'.join(f'{i + 1}. {줄}' for i, 줄 in enumerate(일['기록']))
              + '\n\n남은 횟수: ' + json.dumps(남은, ensure_ascii=False) + f"\n코스 초안: {'있음' if 일['코스'] else '없음'}")
        답, 초 = await 부르기(총괄_지시, 입력)
        try:
            행동 = [h for h in JSON_꺼내기(답).get('행동', []) if isinstance(h, dict)]
        except ValueError:
            행동 = []
        행동 = [h for h in 행동 if h.get('도구') == 'finish' or (h.get('도구') in 한도 and 남은[h['도구']] > 0)]
        if not 행동:   # 총괄이 쓸 수 없는 답을 냈을 때: 코스가 없으면 한 번 짜 보고, 있으면 끝낸다
            행동 = [{'도구': 'plan_course', '지시': ''}] if 일['코스'] is None and 일['전달통과'] and 남은['plan_course'] > 0 else [{'도구': 'finish', '요약': '', '남은_문제': ['총괄 에이전트가 다음 일을 정하지 못했습니다.']}]
        _기록(일, '총괄', '다음 일을 정함: ' + ', '.join(누구.get(h['도구'], '마무리') + (f" ({str(h.get('지시'))[:40]})" if h.get('지시') else '') for h in 행동), 초)
    끝 = next((h for h in 행동 if h.get('도구') == 'finish'), None)
    if 끝:
        남은문제 = [str(x) for x in 끝.get('남은_문제') or []][:6]
        if 일['코스'] is None:
            멈춤(일, '코스 초안을 만들지 못했습니다. ' + ' '.join(남은문제)[:200])
        else:
            일.update({'상태': '완료', '단계': 3, '마무리': str(끝.get('요약', ''))[:400], '남은_문제': 남은문제,
                      '사람이_정할_것': [str(x) for x in 끝.get('사람이_정할_것') or 일.get('대기', [])][:10]})
            _마침(일)
        _기록(일, '총괄', '마무리: ' + str(끝.get('요약', ''))[:120])
        저장.끝(일)
        return
    일['할일'] = 행동
    일['일하는중'] = list(dict.fromkeys(누구[h['도구']] for h in 행동))


async def _실행(일, 저장):
    from 근거추출 import 추출
    조건, 할일 = 일['조건'], 일['할일']
    근거 = 추출(조건)

    async def 하나(h):
        도구, 지시, 이름 = h['도구'], str(h.get('지시') or ''), 누구[h['도구']]
        일['횟수'][도구] = 일['횟수'].get(도구, 0) + 1
        try:
            if 도구 == 'collect_data':
                t = time.monotonic()
                _, 글 = 자료_확인(조건)
                저장.단계1(일, 글)
                요약 = f"근거 {len(근거['행'])}행, 경고 {len(근거['경고'])}건, 알림 {len(근거['알림'])}건"
                _기록(일, 이름, 요약, round(time.monotonic() - t, 2))
                일['요약'].append('조건에 맞는 자료에서 ' + 요약 + '을 뽑았습니다.')
                일.update({'자료확인': True, '단계': 1})
                return '자료 확인: ' + 요약
            if 도구 == 'analyze_demand':
                r = await 수요_분석(조건, 근거, 지시)
                일['수요'] = {'요약': r['요약'], '해석': r['해석']}
                글, 전달 = 전달_만들기(조건, 근거, 일['수요'])
                형식 = [p for p in 전달['검사결과'] if p != '통과']
                저장.단계2(일, 글, 전달)
                일['전달통과'] = not 형식
                고칠 = r['문제'] + 형식[:5]
                _기록(일, 이름, f"요약 {len(r['요약'])}문장" + (f', 고칠 점 {len(고칠)}건' if 고칠 else ''), r['초'])
                if not 고칠:
                    일['요약'] = 일['요약'][:1] + [f"근거 {len(전달['근거목록'])}건과 주의 {len(전달['경고목록'])}건을 요약 {len(r['요약'])}문장으로 정리했습니다."]
                    일['단계'] = max(일['단계'], 2)
                return '수요 분석 결과: ' + json.dumps({'요약': [x['문장'] for x in r['요약']], '해석': r['해석'], '고칠 점': 고칠}, ensure_ascii=False)
            if 도구 == 'plan_course':
                if not 일['전달통과']:
                    return '코스 짜기 불가: 수요 분석이 문제 없이 끝나야 합니다.'
                _, 전달 = 전달_만들기(조건, 근거, 일['수요'])
                입력3 = dict(전달, 코스작성조건=조건_검사(식사칸(조건), 조건['체류기간']))
                r = await 코스_짜기(입력3, 지시)
                검사 = 코스검사(r['코스'], 입력3)
                저장.코스(일, r['코스'], 입력3, 검사)
                일.update({'코스': r['코스'], '코스조건': 입력3['코스작성조건'], '대기': 검사['대기']})
                칸들 = [f"{k.get('일차')}일차 {k.get('시간칸')} {k.get('장소명')} {k.get('시각', {}).get('값') or '시각 미정'}" for k in r['코스'].get('칸목록', [])]
                _기록(일, 이름, f'일정 {len(칸들)}개' + (f", 고칠 점 {len(검사['고칠'])}건" if 검사['고칠'] else ''), r['초'])
                if not 검사['고칠']:
                    일['요약'] = 일['요약'][:2] + [f'일정 {len(칸들)}개로 코스 초안을 만들었습니다.']
                return '코스 짜기 결과: ' + json.dumps({'일정': 칸들, '고칠 점': 검사['고칠'][:6], '시간 충돌': 검사['충돌'][:5], '담당자 확인 대기': 검사['대기'][:8]}, ensure_ascii=False)
            대상 = 'demand' if 도구 == 'review_demand' else 'course'
            if (대상 == 'demand' and not 일['수요']) or (대상 == 'course' and not 일['코스']):
                return f'검증 불가: 검증할 결과가 아직 없습니다 ({도구}).'
            r = await 검증(대상, 조건, 근거, 일['수요'], 일['코스'], 일['코스조건'] or {})
            말 = '수요 분석' if 대상 == 'demand' else '코스'
            _기록(일, 이름, f'{말}: ' + ('통과' if r['통과'] else f"문제 {len(r['문제'])}건 — " + r['문제'][0][:60]), r['초'])
            return f'{말} 검증: ' + json.dumps({'통과': r['통과'], '문제': r['문제']}, ensure_ascii=False)
        except asyncio.TimeoutError:
            _기록(일, 이름, '정해 둔 시간 안에 끝나지 않아 끊었습니다')
            return f'{이름}: 시간 초과로 끝나지 않았습니다.'
        except ValueError:
            _기록(일, 이름, '답을 읽지 못했습니다 (형식 오류)')
            return f'{이름}: 답의 형식이 맞지 않아 읽지 못했습니다.'
        finally:
            if 이름 in 일['일하는중'] and not any(누구[x['도구']] == 이름 and x is not h and not x.get('_끝') for x in 할일):
                일['일하는중'].remove(이름)
            h['_끝'] = True

    결과 = await asyncio.gather(*[하나(h) for h in 할일])
    일['기록'] += 결과
    일['할일'] = []
    일['일하는중'] = ['총괄']
