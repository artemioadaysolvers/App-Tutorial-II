# Verificación de la entrega

Fecha de la entrega: 15 de octubre de 2026.

- Python 3.12: instalación de las dependencias y comprobación de importaciones correctas.
- Pruebas automatizadas: **22 aprobadas**. Verifican Google simulado, sesiones inválidas o vencidas, identidad del usuario, campos vacíos o demasiado largos, reintentos sin duplicados, conflictos y fallos de almacenamiento.
- Revisión de Python con Ruff: correcta.
- Sintaxis de Docker Compose y workflows YAML: correcta.
- Workflows de GitHub: actionlint, correcto.
- Scripts PowerShell: analizados sin errores de sintaxis.
- Infraestructura: Bicep compilado correctamente a `infra/main.json`.

Las pruebas de Google y Cosmos DB usan dobles controlados. No se utilizaron credenciales reales, no se crearon recursos de Azure y no se modificó el repositorio de referencia. Docker no está disponible en este entorno; el workflow incluido construye y comprueba el contenedor antes de desplegar. La activación real requiere seguir las guías y verificar `/ready` y un envío desde Android.

La ejecución de pruebas emitió un aviso de deprecación de Starlette sobre su adaptador HTTPX; las 22 pruebas terminaron correctamente. No afecta al servidor Uvicorn ni al cliente móvil.
