"""에이전트 한 번 부르기: 지침을 미리 붙여 넣고, 도구 없이 한 번에 답하게 한다.

예전 방식은 에이전트가 지침 10여 개와 CSV를 도구로 하나씩 읽어 단계마다 몇 분이 걸렸다.
여기서는 필요한 글과 자료를 처음부터 넣어 주므로 왕복이 없고, 걸린 시간을 함께 돌려준다.

AI 제공자: AI_PROVIDER 설정을 따르고, 없으면 GEMINI_API_KEY가 있을 때 Gemini, 아니면 로컬 Claude Code 로그인을 쓴다.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

앱 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(앱))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from 경로 import 뿌리 as 저장소  # noqa: E402
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


def 제공자():
    설정 = 설정_읽기(앱.parent)
    고른 = (설정.get('AI_PROVIDER') or '').strip().lower()
    return 고른 or ('gemini' if (설정.get('GEMINI_API_KEY') or '').strip() else 'claude'), 설정


async def 부르기(시스템, 입력, 모델=None, 제한=None):
    """(답, 걸린 초). 도구 없음 · 한 번에 답."""
    누구, 설정 = 제공자()
    시작 = time.monotonic()
    if 누구 == 'gemini':
        일 = asyncio.to_thread(_제미나이, 시스템, 입력, 설정)
    else:
        일 = _클로드(시스템, 입력, 모델 or (설정.get('CLAUDE_MODEL') or 'claude-sonnet-5-5').strip())
    답 = await asyncio.wait_for(일, timeout=제한 or 제한_초)
    return 답, round(time.monotonic() - 시작, 1)


async def _클로드(시스템, 입력, 모델):
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
    옵션 = ClaudeAgentOptions(model=모델, system_prompt=시스템, tools=[], allowed_tools=[], cwd=str(앱), max_turns=1,
                          setting_sources=[], thinking={'type': 'disabled'}, effort='low')
    조각 = []
    async for 메시지 in query(prompt=입력, options=옵션):
        if isinstance(메시지, AssistantMessage):
            조각 += [b.text for b in 메시지.content if isinstance(b, TextBlock)]
    return '\n'.join(조각).strip()


def _제미나이(시스템, 입력, 설정):
    from google import genai
    from google.genai import types
    모델 = (설정.get('GEMINI_MODEL') or 'gemini-3.8-flash').strip()   # 기본값은 .env.example 과 같다
    창 = genai.Client(api_key=설정['GEMINI_API_KEY'].strip())
    try:
        응답 = 창.models.generate_content(model=모델, contents=입력, config=types.GenerateContentConfig(
            system_instruction=시스템, response_mime_type='application/json'))
    finally:
        창.close()
    if not 응답.text:
        raise ValueError('Gemini가 글을 돌려주지 않았습니다.')
    return 응답.text.strip()


def JSON_꺼내기(글):
    """답에서 JSON 객체 하나를 꺼낸다. 앞뒤에 붙은 말과 코드 울타리는 버린다."""
    a, b = 글.find('{'), 글.rfind('}')
    if a < 0 or b <= a:
        raise ValueError('JSON 객체가 없습니다.')
    값 = json.loads(글[a:b + 1])
    if not isinstance(값, dict):
        raise ValueError('JSON 객체가 아닙니다.')
    return 값
