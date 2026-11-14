# Área 4 · DevOps, segurança e qualidade: documentação para o PDF

## 1. Organização (0,5 pt)

O projeto é versionado no Git/GitHub e organizado por módulos, um por área:

```
idea-seeders-gs-citizen-tech/
├── ia/                  Área 1 · classificador, prompt, dataset e avaliação
├── dados/               Área 2 · banco, pipeline do data lake, funções analíticas
├── app/                 Área 3 · API (FastAPI) e telas (Streamlit)
├── iot/                 Área 3 · simulador do poste e circuito do Wokwi
├── tests/               Área 4 · testes automatizados (pytest)
├── .github/workflows/   Área 4 · CI/CD (GitHub Actions)
├── Dockerfile           Área 4 · imagem da aplicação
├── docker-compose.yml   Área 4 · sobe API + telas com um comando
└── docs/                Arquitetura e material do PDF
```

> 📸 Print da página do repositório no GitHub + do histórico de commits.

## 2. DevOps (1 pt)

### Docker

`docker compose up --build` sobe tudo:
- **api:** cria o banco de demonstração, gera o data lake e sobe a API na porta 8000;
- **web:** sobe as telas na porta 8501, só depois que a API passa no *healthcheck*.

O banco e o data lake ficam em volumes, então os dados não se perdem ao reiniciar.

> 📸 Print do terminal com `docker compose up` + `docker ps` mostrando os dois containers "healthy".

### CI/CD com GitHub Actions

Cada `git push` dispara o workflow `.github/workflows/ci.yml`, **sem nenhum passo manual**:

| Etapa | O que faz |
|---|---|
| 1. Testes automatizados | Instala as dependências, roda os 27 casos de teste e o pipeline de dados; guarda o relatório e a camada gold como artefato |
| 2. Build e teste dos containers | Faz o build da imagem, sobe API e telas com Docker Compose e confere se respondem (inclusive um login de verdade) |
| 3. Publicar imagem (deploy) | Na branch principal, publica a imagem no GitHub Container Registry (`ghcr.io`) |

Se qualquer teste falhar, as etapas seguintes não rodam: código quebrado nunca vira imagem publicada.
Esse é o diferencial "pipeline ponta a ponta" do PDF.

> 📸 Print da aba **Actions** do GitHub com as 3 etapas verdes ✅ + print da imagem em **Packages**.

## 3. Segurança (0,5 pt)

| # | Prática | Onde está | Como funciona |
|---|---|---|---|
| 1 | **Autenticação** | `app/api/seguranca.py` | Login gera um token JWT assinado que expira em 8 h; rotas protegidas exigem o token |
| 2 | **Senhas protegidas** | `app/api/seguranca.py` | Senhas guardadas só como hash bcrypt, nunca em texto puro |
| 3 | **Controle de acesso por perfil** | `app/api/seguranca.py` | Só o perfil gestor vê a fila e muda status; o cidadão vê só os próprios relatos |
| 4 | **Validação de entrada** | `app/api/modelos.py`, `ia/classificador.py` | Pydantic rejeita e-mail inválido, senha curta, texto vazio, bairro inexistente; relatos acima de 1000 caracteres são cortados |
| 5 | **Proteção de dados (LGPD)** | `dados/pipeline.py`, `app/api/main.py` | Relatos anônimos por padrão; a fila não mostra quem relatou; o data lake não extrai usuários nem leva o texto livre para a gold |
| 6 | **Autenticação de dispositivos** | `app/api/seguranca.py` | Postes só enviam leituras com a chave `X-API-Key` |
| 7 | **SQL parametrizado** | `app/api/main.py` | Valores sempre vão como parâmetros (`?`), evitando SQL injection |
| 8 | **Segredos fora do código** | `.env` + `.gitignore` | Chave do Gemini, segredo do JWT e chave IoT ficam no `.env`, que não vai para o GitHub |
| 9 | **Proteção contra prompt injection** | `ia/prompt.py` | O relato vai isolado entre marcadores, e o prompt manda ignorar instruções dentro dele |
| 10 | **Container sem root** | `Dockerfile` | A aplicação roda com um usuário comum dentro do container |
| 11 | **Login sem vazar informação** | `app/api/main.py` | Mesma mensagem para e-mail inexistente e senha errada |

O PDF pede 2 ou mais práticas. Para a apresentação, destaquem as práticas 1, 2, 4 e 5.

## 4. Testes (1 pt)

### Como rodar

```bash
pip install -r requirements.txt
pytest
```

Os testes usam um banco e um data lake temporários e a IA desligada: não mexem nos dados reais e
funcionam sem internet. Eles também rodam sozinhos no GitHub Actions a cada push.

### Plano de testes

| ID | Área | Cenário | Entrada | Resultado esperado |
|---|---|---|---|---|
| CT01 | IA | Classificar relatos típicos | 5 relatos, um por categoria | Categoria e urgência corretas |
| CT02 | IA | Relato inválido | Vazio, só espaços, "oi", `None`, número | Erro de validação |
| CT03 | IA | Relato muito longo | 5000 caracteres | Cortado em 1000 |
| CT04 | IA | IA devolve valor fora da lista | Categoria "terrorismo", urgência "altissima" | Resposta descartada |
| CT05 | IA | Sem internet / IA desligada | Relato comum | Classificado pelas regras offline |
| CT06 | IA | Prompt seguro | Texto do prompt | Contém todas as categorias, proíbe identificar pessoas e ignora instruções do relato |
| CT07 | API | Cadastro e login | Nome, e-mail e senha válidos | 201 no cadastro, 200 e token no login |
| CT08 | API | E-mail duplicado | Mesmo e-mail duas vezes | 409 |
| CT09 | Segurança | Senha errada | Senha incorreta / e-mail inexistente | 401 com a mesma mensagem |
| CT10 | Segurança | Senha no banco | Novo cadastro | Guardada como hash bcrypt |
| CT11 | Segurança | Cadastro inválido | E-mail sem @, senha de 3 dígitos | 422 |
| CT12 | Segurança | Acesso sem login | Sem token / token falso | 401 |
| CT13 | Segurança | Cidadão na área do gestor | Token de cidadão | 403 |
| CT14 | Fluxo | Relato classificado | "Tem um homem me seguindo agora" | Assédio, alta, aparece em "Minhas ocorrências" |
| CT15 | API | Relato inválido | Texto vazio / bairro "Moema" | 422 |
| CT16 | Fluxo | Fila priorizada | Fila do gestor | Ordenada de alta para baixa |
| CT17 | LGPD | Fila anônima | Fila do gestor | Nenhum `usuario_id` |
| CT18 | Fluxo | Gestor resolve | Status "resolvida" | Data de resolução gravada; cidadão vê o novo status |
| CT19 | IoT | Sensor sem chave | Sem chave / chave errada | 401 |
| CT20 | IoT | Botão de pânico | `panico: true` | Ocorrência de urgência alta na fila |
| CT21 | IoT | Luz apagada repetida | 2 leituras de luz apagada | Só 1 ocorrência criada |
| CT22 | IoT | Poste inexistente | POSTE-999 | 404 |
| CT23 | Dados | Pipeline completo | Banco de demonstração | Camadas bronze, silver e gold geradas sem perda |
| CT24 | LGPD | Data lake sem dados pessoais | Saída do pipeline | Sem tabela de usuários, sem `usuario_id`, sem texto na gold |
| CT25 | Dados | Limpeza da silver | Registro com categoria inválida e com data quebrada | Os dois descartados |
| CT26 | Dados | Funções analíticas | 5 ocorrências com valores conhecidos | Totais, %, tempos e variação corretos |
| CT27 | Dados | Alerta de manutenção | Poste com 50% e poste com 10% de luz apagada | Só o de 50% no alerta |

### Evidência de execução

```
tests/test_api.py::test_ct07_cadastro_e_login PASSED
tests/test_api.py::test_ct08_email_duplicado PASSED
...
tests/test_ia.py::test_ct06_prompt_tem_regras_de_seguranca PASSED

============================== 35 passed ==============================
```

São 27 casos e 35 execuções, porque CT01 e CT02 testam várias entradas cada.

> 📸 Print do terminal com `pytest` (todos PASSED) + print da etapa "Testes automatizados" no GitHub Actions.
