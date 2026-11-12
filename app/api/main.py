"""
API do VigIA (FastAPI).

Rodar (a partir desta pasta):
    uvicorn main:app --reload
Documentação interativa: http://localhost:8000/docs
"""

import sqlite3
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status

import db
from modelos import BAIRROS, AtualizarStatus, Cadastro, LeituraSensor, Login, NovaOcorrencia
from seguranca import (conferir_senha, dispositivo_autorizado, gerar_hash, gerar_token,
                       somente_gestor, usuario_logado)

# Reaproveita a IA da Área 1
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ia"))
from classificador import classificar  # noqa: E402

app = FastAPI(title="VigIA API", description="Segurança comunitária com IA e postes inteligentes.")
db.criar_tabelas()

ORDEM_URGENCIA = "CASE urgencia WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END"
CAMPOS_OCORRENCIA = """id, texto, bairro, latitude, longitude, categoria, urgencia, justificativa_ia,
    origem_classificacao, status, poste_id, criada_em, atualizada_em, resolvida_em"""


@app.get("/", tags=["status"])
def status_api():
    return {"servico": "VigIA API", "status": "ok"}


@app.get("/bairros", tags=["status"])
def listar_bairros():
    return BAIRROS


# ---------------------------------------------------------------- autenticação
@app.post("/auth/cadastro", status_code=status.HTTP_201_CREATED, tags=["autenticação"])
def cadastrar(dados: Cadastro, conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    try:
        with conexao:
            cursor = conexao.execute(
                "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
                (dados.nome, dados.email.lower(), gerar_hash(dados.senha)),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está cadastrado.")
    return {"id": cursor.lastrowid, "nome": dados.nome, "perfil": "cidadao"}


@app.post("/auth/login", tags=["autenticação"])
def login(dados: Login, conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    usuario = conexao.execute(
        "SELECT id, nome, senha_hash, perfil FROM usuarios WHERE email = ?", (dados.email.lower().strip(),)
    ).fetchone()
    # Mesma mensagem para e-mail e senha errados: não revela quais e-mails existem
    if usuario is None or not conferir_senha(dados.senha, usuario["senha_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    return {
        "token": gerar_token(usuario["id"], usuario["perfil"]),
        "nome": usuario["nome"],
        "perfil": usuario["perfil"],
    }


# ---------------------------------------------------------------- ocorrências
@app.post("/ocorrencias", status_code=status.HTTP_201_CREATED, tags=["ocorrências"])
def criar_ocorrencia(dados: NovaOcorrencia, usuario: dict = Depends(usuario_logado),
                     conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    # Uma tentativa só: se o Gemini estiver lento, as regras respondem na hora
    resultado = classificar(dados.texto, tentativas=1)
    with conexao:
        cursor = conexao.execute(
            """INSERT INTO ocorrencias (usuario_id, texto, bairro, latitude, longitude, anonima,
                   categoria, urgencia, justificativa_ia, origem_classificacao)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (usuario["id"], dados.texto, dados.bairro, dados.latitude, dados.longitude, int(dados.anonima),
             resultado["categoria"], resultado["urgencia"], resultado["justificativa"], resultado["origem"]),
        )
    return _buscar_ocorrencia(conexao, cursor.lastrowid)


@app.get("/ocorrencias/minhas", tags=["ocorrências"])
def minhas_ocorrencias(usuario: dict = Depends(usuario_logado),
                       conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    linhas = conexao.execute(
        f"SELECT {CAMPOS_OCORRENCIA} FROM ocorrencias WHERE usuario_id = ? ORDER BY criada_em DESC",
        (usuario["id"],),
    ).fetchall()
    return [dict(linha) for linha in linhas]


@app.get("/ocorrencias", tags=["ocorrências"])
def fila_de_atendimento(bairro: str | None = None, categoria: str | None = None,
                        status_filtro: str | None = None, _: dict = Depends(somente_gestor),
                        conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    """Fila do gestor, da mais urgente para a menos urgente. Nunca expõe quem relatou."""
    condicoes, parametros = [], []
    for campo, valor in (("bairro", bairro), ("categoria", categoria), ("status", status_filtro)):
        if valor:
            condicoes.append(f"{campo} = ?")  # campo vem da lista fixa acima, valor vai como parâmetro
            parametros.append(valor)
    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
    linhas = conexao.execute(
        f"SELECT {CAMPOS_OCORRENCIA} FROM ocorrencias {where} ORDER BY {ORDEM_URGENCIA}, criada_em DESC",
        parametros,
    ).fetchall()
    return [dict(linha) for linha in linhas]


@app.patch("/ocorrencias/{ocorrencia_id}/status", tags=["ocorrências"])
def atualizar_status(ocorrencia_id: int, dados: AtualizarStatus, _: dict = Depends(somente_gestor),
                     conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    with conexao:
        cursor = conexao.execute(
            """UPDATE ocorrencias
               SET status = ?, atualizada_em = datetime('now', 'localtime'),
                   resolvida_em = CASE WHEN ? = 'resolvida' THEN datetime('now', 'localtime') ELSE NULL END
               WHERE id = ?""",
            (dados.status, dados.status, ocorrencia_id),
        )
    if cursor.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ocorrência não encontrada.")
    return _buscar_ocorrencia(conexao, ocorrencia_id)


def _buscar_ocorrencia(conexao, ocorrencia_id: int) -> dict:
    linha = conexao.execute(f"SELECT {CAMPOS_OCORRENCIA} FROM ocorrencias WHERE id = ?", (ocorrencia_id,)).fetchone()
    return dict(linha)


# ---------------------------------------------------------------- IoT
@app.post("/sensores/leituras", status_code=status.HTTP_201_CREATED, tags=["IoT"],
          dependencies=[Depends(dispositivo_autorizado)])
def registrar_leitura(leitura: LeituraSensor, conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    """Recebe a leitura de um poste e abre ocorrências automaticamente quando precisa."""
    poste = conexao.execute("SELECT id, codigo, bairro, latitude, longitude FROM postes WHERE codigo = ?",
                            (leitura.codigo_poste,)).fetchone()
    if poste is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Poste não cadastrado.")

    criadas = []
    with conexao:
        cursor = conexao.execute(
            "INSERT INTO leituras_sensores (poste_id, luz_ligada, presenca, panico) VALUES (?, ?, ?, ?)",
            (poste["id"], int(leitura.luz_ligada), int(leitura.presenca), int(leitura.panico)),
        )
        leitura_id = cursor.lastrowid

        # Regra 1: botão de pânico sempre abre uma ocorrência de urgência alta
        if leitura.panico:
            criadas.append(_ocorrencia_do_sensor(
                conexao, poste, "outros", "alta",
                f"Botão de pânico acionado no poste {poste['codigo']}.",
                "Acionamento do botão de pânico indica pessoa em perigo."))

        # Regra 2: luz apagada abre uma ocorrência de iluminação (se ainda não houver uma aberta)
        if not leitura.luz_ligada:
            ja_existe = conexao.execute(
                """SELECT 1 FROM ocorrencias WHERE poste_id = ? AND categoria = 'iluminacao'
                   AND status != 'resolvida'""", (poste["id"],)).fetchone()
            if not ja_existe:
                urgencia = "media" if leitura.presenca else "baixa"
                criadas.append(_ocorrencia_do_sensor(
                    conexao, poste, "iluminacao", urgencia,
                    f"Poste {poste['codigo']} com a luz apagada (detectado pelo sensor).",
                    "Luz apagada com pessoas passando no local." if leitura.presenca
                    else "Luz apagada, sem movimento no momento."))

    return {"leitura_id": leitura_id, "ocorrencias_criadas": criadas}


def _ocorrencia_do_sensor(conexao, poste, categoria, urgencia, texto, justificativa) -> int:
    cursor = conexao.execute(
        """INSERT INTO ocorrencias (poste_id, texto, bairro, latitude, longitude, categoria, urgencia,
               justificativa_ia, origem_classificacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sensor')""",
        (poste["id"], texto, poste["bairro"], poste["latitude"], poste["longitude"],
         categoria, urgencia, justificativa),
    )
    return cursor.lastrowid


@app.get("/postes", tags=["IoT"])
def status_dos_postes(_: dict = Depends(usuario_logado), conexao: sqlite3.Connection = Depends(db.obter_conexao)):
    """Última leitura de cada poste."""
    linhas = conexao.execute(
        """SELECT p.codigo, p.bairro, p.latitude, p.longitude,
                  l.luz_ligada, l.presenca, l.panico, l.lido_em
           FROM postes p
           LEFT JOIN leituras_sensores l ON l.id = (
               SELECT id FROM leituras_sensores WHERE poste_id = p.id ORDER BY lido_em DESC, id DESC LIMIT 1)
           ORDER BY p.codigo"""
    ).fetchall()
    return [dict(linha) for linha in linhas]
