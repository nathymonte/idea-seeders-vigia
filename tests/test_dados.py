"""Testes da Área 2: pipeline do data lake e funções analíticas."""

from datetime import date

import pandas as pd
import pytest

import indicadores as ind
import pipeline


@pytest.fixture(scope="module")
def lake(banco_com_dados):
    """Roda o pipeline completo sobre o banco temporário."""
    brutos = pipeline.ingerir_bronze()
    ocorrencias, leituras, postes, qualidade = pipeline.gerar_silver(brutos)
    gold = pipeline.gerar_gold(ocorrencias, leituras, postes)
    return {"brutos": brutos, "silver": ocorrencias, "gold": gold, "qualidade": qualidade}


def test_ct23_pipeline_gera_as_tres_camadas(lake):
    """CT23 · O pipeline gera as camadas bronze, silver e gold, sem perder registros válidos."""
    for camada, arquivo in [("bronze", "ocorrencias.csv"), ("silver", "ocorrencias.csv"),
                            ("gold", "fato_ocorrencias.csv"), ("gold", "resumo_bairro.csv")]:
        assert (pipeline.LAKE / camada / arquivo).exists()
    assert lake["qualidade"]["ocorrencias_saida"] == len(lake["brutos"]["ocorrencias"])


def test_ct24_lake_nao_tem_dados_pessoais(lake):
    """CT24 · LGPD: usuários não vão para o lake; silver e gold não têm quem relatou; gold não tem o texto."""
    assert not (pipeline.LAKE / "bronze" / "usuarios.csv").exists()
    assert "usuario_id" not in lake["silver"].columns
    assert "texto" not in lake["gold"]["fato_ocorrencias"].columns


def test_ct25_silver_descarta_registros_invalidos(banco_com_dados):
    """CT25 · Registros com categoria inválida ou data quebrada são descartados na silver."""
    bruto = pd.DataFrame([
        {"id": 1, "usuario_id": 1, "anonima": 1, "ingerido_em": "x", "texto": " ok ", "categoria": "assedio",
         "urgencia": "alta", "status": "aberta", "criada_em": "2026-11-01 22:00:00", "atualizada_em": None,
         "resolvida_em": None, "origem_classificacao": "regras", "poste_id": None},
        {"id": 2, "usuario_id": 1, "anonima": 1, "ingerido_em": "x", "texto": "x", "categoria": "INVALIDA",
         "urgencia": "alta", "status": "aberta", "criada_em": "2026-11-01 22:00:00", "atualizada_em": None,
         "resolvida_em": None, "origem_classificacao": "regras", "poste_id": None},
        {"id": 3, "usuario_id": 1, "anonima": 1, "ingerido_em": "x", "texto": "x", "categoria": "assedio",
         "urgencia": "alta", "status": "aberta", "criada_em": "data quebrada", "atualizada_em": None,
         "resolvida_em": None, "origem_classificacao": "regras", "poste_id": None},
    ])
    postes = pd.DataFrame([{"id": 1, "codigo": "POSTE-001"}])
    qualidade = {}
    resultado = pipeline.tratar_ocorrencias(bruto, postes, qualidade)
    assert list(resultado["id"]) == [1]
    assert resultado.iloc[0]["faixa_horaria"].endswith("Noite (18h-24h)")


def test_ct26_indicadores_calculam_certo():
    """CT26 · As funções analíticas calculam os indicadores corretamente."""
    oc = pd.DataFrame({
        "data": [date(2026, 11, d) for d in (1, 2, 3, 8, 9)],
        "urgencia": ["Alta", "Baixa", "Alta", "Média", "Baixa"],
        "status": ["Resolvida", "Aberta", "Resolvida", "Em atendimento", "Resolvida"],
        "tempo_resolucao_horas": [4.0, None, 6.0, None, 100.0],
        "faixa_horaria": ["4 Noite (18h-24h)", "2 Manhã (6h-12h)", "1 Madrugada (0h-6h)",
                          "3 Tarde (12h-18h)", "4 Noite (18h-24h)"],
    })
    assert ind.total_ocorrencias(oc) == 5
    assert ind.ocorrencias_pendentes(oc) == 2
    assert ind.pct_urgencia_alta(oc) == pytest.approx(0.4)
    assert ind.tempo_medio_resolucao(oc) == pytest.approx(36.7)
    assert ind.tempo_medio_resolucao(oc, "Alta") == pytest.approx(5.0)
    assert ind.pct_relatos_noturnos(oc) == pytest.approx(0.6)
    # 08 a 14/11 (2 ocorrências) vs 01 a 07/11 (3 ocorrências) = -33%
    assert ind.variacao_periodo_anterior(oc, date(2026, 11, 8), date(2026, 11, 14)) == pytest.approx(-1 / 3)


def test_ct27_alerta_de_postes_com_falha():
    """CT27 · Postes apagados em mais de 20% das leituras entram no alerta de manutenção."""
    leituras = pd.DataFrame({
        "poste": ["POSTE-001"] * 10 + ["POSTE-002"] * 10,
        "luz_apagada": [0] * 9 + [1] + [1] * 5 + [0] * 5,
    })
    assert ind.postes_com_falha_frequente(leituras) == ["POSTE-002"]
