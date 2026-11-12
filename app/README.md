# Área 3 · MVP e experiência digital

A plataforma tem duas partes:
- **API** (`api/`): FastAPI com as regras de negócio, a segurança e a ligação com a IA e os sensores.
- **Telas** (`frontend/`): Streamlit, com telas diferentes para o cidadão e para o gestor.

## Como rodar

Todos os comandos são a partir da **raiz do projeto**, com a `.venv` ativada.

```bash
pip install -r app/requirements.txt

# 1. Criar o banco com dados de demonstração (só na primeira vez)
cd app/api
python carga_inicial.py
#    para recomeçar do zero: python carga_inicial.py --zerar

# 2. Subir a API (deixe este terminal aberto)
uvicorn main:app --reload
```

Em **outro terminal**, na raiz do projeto:

```bash
# 3. Subir as telas: abre http://localhost:8501 no navegador
streamlit run app/frontend/app.py
```

A documentação interativa da API fica em <http://localhost:8000/docs>.

## Contas de teste

| Perfil | E-mail | Senha |
|---|---|---|
| Cidadão | cidadao@vigia.com | cidadao123 |
| Gestor | gestor@vigia.com | gestor123 |

## Telas

| # | Tela | Perfil | O que faz |
|---|---|---|---|
| 1 | Entrar / Criar conta | Todos | Login e cadastro |
| 2 | Novo relato | Cidadão | Relato em texto livre; mostra a classificação da IA na hora |
| 3 | Minhas ocorrências | Cidadão | Acompanha o status de cada relato |
| 4 | Fila de atendimento | Gestor | Fila ordenada por urgência, com filtros e mudança de status |
| 5 | Postes inteligentes | Todos | Mapa e tabela com a última leitura de cada poste |

## Endpoints da API

| Método | Caminho | Quem usa |
|---|---|---|
| POST | `/auth/cadastro` | Público |
| POST | `/auth/login` | Público |
| POST | `/ocorrencias` | Cidadão logado |
| GET | `/ocorrencias/minhas` | Cidadão logado |
| GET | `/ocorrencias` | Gestor (fila, com filtros `bairro`, `categoria`, `status_filtro`) |
| PATCH | `/ocorrencias/{id}/status` | Gestor |
| POST | `/sensores/leituras` | Poste (cabeçalho `X-API-Key`) |
| GET | `/postes` | Usuário logado |

O relato do cidadão é classificado com **uma tentativa** no Gemini. Se a IA não responder de
primeira, as regras offline classificam na hora, para ninguém ficar esperando.
