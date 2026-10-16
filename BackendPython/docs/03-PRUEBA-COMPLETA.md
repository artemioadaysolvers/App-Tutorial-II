# 3. Verificar el sistema completo

1. Comprueba `https://TU-BACKEND/health`: debe responder `status: ok` y el SHA del commit desplegado.
2. Comprueba `https://TU-BACKEND/ready`: debe responder `status: ready`. Si falla, la app no podrá guardar.
3. Configura y compila la app siguiendo su README. La URL debe ser HTTPS. Registra en Google la SHA-1 de la firma del APK instalado.
4. Instala el APK en Android con Google Play Services. Pulsa el botón de Google y elige una cuenta autorizada.
5. Completa Mensaje 1, Mensaje 2 y Mensaje 3 y pulsa **Enviar mensajes**. Solo aparecerá confirmación si Cosmos DB confirmó el guardado.
6. En Azure Portal → Cosmos DB → Data Explorer → `MensajesDB` → `mensajes` → Items, abre el documento. Comprueba los tres campos, `userId` y `createdAt` en UTC.
7. Envía con un campo vacío: la app debe pedir completarlo. Corta la conexión antes de enviar: debe mostrar un error y conservar el texto.
8. Si una solicitud se guardó y se perdió la respuesta, reintentar sin editar conserva el `requestId` y devuelve el mismo registro.
9. Cierra sesión y prueba otra cuenta: no debe recuperar el borrador de la anterior. Al vencer una sesión, se solicita entrar de nuevo. Un borrador se conserva en memoria para la misma cuenta mientras la app siga abierta; no se almacena en disco.
10. Cambia código del backend y haz push a `main`. Espera que Actions termine y comprueba que `/health` cambió al nuevo SHA. Los documentos anteriores deben seguir en Cosmos DB.

La validación local automatizada no sustituye esta prueba: requiere tus recursos reales y un APK firmado.
