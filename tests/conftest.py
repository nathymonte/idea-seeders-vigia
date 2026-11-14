"""
Configuração dos testes.

Os testes usam um banco e um data lake TEMPORÁRIOS, nunca os arquivos reais do projeto,
e rodam com a IA desligada (regras offline): não gastam a cota do Gemini e funcionam sem internet.
"""

import os
import sys
import tempfile
from pathlib import Path

# Precisa acontecer ANTES de importar qualquer módulo do projeto
PASTA_TEMP = Path(tempfile.mkdtemp(prefix="vigia_testes_"))
os.environ["VIGIA_DB"] = str(PASTA_TEMP / "teste.db")
os.environ["VIGIA_LAKE"] = str(PASTA_TEMP / "lake")
os.environ["VIGIA_USAR_IA"] = "0"
os.environ.setdefault("JWT_SECRET", "segredo-so-para-os-testes-automatizados")

RAIZ = Path(__file__).resolve().parents[1]
for pasta in ("app/api", "ia", "dados"):
    sys.path.insert(0, str(RAIZ / pasta))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def banco_com_dados():
    """Cria o banco temporário com os dados de demonstração (uma vez para todos os testes)."""
    import carga_inicial
    import db

    db.criar_tabelas()
    with db.conectar() as conexao:
        carga_inicial.criar_usuarios(conexao)
        carga_inicial.criar_postes(conexao)
        carga_inicial.criar_ocorrencias(conexao, extras=60)
        carga_inicial.criar_leituras(conexao)
    return db.CAMINHO_BANCO


@pytest.fixture(scope="session")
def cliente(banco_com_dados):
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


def _token(cliente, email, senha):
    resposta = cliente.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['token']}"}


@pytest.fixture(scope="session")
def auth_cidadao(cliente):
    return _token(cliente, "cidadao@vigia.com", "cidadao123")


@pytest.fixture(scope="session")
def auth_gestor(cliente):
    return _token(cliente, "gestor@vigia.com", "gestor123")


CHAVE_IOT = {"X-API-Key": os.getenv("IOT_API_KEY", "vigia-iot-dev")}
