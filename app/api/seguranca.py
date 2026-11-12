"""
Práticas de segurança da API:
  1. Senhas guardadas só como hash (bcrypt).
  2. Autenticação com token JWT que expira em 8 horas.
  3. Controle de acesso por perfil (cidadão x gestor).
  4. Chave de API para os dispositivos IoT.
A validação de entrada fica nos modelos Pydantic (modelos.py).
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SEGREDO = os.getenv("JWT_SECRET", "troque-este-segredo-no-arquivo-env-vigia")
JWT_ALGORITMO = "HS256"
JWT_VALIDADE_HORAS = 8
IOT_API_KEY = os.getenv("IOT_API_KEY", "vigia-iot-dev")

_bearer = HTTPBearer(auto_error=False)


def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def conferir_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())


def gerar_token(usuario_id: int, perfil: str) -> str:
    agora = datetime.now(timezone.utc)
    dados = {
        "sub": str(usuario_id),
        "perfil": perfil,
        "iat": agora,
        "exp": agora + timedelta(hours=JWT_VALIDADE_HORAS),
    }
    return jwt.encode(dados, JWT_SEGREDO, algorithm=JWT_ALGORITMO)


def usuario_logado(credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    try:
        dados = jwt.decode(credenciais.credentials, JWT_SEGREDO, algorithms=[JWT_ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Faça login de novo.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.")
    return {"id": int(dados["sub"]), "perfil": dados["perfil"]}


def somente_gestor(usuario: dict = Depends(usuario_logado)) -> dict:
    if usuario["perfil"] != "gestor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso restrito a gestores.")
    return usuario


def dispositivo_autorizado(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != IOT_API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave do dispositivo inválida.")
