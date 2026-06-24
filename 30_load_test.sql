-- =====================================================================
-- 30_load_test.sql  -- QUERY DE CARGA (prueba de auto-scaling del warehouse)
-- Query intencionalmente pesada (~45-60s c/u): hash SHA-256 por fila sobre
-- ~194M filas (orders x range(1200)) + shuffle/agg. Cada TAREA del job
-- ejecuta estas 3 sentencias en serie (~2.5 min). Lanzando muchas tareas
-- en paralelo se supera la capacidad de 1 cluster Medium (~10 queries
-- concurrentes), los queries se ENCOLAN y el warehouse levanta el 2do
-- cluster (max_num_clusters = 2).
--
-- :salt  = parametro por-tarea (evita el result cache entre tareas)
-- =====================================================================

SELECT substr(h,1,2) p, count(*) c, max(h) m
FROM (
  SELECT sha2(concat(a.`order`, '-', cast(b.id AS string), '-', :salt, '-A'), 256) AS h
  FROM workspace.`on`.orders a CROSS JOIN range(1200) b
) GROUP BY 1 ORDER BY c DESC;

SELECT substr(h,1,2) p, count(*) c, max(h) m
FROM (
  SELECT sha2(concat(a.`order`, '-', cast(b.id AS string), '-', :salt, '-B'), 256) AS h
  FROM workspace.`on`.orders a CROSS JOIN range(1200) b
) GROUP BY 1 ORDER BY c DESC;

SELECT substr(h,1,2) p, count(*) c, max(h) m
FROM (
  SELECT sha2(concat(a.`order`, '-', cast(b.id AS string), '-', :salt, '-C'), 256) AS h
  FROM workspace.`on`.orders a CROSS JOIN range(1200) b
) GROUP BY 1 ORDER BY c DESC;
