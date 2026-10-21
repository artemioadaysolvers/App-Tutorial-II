# Verificación de la entrega

Fecha: 20 de octubre de 2026. Ampliación 1D/2D/3D y máximo 3 variables base por simulación.

## Comprobado

- Dependencias npm instaladas y package-lock.json incluido. TypeScript aprobado.
- Pruebas frontend aprobadas: parser, precedencia, rechazo de expresiones arbitrarias, las 12 distribuciones e histogramas conjuntos 1D/2D/3D de frecuencias relativas, datos constantes, límites de intervalos y conservación de dependencia.
- Backend: 24 pruebas aprobadas con Python 3.12.14 y NumPy 2.2.6; 1 integración Firestore omitida por falta de emulador. Se verifica el máximo global de 3 variables para cada dimensionalidad, rechazo de X4/X10, exactamente 100/200/300 números y componentes compartiendo las mismas realizaciones.
- API y lógica real de Store con transporte simulado: 10 guardados, 25 intentos por día UTC, borrado sin devolución de cupo, cambio de fecha, una reserva por cuenta, admisiones concurrentes, caducidad y bloqueo de propietarios antiguos, liberación tras fallos, reintentos guardados sin recálculo ni cupo extra y separación de usuarios.
- Persistencia plana de los resultados y definición AST como texto JSON para no superar el límite de anidamiento de Firestore. No se guardan sorteos intermedios de las variables base.
- Medias de las 12 distribuciones comprobadas con 100.000 muestras y varianza de Poisson generalizada.
- Cálculo que excede su plazo de prueba: proceso terminado, sin hijos activos ni guardado parcial.
- Ejemplos JSON 1D/2D/3D ejecutados: 100/200/300 resultados finitos.
- requirements.lock resuelto para CPython 3.12 Linux x86_64: todos los wheels descargados.
- Manual de 22 páginas generado, renderizado y revisado visualmente.

## Android

Compilación final release ARM64 completada con éxito (BUILD SUCCESSFUL en 5 min 44 s; 219 tareas: 13 ejecutadas y 206 actualizadas). APK unsigned de 20,116,027 bytes. Fuentes comprobadas idénticas a las del ZIP, incluido el límite global de 3 variables. Se verificó el empaquetado, incluyendo el nuevo View Kotlin de histogramas conjuntos, C++, Java, Kotlin, Hermes y lint. Comando: `gradlew.bat :app:assembleRelease -PreactNativeArchitectures=arm64-v8a --no-daemon --max-workers=2`.

Google Services procesó un google-services.json sintético de validación, sin credenciales reales. configure.mjs se comprobó con esa configuración sintética y una URL de prueba. El ZIP conserva configured=false y no incluye ese JSON: debes configurar tu proyecto real.

Android fija Kotlin 2.4.0 y su classpath explícito para Firebase Auth 25/Firebase BoM 35. En Windows se usó una ruta corta para evitar el límite de 260 caracteres de Ninja; extrae en C:\dev\MonteCarlo como indica el manual. Advertencias de dependencias y métricas no impidieron construir el APK unsigned. El ZIP contiene fuentes y no incluye el APK de validación: debes generar y firmar tu APK con tu configuración.

No se ejecutó la app ni se inspeccionaron los gráficos en un teléfono o emulador. La comprobación nativa es de compilación y empaquetado; las pruebas de frecuencias y componentes se ejecutaron por separado.

## Requiere tu proyecto y tus claves

No se crearon cuentas, desplegaron servicios ni utilizaron credenciales reales de Google del usuario. No se probó Google Login real ni persistencia en Firestore real. Sigue las pruebas de aceptación de los capítulos 10 y 22 con tu proyecto.

La integración opcional tests/test_firestore.py usa el SDK real entre clientes para comprobar una única admisión y la cuota diaria. Solo se activa con FIRESTORE_EMULATOR_HOST y exige localhost o 127.0.0.1; elimina sus datos temporales al finalizar. La prueba habitual usa transporte simulado; no sustituye la comprobación contra el emulador.

Docker fija Python 3.12.10 y NumPy 2.2.6. Docker no se ejecutó en este equipo; las pruebas locales usan Python 3.12.14 con las mismas dependencias. Descargar wheels Linux no sustituye ejecutar el contenedor.

El ZIP excluye node_modules, SDK, cachés, credenciales de Google y claves de release. Incluye Gradle Wrapper y la clave debug pública de desarrollo del template. Release se firma con tu propia clave desde Android Studio.

No se recibió el documento de referencia visual mencionado por el usuario. Se implementan histogramas conjuntos nativos funcionales; no se afirma que repliquen figuras de un documento no disponible.
