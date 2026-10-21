# azar. / Monte Carlo Lab

Aplicación Android nativa con React Native 0.85.3 + TypeScript. Sin Expo ni WebView. Backend Python 3.12.10 + NumPy 2.2.6 en Docker. Firebase Authentication (Google) y Cloud Firestore en Google Cloud. El manual PDF incluye cada paso, comandos y resolución de errores.

Android fija Kotlin 2.4.0 explícitamente para compilar el SDK Firebase Auth 25 incluido en Firebase BoM 35 de React Native Firebase 27. Android Studio descarga esa versión al sincronizar; no hay que instalar Kotlin por separado.

## Inicio

1. Lee `docs/Manual_Android_Google_Cloud.pdf`.
2. Extrae este proyecto en una ruta corta, por ejemplo `C:\dev\MonteCarlo`.
3. Instala Node 22.11 o superior (recomendado Node 24 LTS), JDK 17, Android Studio, SDK 36, Build Tools 36.0.0 y NDK 27.1.12297006.
4. En `mobile`, ejecuta `npm ci`.
5. Registra `com.montecarlolab` en Firebase; activa Google, agrega SHA-1 y SHA-256 del certificado, crea Firestore nativo y coloca TU `google-services.json` en `mobile/android/app/`.
6. Despliega reglas/índices de Firestore (`firebase deploy --only firestore --project TU_PROJECT_ID`) y backend (`bash scripts/deploy.sh TU_PROJECT_ID` en Cloud Shell).
7. En `mobile`, ejecuta `npm run configure -- https://TU-SERVICIO.run.app`.
8. Abre `mobile/android` en Android Studio. Sincroniza, crea tu clave de firma y usa Generate Signed App Bundle / APK > APK > release.

La primera instalación descarga dependencias desde Internet. El ZIP incluye fuentes, lockfile npm y Gradle Wrapper, no SDK, node_modules ni credenciales. Sin configuración la app compila y muestra instrucciones; el login requiere tu proyecto real de Google.

## Comprobaciones

```powershell
cd mobile
npm ci
npm run typecheck
npm test
cd ../backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Python local recomendado 3.12; Docker fija 3.12.10. Para comprobar el kernel dentro de Docker: `docker build -t montecarlo-api .` y `docker run --rm montecarlo-api python -c "from app.engine import simulate; print('NumPy listo')"`. Las pruebas detalladas de backend se ejecutan con `docker run --rm -v "${PWD}/tests:/srv/tests:ro" montecarlo-api sh -c "python -m unittest discover -s tests -p test_engine.py -v"`.

## Contrato

- `POST /v1/experiments`: cuerpo como `examples/experiment.json`, `Authorization: Bearer FIREBASE_ID_TOKEN`, `Idempotency-Key: UUID`.
- `GET /v1/experiments`: tabla sin muestras; `GET /v1/experiments/{uuid}`: detalle con resultados.
- `DELETE /v1/experiments/{uuid}`: borra permanentemente en Firestore. `GET /health`: público.
- 1 a 3 variables base independientes compartidas entre 1, 2 o 3 componentes. 100 realizaciones conjuntas exactas: 100, 200 o 300 números finales. Máximo 10 experimentos guardados y 25 escenarios admitidos por día UTC y UID; transacciones Firestore entre instancias.
- JSON <= 32 KiB, esquema cerrado, nombres X1...X3, título <=80, AST <=127 nodos y profundidad <=20. No se usa eval ni ejecución de código.
- AST: `{ "const": 2 }`, `{ "var": "X1" }`, `{ "op": "add", "args": [...] }`. Binarios add/sub/mul/div/pow; unarios neg/abs/sqrt/log/exp/sin/cos. Potencia asociativa a derecha; `-X1^2` = `-(X1^2)`.
- Dominio opcional `{min,max}` inclusivo: muestreo por rechazo de la distribución condicionada. No es clipping ni cambio de escala. Intervalos con masa muy pequeña o nula fallan después de un presupuesto de intentos; no guardan resultados parciales.
- 60 s de reloj para el proceso de simulación, incluida su inicialización. Se termina el proceso al vencer; la red/autenticación/guardado añaden tiempo (HTTP 90 s).
- Solo se guardan resultados finales en una lista plana por filas: x0,y0,z0,x1,y1,z1,..., más definición, dimensiones, fecha, color e ID; ninguna muestra individual de las variables. El color se elige al crear y se conserva al consultar.
- Histograma 1...50 particiones iguales, barras = conteo/100. Suma 1. Último intervalo cerrado; los demás [a,b). Si todos los resultados son iguales se amplía el eje para dibujar.

## Distribuciones

Uniforme: low<high. Normal: mean libre, std>0. LogNormal: mean y sigma del logaritmo, sigma>0. Weibull: shape,scale>0. Gamma: shape,scale>0. Beta: alpha,beta>0. Exponencial: rate>0, es continua. Bernoulli: p en [0,1]. Categórica: hasta 50 valores numéricos únicos y probabilidades que suman 1. Poisson cero-inflada: lam>0, pi en [0,1]. Logarítmica: serie logarítmica NumPy, p en (0,1).

Poisson generalizada implementada con NumPy mediante ramificación Poisson, variante Consul-Jain: `P(K=k)=lambda*(lambda+theta*k)^(k-1)*exp(-lambda-theta*k)/k!`, k>=0 (P(0)=exp(-lambda)). Rango soportado `0<lambda<=100`, `0<=theta<=0.9`. Media lambda/(1-theta), varianza lambda/(1-theta)^3. No incluye dispersión negativa. Con theta=0 se reduce a Poisson. Sin SciPy, SymPy o pandas en simulación.

## Seguridad y despliegue

Firebase Admin valida firma, emisor, audiencia, vencimiento y revocación; acepta únicamente proveedor Google. UID solo desde el token. La cuenta de Cloud Run necesita datastore.user y firebaseauth.viewer. Las reglas deniegan accesos directos desde clientes; Admin usa IAM. El servicio Run es accesible en HTTP público, pero cada endpoint de datos exige token Firebase. No introduzcas claves privadas en la app.

Firestore guarda la definición como `spec_json`, un texto JSON, para respetar el [límite de profundidad de mapas y arreglos](https://firebase.google.com/docs/firestore/quotas). La API la reconstruye y devuelve como objeto `spec`; el AST conserva su profundidad máxima de 20. Los resultados son una lista plana de 100/200/300 números; Firestore no permite arreglos anidados. dimensions indica cómo reconstruir los cien vectores. Docker instala el snapshot completo de `backend/requirements.lock`; `requirements.txt` enumera las dependencias directas.

No se ha configurado ni desplegado ningún proyecto de Google por ti. Cloud Run, Cloud Build, Artifact Registry y Firestore pueden requerir facturación. Usa un proyecto propio con las APIs activadas. No registres tokens ni muestras en logs. Antes de publicar comercialmente, adapta identidad, iconos y política de privacidad.

## Diseño

Paleta papel, verde tinta y terracota; tipografía Android `monospace`, estilo máquina de escribir. No hay una referencia visual adjunta de conversaciones anteriores: se usa una interpretación de ese estilo. Histograma 1D con Views de React Native. Histogramas 2D/3D con un View Android propio en Kotlin y android.graphics.Canvas: barras conjuntas 2D (altura = frecuencia relativa), voxels 3D (intensidad = frecuencia relativa), giro y cortes de Z. Sin navegador embebido, Three.js ni WebView. No se adjuntó el documento visual mencionado, por lo que no se afirma una reproducción de sus figuras.

## Vectores, bloqueo y cupo diario (ampliación)

La app envía protocolo 2: `expressions: [AST_X, AST_Y, AST_Z]` con 1 a 3 elementos y `samples: 100`. Ejemplos en `examples/experiment-1d.json`, `experiment-2d.json`, `experiment-3d.json`. El protocolo 1 con `expression` sigue siendo compatible para experimentos existentes. Las variables X1...X3 se muestrean una vez por realización y se comparten entre componentes: `(X1, 2*X1)` conserva esa dependencia. Cada AST admite 127 nodos, profundidad 20 y debe contener alguna variable definida. El límite de 3 variables es para todo el escenario, no por componente.

Cada simulación vectorial cuenta como UN escenario. Un intento válido admitido consume un cupo incluso si el cálculo falla o excede 60s. Rechazos de formato, autenticación, cuenta ocupada, cuota y capacidad no consumen cupos. Repetir una clave ya guardada y el mismo contenido devuelve el resultado sin recalcular ni cobrar otro cupo. Borrar no devuelve cupo; el contador se reinicia a las 00:00 UTC (no según el reloj del teléfono). `GET /v1/usage` autenticado devuelve used, remaining, limit, day_utc, resets_at y running.

`Store.begin` reserva la cuenta y aumenta el contador en UNA transacción. Una segunda simulación o eliminación con reserva activa recibe 429, aunque llegue de otro dispositivo o instancia. No depende del estado busy del frontend. Las consultas de lista, detalle y uso siguen permitidas. La compuerta local limita además a un cálculo por instancia. La reserva vence a los 120s si cae el servidor; el cálculo dura máximo 60s, su presupuesto se reduce si la admisión se demora. El token de reserva impide guardar o liberar una reserva ajena. Guardado y liberación ocurren juntos en la transacción. Los fallos liberan la reserva; si la red impide limpiarla, vence automáticamente. Las reglas prohíben cambiar contadores directamente desde clientes.

Particiones configurables por eje: 1D 1...50, 2D 1...12, 3D 1...8. Cada celda conjunta vale conteo/100; todas suman 1. El último intervalo incluye el máximo. Los cortes Z conservan el denominador 100 y por eso pueden sumar menos de 1; no son una distribución condicionada renormalizada. La tabla muestra los intervalos de todas las celdas ocupadas; las demás valen cero. Cambiar particiones, cortes o giro no consulta ni escribe la base de datos y no consume escenarios.

Referencias de implementación: [transacciones Firestore](https://firebase.google.com/docs/firestore/manage-data/transactions), [Views nativas de React Native](https://reactnative.dev/docs/legacy/native-components-android) y [dibujo Android Canvas](https://developer.android.com/develop/ui/views/layout/custom-views/custom-drawing).
