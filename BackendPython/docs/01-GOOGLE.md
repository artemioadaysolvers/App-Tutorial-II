# 1. Configurar el acceso con Google

Todo debe estar en el mismo proyecto de Google Cloud. Necesitas dos tipos de cliente OAuth: **Web**, que identifica al backend, y **Android**, que identifica la app y su firma.

1. Abre [Google Cloud Console](https://console.cloud.google.com/) y crea o selecciona un proyecto.
2. En **Google Auth Platform**, configura la información de la aplicación, correo de soporte y audiencia. Si la aplicación es externa y está en modo de prueba, añade los correos que podrán probarla a **Test users / Usuarios de prueba**.
3. En **Clients / Clientes**, crea un cliente OAuth de tipo **Web application / Aplicación web**. Copia su **Client ID**, terminado en `.apps.googleusercontent.com`.
4. Usa exactamente ese ID en:
   - Backend: `GOOGLE_WEB_CLIENT_ID`.
   - App: `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`.
5. Crea otro cliente OAuth de tipo **Android**, con el paquete `com.artemio.mensajes` (o el que hayas elegido) y la huella **SHA-1 del certificado que firma el APK**.
6. Obtén la SHA-1 local después de generar el proyecto Android. En PowerShell:

```powershell
Set-Location android
.\gradlew.bat :app:signingReport
```

Registra la firma usada para probar. Si usas EAS Build, consulta sus credenciales con `npx eas-cli@latest credentials --platform android` y registra esa SHA-1. Para una versión distribuida por Google Play, registra también la firma de **Play App Signing**. Firmas diferentes pueden necesitar clientes Android adicionales.

El client ID Android no se copia al `.env`: Google lo relaciona por paquete y firma. El ID de tipo Web sí se configura tanto en la app como en el backend. No pongas un client secret en el teléfono. Este flujo no requiere Firebase ni permisos sobre Drive.

Si aparece `DEVELOPER_ERROR` o código 10, comprueba: paquete exacto, SHA-1 del APK instalado, ambos clientes en el mismo proyecto y uso del cliente de tipo Web en `.env`. Si Google indica acceso bloqueado en modo de prueba, añade el correo a usuarios de prueba. Tras cambiar el `.env` de la app, vuelve a compilar.

La app utiliza la librería gratuita `@react-native-google-signin/google-signin`. Su integración clásica sigue funcionando y utiliza el SDK Android legado; Google recomienda migrar a Credential Manager para proyectos que lo requieran. No se utiliza ninguna función de pago.

Fuentes: [Expo](https://docs.expo.dev/guides/google-authentication/), [configuración de la librería](https://react-native-google-signin.github.io/docs/setting-up/expo), [verificación de identidad](https://developers.google.com/identity/sign-in/web/backend-auth).
