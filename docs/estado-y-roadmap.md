# Estado del proyecto y hoja de ruta

> Última actualización: **2026-07-28**.
> Preguntas abiertas al equipo contable: [`preguntas-contadores.md`](preguntas-contadores.md).
> Detalle técnico de Siigo: [`integracion-siigo.md`](integracion-siigo.md).

## Qué es esto

ContaFlow causa automáticamente las facturas de compra que hoy los auxiliares contables
digitan una por una en Siigo. El flujo es:

```
Excel de la DIAN (documentos recibidos)
  → ContaFlow lee, deduplica por CUFE y sugiere cuenta PUC
  → el contador revisa y confirma (el sistema aprende del proveedor)
  → causación
  → Siigo
  → informes automáticos del periodo
```

## Terminado y en producción

| Funcionalidad | Notas |
|---|---|
| Lectura del Excel de la DIAN | Alias por columna, tolerante a renombres. CUFE como llave de deduplicación |
| Notas crédito | Se detectan al leer e **invierten el asiento completo** |
| Clasificación asistida que aprende | Reglas por proveedor + palabras clave. Tras 3 confirmaciones humanas y confianza ≥0,85 auto-causa. Al confirmar, propaga a las demás pendientes del mismo proveedor |
| Plan de cuentas **por empresa** | `puc_accounts` con único `(client_id, code)`. Un cliente nuevo nace **vacío**: el plan se importa desde Siigo |
| Importar plan real desde Siigo | Excel de Siigo. Omite cuentas de agrupación, nunca borra, avisa referencias rotas |
| Causación sin códigos quemados | Cada empresa define qué cuenta cumple cada rol (`client_account_settings`) |
| Validaciones | No se puede clasificar contra una cuenta ajena al plan del cliente, ni causar contra una cuenta muerta |
| Integración Siigo | `POST /v1/journals`, funcional en **modo mock**. Falta credenciales |
| Informes | Por sector (restaurante / genérico), Excel y PDF, generados tras causar |

## Construido pero sin activar

**Modo `/v1/purchases`** (`SIIGO_DOCUMENT_MODE=purchases`). En vez de mandar el asiento
armado, manda la factura y **Siigo deriva impuestos y cuenta por pagar**. Es el único de
los dos endpoints que acepta `retentions` y forma de pago, así que es el camino natural
para no implementar nosotros la lógica tributaria colombiana.

No activado porque falta `SIIGO_PAYMENT_TYPE_ID`, que los proveedores existan en Siigo por
NIT, y **validar el contrato contra la API real** (los campos salieron de la documentación
pública, no de una llamada verificada).

## Pendiente

Por orden sugerido:

1. **Retenciones** — el hueco contable más grande. Bloqueado por la pregunta 4 del
   documento de preguntas: ¿el valor viene en el Excel de la DIAN o se calcula?
   Las cuentas destino ya existen en el plan real (`2365xx` por concepto y tarifa).
2. **Siigo en producción** — solo falta credenciales + tipo de comprobante.
3. **Contado vs crédito** — bloqueado: el Excel de la DIAN no trae forma de pago.
4. **Cuentas por pagar a fin de mes** — reporte de corte reusando la infra de informes.
5. **Lectura de la representación gráfica** (PDF de la factura con IA) — resolvería de
   paso la forma de pago y el detalle de retenciones.
6. **Acuse de recibo** — alcance sin definir.
7. **Documento soporte electrónico** e **información exógena** — fuera de alcance por
   ahora; requieren integración firmada con la DIAN. Ojo: Siigo expone
   `/v1/purchase-support-documents`, así que podría ser integración y no desarrollo.
8. **Más plantillas de informe** (constructora) y revisar que la narrativa esté en
   lenguaje llano.

## Decisiones tomadas y por qué

- **El plan de cuentas es por cliente, no global.** Cada empresa tiene el suyo, igual que
  en Siigo, donde el catálogo es por compañía. Antes era una tabla única y dos empresas
  chocaban en la llave primaria.
- **Importación manual del plan, no por API.** Siigo **no expone** el catálogo de cuentas
  contables por API. Se verificó contra su documentación pública. Cuidado con
  `/v1/account-groups`: son grupos de inventario, no el PUC.
- **Nada de códigos contables quemados.** La causación nombra el *rol* (proveedores, IVA
  descontable) y el código sale de la configuración del cliente. Se eligió tabla de roles
  en vez de columnas fijas para que agregar retenciones no requiera otra migración.
- **Un cliente nuevo nace sin plan de cuentas.** Se sembraba el subconjunto PUC del
  decreto (`2205`, `240801`, `5135`…), pero ninguno de esos códigos existe en el plan real
  de Siigo como cuenta de movimiento: allá son agrupaciones y el comprobante se rechaza.
  El seed mostraba cuentas que parecían usables y no lo eran, y dejaba huérfanas las
  clasificaciones hechas contra ellas al importar el plan real. La única fuente del plan es
  la importación desde Siigo.
- **Fallar antes que adivinar.** Si falta configuración o la cuenta no existe, la causación
  se niega a correr. Un asiento contra la cuenta equivocada es peor que no causar.
- **Al reimportar el plan nunca se borra.** Las cuentas que desaparecen quedan inactivas:
  hay reglas aprendidas y facturas ya causadas apuntando a esos códigos.
- **`journals` sigue siendo el modo por defecto** hasta poder validar `purchases` contra la
  API real.

## Trampas conocidas del entorno

- **`alembic revision --autogenerate` no es confiable aquí.** La BD local fue creada con
  `create_all()` y luego stampeada, así que migraciones intermedias nunca corrieron en
  ella y el autogenerate inventa migraciones duplicadas que pasan en local y tumban el
  despliegue. **Validar toda migración nueva contra una BD vacía:**

  ```bash
  docker exec v2-postgres-1 psql -U contaflow -d postgres -c "CREATE DATABASE migtest;"
  docker exec -e DATABASE_URL="postgresql+asyncpg://contaflow:contaflow@postgres:5432/migtest" \
    v2-backend-1 python -m alembic upgrade head
  ```

- **`git push` a `master` despliega a producción** (ECS + Vercel) y corre las migraciones
  contra RDS.
- **No hay Python local.** Tests, lint y tipos corren dentro de Docker:
  `docker exec v2-backend-1 python -m pytest tests --no-cov -q`
- La imagen de backend puede quedar desactualizada respecto a `pyproject.toml`
  (le faltaba `aiosqlite`, necesario para los tests de integración). `docker compose build
  backend` lo resuelve.
- Los archivos `.xlsx` están gitignorados: son datos reales de clientes.
