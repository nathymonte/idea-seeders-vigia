"""
Telas do VigIA (Streamlit).

Rodar (com a API já no ar):
    streamlit run app/frontend/app.py

Telas:
  1. Entrar / Criar conta
  2. Novo relato             (cidadão)
  3. Minhas ocorrências      (cidadão)
  4. Fila de atendimento     (gestor)
  5. Postes inteligentes     (todos)
  6. Dashboard               (gestor) — lê a camada gold do data lake
"""

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "dados"))
import indicadores as ind  # noqa: E402  (funções analíticas da Área 2)

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

API_URL = os.getenv("API_URL", "http://localhost:8000")

CATEGORIAS = {
    "iluminacao": "💡 Iluminação",
    "roubo_furto": "🚨 Roubo/furto",
    "assedio": "⚠️ Assédio",
    "vandalismo": "🔨 Vandalismo",
    "outros": "📌 Outros",
}
URGENCIAS = {"alta": "🔴 Alta", "media": "🟠 Média", "baixa": "🟢 Baixa"}
STATUS = {"aberta": "Aberta", "em_atendimento": "Em atendimento", "resolvida": "Resolvida"}
ORIGENS = {"gemini": "IA (Gemini)", "regras": "IA (modo offline)", "sensor": "Sensor do poste",
           "carga_inicial": "Dado de demonstração"}

st.set_page_config(page_title="VigIA", page_icon="👁️", layout="wide")


# ------------------------------------------------------------------ comunicação com a API
def chamar_api(metodo: str, caminho: str, **kwargs):
    """Faz a requisição e devolve (dados, erro)."""
    cabecalhos = {}
    if st.session_state.get("token"):
        cabecalhos["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        resposta = requests.request(metodo, f"{API_URL}{caminho}", headers=cabecalhos, timeout=60, **kwargs)
    except requests.ConnectionError:
        return None, f"Não consegui falar com a API em {API_URL}. Ela está rodando?"
    if resposta.status_code == 401 and st.session_state.get("token"):
        sair()
        return None, "Sua sessão expirou. Entre de novo."
    if not resposta.ok:
        detalhe = resposta.json().get("detail", "Erro inesperado.")
        if isinstance(detalhe, list):  # erros de validação do Pydantic
            detalhe = " ".join(item["msg"].replace("Value error, ", "") for item in detalhe)
        return None, detalhe
    return resposta.json(), None


def sair():
    for chave in ("token", "nome", "perfil"):
        st.session_state.pop(chave, None)


@st.cache_data(ttl=3600)
def bairros():
    dados, _ = chamar_api("GET", "/bairros")
    return dados or []


# ------------------------------------------------------------------ tela 1: entrar / criar conta
def tela_entrar():
    st.title("👁️ VigIA")
    st.caption("Seu bairro de olhos abertos. Relate problemas de segurança e acompanhe o atendimento.")

    entrar, criar = st.tabs(["Entrar", "Criar conta"])
    with entrar:
        with st.form("login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                dados, erro = chamar_api("POST", "/auth/login", json={"email": email, "senha": senha})
                if erro:
                    st.error(erro)
                else:
                    st.session_state.update(token=dados["token"], nome=dados["nome"], perfil=dados["perfil"])
                    st.rerun()
        st.info("Contas de teste: **cidadao@vigia.com** / cidadao123 · **gestor@vigia.com** / gestor123")

    with criar:
        with st.form("cadastro"):
            nome = st.text_input("Nome")
            email_novo = st.text_input("E-mail", key="email_novo")
            senha_nova = st.text_input("Senha (mínimo 6 caracteres)", type="password", key="senha_nova")
            if st.form_submit_button("Criar conta", type="primary"):
                _, erro = chamar_api("POST", "/auth/cadastro",
                                     json={"nome": nome, "email": email_novo, "senha": senha_nova})
                if erro:
                    st.error(erro)
                else:
                    st.success("Conta criada! Agora é só entrar na aba ao lado.")


# ------------------------------------------------------------------ tela 2: novo relato
def tela_novo_relato():
    st.header("📝 Novo relato")
    st.write("Conte o que está acontecendo com as suas palavras. A IA da VigIA classifica e "
             "encaminha para a equipe certa.")
    with st.form("relato", clear_on_submit=True):
        texto = st.text_area("O que está acontecendo?", max_chars=1000, height=140,
                             placeholder="Ex.: o poste da esquina está apagado há uma semana e ontem tentaram me assaltar")
        bairro = st.selectbox("Bairro", bairros())
        anonima = st.checkbox("Enviar de forma anônima (recomendado)", value=True,
                              help="Seu nome nunca aparece para a equipe de atendimento.")
        enviar = st.form_submit_button("Enviar relato", type="primary")

    if enviar:
        with st.spinner("A IA está analisando o seu relato..."):
            dados, erro = chamar_api("POST", "/ocorrencias",
                                     json={"texto": texto, "bairro": bairro, "anonima": anonima})
        if erro:
            st.error(erro)
            return
        st.success(f"Relato nº {dados['id']} enviado! Acompanhe em **Minhas ocorrências**.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Categoria", CATEGORIAS[dados["categoria"]])
        col2.metric("Urgência", URGENCIAS[dados["urgencia"]])
        col3.metric("Classificado por", ORIGENS[dados["origem_classificacao"]])
        st.caption(f"Por quê: {dados['justificativa_ia']}")
        if dados["urgencia"] == "alta":
            st.warning("Se você estiver em perigo agora, ligue **190** (Polícia Militar) ou **153** (GCM).")


# ------------------------------------------------------------------ tela 3: minhas ocorrências
def tela_minhas_ocorrencias():
    st.header("📋 Minhas ocorrências")
    dados, erro = chamar_api("GET", "/ocorrencias/minhas")
    if erro:
        st.error(erro)
        return
    if not dados:
        st.info("Você ainda não enviou nenhum relato.")
        return
    for oc in dados:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**#{oc['id']}** · {oc['bairro']} · {oc['criada_em'][:16]}")
            col1.write(oc["texto"])
            col1.caption(f"{CATEGORIAS[oc['categoria']]} · {URGENCIAS[oc['urgencia']]}")
            col2.markdown(f"### {STATUS[oc['status']]}")


# ------------------------------------------------------------------ tela 4: fila do gestor
def tela_fila():
    st.header("🗂️ Fila de atendimento")
    st.caption("Ordenada da ocorrência mais urgente para a menos urgente. Relatos são anônimos.")

    f1, f2, f3 = st.columns(3)
    bairro = f1.selectbox("Bairro", ["Todos"] + bairros())
    categoria = f2.selectbox("Categoria", ["Todas"] + list(CATEGORIAS), format_func=lambda c: CATEGORIAS.get(c, c))
    status = f3.selectbox("Status", ["Pendentes", "Todos"] + list(STATUS), format_func=lambda s: STATUS.get(s, s))

    parametros = {}
    if bairro != "Todos":
        parametros["bairro"] = bairro
    if categoria != "Todas":
        parametros["categoria"] = categoria
    if status in STATUS:
        parametros["status_filtro"] = status

    dados, erro = chamar_api("GET", "/ocorrencias", params=parametros)
    if erro:
        st.error(erro)
        return
    if status == "Pendentes":
        dados = [oc for oc in dados if oc["status"] != "resolvida"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Ocorrências na fila", len(dados))
    m2.metric("Urgência alta", sum(oc["urgencia"] == "alta" for oc in dados))
    m3.metric("Vindas dos sensores", sum(oc["origem_classificacao"] == "sensor" for oc in dados))

    for oc in dados[:50]:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1.3])
            col1.markdown(f"{URGENCIAS[oc['urgencia']]} · **#{oc['id']}** · {CATEGORIAS[oc['categoria']]} · "
                          f"{oc['bairro']} · {oc['criada_em'][:16]}")
            col1.write(oc["texto"])
            col1.caption(f"{ORIGENS[oc['origem_classificacao']]}: {oc['justificativa_ia']}")
            novo = col2.selectbox("Status", list(STATUS), index=list(STATUS).index(oc["status"]),
                                  format_func=STATUS.get, key=f"status_{oc['id']}")
            if col2.button("Atualizar", key=f"botao_{oc['id']}", disabled=novo == oc["status"]):
                _, erro = chamar_api("PATCH", f"/ocorrencias/{oc['id']}/status", json={"status": novo})
                if erro:
                    st.error(erro)
                else:
                    st.toast(f"Ocorrência #{oc['id']}: {STATUS[novo]}")
                    st.rerun()


# ------------------------------------------------------------------ tela 5: postes
def tela_postes():
    st.header("💡 Postes inteligentes")
    st.caption("Última leitura de cada poste: sensor de luz, sensor de presença e botão de pânico.")
    dados, erro = chamar_api("GET", "/postes")
    if erro:
        st.error(erro)
        return
    tabela = pd.DataFrame(dados)
    if tabela.empty:
        st.info("Nenhum poste cadastrado.")
        return

    apagados = tabela[tabela["luz_ligada"] == 0]
    m1, m2, m3 = st.columns(3)
    m1.metric("Postes monitorados", len(tabela))
    m2.metric("Com a luz apagada", len(apagados))
    m3.metric("Pânico na última leitura", int((tabela["panico"] == 1).sum()))

    tabela["cor"] = tabela["luz_ligada"].map({1: "#2e7d32", 0: "#c62828"}).fillna("#9e9e9e")
    st.map(tabela, latitude="latitude", longitude="longitude", color="cor", size=600)
    st.caption("🟢 luz funcionando · 🔴 luz apagada")

    visao = pd.DataFrame({
        "Poste": tabela["codigo"],
        "Bairro": tabela["bairro"],
        "Luz": tabela["luz_ligada"].map({1: "💡 Ligada", 0: "⚫ Apagada"}),
        "Movimento": tabela["presenca"].map({1: "🚶 Sim", 0: "Não"}),
        "Pânico": tabela["panico"].map({1: "🆘 ACIONADO", 0: "—"}),
        "Última leitura": tabela["lido_em"],
    })
    st.dataframe(visao, hide_index=True, width="stretch")


# ------------------------------------------------------------------ tela 6: dashboard (Área 2)
@st.cache_data(ttl=600)
def dados_gold():
    return ind.carregar_gold()


def porcentagem(valor):
    return f"{valor:.0%}".replace(".", ",")


def tela_dashboard():
    st.header("📊 Dashboard")
    st.caption("Dados da camada gold do data lake: relatos dos cidadãos + sensores dos postes.")

    if st.button("🔄 Atualizar dados (rodar o pipeline)"):
        with st.spinner("Rodando bronze → silver → gold..."):
            resultado = subprocess.run([sys.executable, str(RAIZ / "dados" / "pipeline.py")],
                                       capture_output=True, text=True)
        if resultado.returncode != 0:
            st.error(resultado.stdout + resultado.stderr)
        else:
            dados_gold.clear()
            st.toast("Data lake atualizado!")

    try:
        gold = dados_gold()
    except FileNotFoundError:
        st.warning("O data lake ainda não foi gerado. Clique no botão acima ou rode `python dados/pipeline.py`.")
        return
    ocorrencias_todas, leituras_todas = gold["fato_ocorrencias"], gold["fato_leituras"]

    # ---- filtros
    f1, f2, f3 = st.columns([2, 2, 2])
    lista_bairros = sorted(ocorrencias_todas["bairro"].unique())
    filtro_bairros = f1.multiselect("Bairro", lista_bairros, placeholder="Todos")
    data_max = ocorrencias_todas["data"].max()
    periodo = f2.date_input("Período", value=(data_max - timedelta(days=29), data_max),
                            min_value=ocorrencias_todas["data"].min(), max_value=data_max, format="DD/MM/YYYY")
    filtro_categorias = f3.multiselect("Categoria", sorted(ocorrencias_todas["categoria"].unique()),
                                       placeholder="Todas")
    if not isinstance(periodo, tuple) or len(periodo) != 2:
        st.info("Escolha a data final do período.")
        return
    inicio, fim = periodo

    bairros_sel = filtro_bairros or lista_bairros
    oc_base = ocorrencias_todas[ocorrencias_todas["bairro"].isin(bairros_sel)]
    if filtro_categorias:
        oc_base = oc_base[oc_base["categoria"].isin(filtro_categorias)]
    oc = oc_base[oc_base["data"].between(inicio, fim)]
    leituras = leituras_todas[leituras_todas["bairro"].isin(bairros_sel)
                              & leituras_todas["data"].between(inicio, fim)]

    # ---- indicadores
    variacao = ind.variacao_periodo_anterior(oc_base, inicio, fim)
    tempo = ind.tempo_medio_resolucao(oc)
    tempo_alta = ind.tempo_medio_resolucao(oc, "Alta")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Ocorrências", ind.total_ocorrencias(oc),
              delta=None if variacao is None else f"{variacao:+.0%} vs período anterior", delta_color="inverse")
    k2.metric("Pendentes", ind.ocorrencias_pendentes(oc))
    k3.metric("Urgência alta", porcentagem(ind.pct_urgencia_alta(oc)))
    k4.metric("Tempo médio de resolução", f"{tempo:.0f} h" if tempo is not None else "—")
    k5.metric("Resolução das urgências altas", f"{tempo_alta:.0f} h" if tempo_alta is not None else "—")

    if oc.empty:
        st.info("Nenhuma ocorrência com esses filtros.")
    else:
        cores_urgencia = alt.Scale(domain=["Alta", "Média", "Baixa"], range=["#d32f2f", "#f57c00", "#388e3c"])
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Ocorrências por bairro")
            grafico = alt.Chart(oc).mark_bar().encode(
                x=alt.X("count():Q", title="Ocorrências"),
                y=alt.Y("bairro:N", sort="-x", title=None),
                color=alt.Color("urgencia:N", scale=cores_urgencia, title="Urgência"),
                tooltip=["bairro", "urgencia", "count()"],
            )
            st.altair_chart(grafico, width="stretch")
        with g2:
            st.subheader("Quando os relatos acontecem")
            st.caption(f"{porcentagem(ind.pct_relatos_noturnos(oc))} dos relatos são entre 18h e 6h.")
            por_faixa = ind.ocorrencias_por(oc, "faixa_horaria")
            por_faixa["faixa"] = por_faixa["faixa_horaria"].str[2:]
            grafico = alt.Chart(por_faixa).mark_bar(color="#3949ab").encode(
                x=alt.X("faixa:N", sort=list(por_faixa["faixa"]), title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("ocorrencias:Q", title="Ocorrências"),
                tooltip=["faixa", "ocorrencias"],
            )
            st.altair_chart(grafico, width="stretch")

        g3, g4 = st.columns(2)
        with g3:
            st.subheader("Por categoria")
            grafico = alt.Chart(ind.ocorrencias_por(oc, "categoria")).mark_arc(innerRadius=60).encode(
                theta="ocorrencias:Q",
                color=alt.Color("categoria:N", title="Categoria", scale=alt.Scale(scheme="tableau10")),
                tooltip=["categoria", "ocorrencias"],
            )
            st.altair_chart(grafico, width="stretch")
        with g4:
            st.subheader("Evolução semanal")
            st.caption("A primeira e a última semana do período podem estar incompletas.")
            semanal = oc.assign(semana=pd.to_datetime(oc["data"]).dt.to_period("W").dt.start_time)
            semanal = semanal.groupby("semana").size().reset_index(name="ocorrencias")
            grafico = alt.Chart(semanal).mark_line(point=True, color="#3949ab").encode(
                x=alt.X("semana:T", title="Semana", axis=alt.Axis(format="%d/%m")),
                y=alt.Y("ocorrencias:Q", title="Ocorrências"),
                tooltip=[alt.Tooltip("semana:T", format="%d/%m/%Y"), "ocorrencias"],
            )
            st.altair_chart(grafico, width="stretch")

    # ---- sensores
    st.divider()
    st.subheader("💡 Postes e sensores")
    s1, s2, s3 = st.columns(3)
    s1.metric("Leituras com a luz apagada", porcentagem(ind.pct_luz_apagada(leituras)))
    s2.metric("Acionamentos de pânico", ind.acionamentos_panico(leituras))
    s3.metric("Escuro com gente passando", ind.situacoes_de_risco(leituras),
              help="Leituras em que a lâmpada estava apagada e o sensor de presença detectou movimento.")
    falhas = ind.postes_com_falha_frequente(leituras)
    if falhas:
        st.warning(f"Manutenção recomendada: **{', '.join(falhas)}** ficaram apagados em mais de 20% das noites.")

    if not leituras.empty:
        g5, g6 = st.columns(2)
        with g5:
            st.caption("% de leituras com a luz apagada, por poste")
            taxa = leituras.groupby(["poste", "bairro"])["luz_apagada"].mean().reset_index()
            grafico = alt.Chart(taxa).mark_bar().encode(
                x=alt.X("luz_apagada:Q", title="Luz apagada", axis=alt.Axis(format="%")),
                y=alt.Y("poste:N", sort="-x", title=None),
                color=alt.condition(alt.datum.luz_apagada > 0.2, alt.value("#d32f2f"), alt.value("#90a4ae")),
                tooltip=["poste", "bairro", alt.Tooltip("luz_apagada:Q", format=".0%")],
            )
            st.altair_chart(grafico, width="stretch")
        with g6:
            st.caption("Escuro com gente passando, por poste e hora da noite")
            ordem_horas = list(range(18, 24)) + list(range(0, 6))
            mapa = leituras.groupby(["poste", "hora"])["escuro_com_movimento"].sum().reset_index()
            grafico = alt.Chart(mapa).mark_rect().encode(
                x=alt.X("hora:O", sort=ordem_horas, title="Hora", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("poste:N", title=None),
                color=alt.Color("escuro_com_movimento:Q", scale=alt.Scale(scheme="reds"), title="Situações"),
                tooltip=["poste", "hora", "escuro_com_movimento"],
            )
            st.altair_chart(grafico, width="stretch")

    # ---- prioridade por bairro
    st.divider()
    st.subheader("🎯 Para onde mandar a equipe primeiro")
    st.caption("Índice de risco (0 a 100) da camada gold: junta urgências altas, pendências e falhas de iluminação. "
               "Considera todo o histórico.")
    resumo = gold["resumo_bairro"]
    resumo = resumo[resumo["bairro"].isin(bairros_sel)]
    st.dataframe(
        resumo[["bairro", "indice_risco", "total_ocorrencias", "pendentes", "urgencia_alta",
                "pct_leituras_luz_apagada", "acionamentos_panico"]],
        hide_index=True, width="stretch",
        column_config={
            "bairro": "Bairro",
            "indice_risco": st.column_config.ProgressColumn("Índice de risco", min_value=0, max_value=100,
                                                            format="%d"),
            "total_ocorrencias": "Ocorrências",
            "pendentes": "Pendentes",
            "urgencia_alta": "Urgência alta",
            "pct_leituras_luz_apagada": st.column_config.NumberColumn("Luz apagada", format="%.1f%%"),
            "acionamentos_panico": "Pânico",
        },
    )


# ------------------------------------------------------------------ navegação
if not st.session_state.get("token"):
    tela_entrar()
else:
    if st.session_state.perfil == "gestor":
        telas = {"Fila de atendimento": tela_fila, "Dashboard": tela_dashboard,
                 "Postes inteligentes": tela_postes}
    else:
        telas = {"Novo relato": tela_novo_relato, "Minhas ocorrências": tela_minhas_ocorrencias,
                 "Postes do bairro": tela_postes}
    with st.sidebar:
        st.markdown(f"### 👁️ VigIA\nOlá, **{st.session_state.nome}**")
        st.caption("Gestor(a)" if st.session_state.perfil == "gestor" else "Cidadão(ã)")
        escolha = st.radio("Menu", list(telas), label_visibility="collapsed")
        if st.button("Sair"):
            sair()
            st.rerun()
    telas[escolha]()
