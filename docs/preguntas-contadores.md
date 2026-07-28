# Preguntas pendientes para el equipo contable

> Escrito para leerse tal cual en una reunión o enviarse por escrito.
> Última actualización: 2026-07-28.
> Estado del proyecto y decisiones tomadas: [`estado-y-roadmap.md`](estado-y-roadmap.md).

Estoy montando el sistema que va a causar automáticamente las facturas de compra que
descargamos de la DIAN y las va a pasar a Siigo. Ya está funcionando, pero hay cosas que
solo ustedes me pueden responder. Las puse en orden: las primeras son las que me tienen
frenado.

## 1. Credenciales de Siigo — es lo que más necesito

Para que el sistema pueda escribir en Siigo necesito las credenciales de API. Las genera
el usuario administrador así:

**Siigo Nube → menú izquierdo "Alianzas" → "Mi Credencial API"**

(Si no aparece ahí: engranaje de Configuración → "Alianzas e Integraciones" →
"Credenciales de integración a plataformas digitales".)

Necesito el **usuario API** y la **access key** completos.

Dos cosas importantes:

- **Pidan primero las credenciales de pruebas.** Siigo las entrega si las solicitan a
  soporte dando el NIT. Así probamos sin tocar la contabilidad real, y cuando todo
  funcione pasamos a producción.
- Estas credenciales son como una llave de la contabilidad de la empresa. **No me las
  manden por correo abierto ni por grupos de WhatsApp**, coordinemos algo seguro.

Necesito **una credencial por cada empresa** que vayamos a conectar.

## 2. ¿En qué comprobante quieren que queden las causaciones?

Cuando el sistema mande una factura a Siigo, tiene que quedar registrada en algún
comprobante de contabilidad. ¿Cuál usan hoy para causar compras?

**Mi sugerencia:** que creemos uno **aparte, solo para lo automático**. Así, si algo sale
mal en las primeras corridas, ustedes lo identifican de una y lo reversan sin tocar lo que
digitaron a mano.

Solo necesito el nombre; el código interno lo saco yo cuando tenga las credenciales.

## 3. Plan de cuentas — confirmar dos cuentas

Cargando el plan de cuentas de JANO encontré que hay dos cuentas de IVA descontable:

- **24081001** — Iva descontable por compras 19%
- **24081003** — Iva descontable por compras 5%

**¿Cuál debe usar el sistema por defecto?** ¿O tiene que decidirlo según el IVA que traiga
cada factura?

Para proveedores voy a usar **22050501 – Proveedores nacionales**. ¿Está bien?

Si vamos a conectar más empresas, necesito el plan de cuentas de cada una:
**Reportes → Contables → Contables → Listado de cuentas contables → Descargar Excel**

## 4. Retenciones — la pregunta más importante

Hoy el sistema solo separa el IVA. **Las retenciones todavía no las maneja**, y sin eso el
asiento queda incompleto, así que es lo próximo que voy a construir.

En el plan de cuentas ya está todo el árbol armado (`2365...` por concepto y tarifa:
honorarios 7 %, 3,5 %, 2 %, 1 %; servicios 6 %, 4 %, 3,5 %, 1 %; compras 2,5 % y 3,5 %;
arrendamientos; autorretenciones). Sé a qué cuentas van; lo que no sé es de dónde sale el
valor:

**¿La retención viene calculada en el archivo que bajamos de la DIAN, o ustedes la
calculan al causar?**

Si la calculan ustedes, necesito saber:

- ¿La empresa es **autorretenedora**?
- ¿Es **gran contribuyente**?
- ¿En qué **municipio** tributa ICA y a qué tarifa?
- ¿Cómo deciden qué tarifa aplicar: por concepto de la factura, por proveedor, por monto?

## 5. Contado vs crédito

Quería que el sistema rechazara automáticamente las facturas a crédito, pero **el Excel de
la DIAN no dice la forma de pago**.

- **¿De dónde la sacan ustedes hoy?** ¿La miran en el PDF, ya saben qué proveedores son a
  crédito, la consultan en otro lado?
- **¿De verdad hay que rechazar las de crédito, o solo marcarlas distinto?**

## 6. Acuse de recibo

**¿Qué necesitan exactamente?**

- ¿Emitir el acuse electrónico ante la DIAN o el proveedor?
- ¿O dejar registrado internamente que la factura ya se revisó y se aceptó?

Son dos cosas muy distintas en trabajo: lo primero es un desarrollo grande con firma
electrónica, lo segundo se hace en un día.

## 7. Los informes — qué quieren ver

- **¿Qué le sirve al cliente ver cada mes?** No en lenguaje contable, sino lo que le
  interesa a un dueño de negocio.
- **¿Qué cambia entre un restaurante y una constructora?** Ya hay plantilla de restaurante.
- **Cuentas por pagar a fin de mes:** ¿saldo por proveedor a una fecha, antigüedad de
  saldos, algo más?

## 8. Para saber si entran en el alcance

- **Documento soporte electrónico** ante la DIAN — ¿lo necesitan?
- **Información exógena** — ¿la arman a mano hoy? ¿cuánto tiempo les toma?

---

## Resumen de lo mínimo

1. Usuario API y access key (ojalá de pruebas primero)
2. Nombre del comprobante donde van las causaciones
3. Confirmación de las cuentas de IVA descontable y proveedores
4. **Si las retenciones vienen en el archivo de la DIAN o se calculan**
5. De dónde sacan la forma de pago
6. Qué es exactamente el acuse de recibo

Con 1, 2 y 3 queda Siigo funcionando de verdad. El punto 4 desbloquea lo siguiente.
