-- supabase_setup.sql  (SQL Editor de Supabase; sin probar contra un proyecto real)
-- Orden: 1) ejecutar este archivo completo  2) importar los CSV en el orden indicado abajo.

create table escuela (
  escuela_id int primary key, nombre text not null, local_name text, state_name text);

create table departamento (
  departamento_id int primary key,
  escuela_id int not null references escuela(escuela_id),
  nombre text not null);

create table profesor (
  profesor_id int primary key,
  escuela_id int not null references escuela(escuela_id),
  departamento_id int not null references departamento(departamento_id),
  nombre text not null,
  year_since_first_review real, num_student int, star_rating real, diff_index real,
  take_again real, tag_professor text,
  tough_grader smallint, gives_good_feedback smallint, respected smallint, skip_class smallint,
  caring smallint, get_ready_to_read smallint, participation_matters smallint,
  clear_grading_criteria smallint, lecture_heavy smallint, lots_of_homework smallint,
  amazing_lectures smallint, inspirational smallint, hilarious smallint,
  accessible_outside_class smallint, extra_credit smallint, graded_by_few_things smallint,
  test_heavy smallint, group_projects smallint, so_many_papers smallint, beware_of_pop_quizzes smallint);

create table materia (
  materia_id int primary key,
  escuela_id int not null references escuela(escuela_id),
  codigo text not null);

create table lote_importacion (
  lote_id int primary key, archivo text, fecha_importacion timestamptz,
  filas_leidas int, filas_insertadas int, filas_duplicadas int, filas_rechazadas int);

create table review (
  review_id int primary key,
  fila_origen int,
  lote_id int references lote_importacion(lote_id),
  profesor_id int not null references profesor(profesor_id),
  materia_id int references materia(materia_id),
  post_date date, is_online smallint,
  student_star real, student_difficult real,
  asistencia text, para_creditos text, volveria_a_tomar text, calificacion text,
  help_useful int, help_not_useful int,
  comentario text, word_comment int,
  hash_contenido text unique);

create table modelo_version (
  version_modelo text primary key, fecha timestamptz default now(), descripcion text,
  estado text check (estado in ('en_calibracion', 'validado')),
  f1_micro real, f1_por_aspecto jsonb, n_gold int);

create table review_aspecto (
  review_aspecto_id int primary key,
  review_id int not null references review(review_id) on delete cascade,
  aspecto text not null,
  polaridad text not null check (polaridad in ('positivo', 'negativo', 'mixto_neutro')),
  evidencia text,
  version_modelo text not null);

create unique index review_aspecto_uq on review_aspecto (review_id, aspecto, version_modelo);
create index on review_aspecto (review_id);
create index on review (profesor_id);
create index on profesor (departamento_id);
create index on profesor (escuela_id);

-- Seguridad: solo lectura pública (la clave anon se ve en el navegador; sin RLS permitiría escribir).
do $$
declare t text;
begin
  foreach t in array array['escuela','departamento','profesor','materia','lote_importacion',
                           'review','modelo_version','review_aspecto']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "lectura publica" on %I for select to anon using (true)', t);
    execute format('grant select on %I to anon', t);
  end loop;
end $$;

-- Importar CSV (Table Editor > tabla > Insert > Import data from CSV), en este orden:
--   escuela, departamento, profesor, materia, lote_importacion, review
-- (review_aspecto y modelo_version se dejan vacías por ahora).
-- Verifica: select count(*) from review;  -> 19,971 con tu corrida actual.
