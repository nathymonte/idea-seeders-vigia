# Métricas da IA de triagem — modo `gemini`

Gerado em 11/11/2026 20:32 com 40 relatos rotulados manualmente.

## Qualidade

| Métrica | Resultado |
|---|---|
| Acurácia da categoria | 0% |
| Acurácia da urgência | 0% |
| Acurácia de categoria + urgência | 0% |
| Casos de urgência ALTA detectados (recall) | 0% (0 de 8) |

### Acerto por categoria

| Categoria | Acertos |
|---|---|
| iluminacao | 0/9 |
| roubo_furto | 0/10 |
| assedio | 0/8 |
| vandalismo | 0/7 |
| outros | 0/6 |

### Erros de categoria (esperado → IA)

- roubo_furto → erro: 10x
- iluminacao → erro: 9x
- assedio → erro: 8x
- vandalismo → erro: 7x
- outros → erro: 6x

## Ganho de tempo (antes x depois)

| | Triagem manual (antes) | Triagem com a VigIA (depois) |
|---|---|---|
| Tempo por relato | 60 s | 14.66 ms |
| Tempo para 40 relatos | 40 min | 0.6 s |

Redução de **100.0%** no tempo de triagem.

> O tempo manual é o tempo médio que uma pessoa do grupo levou para ler e classificar
> cada relato. Ajuste com `--tempo-manual` depois de cronometrar.
