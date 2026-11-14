"""
Funções analíticas do dashboard do VigIA (requisito "Funções analíticas" da Área 2).

Cada função recebe a tabela já filtrada (por bairro, período, categoria...) e devolve
um indicador. Fazem o papel das medidas DAX de uma ferramenta de BI: o mesmo cálculo
reage automaticamente aos filtros escolhidos na tela.

As tabelas vêm da camada gold do data lake (dados/lake/gold/), geradas por pipeline.py.
"""

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

GOLD = Path(os.getenv("VIGIA_LAKE", Path(__file__).resolve().parent / "lake")) / "gold"


def carregar_gold() -> dict[str, pd.DataFrame]:
    """Lê as tabelas da camada gold (CSV com ';' e decimal ',')."""
    tabelas = {}
    for nome in ("fato_ocorrencias", "fato_leituras", "dim_postes", "resumo_bairro"):
        tabela = pd.read_csv(GOLD / f"{nome}.csv", sep=";", decimal=",", encoding="utf-8-sig")
        if "data" in tabela.columns:
            tabela["data"] = pd.to_datetime(tabela["data"]).dt.date
        tabelas[nome] = tabela
    return tabelas


# ------------------------------------------------------------------ ocorrências
def total_ocorrencias(ocorrencias: pd.DataFrame) -> int:
    return len(ocorrencias)


def ocorrencias_pendentes(ocorrencias: pd.DataFrame) -> int:
    """Ocorrências que ainda não foram resolvidas (abertas ou em atendimento)."""
    return int((ocorrencias["status"] != "Resolvida").sum())


def pct_urgencia_alta(ocorrencias: pd.DataFrame) -> float:
    """Percentual de ocorrências classificadas como urgência alta (0 a 1)."""
    if ocorrencias.empty:
        return 0.0
    return float((ocorrencias["urgencia"] == "Alta").mean())


def tempo_medio_resolucao(ocorrencias: pd.DataFrame, urgencia: str | None = None) -> float | None:
    """Média de horas entre o relato e a resolução. Pode filtrar por urgência."""
    if urgencia:
        ocorrencias = ocorrencias[ocorrencias["urgencia"] == urgencia]
    tempos = ocorrencias["tempo_resolucao_horas"].dropna()
    return round(float(tempos.mean()), 1) if not tempos.empty else None


def pct_relatos_noturnos(ocorrencias: pd.DataFrame) -> float:
    """Percentual de relatos entre 18h e 6h."""
    if ocorrencias.empty:
        return 0.0
    return float(ocorrencias["faixa_horaria"].str.contains("Noite|Madrugada").mean())


def variacao_periodo_anterior(ocorrencias_todas: pd.DataFrame, inicio: date, fim: date) -> float | None:
    """
    Compara o total do período escolhido com o período anterior de mesmo tamanho.
    Ex.: 01/11 a 14/11 é comparado com 18/10 a 31/10. Devolve a variação (0,1 = +10%).
    """
    dias = (fim - inicio).days + 1
    inicio_anterior, fim_anterior = inicio - timedelta(days=dias), inicio - timedelta(days=1)
    atual = ocorrencias_todas["data"].between(inicio, fim).sum()
    anterior = ocorrencias_todas["data"].between(inicio_anterior, fim_anterior).sum()
    if anterior == 0:
        return None
    return float((atual - anterior) / anterior)


def ocorrencias_por(ocorrencias: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Contagem de ocorrências agrupada por uma coluna (bairro, categoria, faixa_horaria...)."""
    return ocorrencias.groupby(coluna).size().reset_index(name="ocorrencias")


def ranking_bairros(ocorrencias: pd.DataFrame) -> pd.DataFrame:
    """Bairros ordenados pelo total de ocorrências, com a posição no ranking."""
    tabela = ocorrencias_por(ocorrencias, "bairro").sort_values("ocorrencias", ascending=False)
    tabela["posicao"] = range(1, len(tabela) + 1)
    return tabela


# ------------------------------------------------------------------ sensores
def pct_luz_apagada(leituras: pd.DataFrame) -> float:
    """Percentual das leituras noturnas em que a lâmpada estava apagada."""
    if leituras.empty:
        return 0.0
    return float(leituras["luz_apagada"].mean())


def acionamentos_panico(leituras: pd.DataFrame) -> int:
    return int(leituras["panico"].sum())


def situacoes_de_risco(leituras: pd.DataFrame) -> int:
    """Quantas vezes havia gente passando com a lâmpada apagada."""
    return int(leituras["escuro_com_movimento"].sum())


def postes_com_falha_frequente(leituras: pd.DataFrame, limite: float = 0.2) -> list[str]:
    """Postes apagados em mais de `limite` (padrão 20%) das leituras: candidatos à manutenção."""
    taxa = leituras.groupby("poste")["luz_apagada"].mean()
    return sorted(taxa[taxa > limite].index)
