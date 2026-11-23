-- 배포판(Vercel)이 로그인 없이 기획을 만들고 읽을 수 있게 한다. 첫 파일(…_init.sql) 다음에 실행한다. 여러 번 실행해도 된다.
--
-- 주의: 아래 규칙은 anon 키를 가진 누구나 이 네 표를 읽고 쓸 수 있게 연다. 지금 배포판은 서버만 키를 갖고 있지만
-- anon 키는 원래 공개를 전제로 한 키다. 로그인을 붙이거나 Vercel에 SUPABASE_SERVICE_ROLE_KEY 를 넣게 되면
-- 이 파일의 anon 규칙 네 개를 지우면 된다 (서버는 service_role 키가 있으면 그것을 먼저 쓴다).

alter table public.plans alter column owner_id drop not null;            -- 로그인 없이 만든 기획은 주인이 없다
alter table public.plans add column if not exists agent_state jsonb;     -- 에이전트 엔진이 요청 사이에 이어 가는 상태

-- 첫 파일을 예전 판으로 실행한 경우 빠져 있는 열 (이미 있으면 건너뛴다)
alter table public.plans add column if not exists summary        text;
alter table public.plans add column if not exists left_for_human jsonb not null default '[]';
alter table public.plans add column if not exists unresolved     jsonb not null default '[]';
alter table public.plans add column if not exists activity       jsonb not null default '[]';
alter table public.plans add column if not exists total_seconds  numeric;

grant usage on schema public to anon;
grant select, insert, update on public.plans to anon;
grant select, insert on public.stage_results, public.courses, public.course_stops to anon;

drop policy if exists plans_public on public.plans;
create policy plans_public on public.plans for all to anon using (owner_id is null) with check (owner_id is null);

drop policy if exists stage_results_public on public.stage_results;
create policy stage_results_public on public.stage_results for all to anon
  using (exists (select 1 from public.plans p where p.id = plan_id and p.owner_id is null))
  with check (exists (select 1 from public.plans p where p.id = plan_id and p.owner_id is null));

drop policy if exists courses_public on public.courses;
create policy courses_public on public.courses for all to anon
  using (exists (select 1 from public.plans p where p.id = plan_id and p.owner_id is null))
  with check (exists (select 1 from public.plans p where p.id = plan_id and p.owner_id is null));

drop policy if exists course_stops_public on public.course_stops;
create policy course_stops_public on public.course_stops for all to anon
  using (exists (select 1 from public.courses c join public.plans p on p.id = c.plan_id where c.id = course_id and p.owner_id is null))
  with check (exists (select 1 from public.courses c join public.plans p on p.id = c.plan_id where c.id = course_id and p.owner_id is null));

notify pgrst, 'reload schema';   -- API가 새 열을 바로 알아보게 한다
