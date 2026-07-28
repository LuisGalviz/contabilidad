# Preguntas pendientes para el equipo contable

> Escrito para leerse tal cual en una reunión o enviarse por escrito.
> Última actualización: 2026-07-28, después de probar el sistema completo con el plan de
> cuentas y las facturas reales de JANO.
> Estado del proyecto y decisiones tomadas: [`estado-y-roadmap.md`](estado-y-roadmap.md).

Ya probé el recorrido completo con datos reales: importé el plan de cuentas de JANO desde
Siigo, cargué las facturas de enero y febrero de la DIAN, el sistema aprendió a clasificar
y generó los asientos cuadrados. Funciona. Lo que sigue son las cosas que solo ustedes me
pueden responder, y algunas cambiaron después de ver los archivos reales.

## 1. Credenciales de Siigo — es lo que más necesito

Para que el sistema pueda escribir en Siigo necesito las credenciales de API. Las genera
el usuario administrador así:

**Siigo Nube → menú izquierdo "Alianzas" → "Mi Credencial API"**

(Si no aparece ahí: engranaje de Configuración → "Alianzas e Integraciones" →
"Credenciales de integración a plataformas digitales".)

Necesito el **usuario API** y la **access key** completos.

Dos cosas importantes:

- **Pidan primero las credenciales de pruebas.** Siigo las entrega si las solicitan a
  soporte dando el NIT. Así probamos sin tocar la contabilidad real.
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

## 3. IVA descontable: ¿19 % o 5 %?

Ya cargué el plan de cuentas de JANO. Para proveedores voy a usar
**22050501 – Proveedores nacionales** (confírmenme si está bien).

Para el IVA hay dos cuentas y necesito saber cuál usar:

- **24081001** — Iva descontable por compras 19 %
- **24081003** — Iva descontable por compras 5 %

**¿El sistema debe elegir según el IVA que traiga cada factura, o siempre va a la misma?**
Yo asumiría lo primero, pero prefiero que me lo confirmen.

Relacionado: en enero varias facturas vienen con **IVA en cero** (por ejemplo las de F2X).
¿Se causan simplemente sin línea de IVA, o hay algo especial que hacer con esas?

Si vamos a conectar más empresas, necesito el plan de cuentas de cada una:
**Reportes → Contables → Contables → Listado de cuentas contables → Descargar Excel**

## 4. Retenciones — ya sé que hay que calcularlas, necesito los parámetros

**Esto cambió respecto a lo que les iba a preguntar.** Revisé el archivo de la DIAN y las
columnas `Rete IVA` y `Rete Renta` vienen **en cero en las 72 facturas de enero**. Tiene
sentido: la retención la practica el comprador, no el proveedor, así que no aparece en su
factura electrónica.

O sea que **el sistema tiene que calcularlas**. Para eso necesito de ustedes:

- ¿La empresa es **autorretenedora**?
- ¿Es **gran contribuyente**?
- ¿En qué **municipio** tributa ICA y a qué tarifa?
- **¿Cómo deciden qué tarifa de retefuente aplicar?** ¿Por el concepto de la factura, por
  el tipo de proveedor, por el monto? Necesito la regla tal como la aplican hoy.
- ¿Hay **topes o cuantías mínimas** por debajo de las cuales no retienen?

Las cuentas destino ya las tienen armadas en el plan (`2365…` con honorarios al 7 %,
3,5 %, 2 % y 1 %; servicios al 6 %, 4 %, 3,5 % y 1 %; compras al 2,5 % y 3,5 %;
arrendamientos; autorretenciones). Lo que me falta es **cuándo aplicar cada una**.

> Nota técnica por si la ven: la columna que la DIAN llama `Rete ICA` en ese Excel **no es
> una retención, es la base gravable**. Lo verifiqué con los números. No la usen para
> cuadrar retenciones.

## 5. Contado vs crédito — confírmenme la equivalencia

**Esto también cambió.** Yo creía que el archivo de la DIAN no traía la forma de pago,
pero sí la trae: hay una columna **`Forma de Pago`** con valores `1` y `2`. En enero
salieron 65 facturas con `1`, 4 con `2` y 3 sin dato.

- **¿Me confirman que `1` es contado y `2` es crédito?**
- El archivo también trae **`Medio de Pago`** (transferencia, efectivo, tarjeta…).
  **¿Les sirve para algo contablemente**, o con la forma de pago basta?
- Y la pregunta de fondo: yo había planteado **rechazar automáticamente las de crédito**.
  ¿De verdad hay que rechazarlas, o basta con marcarlas y causarlas distinto?

## 6. El archivo no trae el concepto de la factura

El sistema aprende a clasificar viendo qué cuenta le asignan a cada proveedor. Pero el
Excel de la DIAN **no trae ninguna columna de concepto o descripción**, así que hoy solo
puede aprender **por proveedor**, no por lo que se compró.

Eso funciona bien cuando un proveedor siempre significa lo mismo (F2X → combustible). Pero
falla si a un mismo proveedor le compran cosas distintas.

- **¿Es común eso en la práctica?** Por ejemplo Sodimac: ¿le compran siempre lo mismo, o a
  veces materiales y a veces herramientas que van a cuentas diferentes?
- Si pasa seguido, ¿cómo lo resuelven hoy? ¿Abren el PDF de la factura?

De la respuesta depende si vale la pena que el sistema lea la representación gráfica de la
factura, que es un desarrollo grande.

## 7. Acuse de recibo

**¿Qué necesitan exactamente?**

- ¿Emitir el acuse electrónico ante la DIAN o el proveedor?
- ¿O dejar registrado internamente que la factura ya se revisó y se aceptó?

Son dos cosas muy distintas en trabajo: lo primero es un desarrollo grande con firma
electrónica, lo segundo se hace en un día.

## 8. Los informes — qué quieren ver

El sistema ya genera informes automáticos cada vez que se causa un periodo.

- **¿Qué le sirve al cliente ver cada mes?** No en lenguaje contable, sino lo que le
  interesa a un dueño de negocio.
- **¿Qué cambia entre un restaurante y una constructora?** Ya hay plantilla de restaurante.
- **Cuentas por pagar a fin de mes:** ¿saldo por proveedor a una fecha, antigüedad de
  saldos, algo más?

## 9. Para saber si entran en el alcance

- **Documento soporte electrónico** ante la DIAN — ¿lo necesitan?
- **Información exógena** — ¿la arman a mano hoy? ¿cuánto tiempo les toma?

---

## Resumen de lo mínimo

1. Usuario API y access key (ojalá de pruebas primero)
2. Nombre del comprobante donde van las causaciones
3. Cuál cuenta de IVA descontable usar, y confirmar proveedores `22050501`
4. **Parámetros de retención**: autorretenedor, gran contribuyente, municipio y tarifa de
   ICA, y la regla para elegir la tarifa de retefuente
5. Confirmar que en la DIAN `1` = contado y `2` = crédito, y qué hacer con las de crédito
6. Si un mismo proveedor suele ir a cuentas distintas

Con 1, 2 y 3 queda Siigo funcionando de verdad. El punto 4 es el que desbloquea lo
siguiente y es el más largo de responder, así que ojalá lo vayan pensando.
