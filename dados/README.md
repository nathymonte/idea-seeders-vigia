# Área 2 · Big Data e visualização

## Modelo de dados

O banco operacional é um SQLite com 4 tabelas. O script está em [`banco/schema.sql`](banco/schema.sql).

```
usuarios (1) ──< ocorrencias          postes (1) ──< leituras_sensores
```

| Tabela | O que guarda | Quem preenche |
|---|---|---|
| `usuarios` | Cidadãos e gestores, com senha em hash | App (cadastro) |
| `ocorrencias` | Relato em texto, bairro, categoria/urgência da IA, status | App + IA |
| `postes` | Cadastro dos postes inteligentes | Carga inicial |
| `leituras_sensores` | Luz (LDR), presença (PIR) e botão de pânico | ESP32 (Wokwi) |

Decisões de privacidade (LGPD):
- Toda ocorrência é **anônima por padrão** (`anonima = 1`). O dashboard nunca mostra quem relatou.
- A senha é armazenada só como hash (`senha_hash`).
- A IA classifica a situação, nunca pessoas. Nenhum dado de aparência é coletado.

## Criar o banco

```bash
sqlite3 dados/banco/vigia.db < dados/banco/schema.sql
```

Ou, sem o sqlite3 instalado:

```bash
python -c "import sqlite3; sqlite3.connect('dados/banco/vigia.db').executescript(open('dados/banco/schema.sql', encoding='utf-8').read())"
```

## Próximas etapas (Etapa 3)

- Data lake em `dados/lake/` com as camadas bronze → silver → gold
- Script de ingestão e tratamento com pandas
- Dashboard no Power BI com medidas DAX
