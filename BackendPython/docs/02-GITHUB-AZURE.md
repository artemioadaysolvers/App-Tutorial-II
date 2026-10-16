# 2. Azure y actualización automática desde GitHub

El ZIP contiene un proyecto nuevo. Usa un **repositorio nuevo** para este backend. El repositorio de calculadora se consultó como ejemplo y no fue modificado. Si deseas integrar ambos servicios, revisa y combina sus rutas y workflows conscientemente.

## A. Crear recursos nuevos

Instala Azure CLI y PowerShell 7. Necesitas una suscripción y permisos para crear recursos y asignar roles. Los servicios pueden generar cargos; el script crea App Service **B1**, ACR **Basic** y Cosmos DB **serverless**. Selecciona una región que admita estos servicios y revisa sus precios.

En PowerShell, desde la raíz del backend:

```powershell
az login
az account set --subscription TU-ID-DE-SUSCRIPCION
.\scripts\crear-azure.ps1 -Prefix mensajes123 -ResourceGroup rg-mensajes-nuevo -Location eastus -GoogleWebClientId TU-CLIENTE-WEB.apps.googleusercontent.com
```

El grupo debe ser nuevo para evitar modificar recursos anteriores. El script genera un secreto de sesión aleatorio, crea la base `MensajesDB` y el contenedor `mensajes` con partición `/userId`, configura App Service y autoriza su identidad para descargar imágenes de ACR. Las claves de Cosmos se guardan como configuración de App Service; no aparecen en las salidas. Si falta el compilador Bicep, ejecuta `az bicep install` o usa `infra/main.json`, la plantilla ARM equivalente incluida.

El script utiliza `infra/main.json`, la plantilla ARM compilada incluida, e imprime `AZURE_RESOURCE_GROUP`, `AZURE_WEBAPP_NAME`, `ACR_NAME` y la URL final. Si modificas `main.bicep`, regenera `main.json` con `az bicep build --file infra/main.bicep`. Hasta el primer despliegue, el contenedor es una imagen inicial y **la API todavía no estará lista**.

## B. Conectar GitHub con Azure una vez

1. Crea tu repositorio nuevo, por ejemplo `Mensajes-Backend`, con rama `main`.
2. Desde la raíz del backend ejecuta, reemplazando los nombres con los del paso anterior:

```powershell
.\scripts\configurar-github.ps1 -Repository TU-USUARIO/Mensajes-Backend -ResourceGroup rg-mensajes-nuevo -AcrName NOMBRE-ACR -WebAppName NOMBRE-WEBAPP
```

Este script crea una aplicación de Microsoft Entra, una identidad federada para `repo:TU-USUARIO/Mensajes-Backend:ref:refs/heads/main`, permiso **AcrPush** en ACR y **Website Contributor** en esa Web App. Si tu organización limita crear aplicaciones o asignar roles, un administrador debe configurar esos elementos. Ejecuta el script una sola vez: repetirlo crea otra identidad.

3. En tu repositorio → **Settings → Secrets and variables → Actions**, añade los valores impresos:

| Tipo | Nombre |
|---|---|
| Secret | `AZURE_CLIENT_ID` |
| Secret | `AZURE_TENANT_ID` |
| Secret | `AZURE_SUBSCRIPTION_ID` |
| Variable | `ACR_NAME` |
| Variable | `AZURE_RESOURCE_GROUP` |
| Variable | `AZURE_WEBAPP_NAME` |
| Variable | `AZURE_DEPLOYMENT_MODE` = `classic` |

No crees un GitHub Environment llamado production para este workflow sin adaptar también el subject de federación. El workflow incluido usa la rama `main`, sin Environment.

## C. Subir el contenido

**Sube los archivos que están dentro de `BackendPython`, no el ZIP como un único archivo y no la carpeta contenedora adicional.** La raíz del repositorio debe contener `Dockerfile`, `app/`, `requirements.txt` y `.github/`.

Con Git instalado, desde esa carpeta:

```powershell
git init -b main
git add .
git commit -m "Backend Python con Google y Cosmos DB"
git remote add origin https://github.com/TU-USUARIO/Mensajes-Backend.git
git push -u origin main
```

No fuerces un push sobre un repositorio con contenido. Si lo creaste con README, clónalo primero y copia dentro estos archivos. `.gitignore` excluye `.env`; comprueba que no hayas subido claves. Conserva la carpeta `.github`, aunque aparezca oculta en alguna vista.

## D. Qué ocurre en cada actualización

Cada push a `main` ejecuta:

1. Pruebas de Python y construcción/verificación de Docker.
2. Acceso a Azure mediante OIDC, sin contraseña de Azure en GitHub.
3. Publicación en ACR con la etiqueta **SHA del commit**.
4. Cambio de imagen y reinicio de App Service.
5. Comprobación de que `/health` informa ese SHA y de que `/ready` accede a Cosmos DB.

Una pull request ejecuta pruebas sin desplegar. Si una prueba falla, el despliegue no empieza. El despliegue directo sobre B1 puede tener una interrupción breve; la base de datos permanece fuera del contenedor. El workflow no vuelve automáticamente a una imagen anterior si la nueva versión no arranca: informa un fallo en Actions para revisarlo.

En GitHub → **Actions**, abre el workflow para ver su resultado. La URL no cambia entre versiones. La app móvil no se recompila por cambios del servidor mientras se conserve la URL y el contrato de la API.

## E. Si reutilizas recursos existentes o tu App Service usa sidecar

No ejecutes `crear-azure.ps1` sobre recursos existentes. Crea un contenedor Cosmos nuevo con partición **`/userId`**; el contenedor de la calculadora con `/tipo` no sirve para este proyecto.

El workflow y el script de conexión asumen que ACR y App Service están en el grupo indicado por `AZURE_RESOURCE_GROUP`. Si están en grupos diferentes, adapta los argumentos `--resource-group` de ACR al grupo correspondiente.

En App Service configura: `GOOGLE_WEB_CLIENT_ID`, `JWT_SECRET` aleatorio de 32 caracteres o más, `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE=MensajesDB`, `COSMOS_CONTAINER=mensajes`. Para modo clásico añade `WEBSITES_PORT=8080`. Activa HTTPS Only y usa `/ready` como health check. Habilita identidad administrada y asígnale **AcrPull** sobre ACR. Para ACR con permisos ABAC, utiliza el rol equivalente de lectura/escritura de repositorios en lugar de AcrPull/AcrPush.

Para `sitecontainers`, como en el ejemplo:

- `AZURE_DEPLOYMENT_MODE=sidecar`.
- `AZURE_CONTAINER_NAME` = nombre real del contenedor principal.
- En ese contenedor, habilita la identidad administrada para descargar desde ACR y configura el puerto destino **8080**.

El workflow utiliza `az webapp sitecontainers update` en ese modo. Resuelve el hostname real de ACR mediante Azure; no supone que siempre sea `NOMBRE.azurecr.io`.

## Problemas frecuentes

- **OIDC no encuentra credencial:** comprueba usuario/repositorio, mayúsculas y rama `main` del subject.
- **ACR unauthorized:** revisa los roles de la identidad de GitHub y de App Service; espera su propagación.
- **Contenedor no arranca:** revisa logs, variables, puerto 8080 y que `JWT_SECRET` no sea el valor de ejemplo.
- **`/ready` devuelve 503:** revisa cuenta, claves, base, contenedor, partición `/userId` y reglas de red de Cosmos DB.
- **Cambiaste `JWT_SECRET`:** las sesiones anteriores caducan y los usuarios deben volver a entrar.

Fuentes: [despliegue de contenedores](https://learn.microsoft.com/en-us/azure/app-service/deploy-container-github-action), [GitHub OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect), [sitecontainers](https://learn.microsoft.com/en-us/cli/azure/webapp/sitecontainers?view=azure-cli-latest).
