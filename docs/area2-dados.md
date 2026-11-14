# Área 2 · Big Data e visualização: documentação para o PDF

## 1. Estrutura de dados (1 pt)

O VigIA tem **duas fontes** que chegam ao mesmo banco:
- **Relatos dos cidadãos**, em texto livre, classificados pela IA (categoria, urgência).
- **Leituras dos postes inteligentes**, a cada hora durante a noite (luz, presença, pânico).

O banco operacional (SQLite) tem 4 tabelas: `usuarios`, `ocorrencias`, `postes` e `leituras_sensores`
(`dados/banco/schema.sql`). Para análise, os dados passam por um **data lake em três camadas**:

| Camada | Pasta | Conteúdo |
|---|---|---|
| Bronze | `dados/lake/bronze/` | Cópia fiel dos dados brutos, com a data da ingestão |
| Silver | `dados/lake/silver/` | Dados limpos, validados, anonimizados e enriquecidos |
| Gold | `dados/lake/gold/` | Fatos, dimensões e resumos prontos para o dashboard |

> 📸 Print da árvore de pastas do `dados/lake` + o diagrama de `docs/arquitetura.md`.

## 2. Ingestão e processamento (1 pt)

Um script em Python com pandas (`dados/pipeline.py`) roda as três etapas em sequência:

1. **Bronze:** extrai `ocorrencias`, `leituras_sensores` e `postes`. A tabela `usuarios` nunca sai do banco.
2. **Silver:**
   - remove o id de quem relatou (anonimização, LGPD);
   - descarta registros duplicados, com categoria, urgência ou status inválidos e com data quebrada;
   - cria novas colunas: data, hora, faixa horária, dia da semana, mês, tempo de resolução em horas,
     origem (cidadão ou sensor) e o indicador `escuro_com_movimento` (lâmpada apagada com gente passando).
3. **Gold:** gera 2 fatos, 1 dimensão e 1 resumo por bairro. O resumo cruza as duas fontes em um
   **índice de risco de 0 a 100**.

Resultado da execução (`dados/lake/relatorio_execucao.json`):

| | Lidas | Válidas | Descartadas |
|---|---|---|---|
| Ocorrências | 440 | 440 | 0 |
| Leituras de sensores | 2.880 | 2.880 | 0 |

> 📸 Print do terminal rodando `python dados/pipeline.py`.

## 3. Dashboard (1,5 pt)

O dashboard fica **dentro do próprio app**, na tela **Dashboard** do gestor (Streamlit + Altair). Ele
lê a camada gold do data lake e tem um botão **Atualizar dados**, que roda o pipeline de novo. Assim,
um relato novo ou uma leitura de sensor chega ao dashboard sem nenhum passo manual.

- **Ocorrências:** total (com a variação em relação ao período anterior), pendentes, % de urgência
  alta, tempo médio de resolução (geral e das urgências altas).
- **Gráficos:** ocorrências por bairro e urgência, por faixa horária, por categoria e evolução semanal.
- **Postes e sensores:** % de leituras com luz apagada, acionamentos de pânico, "escuro com gente
  passando", alerta de postes que precisam de manutenção e mapa de calor por poste e hora.
- **Prioridade:** ranking dos bairros pelo índice de risco.
- **Filtros:** bairro, período e categoria. Todos os indicadores recalculam na hora.

**Que decisão o dashboard ajuda a tomar?** Para qual bairro mandar a equipe primeiro, quais postes
consertar e se o tempo de resposta às urgências está bom.

**O que os dados mostram** (dados de demonstração):
- **68% dos relatos acontecem à noite ou de madrugada.** Isso reforça o foco em iluminação.
- **Roubo/furto é a categoria mais relatada** (122 de 440), seguida de iluminação (98).
- **Urgências altas são resolvidas em ~7 h em média, contra ~131 h das baixas:** a priorização da
  fila funciona.
- **Dois postes, no Jardim Ângela e em Parelheiros, ficam apagados em ~60% das noites.** Os demais
  ficam em ~3%. O sensor encontra o problema antes de qualquer reclamação.

> 📸 Prints do dashboard inteiro e de uma versão com filtro aplicado (ex.: só Grajaú, só assédio).

## 4. Funções analíticas (0,5 pt)

Os indicadores são calculados por funções em `dados/indicadores.py`. Elas recebem os dados já
filtrados na tela e devolvem o indicador, o mesmo papel das medidas DAX em ferramentas de BI.

| Função | O que calcula |
|---|---|
| `tempo_medio_resolucao(oc, urgencia)` | Média de horas até resolver, geral ou por urgência |
| `variacao_periodo_anterior(oc, inicio, fim)` | Variação do total vs o período anterior de mesmo tamanho |
| `pct_urgencia_alta(oc)` | % de ocorrências de urgência alta |
| `pct_relatos_noturnos(oc)` | % de relatos entre 18h e 6h |
| `pct_luz_apagada(leituras)` | % de leituras noturnas com a lâmpada apagada |
| `situacoes_de_risco(leituras)` | Leituras com lâmpada apagada e gente passando |
| `postes_com_falha_frequente(leituras)` | Postes apagados em mais de 20% das noites |
| `ranking_bairros(oc)` | Bairros ordenados por número de ocorrências |

Exemplo:

```python
def variacao_periodo_anterior(ocorrencias_todas, inicio, fim):
    dias = (fim - inicio).days + 1
    inicio_anterior, fim_anterior = inicio - timedelta(days=dias), inicio - timedelta(days=1)
    atual = ocorrencias_todas["data"].between(inicio, fim).sum()
    anterior = ocorrencias_todas["data"].between(inicio_anterior, fim_anterior).sum()
    return (atual - anterior) / anterior
```

> 📸 Print do código de uma função + o indicador correspondente no dashboard.
