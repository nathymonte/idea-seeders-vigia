"""Testes da Área 3 (API) e das práticas de segurança da Área 4."""

import sqlite3

from conftest import CHAVE_IOT


# ------------------------------------------------------------------ autenticação
def test_ct07_cadastro_e_login(cliente):
    """CT07 · Um cidadão consegue se cadastrar e entrar."""
    resposta = cliente.post("/auth/cadastro", json={"nome": "Ana", "email": "ana@teste.com", "senha": "segura123"})
    assert resposta.status_code == 201
    resposta = cliente.post("/auth/login", json={"email": "ana@teste.com", "senha": "segura123"})
    assert resposta.status_code == 200
    assert resposta.json()["perfil"] == "cidadao"
    assert resposta.json()["token"]


def test_ct08_email_duplicado(cliente):
    """CT08 · Não é possível cadastrar o mesmo e-mail duas vezes."""
    dados = {"nome": "Bia", "email": "bia@teste.com", "senha": "segura123"}
    assert cliente.post("/auth/cadastro", json=dados).status_code == 201
    assert cliente.post("/auth/cadastro", json=dados).status_code == 409


def test_ct09_senha_errada(cliente):
    """CT09 · Senha errada é recusada com mensagem genérica (não revela se o e-mail existe)."""
    errada = cliente.post("/auth/login", json={"email": "cidadao@vigia.com", "senha": "chute"})
    inexistente = cliente.post("/auth/login", json={"email": "ninguem@vigia.com", "senha": "chute"})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()


def test_ct10_senha_guardada_como_hash(banco_com_dados, cliente):
    """CT10 · A senha nunca é guardada em texto puro no banco."""
    cliente.post("/auth/cadastro", json={"nome": "Caio", "email": "caio@teste.com", "senha": "minhasenha"})
    with sqlite3.connect(banco_com_dados) as conexao:
        senha_hash = conexao.execute("SELECT senha_hash FROM usuarios WHERE email = 'caio@teste.com'").fetchone()[0]
    assert senha_hash != "minhasenha"
    assert senha_hash.startswith("$2b$")  # formato do bcrypt


def test_ct11_validacao_do_cadastro(cliente):
    """CT11 · E-mail inválido e senha curta são rejeitados na entrada."""
    assert cliente.post("/auth/cadastro", json={"nome": "X", "email": "sem-arroba", "senha": "123"}).status_code == 422


# ------------------------------------------------------------------ controle de acesso
def test_ct12_rotas_protegidas_exigem_login(cliente):
    """CT12 · Sem token, não dá para relatar nem ver dados."""
    assert cliente.post("/ocorrencias", json={"texto": "teste de relato", "bairro": "Grajaú"}).status_code == 401
    assert cliente.get("/postes").status_code == 401
    assert cliente.get("/ocorrencias", headers={"Authorization": "Bearer token-falso"}).status_code == 401


def test_ct13_cidadao_nao_ve_fila_do_gestor(cliente, auth_cidadao):
    """CT13 · Um cidadão não acessa a fila de atendimento nem muda status."""
    assert cliente.get("/ocorrencias", headers=auth_cidadao).status_code == 403
    assert cliente.patch("/ocorrencias/1/status", json={"status": "resolvida"}, headers=auth_cidadao).status_code == 403


# ------------------------------------------------------------------ fluxo de ocorrências
def test_ct14_relato_e_classificado(cliente, auth_cidadao):
    """CT14 · Um relato enviado chega classificado e aparece em 'Minhas ocorrências'."""
    resposta = cliente.post("/ocorrencias", headers=auth_cidadao,
                            json={"texto": "Tem um homem me seguindo agora, estou com medo", "bairro": "Grajaú"})
    assert resposta.status_code == 201
    ocorrencia = resposta.json()
    assert ocorrencia["categoria"] == "assedio"
    assert ocorrencia["urgencia"] == "alta"
    assert ocorrencia["status"] == "aberta"
    minhas = cliente.get("/ocorrencias/minhas", headers=auth_cidadao).json()
    assert ocorrencia["id"] in [o["id"] for o in minhas]


def test_ct15_relato_invalido(cliente, auth_cidadao):
    """CT15 · Relato vazio ou de bairro não atendido é rejeitado."""
    assert cliente.post("/ocorrencias", headers=auth_cidadao, json={"texto": "    ", "bairro": "Grajaú"}).status_code == 422
    assert cliente.post("/ocorrencias", headers=auth_cidadao,
                        json={"texto": "poste apagado aqui", "bairro": "Moema"}).status_code == 422


def test_ct16_fila_ordenada_por_urgencia(cliente, auth_gestor):
    """CT16 · A fila do gestor vem da urgência mais alta para a mais baixa."""
    fila = cliente.get("/ocorrencias", headers=auth_gestor).json()
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    niveis = [ordem[o["urgencia"]] for o in fila]
    assert niveis == sorted(niveis)


def test_ct17_fila_nao_expoe_quem_relatou(cliente, auth_gestor):
    """CT17 · LGPD: a fila do gestor não mostra quem fez o relato."""
    fila = cliente.get("/ocorrencias", headers=auth_gestor).json()
    assert fila and all("usuario_id" not in o for o in fila)


def test_ct18_gestor_atualiza_status(cliente, auth_gestor, auth_cidadao):
    """CT18 · O gestor resolve uma ocorrência e o cidadão vê o novo status."""
    criada = cliente.post("/ocorrencias", headers=auth_cidadao,
                          json={"texto": "Picharam o muro da praça", "bairro": "Itaquera"}).json()
    resposta = cliente.patch(f"/ocorrencias/{criada['id']}/status", json={"status": "resolvida"}, headers=auth_gestor)
    assert resposta.status_code == 200
    assert resposta.json()["resolvida_em"] is not None
    minhas = {o["id"]: o for o in cliente.get("/ocorrencias/minhas", headers=auth_cidadao).json()}
    assert minhas[criada["id"]]["status"] == "resolvida"


# ------------------------------------------------------------------ IoT
def test_ct19_sensor_exige_chave(cliente):
    """CT19 · Um dispositivo sem a chave de API não consegue enviar leituras."""
    leitura = {"codigo_poste": "POSTE-001", "luz_ligada": True, "presenca": False}
    assert cliente.post("/sensores/leituras", json=leitura).status_code == 401
    assert cliente.post("/sensores/leituras", json=leitura, headers={"X-API-Key": "errada"}).status_code == 401


def test_ct20_panico_abre_ocorrencia_alta(cliente, auth_gestor):
    """CT20 · O botão de pânico abre uma ocorrência de urgência alta na fila do gestor."""
    resposta = cliente.post("/sensores/leituras", headers=CHAVE_IOT,
                            json={"codigo_poste": "POSTE-004", "luz_ligada": True, "presenca": True, "panico": True})
    assert resposta.status_code == 201
    [nova_id] = resposta.json()["ocorrencias_criadas"]
    fila = {o["id"]: o for o in cliente.get("/ocorrencias", headers=auth_gestor).json()}
    assert fila[nova_id]["urgencia"] == "alta"
    assert fila[nova_id]["origem_classificacao"] == "sensor"


def test_ct21_luz_apagada_nao_duplica(cliente):
    """CT21 · Luz apagada abre UMA ocorrência de iluminação, sem repetir a cada leitura."""
    leitura = {"codigo_poste": "POSTE-008", "luz_ligada": False, "presenca": False}
    primeira = cliente.post("/sensores/leituras", json=leitura, headers=CHAVE_IOT).json()
    segunda = cliente.post("/sensores/leituras", json=leitura, headers=CHAVE_IOT).json()
    assert len(primeira["ocorrencias_criadas"]) == 1
    assert segunda["ocorrencias_criadas"] == []


def test_ct22_poste_inexistente(cliente):
    """CT22 · Leitura de um poste não cadastrado é recusada."""
    leitura = {"codigo_poste": "POSTE-999", "luz_ligada": True, "presenca": False}
    assert cliente.post("/sensores/leituras", json=leitura, headers=CHAVE_IOT).status_code == 404
