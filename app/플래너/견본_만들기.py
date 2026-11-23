"""배포판(Vercel)이 쓸 파일을 app/ 안으로 옮긴다: 보여 줄 견본 기획(견본/)과 에이전트가 읽는 지침 · 자료(묶음/).
지침이나 자료를 고쳤으면 다시 실행하고 커밋한다.

사용: python 플래너/견본_만들기.py
"""
import json
import re
import shutil
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent
sys.path[:0] = [str(여기.parent), str(여기)]

from 관리자조회 import 결과저장소  # noqa: E402
from 보기 import 최신코스  # noqa: E402

원본, 견본 = 결과저장소(여기.parent / 'runs'), 여기 / '견본'


def 줄여_쓰기(파일, 값):
    값.pop('2단계결과_원문', None)   # 화면이 쓰지 않는 긴 원문은 뺀다
    파일.write_text(json.dumps(값, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    shutil.rmtree(견본, ignore_errors=True)
    for 기획 in 원본.목록():
        찾음 = 최신코스(원본, 기획['id'])
        if 찾음 is None:
            continue
        원폴더, 시험 = 원본.루트 / 기획['id'], 찾음[1]
        새폴더 = 견본 / 기획['id'] / 시험.name
        새폴더.mkdir(parents=True)
        shutil.copyfile(원폴더 / '1단계_선택.json', 새폴더.parent / '1단계_선택.json')
        줄여_쓰기(새폴더.parent / '3단계_전달_준비.json', json.loads((원폴더 / '3단계_전달_준비.json').read_text(encoding='utf-8')))
        줄여_쓰기(새폴더 / '3단계_입력.json', json.loads((시험 / '3단계_입력.json').read_text(encoding='utf-8')))
        for 이름 in ['3단계_구조화.json', '통합시험_상태.json', '4단계_구조화.json', '4단계_전달_검사.json']:
            if (시험 / 이름).is_file():
                shutil.copyfile(시험 / 이름, 새폴더 / 이름)
        print('견본:', 기획['id'], 기획['조건'])
    # 배포판(Root Directory = app)은 저장소 최상위의 지침/ 과 research/data/ 를 볼 수 없다. 에이전트가 읽는 것만 묶음/ 으로 옮긴다
    뿌리, 묶음 = 여기.parent.parent, 여기 / '묶음'
    shutil.rmtree(묶음, ignore_errors=True)
    for 폴더 in ['2_수요근거', '3_코스검토', '공통']:
        shutil.copytree(뿌리 / '지침' / 폴더, 묶음 / '지침' / 폴더)
    소스 = (여기 / '근거추출.py').read_text(encoding='utf-8')
    for 이름 in sorted(set(re.findall(r"'([^'\s]+\.csv)'", 소스)) | {'장소운영정보_중구동구_데모코스_2026.csv', '이동시간_중구동구_데모코스_2026.csv'}):
        (묶음 / 'research' / 'data' / 이름).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(뿌리 / 'research' / 'data' / 이름, 묶음 / 'research' / 'data' / 이름)
    print('묶음:', sum(1 for _ in 묶음.rglob('*') if _.is_file()), '개 파일')
    (견본 / '자료').mkdir(parents=True, exist_ok=True)
    for 이름 in ['장소운영정보_중구동구_데모코스_2026.csv', '이동시간_중구동구_데모코스_2026.csv']:   # 배포판은 app/ 밖을 볼 수 없다
        shutil.copyfile(여기.parent.parent / 'research' / 'data' / 이름, 견본 / '자료' / 이름)
