"""지침과 자료가 있는 곳. 로컬은 저장소 최상위, 배포판(Vercel, Root Directory = app)은 app/ 밖을 볼 수 없어 묶음/ 을 쓴다."""
from pathlib import Path

여기 = Path(__file__).resolve().parent
_저장소 = 여기.parent.parent
뿌리 = _저장소 if (_저장소 / '지침').is_dir() else 여기 / '묶음'
자료 = 뿌리 / 'research' / 'data'
