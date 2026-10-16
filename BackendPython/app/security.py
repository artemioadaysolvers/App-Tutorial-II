from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from pydantic import ValidationError
import requests

from app.config import Settings, get_settings
from app.models import Session, User

bearer = HTTPBearer(auto_error=False)
ISSUER = "mensajes-backend"
AUDIENCE = "mensajes-mobile"


class GoogleRequest(Request):
    def __call__(self, *args, **kwargs):
        kwargs.setdefault("timeout", 10)
        return super().__call__(*args, **kwargs)


def verify_google_token(token: str, settings: Settings) -> User:
    try:
        # Verifies signature, audience, issuer and expiration with Google's keys.
        with requests.Session() as transport:
            claims = id_token.verify_oauth2_token(
                token, GoogleRequest(session=transport), settings.google_web_client_id
            )
    except (TransportError, requests.RequestException) as exc:
        raise HTTPException(503, "No fue posible verificar Google. Inténtalo de nuevo") from exc
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(401, "La identidad de Google no es válida") from exc
    if not claims.get("sub") or claims.get("email_verified") is not True:
        raise HTTPException(401, "Google debe confirmar la cuenta y su correo")
    email = claims.get("email")
    if not isinstance(email, str) or not email:
        raise HTTPException(401, "Google no devolvió un correo verificado")
    return User(id=claims["sub"], email=email, name=claims.get("name") or email)


def issue_session(user: User, settings: Settings) -> Session:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.session_minutes)
    token = jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "iat": now,
            "exp": expires,
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return Session(accessToken=token, expiresAt=expires, user=user)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if not credentials:
        raise HTTPException(401, "Inicia sesión con Google", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["sub", "email", "name", "iat", "exp", "iss", "aud"]},
        )
        return User(id=claims["sub"], email=claims["email"], name=claims["name"])
    except (jwt.PyJWTError, ValidationError, KeyError) as exc:
        raise HTTPException(
            401, "Tu sesión venció. Vuelve a entrar con Google",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
