-- DESHACER (solo si algo salió mal): la página vuelve sola a reglas-v0.2-lexico
delete from modelo_version where version_modelo = 'v2b-roberta-base';
delete from review_aspecto where version_modelo = 'v2b-roberta-base';
