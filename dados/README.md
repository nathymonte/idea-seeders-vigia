# Área 2 · Big Data e visualização

```
SQLite (app)  ──►  bronze  ──►  silver  ──►  gold  ──►  Dashboard (Streamlit)
  banco/          lake/bronze   lake/silver  lake/gold    indicadores.py + tela do gestor
```

## Como rodar

Na raiz do projeto:

```bash
python app/api/carga_inicial.py --zerar   # banco com 440 ocorrências e 2.880 leituras de sensores
python dados/pipeline.py                   # gera o data lake
```

Depois, suba o app (ver [`app/README.md`](../app/README.md)), entre como **gestor** e abra **Dashboard**.
O botão **Atualizar dados** roda o pipeline de novo, para que relatos novos e leituras dos sensores apareçam no dashboard.

## Dashboard

| Bloco | Indicadores |
|---|---|
| Ocorrências | Total (com variação vs período anterior), pendentes, % de urgência alta, tempo médio de resolução (geral e das urgências altas) |
| Gráficos | Por bairro e urgência, por faixa horária, por categoria, evolução semanal |
| Sensores | % de leituras com luz apagada, acionamentos de pânico, escuro com gente passando, alerta de postes para manutenção, mapa de calor por hora |
| Prioridade | Ranking dos bairros pelo índice de risco |

**Filtros:** bairro, período e categoria. Todos os indicadores recalculam na hora.

## Funções analíticas

Os indicadores são calculados por funções em [`indicadores.py`](indicadores.py), como
`tempo_medio_resolucao()`, `variacao_periodo_anterior()`, `pct_luz_apagada()` e
`postes_com_falha_frequente()`. Elas fazem o papel das medidas DAX: recebem os dados já filtrados
e devolvem o indicador.

## Fontes de dados

| Fonte | Tabela | Volume (demo) | Origem |
|---|---|---|---|
| Relatos dos cidadãos | `ocorrencias` | 440 | App + IA (Área 1) |
| Sensores dos postes | `leituras_sensores` | 2.880 (8 postes × 30 noites × 12 h) | IoT (Área 3) |
| Cadastro de postes | `postes` | 8 | Carga inicial |

Os dados de demonstração são sintéticos, com padrões realistas: mais relatos à noite, mais
ocorrências em alguns bairros e dois postes com lâmpada falhando.

## Camadas do data lake

| Camada | O que tem | Regras aplicadas |
|---|---|---|
| **bronze** | Cópia fiel do banco + data da ingestão | Nada é alterado. A tabela de usuários **não é extraída** (LGPD) |
| **silver** | Dados limpos e enriquecidos | Remove o id de quem relatou; descarta duplicados, categorias inválidas e datas quebradas; cria `faixa_horaria`, `dia_semana`, `mes`, `tempo_resolucao_horas` e `escuro_com_movimento` |
| **gold** | Tabelas prontas para o dashboard | Fatos e dimensões em modelo estrela, sem o texto livre dos relatos; resumo por bairro com índice de risco |

Cada execução grava `lake/relatorio_execucao.json` com as linhas lidas, válidas e descartadas.

### Tabelas da gold

| Arquivo | Uso no dashboard |
|---|---|
| `fato_ocorrencias.csv` | Indicadores de ocorrências, filtros por bairro, período e categoria |
| `fato_leituras.csv` | Indicadores dos sensores (luz apagada, pânico, risco) |
| `dim_postes.csv` | Mapa dos postes |
| `resumo_bairro.csv` | Ranking de prioridade por bairro (índice de risco 0 a 100) |

Os CSVs usam `;` como separador e `,` como decimal (padrão brasileiro, abrem direto no Excel).

## Modelo de dados do banco

O script está em [`banco/schema.sql`](banco/schema.sql).

```
usuarios (1) ──< ocorrencias >── (1) postes (1) ──< leituras_sensores
```

Decisões de privacidade (LGPD):
- Toda ocorrência é **anônima por padrão**, e o dashboard nunca mostra quem relatou.
- A senha é armazenada só como hash.
- A IA classifica a situação, nunca pessoas.
