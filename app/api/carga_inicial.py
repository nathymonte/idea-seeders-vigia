"""
Cria o banco com dados de demonstração.

    python carga_inicial.py           # cria só o que faltar
    python carga_inicial.py --zerar   # apaga o banco e recria do zero

Gera:
  - 1 gestor e 1 cidadão de teste (logins no README)
  - 8 postes, um por bairro
  - os 40 relatos do dataset da IA, espalhados pelos últimos 60 dias
  - 7 dias de leituras noturnas dos sensores (18h às 6h), de hora em hora
Esses dados também alimentam o dashboard da Área 2.
"""

import csv
import random
import sys
from datetime import datetime, timedelta

import db
from seguranca import gerar_hash

random.seed(42)  # mesmos dados toda vez

POSTES = [  # código, bairro, latitude, longitude (aproximadas)
    ("POSTE-001", "Capão Redondo", -23.6719, -46.7794),
    ("POSTE-002", "Jardim Ângela", -23.7122, -46.7708),
    ("POSTE-003", "Grajaú", -23.7856, -46.6650),
    ("POSTE-004", "Cidade Tiradentes", -23.5822, -46.4092),
    ("POSTE-005", "Itaquera", -23.5400, -46.4560),
    ("POSTE-006", "Brasilândia", -23.4689, -46.6870),
    ("POSTE-007", "Parelheiros", -23.8270, -46.7270),
    ("POSTE-008", "Jardim São Luís", -23.6530, -46.7390),
]
COORDENADAS = {bairro: (lat, lon) for _, bairro, lat, lon in POSTES}
DATASET = db.RAIZ / "ia" / "dataset" / "relatos_rotulados.csv"
FORMATO = "%Y-%m-%d %H:%M:%S"


def criar_usuarios(conexao):
    usuarios = [
        ("Gestora Subprefeitura", "gestor@vigia.com", "gestor123", "gestor"),
        ("Maria Cidadã", "cidadao@vigia.com", "cidadao123", "cidadao"),
    ]
    for nome, email, senha, perfil in usuarios:
        conexao.execute(
            "INSERT OR IGNORE INTO usuarios (nome, email, senha_hash, perfil) VALUES (?, ?, ?, ?)",
            (nome, email, gerar_hash(senha), perfil),
        )


def criar_postes(conexao):
    conexao.executemany(
        "INSERT OR IGNORE INTO postes (codigo, bairro, latitude, longitude) VALUES (?, ?, ?, ?)", POSTES
    )


def criar_ocorrencias(conexao):
    if conexao.execute("SELECT COUNT(*) FROM ocorrencias").fetchone()[0] > 0:
        return
    cidadao_id = conexao.execute("SELECT id FROM usuarios WHERE email = 'cidadao@vigia.com'").fetchone()[0]
    agora = datetime.now()
    with open(DATASET, encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            criada = agora - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23),
                                       minutes=random.randint(0, 59))
            # Ocorrências antigas tendem a estar resolvidas; urgentes são resolvidas mais rápido
            idade_dias = (agora - criada).days
            status = random.choices(["aberta", "em_atendimento", "resolvida"],
                                    weights=[1, 1, 1 + idade_dias / 10])[0]
            resolvida = None
            if status == "resolvida":
                horas = {"alta": 6, "media": 48, "baixa": 120}[linha["urgencia_esperada"]]
                resolvida = min(criada + timedelta(hours=random.uniform(0.3, 2) * horas), agora)
            lat, lon = COORDENADAS[linha["bairro"]]
            conexao.execute(
                """INSERT INTO ocorrencias (usuario_id, texto, bairro, latitude, longitude, anonima, categoria,
                       urgencia, justificativa_ia, origem_classificacao, status, criada_em, atualizada_em,
                       resolvida_em)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'Classificação feita à mão (dataset rotulado).', 'carga_inicial', ?, ?, ?, ?)""",
                (cidadao_id, linha["texto"], linha["bairro"], lat + random.uniform(-0.01, 0.01),
                 lon + random.uniform(-0.01, 0.01), linha["categoria_esperada"], linha["urgencia_esperada"],
                 status, criada.strftime(FORMATO),
                 resolvida.strftime(FORMATO) if resolvida else None,
                 resolvida.strftime(FORMATO) if resolvida else None),
            )


def criar_leituras(conexao):
    if conexao.execute("SELECT COUNT(*) FROM leituras_sensores").fetchone()[0] > 0:
        return
    agora = datetime.now().replace(minute=0, second=0, microsecond=0)
    postes = conexao.execute("SELECT id, codigo FROM postes").fetchall()
    defeituosos = {"POSTE-002", "POSTE-007"}  # dois postes com lâmpada falhando para a demo
    leituras = []
    for poste in postes:
        for horas_atras in range(7 * 24, 0, -1):
            momento = agora - timedelta(hours=horas_atras)
            if 6 <= momento.hour < 18:
                continue  # o poste só envia leituras à noite, quando a lâmpada deveria estar acesa
            luz = 0 if poste["codigo"] in defeituosos and random.random() < 0.6 else 1
            presenca = 1 if random.random() < 0.35 else 0
            panico = 1 if random.random() < 0.008 else 0
            leituras.append((poste["id"], luz, presenca, panico, momento.strftime(FORMATO)))
    conexao.executemany(
        "INSERT INTO leituras_sensores (poste_id, luz_ligada, presenca, panico, lido_em) VALUES (?, ?, ?, ?, ?)",
        leituras,
    )


if __name__ == "__main__":
    if "--zerar" in sys.argv and db.CAMINHO_BANCO.exists():
        db.CAMINHO_BANCO.unlink()
    db.criar_tabelas()
    with db.conectar() as conexao:
        criar_usuarios(conexao)
        criar_postes(conexao)
        criar_ocorrencias(conexao)
        criar_leituras(conexao)
        totais = {tabela: conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                  for tabela in ("usuarios", "postes", "ocorrencias", "leituras_sensores")}
    print(f"Banco pronto em {db.CAMINHO_BANCO}")
    for tabela, total in totais.items():
        print(f"  {tabela}: {total}")
