"""Conexão com o banco SQLite do VigIA."""

import os
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

try:  # carrega o .env da raiz antes de qualquer configuração ser lida
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
except ImportError:
    pass

SCHEMA = RAIZ / "dados" / "banco" / "schema.sql"
CAMINHO_BANCO = Path(os.getenv("VIGIA_DB", RAIZ / "dados" / "banco" / "vigia.db"))


def conectar() -> sqlite3.Connection:
    conexao = sqlite3.connect(CAMINHO_BANCO, check_same_thread=False)
    conexao.row_factory = sqlite3.Row  # linhas viram dicionários
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas() -> None:
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as conexao:
        conexao.executescript(SCHEMA.read_text(encoding="utf-8"))


def obter_conexao():
    """Dependência do FastAPI: abre uma conexão por requisição e fecha no final."""
    conexao = conectar()
    try:
        yield conexao
    finally:
        conexao.close()
