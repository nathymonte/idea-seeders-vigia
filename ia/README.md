# Área 1 · IA e automação

A IA do VigIA faz a **triagem automática dos relatos** dos cidadãos. Ela lê o texto livre e devolve
uma **categoria** (iluminação, roubo/furto, assédio, vandalismo ou outros), uma **urgência**
(baixa, média ou alta) e uma justificativa curta. Com isso, a subprefeitura e a GCM recebem uma
fila já priorizada, em vez de ler relato por relato.

## Como funciona

```
Relato do cidadão ──► validação da entrada ──► Gemini (prompt de triagem) ──► JSON validado
                                                     │ falhou / sem internet
                                                     ▼
                                          regras de palavras-chave (plano B)
```

| Arquivo | Função |
|---|---|
| `prompt.py` | Prompt de sistema, categorias, critérios de urgência e exemplos (few-shot) |
| `classificador.py` | Chama o Gemini, valida a resposta e cai para as regras se necessário |
| `avaliar.py` | Mede acurácia e ganho de tempo sobre o dataset rotulado |
| `dataset/relatos_rotulados.csv` | 40 relatos fictícios com a classificação correta feita à mão |
| `resultados/` | Métricas e predições geradas pelo `avaliar.py` |

## Como rodar

Na raiz do projeto:

```bash
pip install -r ia/requirements.txt
cp .env.example .env        # no Windows: copy .env.example .env
# edite o .env e coloque sua GEMINI_API_KEY (gratuita em https://aistudio.google.com/apikey)
cd ia
```

**Classificar um relato:**

```bash
python classificador.py "o poste da esquina tá apagado faz uma semana e ontem tentaram me assaltar"
```

Exemplo de saída:

```json
{
  "categoria": "roubo_furto",
  "urgencia": "media",
  "justificativa": "Tentativa de assalto já ocorrida, sem risco imediato.",
  "origem": "gemini"
}
```

Para forçar o modo sem IA: `python classificador.py --regras "texto"`.

**Medir o desempenho:**

```bash
python avaliar.py --modo gemini      # IA generativa
python avaliar.py --modo regras      # plano B, para comparação
```

Os resultados vão para `resultados/metricas_<modo>.md` e `resultados/predicoes_<modo>.csv`.

## Métrica e ganho

- **Antes:** uma pessoa lê e classifica cada relato manualmente (cerca de 60 s por relato;
  cronometrem e ajustem com `--tempo-manual`).
- **Depois:** a IA classifica em poucos segundos, e a fila já chega ordenada por urgência.
- **Qualidade:** acurácia de categoria e urgência contra os 40 rótulos manuais, e o **recall da
  urgência alta** (quantos casos graves a IA não deixou passar). É a métrica mais importante,
  porque perder um caso urgente custa mais do que superestimar um caso simples.

A documentação completa do prompt para o PDF está em [`../docs/area1-ia-prompts.md`](../docs/area1-ia-prompts.md).
