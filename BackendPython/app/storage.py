from datetime import UTC, datetime
from functools import lru_cache

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceExistsError
from fastapi import HTTPException

from app.config import get_settings
from app.models import MessageDocument, MessageInput, User


class CosmosStore:
    def __init__(self):
        settings = get_settings()
        self.client = CosmosClient(
            settings.cosmos_endpoint,
            credential=settings.cosmos_key.get_secret_value(),
            connection_timeout=10,
            read_timeout=10,
            retry_total=2,
            logging_enable=False,
        )
        self.container = self.client.get_database_client(
            settings.cosmos_database
        ).get_container_client(settings.cosmos_container)

    def ready(self) -> None:
        properties = self.container.read()
        if properties.get("partitionKey", {}).get("paths") != ["/userId"]:
            raise RuntimeError("El contenedor debe tener la partición /userId")

    def save(self, payload: MessageInput, user: User) -> MessageDocument:
        document = MessageDocument(
            id=str(payload.requestId),
            userId=user.id,
            mensaje1=payload.mensaje1,
            mensaje2=payload.mensaje2,
            mensaje3=payload.mensaje3,
            createdAt=datetime.now(UTC),
        )
        try:
            stored = self.container.create_item(document.model_dump(mode="json"))
        except CosmosResourceExistsError:
            # A retry after a timeout returns the original record, without a duplicate.
            stored = self.container.read_item(document.id, partition_key=user.id)
            if any(stored.get(key) != getattr(payload, key)
                   for key in ("mensaje1", "mensaje2", "mensaje3")):
                raise HTTPException(409, "Ese identificador ya corresponde a otro envío") from None
        return MessageDocument.model_validate(stored)


@lru_cache
def get_store() -> CosmosStore:
    from azure.core.exceptions import AzureError
    try:
        return CosmosStore()
    except AzureError:
        raise HTTPException(503, "Almacenamiento no disponible") from None
