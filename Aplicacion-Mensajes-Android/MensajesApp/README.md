# Mensajes — app Android

Proyecto **React Native + Expo + TypeScript** con acceso mediante Google, formulario de **Mensaje 1, Mensaje 2 y Mensaje 3**, envío a la API Python, confirmación de guardado y cierre de sesión. Incluye el código Android generado para abrirlo en Android Studio después de instalar las dependencias.

## Antes de compilar

Primero configura y despliega el proyecto del ZIP **BackendPython-GitHub.zip** siguiendo sus guías. Necesitas:

- URL HTTPS de la API Python, por ejemplo `https://TU-BACKEND.azurewebsites.net`.
- ID de cliente OAuth **Web** de Google, el mismo que utiliza el backend.
- Cliente OAuth **Android** en el mismo proyecto de Google, con paquete y SHA-1 correctos.

La app es nueva y separada de la calculadora Kotlin que adjuntaste. El paquete predeterminado es `com.artemio.mensajes`. No se necesita Firebase. Las claves de Cosmos DB y el secreto de sesión permanecen en el backend.

## 1. Instalar y configurar

Instala Node.js 24 LTS y Android Studio con su SDK y JDK compatibles. Desde esta carpeta en PowerShell:

```powershell
npm ci
Copy-Item .env.example .env
```

Edita `.env`:

```dotenv
EXPO_PUBLIC_API_URL=https://TU-BACKEND.azurewebsites.net
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=TU-CLIENTE-WEB.apps.googleusercontent.com
APP_ANDROID_PACKAGE=com.artemio.mensajes
```

La URL no lleva `/api/v1` al final. Los valores `EXPO_PUBLIC_` se incorporan al código durante la compilación: son identificadores públicos, nunca claves privadas. Después de cambiarlos, vuelve a compilar.

## 2. Generar/sincronizar el proyecto Android

```powershell
npm run prebuild:android
```

La carpeta `android/` ya viene generada como punto de partida; vuelve a sincronizar después de cambiar el paquete o la configuración. Instala los paquetes con `npm ci` antes de abrir Android Studio. Abre **la carpeta `android/`**, deja que Gradle sincronice y selecciona un emulador con Google Play o un teléfono con Google Play Services.

Para ejecutar en desarrollo:

```powershell
npm run android
```

Esta compilación de desarrollo utiliza Metro. Mantén su proceso abierto. **Expo Go no admite esta integración nativa de Google**: utiliza el proyecto Android o un APK propio.

## 3. Registrar Google y compilar un APK de prueba autónomo

Desde `android/`, obtén la firma de prueba y regístrala en tu cliente OAuth Android de Google Cloud:

```powershell
.\gradlew.bat :app:signingReport
```

El nombre del paquete debe coincidir exactamente. Sigue también `docs/01-GOOGLE.md` del backend para configurar la audiencia y los usuarios de prueba de Google.

Para generar un APK autónomo de prueba, con el `.env` completo:

```powershell
.\gradlew.bat :app:assembleRelease
```

Archivo esperado: `android/app/build/outputs/apk/release/app-release.apk`. Esta variante local usa la **firma de depuración incluida**, solo para pruebas. Esa es la SHA-1 que debes registrar para este APK. Para distribuir en Google Play configura tu propia firma de publicación o utiliza EAS Build, que gestiona las credenciales; conserva siempre tu clave de publicación.

## 4. Alternativa: compilar con EAS

1. Crea tu cuenta en [expo.dev](https://expo.dev/) y un proyecto llamado Mensajes desde su panel.
2. Copia el UUID del proyecto al valor `EAS_PROJECT_ID` de tu `.env`.
3. En EAS → **Environment variables**, configura `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` y `EAS_PROJECT_ID` para los entornos que uses (`preview` y `production`). Si cambias el paquete, añade también `APP_ANDROID_PACKAGE` y sincroniza Android antes de compilar.
4. Ejecuta:

```powershell
npx eas-cli@latest login
$env:EAS_PROJECT_ID = 'UUID-DE-TU-PROYECTO-EXPO'
npx eas-cli@latest build --platform android --profile preview
```

El valor de `EAS_PROJECT_ID` en la terminal permite que EAS identifique el proyecto incluso si su CLI no carga el `.env` local al resolver la configuración. Usa el UUID real. Descarga el APK al terminar y registra en Google la SHA-1 de las credenciales de esa compilación. Puedes consultarlas con `npx eas-cli@latest credentials --platform android`. Registrar la firma no exige recompilar si no cambiaste los valores del proyecto.

Para un AAB destinado a Google Play:

```powershell
npx eas-cli@latest build --platform android --profile production
```

Los servicios de EAS tienen sus propios límites y planes. La carpeta Android se entrega como proyecto nativo; los cambios en `app.config.ts` se aplican al volver a ejecutar prebuild, no automáticamente durante un build que ya usa esa carpeta.

## Funcionamiento

1. Google entrega un ID token al acceder. La app lo intercambia con el backend por una sesión firmada de 60 minutos.
2. La sesión se guarda con Expo SecureStore y se valida al abrir la app.
3. Cada campo exige entre 1 y 2000 caracteres. El backend vuelve a validar.
4. La app conserva los campos si falla el envío y usa el mismo identificador al reintentar sin editar.
5. Solo limpia el formulario después de que el servidor confirme el guardado.
6. Si vence la sesión, solicita entrar de nuevo. El borrador se conserva en memoria para la misma cuenta mientras la app siga abierta. Al cerrar sesión manualmente o cambiar de cuenta se limpia.

## Verificación local

```powershell
npm run typecheck
npm test
npm run check:bundle
```

`check:bundle` verifica el empaquetado Android de JavaScript/Hermes; **no genera un APK ni prueba Google o Azure reales**. Para ello hay que compilar, registrar la firma y seguir la guía de prueba completa del backend.

## Contenido

- `App.tsx`: pantallas de acceso y formulario, estados y sesión.
- `src/`: cliente de API, Google, validación y estilos.
- `android/`: proyecto nativo generado; sin SDK, dependencias descargadas ni APK.
- `package-lock.json`: dependencias fijadas para `npm ci`.
- `.env.example`, `app.config.ts`, `eas.json`: configuración y perfiles de compilación.
- `.github/workflows/check-app.yaml`: comprobación del proyecto al subirlo a GitHub, si decides versionarlo allí.

Fuentes: [Google con Expo](https://docs.expo.dev/guides/google-authentication/), [compilar Android](https://docs.expo.dev/build-reference/apk/), [SecureStore](https://docs.expo.dev/versions/latest/sdk/securestore/).
