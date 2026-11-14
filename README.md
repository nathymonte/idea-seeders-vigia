# VigIA: seu bairro de olhos abertos

**Global Solution 2026/2 · CitizenTech · FIAP · Engenharia de Software (4ESOA)**

A VigIA é uma plataforma de segurança comunitária para bairros periféricos. Moradores relatam
problemas (rua escura, assalto, assédio, vandalismo), uma IA faz a triagem automática por categoria
e urgência, postes inteligentes simulados informam quando a luz está apagada ou o botão de pânico
foi acionado, e a subprefeitura e a GCM acompanham tudo em um dashboard com os pontos críticos.

A IA classifica **situações, nunca pessoas**. Não há reconhecimento facial.

- **Cidadão beneficiado:** quem circula a pé à noite em bairros periféricos (trabalhadores
  noturnos, estudantes, mulheres)
- **ODS:** 11 (cidades e comunidades sustentáveis, meta 11.7), 10 (redução das desigualdades)
  e 9 (indústria, inovação e infraestrutura)
- **Vídeo pitch:** _link aqui_

## Estrutura do projeto

| Pasta | Área | Status |
|---|---|---|
| [`ia/`](ia/README.md) | 1 · IA e automação: triagem de relatos com Gemini | ✅ Pronta |
| [`dados/`](dados/README.md) | 2 · Big Data e visualização: data lake bronze/silver/gold + dashboard | ✅ Pronta |
| [`app/`](app/README.md) | 3 · MVP: telas em Streamlit + API FastAPI | ✅ Pronta |
| [`iot/`](iot/README.md) | 3 · IoT: poste inteligente (Wokwi + simulador Python) | ✅ Pronta |
| [`devops/`](devops/README.md) | 4 · DevOps, segurança e testes: Docker, GitHub Actions, pytest | ✅ Pronta |
| [`tests/`](tests) | 4 · 27 casos de teste automatizados | ✅ |
| [`docs/`](docs/arquitetura.md) | Arquitetura e material de apoio para o PDF | 🟡 |

## Pré-requisitos

- Python 3.10 ou superior
- Chave gratuita da API do Gemini: <https://aistudio.google.com/apikey>

## Jeito mais rápido: Docker

Com o [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado, na raiz do projeto:

```bash
docker compose up --build
```

Abra <http://localhost:8501> (telas) e <http://localhost:8000/docs> (API). O banco e o data lake de
demonstração são criados automaticamente.

## Como executar sem Docker

```bash
git clone <url-do-repositorio>
cd idea-seeders-gs-citizen-tech
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
cp .env.example .env            # Windows: copy .env.example .env
# edite o .env com a sua GEMINI_API_KEY
```

Para ver o sistema funcionando (detalhes em [`app/README.md`](app/README.md)):

```bash
pip install -r app/requirements.txt
cd app/api
python carga_inicial.py              # cria o banco com dados de demonstração
uvicorn main:app --reload            # API em http://localhost:8000/docs
```

Em outro terminal, na raiz:

```bash
streamlit run app/frontend/app.py    # telas em http://localhost:8501
python iot/simulador_poste.py --cenario apagado   # poste enviando leituras
python dados/pipeline.py                          # atualiza o data lake para o dashboard
```

Contas de teste: `cidadao@vigia.com` / `cidadao123` e `gestor@vigia.com` / `gestor123`.

Para rodar os testes automatizados:

```bash
pip install -r requirements.txt
pytest
```

Cada área tem o próprio README com mais detalhes.

## Integrantes

| Nome | RM |
|---|---|
| | |

## Uso de IA generativa

| Ferramenta | Para quê |
|---|---|
| Claude (Anthropic) | Apoio na definição do plano do projeto, na estrutura inicial do código das Áreas 1, 2, 3 e 4 e na escrita da documentação. Todo o código foi revisado e testado pelo grupo. |
| Google Gemini | Componente da solução: classificação dos relatos dos cidadãos (Área 1). |
