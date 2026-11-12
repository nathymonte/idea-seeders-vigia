"""Modelos de entrada da API. O Pydantic rejeita automaticamente dados inválidos (erro 422)."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

BAIRROS = [
    "Brasilândia", "Capão Redondo", "Cidade Tiradentes", "Grajaú",
    "Itaquera", "Jardim Ângela", "Jardim São Luís", "Parelheiros",
]


class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)
    senha: str = Field(min_length=6, max_length=72)

    @field_validator("nome", "email")
    @classmethod
    def tirar_espacos(cls, valor: str) -> str:
        return valor.strip()


class Login(BaseModel):
    email: str = Field(max_length=120)
    senha: str = Field(max_length=72)


class NovaOcorrencia(BaseModel):
    texto: str = Field(min_length=5, max_length=1000)
    bairro: str
    anonima: bool = True
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("texto")
    @classmethod
    def texto_nao_vazio(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 5:
            raise ValueError("O relato precisa ter pelo menos 5 caracteres.")
        return valor

    @field_validator("bairro")
    @classmethod
    def bairro_atendido(cls, valor: str) -> str:
        if valor not in BAIRROS:
            raise ValueError("Bairro ainda não atendido pela VigIA.")
        return valor


class AtualizarStatus(BaseModel):
    status: Literal["aberta", "em_atendimento", "resolvida"]


class LeituraSensor(BaseModel):
    codigo_poste: str = Field(pattern=r"^POSTE-\d{3}$")
    luz_ligada: bool
    presenca: bool
    panico: bool = False
