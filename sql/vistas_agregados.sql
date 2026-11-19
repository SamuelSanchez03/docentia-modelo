-- sql/vistas_agregados.sql  (SQL Editor de Supabase; se puede ejecutar varias veces)
-- Agregados para las vistas Directivo y Coordinador: el navegador descarga conteos
-- por profesor × año × modalidad en lugar de las 19,971 reviews y las 36,537 filas de review_aspecto.
-- Se guardan SUMAS y CONTEOS, no medias: así la página puede juntar años, modalidades, departamentos o la
-- escuela entera sin promediar promedios. Las reglas A1–A5 se calculan en js/alertas_logica.js.
-- security_invoker = true: la vista respeta el RLS de las tablas (solo lectura pública).

-- Versión activa del modelo = la más reciente de modelo_version (mismo criterio que js/datos.js).
create or replace view v_modelo_activo with (security_invoker = true) as
  select version_modelo, estado, f1_micro
  from modelo_version order by fecha desc limit 1;

-- 1) Indicadores por profesor × año × modalidad.
--    anio es null para las reviews sin fecha; is_online es 0/1.
create or replace view v_agg_profesor_anio with (security_invoker = true) as
with con_aspecto as (
  select distinct ra.review_id
  from review_aspecto ra
  where ra.version_modelo = (select version_modelo from v_modelo_activo)
)
select
  p.escuela_id,
  p.departamento_id,
  r.profesor_id,
  extract(year from r.post_date)::int                                             as anio,
  r.is_online,
  count(*)::int                                                                   as n,
  count(r.student_star)::int                                                      as n_star,
  sum(r.student_star)::float8                                                     as suma_star,
  sum(r.student_star * r.student_star)::float8                                    as suma_star2,
  count(r.student_difficult)::int                                                 as n_dif,
  sum(r.student_difficult)::float8                                                as suma_dif,
  count(*) filter (where r.student_star <= 2)::int                                as n_star_bajo,     -- A3
  count(*) filter (where r.student_star >= 4)::int                                as n_star_alto,     -- A3
  count(*) filter (where r.volveria_a_tomar in ('Yes', 'No'))::int                as n_volveria_resp, -- §3.4
  count(*) filter (where r.volveria_a_tomar = 'Yes')::int                         as n_volveria_si,
  -- texto válido: mismo criterio que esTextoValido() (vacío y «No Comments» no cuentan)
  count(*) filter (where coalesce(trim(r.comentario), '') <> ''
    and lower(regexp_replace(trim(r.comentario), '^[.! ]+|[.! ]+$', '', 'g'))
        not in ('no comments', 'no comment', 'n/a', 'na'))::int                   as n_comentarios,
  count(ca.review_id)::int                                                        as n_con_aspecto,   -- A4
  -- A5: calificación reportada = letra o WD (las demás respuestas, como «Not» o «INC», no son nota)
  count(*) filter (where r.calificacion in ('A+','A','A-','B+','B','B-','C+','C','C-','D+','D','D-','F','WD'))::int
                                                                                  as n_calif,
  count(r.student_star) filter (where r.calificacion in ('D+','D','D-','F','WD'))::int as n_calif_baja,
  sum(r.student_star) filter (where r.calificacion in ('D+','D','D-','F','WD'))::float8 as suma_star_calif_baja,
  count(r.student_star) filter (where r.calificacion in ('A+','A','A-'))::int     as n_calif_alta,
  sum(r.student_star) filter (where r.calificacion in ('A+','A','A-'))::float8    as suma_star_calif_alta
from review r
join profesor p on p.profesor_id = r.profesor_id
left join con_aspecto ca on ca.review_id = r.review_id
group by p.escuela_id, p.departamento_id, r.profesor_id, extract(year from r.post_date)::int, r.is_online;

-- 2) Menciones de aspecto por profesor × año × modalidad × aspecto × polaridad (modelo activo).
create or replace view v_agg_aspecto_anio with (security_invoker = true) as
select
  p.escuela_id,
  p.departamento_id,
  r.profesor_id,
  extract(year from r.post_date)::int as anio,
  r.is_online,
  ra.aspecto,
  ra.polaridad,
  count(*)::int as n
from review_aspecto ra
join review r   on r.review_id = ra.review_id
join profesor p on p.profesor_id = r.profesor_id
where ra.version_modelo = (select version_modelo from v_modelo_activo)
group by p.escuela_id, p.departamento_id, r.profesor_id, extract(year from r.post_date)::int, r.is_online,
         ra.aspecto, ra.polaridad;

-- 3) Escuelas con su volumen (para ordenar el selector por número de evaluaciones).
create or replace view v_escuela_resumen with (security_invoker = true) as
select e.escuela_id, e.nombre,
       count(r.review_id)::int             as n_reviews,
       count(distinct p.profesor_id)::int  as n_profesores
from escuela e
join profesor p on p.escuela_id = e.escuela_id
left join review r on r.profesor_id = p.profesor_id
group by e.escuela_id, e.nombre;

grant select on v_modelo_activo, v_agg_profesor_anio, v_agg_aspecto_anio, v_escuela_resumen to anon;

-- Verificación rápida (deben coincidir con las tablas):
--   select sum(n) from v_agg_profesor_anio;            -- 19971
--   select sum(n) from v_agg_aspecto_anio;             -- 36537
--   select sum(n_reviews) from v_escuela_resumen;      -- 19971
