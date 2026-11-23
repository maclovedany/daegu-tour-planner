"""에이전트 한 번 부르기: 지침을 미리 붙여 넣고, 도구 없이 한 번에 답하게 한다.

예전 방식은 에이전트가 지침 10여 개와 CSV를 도구로 하나씩 읽어 단계마다 몇 분이 걸렸다.
여기서는 필요한 글과 자료를 처음부터 넣어 주므로 왕복이 없고, 걸린 시간을 함께 돌려준다.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

앱 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(앱))
저장소 = 앱.parent

from 설정 import 설정_읽기  # noqa: E402

제한_초 = 60          # 단계 하나에 허용하는 시간. 넘으면 끊고 총괄 에이전트에게 알린다


def 지침(*파일들):
    """지침 파일 여러 개를 한 덩어리 글로. 에이전트가 다시 읽지 않아도 되게 전문을 넣는다."""
    return '\n\n'.join(f'===== {p} =====\n' + (저장소 / p).read_text(encoding='utf-8') for p in 파일들)


def 절(파일, 시작, 끝):
    """파일에서 '시작' 제목 줄부터 '끝' 제목 줄 앞까지."""
    글 = (저장소 / 파일).read_text(encoding='utf-8')
    a = 글.index(시작)
    b = 글.index(끝, a) if 끝 in 글[a:] else len(글)
    return 글[a:b]


async def 부르기(시스템, 입력, 모델=None, 제한=None):
    """(답, 걸린 초). 도구 없음 · 한 번에 답 · 생각 과정 생략."""
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
    설정 = 설정_읽기(저장소)
    옵션 = ClaudeAgentOptions(
        model=모델 or (설정.get('CLAUDE_MODEL') or 'claude-sonnet-5-5').strip(),
        system_prompt=시스템, tools=[], allowed_tools=[], cwd=str(저장소), max_turns=1,
        setting_sources=[], thinking={'type': 'disabled'}, effort='low',
    )

    async def 한번():
        조각 = []
        async for 메시지 in query(prompt=입력, options=옵션):
            if isinstance(메시지, AssistantMessage):
                조각 += [b.text for b in 메시지.content if isinstance(b, TextBlock)]
        return '\n'.join(조각).strip()

    시작 = time.monotonic()
    답 = await asyncio.wait_for(한번(), timeout=제한 or 제한_초)
    return 답, round(time.monotonic() - 시작, 1)


def JSON_꺼내기(글):
    """답에서 JSON 객체 하나를 꺼낸다. 앞뒤에 붙은 말과 코드 울타리는 버린다."""
    a, b = 글.find('{'), 글.rfind('}')
    if a < 0 or b <= a:
        raise ValueError('JSON 객체가 없습니다.')
    값 = json.loads(글[a:b + 1])
    if not isinstance(값, dict):
        raise ValueError('JSON 객체가 아닙니다.')
    return 값
