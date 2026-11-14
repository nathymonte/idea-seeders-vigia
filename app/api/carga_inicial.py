"""
Cria o banco com dados de demonstração.

    python carga_inicial.py           # cria só o que faltar
    python carga_inicial.py --zerar   # apaga o banco e recria do zero
    python carga_inicial.py --zerar --extras 1000   # mais relatos sintéticos (padrão: 400)

Gera:
  - 1 gestor e 1 cidadão de teste (logins no README)
  - 8 postes, um por bairro
  - os 40 relatos do dataset da IA + 400 relatos sintéticos, espalhados pelos últimos 90 dias
    (mais relatos à noite e em alguns bairros, para o dashboard mostrar padrões)
  - 30 dias de leituras noturnas dos sensores (18h às 6h), de hora em hora
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


# Pesos para os dados sintéticos ficarem com padrões parecidos com a realidade:
# alguns bairros com mais ocorrências e mais relatos à noite.
PESO_BAIRRO = {"Grajaú": 1.6, "Capão Redondo": 1.4, "Jardim Ângela": 1.3, "Brasilândia": 1.0,
               "Cidade Tiradentes": 1.0, "Itaquera": 0.9, "Jardim São Luís": 0.8, "Parelheiros": 0.6}
PESO_HORA = [1.2] * 6 + [0.5] * 6 + [0.7] * 6 + [1.6] * 6  # 0h-5h, 6h-11h, 12h-17h, 18h-23h
DIAS_DE_HISTORICO = 90


def inserir_ocorrencia(conexao, cidadao_id, linha, bairro, criada, agora):
    # Ocorrências antigas tendem a estar resolvidas; urgentes são resolvidas mais rápido
    idade_dias = (agora - criada).days
    status = random.choices(["aberta", "em_atendimento", "resolvida"], weights=[1, 1, 1 + idade_dias / 5])[0]
    resolvida = None
    if status == "resolvida":
        horas = {"alta": 6, "media": 48, "baixa": 120}[linha["urgencia_esperada"]]
        resolvida = min(criada + timedelta(hours=random.uniform(0.3, 2) * horas), agora)
    lat, lon = COORDENADAS[bairro]
    conexao.execute(
        """INSERT INTO ocorrencias (usuario_id, texto, bairro, latitude, longitude, anonima, categoria,
               urgencia, justificativa_ia, origem_classificacao, status, criada_em, atualizada_em, resolvida_em)
           VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'Classificação feita à mão (dataset rotulado).', 'carga_inicial',
                   ?, ?, ?, ?)""",
        (cidadao_id, linha["texto"], bairro, round(lat + random.uniform(-0.01, 0.01), 5), round(lon + random.uniform(-0.01, 0.01), 5),
         linha["categoria_esperada"], linha["urgencia_esperada"], status, criada.strftime(FORMATO),
         resolvida.strftime(FORMATO) if resolvida else None, resolvida.strftime(FORMATO) if resolvida else None),
    )


def criar_ocorrencias(conexao, extras: int):
    """Os 40 relatos do dataset + `extras` relatos sintéticos (reaproveitando os textos)."""
    if conexao.execute("SELECT COUNT(*) FROM ocorrencias").fetchone()[0] > 0:
        return
    cidadao_id = conexao.execute("SELECT id FROM usuarios WHERE email = 'cidadao@vigia.com'").fetchone()[0]
    agora = datetime.now()
    with open(DATASET, encoding="utf-8") as arquivo:
        relatos = list(csv.DictReader(arquivo))

    def momento_aleatorio():
        dia = agora - timedelta(days=random.randint(0, DIAS_DE_HISTORICO))
        hora = random.choices(range(24), weights=PESO_HORA)[0]
        momento = dia.replace(hour=hora, minute=random.randint(0, 59), second=0, microsecond=0)
        return min(momento, agora - timedelta(minutes=5))

    for linha in relatos:
        inserir_ocorrencia(conexao, cidadao_id, linha, linha["bairro"], momento_aleatorio(), agora)
    bairros, pesos = list(PESO_BAIRRO), list(PESO_BAIRRO.values())
    for _ in range(extras):
        linha = random.choice(relatos)
        bairro = random.choices(bairros, weights=pesos)[0]
        inserir_ocorrencia(conexao, cidadao_id, linha, bairro, momento_aleatorio(), agora)


def criar_leituras(conexao):
    if conexao.execute("SELECT COUNT(*) FROM leituras_sensores").fetchone()[0] > 0:
        return
    agora = datetime.now().replace(minute=0, second=0, microsecond=0)
    postes = conexao.execute("SELECT id, codigo, bairro FROM postes").fetchall()
    defeituosos = {"POSTE-002", "POSTE-007"}  # dois postes com lâmpada falhando para a demo
    leituras = []
    for poste in postes:
        for horas_atras in range(30 * 24, 0, -1):
            momento = agora - timedelta(hours=horas_atras)
            if 6 <= momento.hour < 18:
                continue  # o poste só envia leituras à noite, quando a lâmpada deveria estar acesa
            chance_falha = 0.6 if poste["codigo"] in defeituosos else 0.03
            luz = 0 if random.random() < chance_falha else 1
            presenca = 1 if random.random() < 0.35 else 0
            panico = 1 if random.random() < 0.006 * PESO_BAIRRO[poste["bairro"]] else 0
            leituras.append((poste["id"], luz, presenca, panico, momento.strftime(FORMATO)))
    conexao.executemany(
        "INSERT INTO leituras_sensores (poste_id, luz_ligada, presenca, panico, lido_em) VALUES (?, ?, ?, ?, ?)",
        leituras,
    )


if __name__ == "__main__":
    extras = 400
    if "--extras" in sys.argv:
        extras = int(sys.argv[sys.argv.index("--extras") + 1])
    if "--zerar" in sys.argv and db.CAMINHO_BANCO.exists():
        db.CAMINHO_BANCO.unlink()
    db.criar_tabelas()
    with db.conectar() as conexao:
        criar_usuarios(conexao)
        criar_postes(conexao)
        criar_ocorrencias(conexao, extras)
        criar_leituras(conexao)
        totais = {tabela: conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                  for tabela in ("usuarios", "postes", "ocorrencias", "leituras_sensores")}
    print(f"Banco pronto em {db.CAMINHO_BANCO}")
    for tabela, total in totais.items():
        print(f"  {tabela}: {total}")
