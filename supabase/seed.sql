-- 장소 운영 정보 · 좌표 · 이동 시간 넣기. 원본: research/data/장소운영정보_중구동구_데모코스_2026.csv,
-- research/data/이동시간_중구동구_데모코스_2026.csv, app/플래너/자료/장소좌표.csv (좌표: OpenStreetMap Nominatim, 2026-11-23)
-- 값은 원본 그대로이며 비어 있는 칸은 null 로 둔다. 다시 실행해도 같은 이름은 덮어쓴다.

insert into public.places (name, district, place_type, address, lat, lon, location_note, location_source, open_hours, closed_days, last_entry, source_id, source_url, source_grade, checked_on, status, note) values
  ('근대골목', '중구', '관광지·해설', null, 35.8651861, 128.5831845, '정류장·역 기준', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '미입력', '해설은 선택. 신청 방식·단체 조건 [미확인]'),
  ('서문시장', '중구', '시장', null, 35.86943, 128.5807059, '시설', 'OpenStreetMap Nominatim', '매일 09:00-18:00', '매월 1·3번째 일요일. 5번째 일요일은 상가마다 다름. 4번째 일요일은 3·4층 휴점', null, 'S67; S68', null, '개인(S67); 미정, 운영 주체 확인 후 결정(S68)', '2026-11-18', '확인', '현장 방문으로 휴무 확인'),
  ('김광석길', '중구', '관광지', null, 35.8610677, 128.607329, '시설', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '미입력', null),
  ('봉산문화거리', '중구', '관광지', null, 35.8634, 128.5965698, '시설', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '미입력', '확인할 것: 여름 더위 때 실내 대안이 되는 시설'),
  ('봉산찜갈비', '중구', '식당', '대구 중구 동덕로36길 9-18', 35.869395, 128.6095714, '도로 단위', 'OpenStreetMap Nominatim', '09:00-21:00 (라스트오더 20:30)', null, null, 'S75', null, null, '2026-11-18', '미확인', '정기휴무 표기 없음 [미확인]. 공식 사이트 접속 안 됨 (2026-11-18)'),
  ('산호찜갈비', '중구', '식당', '대구 중구 동덕로36길 9-9', 35.869395, 128.6095714, '도로 단위', 'OpenStreetMap Nominatim', '매일 11:00-22:00', '없음 (네이버 ''매일'' 표기)', null, 'S76', null, '개인', '2026-11-18', '확인', null),
  ('뉴욕통닭 (치킨 옵션)', '중구', '식당', '대구 중구 종로 12', 35.8681832, 128.5919044, '도로 단위', 'OpenStreetMap Nominatim', '11:30-18:30', '매주 일요일', null, 'S77', null, '개인', '2026-11-19', '확인', 'research/industry_food/치킨_노포_중구.md 참고'),
  ('평화시장 닭똥집골목 (치킨 옵션)', '동구', '식당가', null, 35.8827839, 128.6214893, '정류장·역 기준', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '미입력', '1단계 지역에 동구를 함께 고를 때만 후보. 조건 세트 A(중구)에는 안 나옴'),
  ('서문시장 야시장', '중구', '야시장', null, 35.86943, 128.5807059, '시설', 'OpenStreetMap Nominatim', '19:00-23:00', '월~목 운영하지 않음', null, 'S69', 'https://www.nightseomun.com/', '공식', '2026-11-18', '확인', '공지 원문 "동계기간 및 악천후와 명절의 경우 시간이 변경 될 수 있습니다." 동계 시간 [미확인]. 월~목 코스의 밤 칸에는 넣을 수 없음'),
  ('향촌문화관', '중구', '실내 관광지 · E4 대체 후보', null, 35.8733574, 128.5941317, '시설', 'OpenStreetMap Nominatim', '4~10월 09:00-19:00; 11~3월 09:00-18:00 (평일·토·일·공휴일 같음)', '매주 월요일(월요일이 공휴일이면 다음 날 휴무), 1월 1일', '관람 종료 30분 전', 'S70; S71', 'https://www.hyangchon.or.kr/', '공식(S70); 개인(S71)', '2026-11-18', '확인', '본편이 아니라 대체 후보. 마지막입장은 네이버 표기(S71)'),
  ('대구근대역사관', '중구', '실내 관광지 · E4 대체 후보', null, 35.8717633, 128.5911236, '시설', 'OpenStreetMap Nominatim', '09:00-18:00', '매주 월요일(공휴일이면 정상 개관), 1월 1일, 설날·추석 당일. 휴관일이 법정공휴일이면 대체 휴관일은 공휴일 다음 첫 평일', '17:30', 'S72', null, '공식', '2026-11-18', '확인', '본편이 아니라 대체 후보. 관람료 무료'),
  ('약령시 한의약박물관', '중구', '실내 관광지 · E4 대체 후보', null, null, null, '위치 미확인', 'OpenStreetMap Nominatim 검색 결과 없음', '09:00-18:00', '매주 월요일(공휴일이면 정상 개관), 1월 1일, 설날·추석 당일. 휴관일이 법정공휴일이면 대체 휴관일은 공휴일 다음 첫 평일', '17:30', 'S73', null, '공식', '2026-11-18', '확인', '본편이 아니라 대체 후보. 관람료 무료'),
  ('국채보상운동기념관', '중구', '실내 관광지 · E4 대체 후보', null, 35.8693059, 128.6017103, '시설', 'OpenStreetMap Nominatim', '3~11월 09:00-18:00; 12~2월 09:00-17:00', '매주 월요일, 1월 1일, 설·추석 명절', null, 'S74', 'https://www.gukchae.com/', '공식', '2026-11-18', '확인', '본편이 아니라 대체 후보. 입장료 무료'),
  ('원주통닭 (치킨 옵션)', '중구', '식당', '대구 중구 동성로6길 42-6', 35.8685311, 128.5983763, '도로 단위', 'OpenStreetMap Nominatim', '11:00-22:00', '매주 월요일', null, 'S78', null, '개인', '2026-11-19', '확인', '동성로 치킨 후보 2 (뉴욕통닭과 함께 유지)'),
  ('동대구역', null, null, null, 35.8772995, 128.6274527, '정류장·역 기준', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '운영정보 없음', null),
  ('반월당역', null, null, null, 35.8653962, 128.5937558, '정류장·역 기준', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '운영정보 없음', null),
  ('동성로', null, null, null, 35.86837, 128.59478, '시설', 'OpenStreetMap Nominatim', null, null, null, null, null, null, null, '운영정보 없음', null)
on conflict (name) do update set district = excluded.district, place_type = excluded.place_type, address = excluded.address, lat = excluded.lat, lon = excluded.lon,
  location_note = excluded.location_note, location_source = excluded.location_source, open_hours = excluded.open_hours, closed_days = excluded.closed_days, last_entry = excluded.last_entry,
  source_id = excluded.source_id, source_url = excluded.source_url, source_grade = excluded.source_grade, checked_on = excluded.checked_on, status = excluded.status, note = excluded.note;

insert into public.travel_times (from_place, to_place, walk_min, transit_min, routes, basis_day, basis_time, tool, checked_on, status, note) values
  ('근대골목', '서문시장', 17, 11, '232 / 402 / 623', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '통과. 도보 17분으로 도보 기준(20분) 이내라 도보도 안내'),
  ('서문시장', '김광석길', 27, 20, '990 / 991 / 309', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '통과'),
  ('김광석길', '산호찜갈비', 23, 17, '403 / 232', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '대구 음식 저녁. 통과'),
  ('김광석길', '뉴욕통닭 (동성로 치킨)', 29, 14, '지하철 / 990 / 991', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '치킨 옵션 (중구). 통과'),
  ('김광석길', '평화시장 닭똥집골목', 60, 39, '401', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '치킨 옵션 (동구). 대중교통 39분, 상한 30분 초과 → 대체 검토'),
  ('산호찜갈비', '서문시장 야시장', 44, 21, '156 / 425', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '통과'),
  ('뉴욕통닭 (동성로 치킨)', '서문시장 야시장', 24, 16, '지하철 / 990 / 991', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '통과'),
  ('평화시장 닭똥집골목', '서문시장 야시장', 75, 29, '156→232 (환승 1회)', '평일', '15:24', '네이버 지도', '2026-11-19', '확인', '경고. 대중교통 29분(상한 3분 이내), 환승 1회'),
  ('동대구역', '근대골목', 62, 17, '지하철 1호선', '평일', '10:00', '네이버 지도', '2026-11-20', '확인', '통과. 1일차 10:00 출발 첫 구간'),
  ('산호찜갈비', '반월당역', 24, 11, '306', '평일', '10:00', '네이버 지도', '2026-11-20', '확인', '통과. 반월당역 = 숙박 권역 기준점'),
  ('서문시장 야시장', '반월당역', 22, 10, '405', '평일', '10:00', '네이버 지도', '2026-11-20', '확인', '통과. 반월당역 = 숙박 권역 기준점')
on conflict (from_place, to_place) do update set walk_min = excluded.walk_min, transit_min = excluded.transit_min, routes = excluded.routes,
  basis_day = excluded.basis_day, basis_time = excluded.basis_time, tool = excluded.tool, checked_on = excluded.checked_on, status = excluded.status, note = excluded.note;
