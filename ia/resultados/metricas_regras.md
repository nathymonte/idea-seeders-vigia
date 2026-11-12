# Métricas da IA de triagem — modo `regras`

Gerado em 10/11/2026 11:49 com 40 relatos rotulados manualmente.

## Qualidade

| Métrica | Resultado |
|---|---|
| Acurácia da categoria | 88% |
| Acurácia da urgência | 85% |
| Acurácia de categoria + urgência | 72% |
| Casos de urgência ALTA detectados (recall) | 100% (8 de 8) |

### Acerto por categoria

| Categoria | Acertos |
|---|---|
| iluminacao | 6/9 |
| roubo_furto | 10/10 |
| assedio | 8/8 |
| vandalismo | 6/7 |
| outros | 5/6 |

### Erros de categoria (esperado → IA)

- iluminacao → roubo_furto: 2x
- vandalismo → iluminacao: 1x
- iluminacao → vandalismo: 1x
- outros → iluminacao: 1x

## Ganho de tempo (antes x depois)

| | Triagem manual (antes) | Triagem com a VigIA (depois) |
|---|---|---|
| Tempo por relato | 60 s | 0.01 ms |
| Tempo para 40 relatos | 40 min | 0.0 s |

Redução de **100.0%** no tempo de triagem.

> O tempo manual é o tempo médio que uma pessoa do grupo levou para ler e classificar
> cada relato. Ajuste com `--tempo-manual` depois de cronometrar.
