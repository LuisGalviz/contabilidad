# Integración con Siigo Nube

ContaFlow puede enviar las **causaciones de facturas de compra** a Siigo Nube como
**comprobantes de contabilidad** (journals, `POST /v1/journals`). La integración está
detrás del puerto `AccountingSystemPort`: cuando está desactivada, las causaciones se
registran solo en el libro interno de ContaFlow, exactamente como antes.

## Modos de operación

| Configuración | Comportamiento |
|---|---|
| `SIIGO_ENABLED=false` (default) | Solo libro interno de ContaFlow. |
| `SIIGO_ENABLED=true` + `SIIGO_USE_MOCK=true` | Simula Siigo en memoria — desarrollo sin credenciales. Las causaciones quedan `pushed_external` con referencia `siigo:MOCK-n`. |
| `SIIGO_ENABLED=true` + `SIIGO_USE_MOCK=false` | Envío real al API de Siigo. Requiere credenciales. |

## Variables de entorno

```bash
SIIGO_ENABLED=true
SIIGO_USE_MOCK=false
SIIGO_API_URL=https://api.siigo.com
SIIGO_USERNAME=usuario-api@empresa.com   # generado por Siigo Nube
SIIGO_ACCESS_KEY=...                     # generado por Siigo Nube
SIIGO_PARTNER_ID=ContaFlow               # nombre de la app (header obligatorio)
SIIGO_JOURNAL_DOCUMENT_ID=0              # id del tipo de comprobante (ver abajo)
```

## Cómo obtener las credenciales (equipo contable)

Solo el usuario **administrador/dueño de la cuenta de Siigo Nube** puede generarlas:

1. Iniciar sesión en Siigo Nube.
2. Menú izquierdo **"Alianzas"** → botón **"Mi Credencial API"**
   (o: engranaje **Configuración** → **"Alianzas e Integraciones"** →
   **"Credenciales de integración a plataformas digitales (Siigo API)"**).
3. Copiar el **usuario API** y la **access key** completos y entregarlos por un canal
   seguro (no por correo abierto ni chats grupales).

Notas:

- Estas credenciales equivalen a una llave de acceso a la contabilidad de la empresa:
  tratarlas como confidenciales.
- Se necesita una credencial **por cada compañía** de Siigo que se quiera conectar.
- Generarlas no afecta el funcionamiento normal de Siigo ni a los usuarios existentes.
- Siigo también entrega **credenciales de un ambiente de pruebas** si se solicitan a sus
  líneas de atención indicando el NIT registrado — útiles antes de salir a producción.

## Destino del documento: `journals` vs `purchases`

`SIIGO_DOCUMENT_MODE` elige a qué endpoint va la causación:

| Modo | Endpoint | Quién decide la contabilización |
|---|---|---|
| `journals` (por defecto) | `POST /v1/journals` | ContaFlow arma el asiento completo |
| `purchases` | `POST /v1/purchases` | Siigo deriva impuestos y cuenta por pagar |

`purchases` es el destino natural de una factura de compra y el que abre la puerta
a **retenciones** (`retentions`) y **forma de pago** (`payments[].due_date`) sin que
ContaFlow tenga que implementar la lógica tributaria colombiana. En modo `purchases`
solo se envían las líneas de gasto/costo como ítems `type: "Account"`; el IVA y la
cuenta por pagar se excluyen para no duplicar lo que Siigo calcula.

**Todavía no se puede activar.** Falta:

1. `SIIGO_PAYMENT_TYPE_ID` — el medio de pago (`GET /v1/payment-types`).
2. Que el **proveedor exista en Siigo** por NIT antes de enviar; hoy no se crea
   automáticamente.
3. Validar el contrato contra la API real: los campos se tomaron de la documentación
   pública, no de una llamada verificada.

## Plan de cuentas: importación manual (no hay API)

Siigo **no expone el catálogo de cuentas contables por su API**. Revisado contra la
documentación pública: existen `/v1/products`, `/customers`, `/invoices`, `/purchases`,
`/credit-notes`, `/vouchers`, `/payment-receipts`, `/journals`, `/quotations` y
`/purchase-support-documents`, pero ninguno de plan de cuentas. Cuidado con
`/v1/account-groups`: son grupos de **inventario**, no el PUC.

La vía es el Excel que el contador descarga desde
`Reportes → Contables → Contables → Listado de cuentas contables → Descargar Excel`
y carga en ContaFlow desde **Plan de cuentas** en el menú lateral.

El plan es **por cliente**: cada empresa tiene el suyo, igual que en Siigo, donde el
catálogo es por compañía. Al importar:

- Las cuentas nuevas se crean y las existentes se actualizan (nombre, clase, estado).
- Las que ya no aparecen en el archivo se marcan **inactivas, nunca se borran**: hay
  reglas de clasificación aprendidas y facturas ya causadas apuntando a esos códigos.
- Se avisa si alguna regla aprendida o algún rol de la causación quedó apuntando a una
  cuenta que desapareció.

Los alias de columna del lector están en
`src/infrastructure/purchases/puc/siigo_chart_importer.py` (`SIIGO_ALIASES`); si Siigo
cambia un encabezado, es una línea. Todavía **no se ha validado contra un archivo real**
exportado de Siigo — los alias son una apuesta razonable hasta tener uno.

## Definiciones pendientes del equipo contable

1. **Tipo de comprobante destino** (`SIIGO_JOURNAL_DOCUMENT_ID`): id del comprobante de
   contabilidad donde deben quedar las causaciones. Se consulta con
   `GET /v1/document-types?type=CC` una vez haya credenciales.
2. Exportar el **Listado de cuentas contables** de cada compañía e importarlo, y señalar
   qué cuenta usan para **proveedores** e **IVA descontable** (se configura en la misma
   pantalla). Sin eso la causación no corre: no hay códigos por defecto quemados.

## Detalles técnicos

- Código en `backend/src/infrastructure/siigo/`:
  - `auth.py` — token JWT de `POST /auth`, cacheado ~24 h con renovación anticipada.
  - `client.py` — cliente HTTP (`httpx`) con header `Partner-Id` y reintentos
    exponenciales (`tenacity`) ante 401/429/5xx y errores de red.
  - `mock_client.py` — simulador en memoria para desarrollo.
  - `mapper.py` — `CausationEntry` → payload de journal (débitos/créditos por cuenta).
  - `accounting_system.py` — implementación de `AccountingSystemPort`; guarda la
    referencia de Siigo en `causation_entries.external_reference` (`siigo:<número>`)
    y marca la causación `pushed_external` (o `failed` si Siigo rechaza).
- La selección interna/Siigo/mock ocurre en
  `backend/src/infrastructure/accounting/factory.py` (`build_accounting_system`),
  el único sitio de inyección — casos de uso y dominio no cambian.
- Tests: `backend/tests/unit/test_siigo_integration.py` y
  `backend/tests/unit/test_accounting_factory.py`.

## Checklist de salida a producción

1. Recibir credenciales (idealmente primero las del ambiente de pruebas).
2. Consultar `GET /v1/document-types?type=CC` y fijar `SIIGO_JOURNAL_DOCUMENT_ID`.
3. Configurar las variables en el entorno del backend (ECS task definition / `.env`).
4. `SIIGO_USE_MOCK=false` y prueba de humo con una causación real de bajo valor.
5. Verificar en Siigo que el comprobante llegó al tipo de documento correcto.
