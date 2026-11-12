"""
Avaliação da IA de triagem (requisitos "Lógica e ganho" e diferencial "IA medida").

Compara a classificação automática com os rótulos feitos à mão em
dataset/relatos_rotulados.csv e mede:
  - acurácia de categoria, de urgência e das duas juntas;
  - recall da urgência ALTA (quantos casos urgentes a IA não deixou passar);
  - tempo médio por relato, comparado com a triagem manual.

Uso:
    python avaliar.py --modo regras
    python avaliar.py --modo gemini
    python avaliar.py --modo gemini --tempo-manual 45

Gera em resultados/:
    predicoes_<modo>.csv   (entrada, saída esperada e saída da IA, linha a linha)
    metricas_<modo>.md     (resumo para colar no PDF)
"""

import argparse
import csv
import os
import time
from collections import Counter
from datetime import datetime

from classificador import classificar_com_gemini, classificar_por_regras
from prompt import CATEGORIAS

PASTA = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(PASTA, "dataset", "relatos_rotulados.csv")
RESULTADOS = os.path.join(PASTA, "resultados")


def carregar_dataset():
    with open(DATASET, encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def avaliar(modo: str, tempo_manual: float, intervalo: float):
    funcao = classificar_com_gemini if modo == "gemini" else classificar_por_regras
    linhas = carregar_dataset()
    predicoes = []
    tempos = []
    erros_seguidos = 0

    for i, linha in enumerate(linhas, start=1):
        inicio = time.perf_counter()
        try:
            saida = funcao(linha["texto"])
        except Exception as erro:
            saida = {"categoria": "erro", "urgencia": "erro", "justificativa": str(erro)}
            erros_seguidos += 1
            print(f"[{i:02d}/{len(linhas)}] ERRO: {erro}")
            if erros_seguidos >= 3:
                raise SystemExit("\n3 erros seguidos: avaliação interrompida. Corrija o erro acima e rode de novo.")
        else:
            erros_seguidos = 0
        tempos.append(time.perf_counter() - inicio)

        predicoes.append({
            **linha,
            "categoria_ia": saida["categoria"],
            "urgencia_ia": saida["urgencia"],
            "justificativa_ia": saida["justificativa"],
            "acertou_categoria": saida["categoria"] == linha["categoria_esperada"],
            "acertou_urgencia": saida["urgencia"] == linha["urgencia_esperada"],
        })
        print(f"[{i:02d}/{len(linhas)}] {saida['categoria']:<12} {saida['urgencia']:<6} | {linha['texto'][:60]}")
        if modo == "gemini" and intervalo:
            time.sleep(intervalo)  # respeita o limite de requisições do plano gratuito

    return predicoes, tempos


def calcular_metricas(predicoes, tempos, tempo_manual):
    total = len(predicoes)
    acerto_cat = sum(p["acertou_categoria"] for p in predicoes)
    acerto_urg = sum(p["acertou_urgencia"] for p in predicoes)
    acerto_ambos = sum(p["acertou_categoria"] and p["acertou_urgencia"] for p in predicoes)

    altas = [p for p in predicoes if p["urgencia_esperada"] == "alta"]
    altas_detectadas = sum(p["urgencia_ia"] == "alta" for p in altas)

    por_categoria = {}
    for categoria in CATEGORIAS:
        grupo = [p for p in predicoes if p["categoria_esperada"] == categoria]
        if grupo:
            por_categoria[categoria] = (sum(p["acertou_categoria"] for p in grupo), len(grupo))

    erros = Counter(
        (p["categoria_esperada"], p["categoria_ia"]) for p in predicoes if not p["acertou_categoria"]
    )
    tempo_medio = sum(tempos) / total
    return {
        "total": total,
        "acc_categoria": acerto_cat / total,
        "acc_urgencia": acerto_urg / total,
        "acc_ambos": acerto_ambos / total,
        "recall_alta": altas_detectadas / len(altas) if altas else 0,
        "altas": (altas_detectadas, len(altas)),
        "por_categoria": por_categoria,
        "erros": erros,
        "tempo_medio": tempo_medio,
        "tempo_total": sum(tempos),
        "tempo_manual": tempo_manual,
        "tempo_manual_total": tempo_manual * total,
    }


def salvar(modo, predicoes, m):
    os.makedirs(RESULTADOS, exist_ok=True)
    caminho_csv = os.path.join(RESULTADOS, f"predicoes_{modo}.csv")
    with open(caminho_csv, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(predicoes[0].keys()))
        escritor.writeheader()
        escritor.writerows(predicoes)

    reducao = 1 - m["tempo_medio"] / m["tempo_manual"]
    linhas = [
        f"# Métricas da IA de triagem — modo `{modo}`",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} com {m['total']} relatos rotulados manualmente.",
        "",
        "## Qualidade",
        "",
        "| Métrica | Resultado |",
        "|---|---|",
        f"| Acurácia da categoria | {m['acc_categoria']:.0%} |",
        f"| Acurácia da urgência | {m['acc_urgencia']:.0%} |",
        f"| Acurácia de categoria + urgência | {m['acc_ambos']:.0%} |",
        f"| Casos de urgência ALTA detectados (recall) | {m['recall_alta']:.0%} ({m['altas'][0]} de {m['altas'][1]}) |",
        "",
        "### Acerto por categoria",
        "",
        "| Categoria | Acertos |",
        "|---|---|",
    ]
    linhas += [f"| {c} | {a}/{t} |" for c, (a, t) in m["por_categoria"].items()]
    linhas += ["", "### Erros de categoria (esperado → IA)", ""]
    linhas += [f"- {esp} → {ia}: {n}x" for (esp, ia), n in m["erros"].most_common()] or ["- Nenhum"]
    linhas += [
        "",
        "## Ganho de tempo (antes x depois)",
        "",
        "| | Triagem manual (antes) | Triagem com a VigIA (depois) |",
        "|---|---|---|",
        f"| Tempo por relato | {m['tempo_manual']:.0f} s | {m['tempo_medio'] * 1000:.2f} ms |",
        f"| Tempo para {m['total']} relatos | {m['tempo_manual_total'] / 60:.0f} min | {m['tempo_total']:.1f} s |",
        "",
        f"Redução de **{reducao:.1%}** no tempo de triagem.",
        "",
        "> O tempo manual é o tempo médio que uma pessoa do grupo levou para ler e classificar",
        "> cada relato. Ajuste com `--tempo-manual` depois de cronometrar.",
    ]
    caminho_md = os.path.join(RESULTADOS, f"metricas_{modo}.md")
    with open(caminho_md, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")
    return caminho_csv, caminho_md


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avalia a IA de triagem do VigIA.")
    parser.add_argument("--modo", choices=["gemini", "regras"], default="gemini")
    parser.add_argument("--tempo-manual", type=float, default=60,
                        help="Segundos que uma pessoa leva para triar um relato (padrão: 60)")
    parser.add_argument("--intervalo", type=float, default=4,
                        help="Pausa entre chamadas ao Gemini, em segundos (padrão: 4)")
    args = parser.parse_args()

    if args.modo == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("Erro: GEMINI_API_KEY não encontrada. Crie o arquivo .env na raiz do projeto "
              "(copie o .env.example) e coloque a chave nele.")
        raise SystemExit(1)

    predicoes, tempos = avaliar(args.modo, args.tempo_manual, args.intervalo)
    metricas = calcular_metricas(predicoes, tempos, args.tempo_manual)
    csv_path, md_path = salvar(args.modo, predicoes, metricas)

    print("\n=== Resumo ===")
    print(f"Acurácia categoria: {metricas['acc_categoria']:.0%}")
    print(f"Acurácia urgência:  {metricas['acc_urgencia']:.0%}")
    print(f"Recall urgência ALTA: {metricas['recall_alta']:.0%}")
    print(f"Tempo médio: {metricas['tempo_medio'] * 1000:.2f} ms por relato (manual: {args.tempo_manual:.0f} s)")
    print(f"Arquivos: {csv_path}\n          {md_path}")
