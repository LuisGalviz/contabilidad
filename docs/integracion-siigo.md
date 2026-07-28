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

## Definiciones pendientes del equipo contable

1. **Tipo de comprobante destino** (`SIIGO_JOURNAL_DOCUMENT_ID`): id del comprobante de
   contabilidad donde deben quedar las causaciones. Se consulta con
   `GET /v1/document-types?type=CC` una vez haya credenciales.
2. Confirmar que el plan de cuentas usado en ContaFlow (PUC) coincide con los códigos
   contables activos en Siigo — el comprobante se rechaza si una cuenta no existe o no
   admite movimientos.

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
