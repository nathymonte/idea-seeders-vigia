"""
Pipeline de dados do VigIA: banco operacional → data lake → dashboard.

    python dados/pipeline.py

Camadas (pasta dados/lake/):
  bronze/  cópia fiel dos dados brutos, com a data da ingestão. Nunca é alterada.
  silver/  dados limpos, validados, anonimizados e enriquecidos (datas, faixas de horário...).
  gold/    tabelas prontas para o dashboard (fatos, dimensões e resumos).

Os CSVs usam ";" como separador e "," como decimal (padrão brasileiro: abrem certinho no Excel).
O dashboard fica no app (tela "Dashboard" do gestor) e usa as funções de dados/indicadores.py.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
# Os caminhos podem ser trocados por variáveis de ambiente (usado nos testes)
BANCO = Path(os.getenv("VIGIA_DB", RAIZ / "dados" / "banco" / "vigia.db"))
LAKE = Path(os.getenv("VIGIA_LAKE", RAIZ / "dados" / "lake"))
BRONZE, SILVER, GOLD = LAKE / "bronze", LAKE / "silver", LAKE / "gold"

# A tabela de usuários NUNCA é extraída: o data lake não guarda dados pessoais (LGPD)
TABELAS_ORIGEM = ["ocorrencias", "leituras_sensores", "postes"]

CATEGORIAS = {"iluminacao": "Iluminação", "roubo_furto": "Roubo/furto", "assedio": "Assédio",
              "vandalismo": "Vandalismo", "outros": "Outros"}
URGENCIAS = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}
STATUS = {"aberta": "Aberta", "em_atendimento": "Em atendimento", "resolvida": "Resolvida"}
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def faixa_horaria(hora: int) -> str:
    if hora < 6:
        return "1 Madrugada (0h-6h)"
    if hora < 12:
        return "2 Manhã (6h-12h)"
    if hora < 18:
        return "3 Tarde (12h-18h)"
    return "4 Noite (18h-24h)"


def salvar_csv(tabela: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(caminho, sep=";", decimal=",", index=False, encoding="utf-8-sig")


# ------------------------------------------------------------------ 1. BRONZE
def ingerir_bronze() -> dict:
    """Extrai as tabelas do banco sem mudar nada, só carimbando a data da ingestão."""
    if not BANCO.exists():
        sys.exit(f"Banco não encontrado em {BANCO}. Rode antes: python app/api/carga_inicial.py")
    ingerido_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    brutos = {}
    with sqlite3.connect(BANCO) as conexao:
        for tabela in TABELAS_ORIGEM:
            dados = pd.read_sql_query(f"SELECT * FROM {tabela}", conexao)
            dados["ingerido_em"] = ingerido_em
            salvar_csv(dados, BRONZE / f"{tabela}.csv")
            brutos[tabela] = dados
    return brutos


# ------------------------------------------------------------------ 2. SILVER
def tratar_ocorrencias(bruto: pd.DataFrame, postes: pd.DataFrame, qualidade: dict) -> pd.DataFrame:
    dados = bruto.copy()
    total_inicial = len(dados)

    # Anonimização: o id de quem relatou não segue adiante
    dados = dados.drop(columns=["usuario_id", "anonima", "ingerido_em"])

    # Limpeza e validação
    dados = dados.drop_duplicates(subset="id")
    dados["texto"] = dados["texto"].str.strip()
    validas = dados["categoria"].isin(CATEGORIAS) & dados["urgencia"].isin(URGENCIAS) & dados["status"].isin(STATUS)
    qualidade["ocorrencias_descartadas"] = int((~validas).sum())
    dados = dados[validas]

    for coluna in ("criada_em", "atualizada_em", "resolvida_em"):
        dados[coluna] = pd.to_datetime(dados[coluna], errors="coerce")
    dados = dados.dropna(subset=["criada_em"])

    # Enriquecimento
    dados["data"] = dados["criada_em"].dt.date
    dados["hora"] = dados["criada_em"].dt.hour
    dados["faixa_horaria"] = dados["hora"].apply(faixa_horaria)
    dados["dia_semana"] = dados["criada_em"].dt.dayofweek.map(lambda d: f"{d + 1} {DIAS_SEMANA[d]}")
    dados["mes"] = dados["criada_em"].dt.strftime("%Y-%m")
    dados["tempo_resolucao_horas"] = ((dados["resolvida_em"] - dados["criada_em"]).dt.total_seconds() / 3600).round(1)
    dados["origem"] = dados["origem_classificacao"].map(lambda o: "Sensor do poste" if o == "sensor" else "Cidadão")
    dados["categoria_nome"] = dados["categoria"].map(CATEGORIAS)
    dados["urgencia_nome"] = dados["urgencia"].map(URGENCIAS)
    dados["status_nome"] = dados["status"].map(STATUS)
    dados["poste_codigo"] = dados["poste_id"].map(postes.set_index("id")["codigo"])

    qualidade["ocorrencias_entrada"] = total_inicial
    qualidade["ocorrencias_saida"] = len(dados)
    return dados


def tratar_leituras(bruto: pd.DataFrame, postes: pd.DataFrame, qualidade: dict) -> pd.DataFrame:
    dados = bruto.drop(columns=["ingerido_em"]).drop_duplicates(subset="id")
    total_inicial = len(dados)
    dados["lido_em"] = pd.to_datetime(dados["lido_em"], errors="coerce")
    dados = dados.dropna(subset=["lido_em"])
    dados = dados[dados["poste_id"].isin(postes["id"])]  # leitura de poste inexistente é descartada

    dados = dados.merge(postes[["id", "codigo", "bairro"]].rename(columns={"id": "poste_id"}), on="poste_id")
    dados["data"] = dados["lido_em"].dt.date
    dados["hora"] = dados["lido_em"].dt.hour
    dados["luz_apagada"] = 1 - dados["luz_ligada"]
    # Situação de risco: lâmpada apagada com gente passando
    dados["escuro_com_movimento"] = ((dados["luz_ligada"] == 0) & (dados["presenca"] == 1)).astype(int)

    qualidade["leituras_entrada"] = total_inicial
    qualidade["leituras_saida"] = len(dados)
    return dados


def gerar_silver(brutos: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    qualidade = {}
    postes = brutos["postes"].drop(columns=["ingerido_em"])
    ocorrencias = tratar_ocorrencias(brutos["ocorrencias"], postes, qualidade)
    leituras = tratar_leituras(brutos["leituras_sensores"], postes, qualidade)
    salvar_csv(ocorrencias, SILVER / "ocorrencias.csv")
    salvar_csv(leituras, SILVER / "leituras_sensores.csv")
    salvar_csv(postes, SILVER / "postes.csv")
    return ocorrencias, leituras, postes, qualidade


# ------------------------------------------------------------------ 3. GOLD
def gerar_gold(ocorrencias: pd.DataFrame, leituras: pd.DataFrame, postes: pd.DataFrame) -> dict:
    # Fato de ocorrências: sem o texto livre (o dashboard não precisa e ele pode conter dados pessoais)
    fato_ocorrencias = ocorrencias[[
        "id", "data", "hora", "faixa_horaria", "dia_semana", "mes", "bairro", "latitude", "longitude",
        "categoria_nome", "urgencia_nome", "status_nome", "origem", "poste_codigo", "tempo_resolucao_horas",
    ]].rename(columns={"categoria_nome": "categoria", "urgencia_nome": "urgencia", "status_nome": "status"})

    fato_leituras = leituras[[
        "id", "codigo", "bairro", "data", "hora", "luz_ligada", "luz_apagada", "presenca", "panico",
        "escuro_com_movimento",
    ]].rename(columns={"codigo": "poste"})

    dim_postes = postes.rename(columns={"codigo": "poste"})[["poste", "bairro", "latitude", "longitude"]]

    # Resumo por bairro: junta as duas fontes (relatos dos cidadãos + sensores)
    resumo = ocorrencias.groupby("bairro").agg(
        total_ocorrencias=("id", "count"),
        pendentes=("status", lambda s: (s != "resolvida").sum()),
        urgencia_alta=("urgencia", lambda s: (s == "alta").sum()),
        tempo_medio_resolucao_horas=("tempo_resolucao_horas", "mean"),
    )
    sensores = leituras.groupby("bairro").agg(
        pct_leituras_luz_apagada=("luz_apagada", "mean"),
        acionamentos_panico=("panico", "sum"),
    )
    resumo_bairro = resumo.join(sensores).reset_index()
    resumo_bairro["tempo_medio_resolucao_horas"] = resumo_bairro["tempo_medio_resolucao_horas"].round(1)
    resumo_bairro["pct_leituras_luz_apagada"] = (resumo_bairro["pct_leituras_luz_apagada"] * 100).round(1)
    # Índice de risco simples (0 a 100) para priorizar bairros
    pontos = (resumo_bairro["urgencia_alta"].rank(pct=True) + resumo_bairro["pendentes"].rank(pct=True)
              + resumo_bairro["pct_leituras_luz_apagada"].rank(pct=True)) / 3
    resumo_bairro["indice_risco"] = (pontos * 100).round(0).astype(int)
    resumo_bairro = resumo_bairro.sort_values("indice_risco", ascending=False)

    tabelas = {
        "fato_ocorrencias": fato_ocorrencias,
        "fato_leituras": fato_leituras,
        "dim_postes": dim_postes,
        "resumo_bairro": resumo_bairro,
    }
    for nome, tabela in tabelas.items():
        salvar_csv(tabela, GOLD / f"{nome}.csv")
    return tabelas


# ------------------------------------------------------------------ execução
if __name__ == "__main__":
    inicio = datetime.now()
    print("1/3 Bronze: extraindo do banco...")
    brutos = ingerir_bronze()
    print("2/3 Silver: limpando, validando e anonimizando...")
    ocorrencias, leituras, postes, qualidade = gerar_silver(brutos)
    print("3/3 Gold: montando as tabelas do dashboard...")
    gold = gerar_gold(ocorrencias, leituras, postes)

    relatorio = {
        "executado_em": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "duracao_segundos": round((datetime.now() - inicio).total_seconds(), 2),
        "qualidade": qualidade,
        "linhas_gold": {nome: len(tabela) for nome, tabela in gold.items()},
    }
    (LAKE / "relatorio_execucao.json").write_text(json.dumps(relatorio, indent=2, ensure_ascii=False),
                                                  encoding="utf-8")

    print("\nPronto! Resumo:")
    print(f"  Ocorrências: {qualidade['ocorrencias_entrada']} lidas → {qualidade['ocorrencias_saida']} válidas "
          f"({qualidade['ocorrencias_descartadas']} descartadas)")
    print(f"  Leituras:    {qualidade['leituras_entrada']} lidas → {qualidade['leituras_saida']} válidas")
    for nome, tabela in gold.items():
        print(f"  gold/{nome}.csv: {len(tabela)} linhas")
    print(f"\nArquivos em {LAKE}")
