# Android / azar.

Consulta `../docs/CAMBIOS.md`, `../docs/Manual.md` y `../README.md` para preparar Google Cloud y generar el APK.

```powershell
npm ci
npm run configure -- https://TU-SERVICIO.run.app
npm run typecheck
npm test
```

Antes de `configure`, agrega tu archivo real `android/app/google-services.json` para el paquete `com.montecarlolab`, con Google Auth activado y cliente Web OAuth tipo 3. Sin él se puede compilar la pantalla de configuración, pero el login no está disponible.

Abre `android` en Android Studio con JDK 17. SDK 36, Build Tools 36.0.0, NDK 27.1.12297006 y CMake 3.22.1. Genera un APK release con tu propia firma mediante el asistente de Android Studio. Un release firmado contiene el bundle JS y funciona sin Metro. La variante debug requiere `npm start`.
