"""홍보물 시안을 파일로 내보낸다 (PDF, 카드뉴스는 PNG). 기획자 화면 서버가 켜져 있어야 한다.

준비: pip install playwright  (이 맥에 설치된 Chrome을 쓴다)
사용: python 플래너/홍보물_내보내기.py "<실행id>" [--port 8770] [--out 폴더]
"""
import argparse
import asyncio
from pathlib import Path
from urllib.parse import quote

종류 = {'map': '관광지도', 'leaflet': '리플릿', 'poster': '포스터', 'cards': 'SNS카드뉴스', 'stamp': '스탬프투어북', 'mockup': '적용예시'}


async def 내보내기(실행id, 포트, 폴더):
    from playwright.async_api import async_playwright
    폴더.mkdir(parents=True, exist_ok=True)
    만든 = []
    async with async_playwright() as p:
        브라우저 = await p.chromium.launch(channel='chrome', headless=True)
        쪽 = await 브라우저.new_page(viewport={'width': 1400, 'height': 1000})
        for 키, 이름 in 종류.items():
            await 쪽.goto(f'http://127.0.0.1:{포트}/promo.html?kind={키}&id={quote(실행id)}')
            await 쪽.wait_for_selector('body[data-ready="1"]', timeout=20000)
            await 쪽.wait_for_timeout(500)
            pdf = 폴더 / f'{이름}.pdf'
            await 쪽.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
            만든.append(pdf)
            if 키 == 'cards':   # 올리기 쉬운 그림 파일도 함께
                await 쪽.emulate_media(media='print')
                for i, 장 in enumerate(await 쪽.query_selector_all('.sheet'), 1):
                    png = 폴더 / f'{이름}_{i:02d}.png'
                    await 장.screenshot(path=str(png))
                    만든.append(png)
                await 쪽.emulate_media(media=None)   # 'screen'으로 두면 뒤따르는 PDF가 화면 모양으로 찍힌다
        await 브라우저.close()
    return 만든


if __name__ == '__main__':
    a = argparse.ArgumentParser(description='홍보물 시안 내보내기')
    a.add_argument('실행id')
    a.add_argument('--port', type=int, default=8770)
    a.add_argument('--out', type=Path)
    인자 = a.parse_args()
    폴더 = 인자.out or Path(__file__).resolve().parent.parent / 'runs' / 인자.실행id / '홍보물'
    for 파일 in asyncio.run(내보내기(인자.실행id, 인자.port, 폴더)):
        print(파일)
