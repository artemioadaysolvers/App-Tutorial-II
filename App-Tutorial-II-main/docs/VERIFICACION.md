# Verificación de esta entrega

Fecha: 27 de octubre de 2026.

## Comprobaciones ejecutadas

- Backend: **41 pruebas ejecutadas: 40 aprobadas y 1 integración Firestore omitida** por no disponer de emulador.
- Entorno backend: CPython 3.12.14, NumPy 2.2.6 y dependencias exactas de requirements-dev.txt / requirements.lock.
- Límites inferior y superior de todos los parámetros; rechazo de tipos incorrectos, booleanos, NaN/Infinity y números fuera de rango.
- Concordancia de los rangos de parámetros entre el frontend y el backend.
- Lognormal mu/sigma, log-location/log-scale, contrastada con muestras NumPy de semilla fija.
- Categórica: diez valores admitidos; once, valores duplicados, fuera de [0,10] o probabilidades inválidas rechazados.
- Hasta cinco variables distintas por componente y quince en 3D. Reutilización de variables y conservación de muestras compartidas. Rechazo de una sexta referencia distinta, nombres inválidos o variables sin uso.
- Truncamiento hacia cero de positivos y negativos, casos como 1.001 y -0.0009, idempotencia del truncamiento y evaluación con valores intermedios sin truncar.
- API: autenticación verificada con dobles de prueba, proveedor Google y check_revoked=True. JSON UTF-8, Content-Type, Content-Length, límite por bloques, campos y claves duplicados, formato y rangos antes de admitir o calcular. Entradas inválidas no consumen cupo ni inician el lanzador.
- API con **proceso hijo real**: experimento 3D de quince variables, 300 resultados finales truncados, persistencia con el Store real sobre transporte simulado y reintento idempotente sin una segunda ejecución.
- Persistencia sin resultados de variables base ni listas intermedias. Validación final en la barrera de escritura; error sin guardado parcial y liberación de reserva.
- Cuotas por usuario, separación de usuarios, bloqueo distribuido, caducidad, idempotencia y terminación forzosa por tiempo conservados y comprobados.
- Frontend: **TypeScript 5.9.3 --noEmit aprobado**. Suite npm test aprobada: parser y precedencia, referencias X1..X15 y máximo cinco distintas, doce distribuciones, rangos, categórica e histogramas 1D/2D/3D.
- Prettier 2.8.8: comprobación de estilo aprobada en los archivos móviles modificados.
- Todos los ejemplos JSON incluidos ejecutados con semilla 42; 100/200/300 valores finitos y truncados según sus componentes.
- ZIP final revisado: integridad CRC, archivos completos, sin dependencias instaladas, cachés, credenciales reales ni resultados temporales.

## Alcance de las pruebas

No se ejecutó el emulador Firestore ni se accedió a una base real. Las pruebas habituales ejecutan la lógica real de Store mediante transporte simulado; no sustituyen una prueba del SDK contra tu proyecto.

No se realizó un despliegue en Google Cloud, inicio de sesión Google real, compilación de APK ni ejecución en teléfono/emulador Android. Se conservan los archivos nativos y de despliegue del ZIP original.

No se ejecutó Docker. Su Dockerfile conserva Python 3.12.10; las pruebas locales usaron Python 3.12.14.

El ZIP conserva el PDF del manual original de instalación; los rangos y reglas vigentes están en CAMBIOS.md y Manual.md. Incluye config.ts sin credenciales (configured=false); debes ejecutar el paso de configuración original con tu proyecto Google antes de usar la aplicación conectada.
