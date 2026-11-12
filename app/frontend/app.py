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
"""

import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

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


# ------------------------------------------------------------------ navegação
if not st.session_state.get("token"):
    tela_entrar()
else:
    if st.session_state.perfil == "gestor":
        telas = {"Fila de atendimento": tela_fila, "Postes inteligentes": tela_postes}
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
