-- 하루하루 · 대구 체류 여행 코스 기획 — Supabase 초기 스키마
-- 지금 app/runs/ 폴더에 파일로 쌓이는 기록(조건, 단계 결과, 근거·경고, 코스 초안, 홍보 초안)을 표로 옮긴 것이다.
-- 실행: Supabase SQL Editor에 붙여 넣거나 `supabase db push`. 그 뒤 seed.sql 로 장소 · 이동 시간을 넣는다.

create extension if not exists pgcrypto;

-- ───────────────────────── 공통 ─────────────────────────
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ───────────────────────── 기획 ─────────────────────────
-- 기획 하나 = 조건 네 가지 + 진행 상태. (runs/<실행>/<회차>)
create table public.plans (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  season        text not null check (season in ('봄', '여름', '가을', '겨울')),
  languages     text[] not null check (cardinality(languages) > 0
                  and languages <@ array['영어권', '일본어', '중국어 간체', '중국어 번체']),
  districts     text[] not null check (cardinality(districts) > 0 and districts <@ array['중구', '동구']),
  stay          text not null check (stay in ('당일', '1박2일')),
  status        text not null default '진행중' check (status in ('진행중', '멈춤', '초안', '확정')),
  current_stage smallint not null default 0 check (current_stage between 0 and 5),
  auto_progress boolean not null default true,   -- 1·2단계의 담당자 선택을 화면이 자동으로 넘겼는지
  notice        text,                            -- 멈췄을 때 사용자에게 보일 안내
  summary       text,                            -- 총괄 에이전트의 마무리 한두 문장
  left_for_human jsonb not null default '[]',    -- 사람이 정하거나 확인할 일
  unresolved    jsonb not null default '[]',     -- 에이전트가 고치지 못하고 남긴 문제
  activity      jsonb not null default '[]',     -- 에이전트 활동 기록 [{누가, 내용, 초, 시각}]
  total_seconds numeric,                         -- 시작부터 마무리까지 걸린 시간
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index plans_owner_idx on public.plans (owner_id, created_at desc);
create trigger plans_touch before update on public.plans for each row execute function public.touch_updated_at();

-- 단계 결과 원문과 구조화 JSON. 같은 단계를 다시 실행하면 version 이 올라간다. (N단계_결과.md, N단계_구조화.json)
create table public.stage_results (
  id           uuid primary key default gen_random_uuid(),
  plan_id      uuid not null references public.plans (id) on delete cascade,
  stage        smallint not null check (stage between 1 and 5),
  version      integer not null default 1 check (version > 0),
  raw_text     text,                             -- AI 가 낸 원문 그대로
  data         jsonb,                            -- 앱이 읽은 구조화 결과
  check_result jsonb not null default '[]',      -- 전달 검사 결과 (통과면 ["통과"])
  created_at   timestamptz not null default now(),
  unique (plan_id, stage, version)
);

-- 2단계 근거표 한 행 (R01 …)
create table public.evidence (
  id            uuid primary key default gen_random_uuid(),
  plan_id       uuid not null references public.plans (id) on delete cascade,
  code          text not null check (code ~ '^R[0-9]{2,}$'),
  item          text not null,                   -- 항목 (방문객, 숙박 …)
  source_item   text,                            -- 원자료 항목명
  value_text    text not null,                   -- 수치 원문 ("59.5%", "2,514명 (계산값)")
  value_num     numeric,                         -- 숫자 하나로 읽히면 그 값
  is_calculated boolean not null default false,
  file_location text not null,                   -- 파일 · 행 위치
  source        text not null,
  year          text,
  sample        text,                            -- 표본 · 대상
  limitation    text,
  unique (plan_id, code)
);

-- 2·3단계 경고 (W1 …, 3단계에서 붙인 경고 포함)
create table public.warnings (
  id             uuid primary key default gen_random_uuid(),
  plan_id        uuid not null references public.plans (id) on delete cascade,
  code           text not null,
  kind           text,                           -- 간접 근거, 변동 큼, 표본 작음 …
  message        text not null,
  evidence_codes text[] not null default '{}',   -- 적용 근거 ID
  unique (plan_id, code)
);

-- ───────────────────────── 장소 자료 (모든 기획이 함께 읽음) ─────────────────────────
create table public.places (
  id             uuid primary key default gen_random_uuid(),
  name           text not null unique,
  district       text,
  place_type     text,
  address        text,
  lat            double precision check (lat between -90 and 90),
  lon            double precision check (lon between -180 and 180),
  location_note  text,                           -- 좌표 정밀도 (시설 / 도로 단위 / 정류장·역 기준 / 위치 미확인)
  location_source text,
  open_hours     text,
  closed_days    text,
  last_entry     text,
  source_id      text,
  source_url     text,
  source_grade   text,
  checked_on     date,
  status         text,                           -- 확인 / 미입력 …
  note           text,
  updated_at     timestamptz not null default now()
);
create trigger places_touch before update on public.places for each row execute function public.touch_updated_at();

create table public.travel_times (
  id          uuid primary key default gen_random_uuid(),
  from_place  text not null,
  to_place    text not null,
  walk_min    integer check (walk_min >= 0),
  transit_min integer check (transit_min >= 0),
  routes      text,
  basis_day   text,                              -- 기준 요일
  basis_time  text,                              -- 기준 출발 시각
  tool        text,
  checked_on  date,
  status      text,
  note        text,
  unique (from_place, to_place)
);

-- ───────────────────────── 코스 ─────────────────────────
-- 코스 저장본. 고칠 때마다 덮어쓰지 않고 revision 을 올린다. (통합시험_*/3단계_구조화.json)
create table public.courses (
  id             uuid primary key default gen_random_uuid(),
  plan_id        uuid not null references public.plans (id) on delete cascade,
  revision       integer not null default 1 check (revision > 0),
  status         text not null default '초안' check (status in ('초안', '확인필요', '확정준비완료', '확정')),
  is_manual_edit boolean not null default false, -- AI 없이 사람이 고친 저장본인지
  start_place    text,
  start_time     time,
  end_place      text,
  end_time       time,
  operation_mode text not null default '미정' check (operation_mode in ('단체동행형', '개별이동형', '미정')),
  day2_morning   text check (day2_morning in ('후보일정추가', '자유시간', '종료장소로바로', '해당없음')),
  conditions     jsonb not null default '{}',    -- 코스작성조건 (식사 방식 · 식비 등 담당자 선택)
  data           jsonb not null,                 -- 3단계 결과 JSON 전체 (식사목록 · 대체이력 · 체크리스트 포함)
  check_result   jsonb not null default '[]',
  pending        jsonb not null default '[]',    -- 담당자 확인 대기 항목
  created_at     timestamptz not null default now(),
  unique (plan_id, revision)
);

-- 코스의 한 칸 (낮-1, 점심-1 …). 지도와 시간표가 이 표를 읽는다.
create table public.course_stops (
  id             uuid primary key default gen_random_uuid(),
  course_id      uuid not null references public.courses (id) on delete cascade,
  variant        text not null default '공통',   -- 안 (공통 / 평일안 / 토요일안)
  slot_code      text not null,                  -- 칸ID = 4단계 장면ID
  position       integer not null,
  day            smallint not null check (day in (1, 2)),
  slot           text not null check (slot in ('낮', '점심', '낮오후', '저녁', '밤', '숙박', '2일차오전')),
  place_name     text not null,
  place_id       uuid references public.places (id) on delete set null,   -- 장소가 정해지지 않았으면 null
  time_value     time,
  time_kind      text not null default '미정' check (time_kind in ('확정', '가정', '미정')),
  stay_min       integer check (stay_min >= 0),
  evidence_codes text[] not null default '{}',
  unique (course_id, variant, slot_code),
  check (time_kind <> '미정' or time_value is null)   -- 미정이면 시각을 채우지 않는다
);
create index course_stops_course_idx on public.course_stops (course_id, variant, position);

-- ───────────────────────── 홍보 ─────────────────────────
create table public.promo_drafts (
  id             uuid primary key default gen_random_uuid(),
  course_id      uuid not null references public.courses (id) on delete cascade,
  is_pre_confirm boolean not null default true,  -- 코스 확정 전에 만든 초안인지
  course_card    jsonb not null default '{}',    -- 대상문장 · 코스이름 · 한눈에 · 식사안내 · 남은경고
  data           jsonb not null,                 -- 4단계 결과 JSON 전체 (대응표 · 표현필터 · 시안 포함)
  check_result   jsonb not null default '[]',
  created_at     timestamptz not null default now()
);
create index promo_drafts_course_idx on public.promo_drafts (course_id, created_at desc);

create table public.promo_scenes (
  id         uuid primary key default gen_random_uuid(),
  promo_id   uuid not null references public.promo_drafts (id) on delete cascade,
  variant    text not null default '공통',
  slot_code  text not null,
  title      text,
  body       text,
  fact_basis jsonb,                              -- 사실 근거 (출처ID · 근거ID)
  cautions   jsonb not null default '[]',
  unique (promo_id, variant, slot_code)
);

create table public.promo_translations (
  id               uuid primary key default gen_random_uuid(),
  promo_id         uuid not null references public.promo_drafts (id) on delete cascade,
  variant          text not null default '공통',
  slot_code        text not null,
  language         text not null,
  translation      text not null,
  back_translation text,                         -- 참고용. 검토를 대신하지 않는다
  status           text not null default 'AI 초안' check (status in ('AI 초안', '검토 중', '검토 완료')),
  reviewer         text,
  reviewed_on      date,
  unique (promo_id, variant, slot_code, language),
  -- 검토 완료는 검토자와 날짜가 있어야 한다. AI 초안에는 검토자를 적지 않는다.
  check (status <> '검토 완료' or (reviewer is not null and reviewed_on is not null)),
  check (status <> 'AI 초안' or (reviewer is null and reviewed_on is null))
);

-- 내보낸 홍보물 파일 (Supabase Storage 'promo' 버킷의 경로)
create table public.promo_assets (
  id           uuid primary key default gen_random_uuid(),
  promo_id     uuid references public.promo_drafts (id) on delete cascade,
  course_id    uuid not null references public.courses (id) on delete cascade,
  kind         text not null check (kind in ('관광지도', '리플릿', '포스터', 'SNS카드뉴스', '스탬프투어북', '적용예시', '홍보영상')),
  language     text not null default '한국어',
  storage_path text not null unique,
  created_at   timestamptz not null default now()
);

-- ───────────────────────── 접근 규칙 (RLS) ─────────────────────────
-- 기획과 그 아래 기록은 만든 사람만 본다. 장소 자료는 로그인한 사람 모두 읽고, 쓰기는 서버(service_role)만 한다.
create or replace function public.owns_plan(p uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.plans where id = p and owner_id = auth.uid());
$$;

create or replace function public.owns_course(c uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.courses co join public.plans p on p.id = co.plan_id
                 where co.id = c and p.owner_id = auth.uid());
$$;

create or replace function public.owns_promo(d uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.promo_drafts pd where pd.id = d and public.owns_course(pd.course_id));
$$;

alter table public.plans              enable row level security;
alter table public.stage_results      enable row level security;
alter table public.evidence           enable row level security;
alter table public.warnings           enable row level security;
alter table public.places             enable row level security;
alter table public.travel_times       enable row level security;
alter table public.courses            enable row level security;
alter table public.course_stops       enable row level security;
alter table public.promo_drafts       enable row level security;
alter table public.promo_scenes       enable row level security;
alter table public.promo_translations enable row level security;
alter table public.promo_assets       enable row level security;

create policy plans_owner on public.plans for all to authenticated
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

create policy stage_results_owner on public.stage_results for all to authenticated
  using (public.owns_plan(plan_id)) with check (public.owns_plan(plan_id));
create policy evidence_owner on public.evidence for all to authenticated
  using (public.owns_plan(plan_id)) with check (public.owns_plan(plan_id));
create policy warnings_owner on public.warnings for all to authenticated
  using (public.owns_plan(plan_id)) with check (public.owns_plan(plan_id));
create policy courses_owner on public.courses for all to authenticated
  using (public.owns_plan(plan_id)) with check (public.owns_plan(plan_id));

create policy course_stops_owner on public.course_stops for all to authenticated
  using (public.owns_course(course_id)) with check (public.owns_course(course_id));
create policy promo_drafts_owner on public.promo_drafts for all to authenticated
  using (public.owns_course(course_id)) with check (public.owns_course(course_id));
create policy promo_assets_owner on public.promo_assets for all to authenticated
  using (public.owns_course(course_id)) with check (public.owns_course(course_id));

create policy promo_scenes_owner on public.promo_scenes for all to authenticated
  using (public.owns_promo(promo_id)) with check (public.owns_promo(promo_id));
create policy promo_translations_owner on public.promo_translations for all to authenticated
  using (public.owns_promo(promo_id)) with check (public.owns_promo(promo_id));

create policy places_read on public.places for select to authenticated using (true);
create policy travel_times_read on public.travel_times for select to authenticated using (true);

-- ───────────────────────── 파일 보관 (Storage) ─────────────────────────
-- 비공개 버킷. 경로의 첫 폴더를 사용자 id 로 둔다: promo/<auth.uid()>/<course_id>/포스터.pdf
insert into storage.buckets (id, name, public) values ('promo', 'promo', false) on conflict (id) do nothing;

create policy promo_files_owner on storage.objects for all to authenticated
  using (bucket_id = 'promo' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'promo' and (storage.foldername(name))[1] = auth.uid()::text);
