# Cambios de esta entrega — 27 de octubre de 2026

Esta entrega aplica los rangos solicitados, cinco variables distintas por componente, diez opciones categóricas y truncamiento de resultados finales a tres decimales. Se conservan los protocolos JSON 1 y 2, las 100 realizaciones y los visualizadores existentes.

## Rangos de parámetros

Los extremos se incluyen, salvo la condición adicional a < b de la uniforme.

| Distribución | Parámetros permitidos | Predeterminados |
|---|---|---|
| Uniforme | 0 ≤ low < high ≤ 10 | low=0, high=10 |
| Normal | mean: [4,6]; std: [0.1,0.8] | mean=5, std=0.5 |
| Lognormal | mu: [-2,0.6]; sigma: [0.05,0.35] | mu=0, sigma=0.25 |
| Weibull | shape: [1,5]; scale: [0.1,0.8] | shape=2, scale=0.8 |
| Gamma | shape: [0.1,10]; scale: [0.01,0.3] | shape=5, scale=0.3 |
| Beta | alpha y beta: [0.1,10] | alpha=2, beta=2 |
| Exponencial | rate: [1.3,100] | rate=2 |
| Bernoulli | p: [0,1] | p=0.5 |
| Categórica | 1 a 10 valores únicos en [0,10]; probabilidades en [0,1] que sumen 1 | values=[0,1,2], probabilities=[0.2,0.3,0.5] |
| Poisson generalizada | lam: [0.1,1]; theta: [0,0.05] | lam=1, theta=0.03 |
| Poisson cero-inflada | lam: [0.1,1.5]; pi: [0,1] | lam=1, pi=0.3 |
| Logarítmica | p: [0.01,0.35] | p=0.2 |

La lognormal usa **mu (log-location)** y **sigma (log-scale)**: ln(X) ~ Normal(mu, sigma²). Se introducen directamente; no se calcula log(mu) ni log(sigma). NumPy recibe mean=mu y sigma=sigma. Las nuevas solicitudes con el antiguo campo mean de la lognormal se rechazan; el historial anterior se puede seguir consultando y la app adapta su etiqueta al mostrarlo.

Los rangos se comprueban en Android y nuevamente en el backend. No se aplica un dominio obligatorio [0,10]: los dominios opcionales del proyecto original siguen disponibles. Los rangos no son una garantía de soporte acotado para distribuciones como normal o lognormal. Beta mantiene soporte [0,1] y Bernoulli produce 0 o 1. Los componentes pueden superar 10.

## Variables por componente

- Cada expresión admite de 1 a 5 variables distintas.
- Máximo de variables definidas: 5 en 1D, 10 en 2D y 15 en 3D; nombres X1 a X15.
- X1+X1+X2 cuenta como dos variables distintas.
- Las variables compartidas conservan la misma realización entre componentes.
- No se admiten nombres duplicados, referencias desconocidas, variables definidas sin uso ni una sexta variable distinta dentro de un componente.
- Ejemplo completo: examples/experiment-15-variables.json.

## Resultados y persistencia

Se evalúan las expresiones con los valores base completos; únicamente los componentes finales se truncan a tres decimales, hacia cero. Ejemplos: 1.2349 → 1.234, -1.2349 → -1.234, 1.001 → 1.001, -0.0009 → 0.0. La conversión usa Decimal sobre la representación decimal para evitar errores de multiplicación binaria.

Se conservan exclusivamente 100, 200 o 300 resultados finales planos, en orden por realización: x0,y0,z0,x1,y1,z1,... No se guardan sorteos de variables base ni resultados intermedios. Se mantiene la definición del experimento y sus metadatos. La barrera de persistencia comprueba longitud, números finitos, límite de magnitud y truncamiento. Los resultados son números, no cadenas: 1.2 y 1.200 representan el mismo valor.

## Validación previa al cálculo

Antes de adquirir una reserva o iniciar el proceso se exige:

1. Un único token Bearer Firebase válido, no revocado, de inicio de sesión con Google.
2. Content-Type application/json, opcionalmente charset=utf-8; cuerpo UTF-8 sin compresión.
3. Hasta 32 KiB, también comprobados durante la lectura por bloques. Content-Length, si existe, debe ser válido y coincidir con los bytes recibidos.
4. JSON bien formado, sin claves duplicadas, NaN/Infinity, campos extra, tipos incorrectos ni booleanos usados como números.
5. Esquema completo de protocolo 1 o 2; 100 realizaciones; título de 1 a 80 caracteres; de 1 a 3 componentes; parámetros y referencias válidos.
6. AST de hasta 127 nodos y profundidad 20 por componente, operadores autorizados, al menos una variable y como máximo cinco distintas.
7. Una única Idempotency-Key con el formato UUID esperado.

Después se mantienen la cuota de 25 intentos diarios por usuario, máximo 10 experimentos guardados, exclusión mutua por cuenta entre instancias, idempotencia y reserva con caducidad. El lanzador y el proceso hijo vuelven a validar el esquema antes de calcular. El proceso conserva su plazo máximo de 60 segundos. Un error no guarda resultados parciales y libera la reserva.

La autenticación e IAM de Google y las reglas Firestore existentes se conservan. Este cambio valida entradas y controla el cálculo; no agrega App Check ni modifica el despliegue o los permisos de una cuenta real.

## Preparación y comprobación

El archivo mobile/src/config.ts incluido contiene configured=false y cadenas vacías. Ejecuta la configuración original con tu google-services.json real antes de usar Google Login y la API.

Desde backend:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Desde mobile:

```sh
npm ci
npm run typecheck
npm test
```

Consulta VERIFICACION.md para los resultados y límites de las pruebas de esta entrega. El PDF incluido es el manual original de instalación; para estos cambios de comportamiento prevalecen este documento y Manual.md.
