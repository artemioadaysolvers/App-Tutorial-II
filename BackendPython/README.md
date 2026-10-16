# Mensajes — backend Python

API en **Python 3.12 + FastAPI**, login con **Google** y documentos JSON en **Azure Cosmos DB for NoSQL**. El proyecto está preparado para un repositorio independiente. Se entrega por separado de la app Android.

## Empieza aquí

1. [Configurar Google](docs/01-GOOGLE.md).
2. [Crear Azure y activar actualizaciones desde GitHub](docs/02-GITHUB-AZURE.md).
3. Copiar la URL HTTPS del backend y el cliente OAuth Web al `.env` de la app y compilarla.
4. [Probar el sistema completo](docs/03-PRUEBA-COMPLETA.md).

**La configuración inicial de Google, Azure y GitHub es necesaria. Los ZIP no contienen claves reales y no crean recursos al descomprimirlos.**

## Qué incluye

- API con verificación del ID token de Google en el servidor; sesiones firmadas de 60 minutos.
- Tres mensajes obligatorios, de hasta 2000 caracteres cada uno. El usuario y la fecha se obtienen en el servidor.
- Reintentos con `requestId`: el mismo envío no se duplica dentro de la partición de un usuario.
- Azure Cosmos DB real; no hay base SQL ni almacenamiento local que aparente un guardado en la nube.
- `Dockerfile` con usuario sin privilegios, `compose.yaml`, versiones de dependencias fijadas y pruebas automatizadas.
- `.github/workflows/deploy-azure.yaml`: en cada push a `main`, prueba, construye y publica Docker, actualiza App Service y comprueba la versión desplegada y Cosmos DB.
- `infra/main.bicep` y su plantilla ARM compilada `infra/main.json`, más scripts de configuración inicial.
- Compatibilidad de despliegue con App Service clásico y con `sitecontainers` (sidecar), como en el repositorio que diste de ejemplo.

## Arrancar con Docker

Instala Docker Desktop. Desde esta carpeta:

```powershell
Copy-Item .env.example .env
# Edita .env con los valores de Google y Cosmos DB; genera JWT_SECRET aleatorio.
docker compose up --build
```

Abre `http://localhost:8080/docs`. `GET /health` comprueba el proceso; `GET /ready` comprueba Cosmos DB y la clave de partición. La configuración de ejemplo se rechaza hasta reemplazar sus valores.

Para desarrollo sin Docker, con Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

No se necesita una clave secreta de Google para este flujo: se valida el ID token contra el cliente OAuth Web y las claves públicas de Google. `JWT_SECRET` y `COSMOS_KEY` pertenecen solo al servidor.

## API

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/v1/auth/google` | Recibe `{ "idToken": "..." }`; devuelve sesión, caducidad y usuario. |
| GET | `/api/v1/me` | Devuelve el usuario de la sesión. Requiere `Authorization: Bearer ...`. |
| POST | `/api/v1/messages` | Guarda los tres mensajes. Requiere sesión. |
| GET | `/health` | Proceso activo y SHA de la imagen ejecutada. |
| GET | `/ready` | Acceso al contenedor Cosmos y partición correcta. |

Ejemplo del cuerpo de un envío:

```json
{
  "requestId": "a6da9499-f7c4-445e-a98f-0fa0d6a146a7",
  "mensaje1": "Hola",
  "mensaje2": "Segundo mensaje",
  "mensaje3": "Gracias"
}
```

Documento guardado en `MensajesDB` → `mensajes`, con clave de partición **`/userId`**:

```json
{
  "id": "a6da9499-f7c4-445e-a98f-0fa0d6a146a7",
  "userId": "identificador-sub-verificado-por-google",
  "mensaje1": "Hola",
  "mensaje2": "Segundo mensaje",
  "mensaje3": "Gracias",
  "createdAt": "2026-10-15T18:30:00Z"
}
```

## Pruebas y límites

```powershell
python -m pytest -q
python -m ruff check app tests
```

Las pruebas sustituyen Google y Cosmos por dobles controlados, para verificar la lógica sin cuentas ni claves. La comprobación real requiere configurar ambas cuentas y enviar desde Android. Los datos viven fuera de Docker, por lo que actualizar el backend no los elimina. El cierre de sesión borra la sesión del teléfono; un token ya emitido puede seguir siendo válido hasta su vencimiento. No hay una ruta pública de historial.

App Service B1, Container Registry y Cosmos DB pueden generar cargos. La plantilla usa Cosmos serverless; no presupone que tengas nivel gratuito. Antes de abrir el servicio a muchos usuarios, configura límites de consumo y protección contra abuso en Azure.

## Referencias

- [Repositorio usado como referencia de despliegue](https://github.com/artemioadaysolvers/Pagina-Web-Completa).
- [Verificar Google en el servidor](https://developers.google.com/identity/sign-in/web/backend-auth).
- [SDK Python de Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/quickstart-python).
- [Docker y FastAPI](https://fastapi.tiangolo.com/deployment/docker/).
- [GitHub Actions y contenedores en App Service](https://learn.microsoft.com/en-us/azure/app-service/deploy-container-github-action).
