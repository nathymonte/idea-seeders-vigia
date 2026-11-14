# Área 4 · DevOps, segurança e qualidade

Os arquivos desta área ficam na raiz do projeto, onde as ferramentas esperam encontrá-los:

| Arquivo | Para quê |
|---|---|
| [`../Dockerfile`](../Dockerfile) | Imagem única da aplicação (API e telas) |
| [`../docker-compose.yml`](../docker-compose.yml) | Sobe API + telas com um comando |
| [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) | CI/CD: testes → build e teste dos containers → publicação da imagem |
| [`../tests/`](../tests) | 27 casos de teste automatizados (pytest) |
| [`../pytest.ini`](../pytest.ini) | Configuração dos testes |

## Rodar com Docker

Precisa do [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up --build
```

- API: <http://localhost:8000/docs>
- Telas: <http://localhost:8501>

Para parar: `Ctrl+C` e depois `docker compose down`. Para apagar também os dados: `docker compose down -v`.

## Rodar os testes

```bash
pip install -r requirements.txt
pytest
```

## CI/CD

A cada `git push`, o GitHub Actions roda sozinho:
1. os testes e o pipeline de dados;
2. o build da imagem, sobe os containers e confere se respondem;
3. na branch principal, publica a imagem em `ghcr.io/<usuario>/<repositorio>`.

O resultado fica na aba **Actions** do repositório.

O plano de testes completo e as práticas de segurança estão em
[`../docs/area4-devops-seguranca.md`](../docs/area4-devops-seguranca.md).
