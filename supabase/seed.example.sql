-- Tiny public example seed. Safe for demos; not a production dump.
-- IDs are deterministic only so related example rows line up.

insert into public.schools (id, name, normalized_name, primary_domain, state, country)
values
  ('00000000-0000-0000-0000-000000000101', 'Arizona State University', 'arizona state university', 'asu.edu', 'AZ', 'US'),
  ('00000000-0000-0000-0000-000000000102', 'Brigham Young University', 'brigham young university', 'byu.edu', 'UT', 'US'),
  ('00000000-0000-0000-0000-000000000103', 'Columbus State Community College', 'columbus state community college', 'cscc.edu', 'OH', 'US')
on conflict (name) do nothing;

insert into public.online_discovery_runs (
  id, school_name, status, use_ai, max_pages, max_depth,
  program_page_count, course_count, missing_task_count, completed_at
)
values
  ('00000000-0000-0000-0000-000000000201', 'Arizona State University', 'completed', false, 1, 0, 1, 2, 0, now()),
  ('00000000-0000-0000-0000-000000000202', 'Brigham Young University', 'completed', false, 1, 0, 1, 2, 0, now()),
  ('00000000-0000-0000-0000-000000000203', 'Columbus State Community College', 'completed', false, 1, 0, 1, 2, 0, now())
on conflict (id) do nothing;

insert into public.online_program_pages (
  id, school_id, discovery_run_id, url, page_title, page_type,
  is_official, is_online, is_credit_bearing, is_non_degree_accessible,
  confidence, evidence, discovered_by
)
values
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000201', 'https://ulc.asu.edu/', 'ASU Universal Learner Courses', 'target_program_page', true, true, true, true, 0.95, 'Official ASU ULC page.', 'official_catalog_import'),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000202', 'https://is.byu.edu/university', 'University Courses Online | BYU Independent Study', 'target_program_page', true, true, true, true, 0.95, 'Official BYU Independent Study university page.', 'official_catalog_import'),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000203', 'https://www.cscc.edu/academics/online-learning/', 'Online Learning | Columbus State Community College', 'course_list_page', true, true, true, true, 0.90, 'Official CSCC online learning page.', 'official_catalog_import')
on conflict (id) do nothing;

insert into public.online_courses (
  school_id, program_page_id, discovery_run_id, course_code, course_title,
  credits, canonical_course_url, delivery_mode, final_status, confidence,
  is_online, is_academic_credit, is_non_degree_accessible,
  price_per_credit, price_per_course, registration_url
)
values
  ('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000201', 'HST 100', 'Early Global History', 3, 'https://courses.ulc.asu.edu/global-history-to-1500-hst-100/', 'online', 'confirmed_or_likely_available', 0.92, true, true, true, null, 425.00, 'https://ulc.asu.edu/how-to-enroll/'),
  ('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000201', 'HST 109', 'American History', 3, 'https://courses.ulc.asu.edu/united-states-to-1865-hst-109/', 'online', 'confirmed_or_likely_available', 0.92, true, true, true, null, 425.00, 'https://ulc.asu.edu/how-to-enroll/'),
  ('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000202', 'CHEM 101', 'Introductory Chemistry', 3, 'https://is.byu.edu/catalog/CHEM-101-300-002', 'online', 'confirmed_or_likely_available', 0.90, true, true, true, null, 768.00, 'https://is.byu.edu/catalog/CHEM-101-300-002'),
  ('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000202', 'CHEM 481', 'Biochemistry', 3, 'https://is.byu.edu/catalog/CHEM-481-300-001', 'online', 'confirmed_or_likely_available', 0.90, true, true, true, null, 768.00, 'https://is.byu.edu/catalog/CHEM-481-300-001'),
  ('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000203', 'ACCT 1211', 'Financial Accounting', 3, 'https://explore.cscc.edu/courses/ACCT1211', 'online', 'confirmed_or_likely_available', 0.86, true, true, true, 192.93, 578.79, 'https://selfservice.cscc.edu/Student/Student/Courses/Search?keyword=ACCT-1211'),
  ('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000203', 'CHEM 1100', 'Chemistry and Society', 5, 'https://explore.cscc.edu/courses/CHEM1100', 'online', 'confirmed_or_likely_available', 0.86, true, true, true, 192.93, 964.65, 'https://selfservice.cscc.edu/Student/Student/Courses/Search?keyword=CHEM-1100')
on conflict (school_id, course_code, canonical_course_url) do nothing;

insert into public.transfer_course_search (
  school_name, source_course_code, source_course_title,
  target_course_code, target_course_title, effective_date, confidence_level
)
values
  ('Arizona State University', 'HST 100', 'GLOBAL HISTORY TO 1500', 'HISTORY 1681', 'intentionally left blank', '20104 To Present', 'verified_by_osu_equivalency'),
  ('Arizona State University', 'HST 109', 'UNITED STATES TO 1865', 'HISTORY 1151', 'intentionally left blank', '20014 To Present', 'verified_by_osu_equivalency');
