import logging
from typing import Annotated

from azure.core.exceptions import AzureError
from fastapi import Depends, FastAPI, HTTPException

from app.config import Settings, get_settings
from app.models import GoogleLogin, MessageDocument, MessageInput, Session, User
from app.security import current_user, issue_session, verify_google_token
from app.storage import CosmosStore, get_store

logger = logging.getLogger("mensajes")
app = FastAPI(title="Mensajes API", version="1.0.0", description="Google + Azure Cosmos DB NoSQL")


@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index():
    return {"service": "Mensajes API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]):
    return {"status": "ok", "release": settings.release_sha}


@app.get("/ready")
def ready(store: Annotated[CosmosStore, Depends(get_store)]):
    try:
        store.ready()
    except (AzureError, RuntimeError):
        raise HTTPException(503, "Almacenamiento no disponible") from None
    return {"status": "ready"}


@app.post("/api/v1/auth/google", response_model=Session)
def google_login(payload: GoogleLogin, settings: Annotated[Settings, Depends(get_settings)]):
    return issue_session(verify_google_token(payload.idToken, settings), settings)


@app.get("/api/v1/me", response_model=User)
def me(user: Annotated[User, Depends(current_user)]):
    return user


@app.post("/api/v1/messages", response_model=MessageDocument, status_code=201)
def save_message(
    payload: MessageInput,
    user: Annotated[User, Depends(current_user)],
    store: Annotated[CosmosStore, Depends(get_store)],
):
    try:
        return store.save(payload, user)
    except AzureError:
        logger.warning("No fue posible completar la escritura en Cosmos DB")
        raise HTTPException(503, "No se pudo confirmar el guardado. Puedes reintentar") from None
