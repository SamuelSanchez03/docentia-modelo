-- 2) VERIFICAR (debe dar 36537 filas para v2b-roberta-base y 32944 para reglas-v0.2-lexico)
select version_modelo, count(*) filas, count(distinct review_id) comentarios, min(review_aspecto_id), max(review_aspecto_id)
from review_aspecto group by version_modelo order by version_modelo;
select version_modelo, estado, f1_micro, fecha from modelo_version order by fecha desc;
