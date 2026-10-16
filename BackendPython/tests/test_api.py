from datetime import UTC, datetime, timedelta
from uuid import uuid4

from azure.core.exceptions import AzureError
from azure.cosmos.exceptions import CosmosResourceExistsError
from fastapi.testclient import TestClient
from google.auth.exceptions import TransportError
import jwt
import pytest

from app.config import Settings, get_settings
from app.main import app
from app.security import AUDIENCE, ISSUER, issue_session
from app.storage import CosmosStore, get_store
from app.models import User


class FakeContainer:
    def __init__(self):
        self.documents = {}
        self.failure = False
        self.partition = "/userId"

    def read(self):
        if self.failure:
            raise AzureError("offline")
        return {"partitionKey": {"paths": [self.partition]}}

    def create_item(self, document):
        if self.failure:
            raise AzureError("offline")
        key = (document["userId"], document["id"])
        if key in self.documents:
            raise CosmosResourceExistsError(status_code=409, message="exists")
        self.documents[key] = dict(document)
        return dict(document)

    def read_item(self, item, partition_key):
        return self.documents[(partition_key, item)]


@pytest.fixture
def setup(monkeypatch):
    settings = Settings(
        _env_file=None,
        google_web_client_id="test.apps.googleusercontent.com",
        jwt_secret="test-only-random-secret-with-more-than-32-characters",
        cosmos_endpoint="https://test.documents.azure.com",
        cosmos_key="test-only",
    )
    container = FakeContainer()
    store = object.__new__(CosmosStore)
    store.container = container
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_store] = lambda: store
    claims = {"sub": "google-user-a", "email": "ana@example.com", "email_verified": True, "name": "Ana"}
    calls = []

    def verify(token, request, audience):
        calls.append((token, audience))
        return dict(claims)

    monkeypatch.setattr("app.security.id_token.verify_oauth2_token", verify)
    with TestClient(app) as client:
        yield client, settings, container, claims, calls
    app.dependency_overrides.clear()


def login(client):
    response = client.post("/api/v1/auth/google", json={"idToken": "google-test-token-long-enough"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["accessToken"]}


def payload(request_id=None):
    return {"requestId": request_id or str(uuid4()), "mensaje1": " Hola ", "mensaje2": "¿Cómo estás?", "mensaje3": "Gracias 😊"}


def test_login_and_verified_identity(setup):
    client, _, _, _, calls = setup
    response = client.get("/api/v1/me", headers=login(client))
    assert response.json() == {"id": "google-user-a", "email": "ana@example.com", "name": "Ana"}
    assert calls[0][1] == "test.apps.googleusercontent.com"
    assert response.headers["cache-control"] == "no-store"


def test_reject_invalid_google_signature(setup, monkeypatch):
    def invalid(*args):
        raise ValueError("bad signature")
    monkeypatch.setattr("app.security.id_token.verify_oauth2_token", invalid)
    assert setup[0].post("/api/v1/auth/google", json={"idToken": "invalid-token-long-enough"}).status_code == 401


def test_google_temporarily_unavailable(setup, monkeypatch):
    def offline(*args):
        raise TransportError("offline")
    monkeypatch.setattr("app.security.id_token.verify_oauth2_token", offline)
    assert setup[0].post("/api/v1/auth/google", json={"idToken": "test-token-long-enough"}).status_code == 503


@pytest.mark.parametrize("change", [{"email_verified": False}, {"sub": ""}, {"email": None}])
def test_reject_unverified_or_incomplete_google_profile(setup, change):
    setup[3].update(change)
    assert setup[0].post("/api/v1/auth/google", json={"idToken": "test-token-long-enough"}).status_code == 401


def test_requires_login(setup):
    assert setup[0].post("/api/v1/messages", json=payload()).status_code == 401
    assert setup[0].get("/api/v1/me").status_code == 401


def test_saves_authenticated_user_and_server_timestamp(setup):
    client, _, container, _, _ = setup
    response = client.post("/api/v1/messages", json=payload(), headers=login(client))
    assert response.status_code == 201
    document = response.json()
    assert document["userId"] == "google-user-a"
    assert document["mensaje1"] == "Hola"
    assert document["mensaje3"] == "Gracias 😊"
    assert datetime.fromisoformat(document["createdAt"]).tzinfo is not None
    assert len(container.documents) == 1


@pytest.mark.parametrize("field,value", [("mensaje1", "  "), ("mensaje2", ""), ("mensaje3", "x" * 2001), ("mensaje1", 5), ("requestId", "invalid")])
def test_reject_bad_input(setup, field, value):
    data = payload()
    data[field] = value
    assert setup[0].post("/api/v1/messages", json=data, headers=login(setup[0])).status_code == 422
    assert not setup[2].documents


def test_reject_forged_user_id(setup):
    data = payload()
    data["userId"] = "someone-else"
    assert setup[0].post("/api/v1/messages", json=data, headers=login(setup[0])).status_code == 422


def test_retry_does_not_duplicate(setup):
    client = setup[0]
    headers = login(client)
    data = payload()
    first = client.post("/api/v1/messages", json=data, headers=headers)
    again = client.post("/api/v1/messages", json=data, headers=headers)
    assert first.status_code == again.status_code == 201
    assert first.json() == again.json()
    assert len(setup[2].documents) == 1


def test_retry_with_different_body_is_conflict(setup):
    client = setup[0]
    headers = login(client)
    data = payload()
    assert client.post("/api/v1/messages", json=data, headers=headers).status_code == 201
    data["mensaje2"] = "Cambio"
    assert client.post("/api/v1/messages", json=data, headers=headers).status_code == 409
    assert len(setup[2].documents) == 1


def test_users_are_partitioned_even_with_same_request_id(setup):
    client, settings, container, _, _ = setup
    data = payload()
    client.post("/api/v1/messages", json=data, headers=login(client))
    other = issue_session(User(id="google-user-b", email="b@example.com", name="B"), settings)
    response = client.post("/api/v1/messages", json=data, headers={"Authorization": "Bearer " + other.accessToken})
    assert response.status_code == 201
    assert response.json()["userId"] == "google-user-b"
    assert len(container.documents) == 2


@pytest.mark.parametrize("variant", ["expired", "wrong-audience", "wrong-secret"])
def test_reject_invalid_session(setup, variant):
    client, settings, _, _, _ = setup
    claims = {"sub": "attacker", "name": "A", "email": "a@example.com", "iss": ISSUER,
              "aud": AUDIENCE, "iat": datetime.now(UTC) - timedelta(hours=2), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    secret = settings.jwt_secret.get_secret_value()
    if variant == "expired":
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=10)
    elif variant == "wrong-audience":
        claims["aud"] = "other-app"
    else:
        secret = "another-secret-with-at-least-32-characters"
    token = jwt.encode(claims, secret, algorithm="HS256")
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_storage_failure_does_not_report_success(setup):
    client = setup[0]
    headers = login(client)
    setup[2].failure = True
    response = client.post("/api/v1/messages", json=payload(), headers=headers)
    assert response.status_code == 503
    assert not setup[2].documents


def test_readiness_checks_storage_and_partition(setup):
    client = setup[0]
    assert client.get("/ready").status_code == 200
    setup[2].partition = "/wrong"
    assert client.get("/ready").status_code == 503
    setup[2].failure = True
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200
