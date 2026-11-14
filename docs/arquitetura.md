# Arquitetura do VigIA

O diagrama abaixo usa Mermaid e aparece desenhado automaticamente no GitHub. Para colocar no PDF:
abra <https://mermaid.live>, cole o código e exporte como PNG.

```mermaid
flowchart LR
    subgraph USUARIOS["👥 Usuários"]
        CID["Cidadão<br/>(celular ou PC)"]
        GES["Gestor<br/>Subprefeitura / GCM"]
    end

    subgraph IOT["📡 Área 3 · IoT"]
        ESP["ESP32 no Wokwi<br/>LDR + PIR + botão de pânico"]
        SIM["Simulador Python<br/>(mock dos sensores)"]
    end

    subgraph MVP["🖥️ Área 3 · MVP"]
        WEB["Telas<br/>Streamlit"]
        API["API REST<br/>FastAPI"]
    end

    subgraph IA["🤖 Área 1 · IA"]
        CLS["Classificador<br/>de relatos"]
        GEM["Google Gemini<br/>(API)"]
        REG["Regras offline<br/>(plano B)"]
    end

    subgraph DADOS["📊 Área 2 · Big Data"]
        DB[("SQLite<br/>banco operacional")]
        LAKE["Data lake<br/>bronze → silver → gold"]
        BI["Dashboard<br/>Streamlit"]
    end

    subgraph DEVOPS["⚙️ Área 4 · DevOps"]
        GIT["GitHub"]
        CI["GitHub Actions<br/>testes + build + deploy"]
        REG2["GitHub Container<br/>Registry"]
        DOCK["Docker Compose"]
    end

    CID -- relato --> WEB
    GES -- atende a fila --> WEB
    WEB -- HTTP + token JWT --> API
    ESP -- "HTTP + chave IoT" --> API
    SIM -- "HTTP + chave IoT" --> API
    API -- texto do relato --> CLS
    CLS --> GEM
    CLS -. sem internet .-> REG
    API -- grava --> DB
    DB -- ingestão --> LAKE
    LAKE --> BI
    WEB -. tela do gestor .-> BI
    GIT --> CI
    CI -- imagem --> REG2
    DOCK -. sobe .-> API
    DOCK -. sobe .-> WEB
```

## Como as áreas se conectam

| De → Para | O que passa | Por quê |
|---|---|---|
| Telas → API | Relatos, login, mudança de status | As telas não acessam o banco direto: toda regra fica na API |
| Postes → API | Luz, presença e pânico | Sensores viram ocorrências automaticamente (pânico = urgência alta, luz apagada = iluminação) |
| API → IA | Texto do relato | Cada relato chega na fila já com categoria e urgência |
| API → Banco | Usuários, ocorrências, leituras | Fonte única dos dados |
| Banco → Data lake → Dashboard | Ocorrências e leituras | Os dados da IA e dos sensores alimentam o dashboard, que fica dentro do próprio app |
| GitHub → Actions → Registry | Cada commit | Testes, build e publicação da imagem rodam sozinhos a cada mudança |

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Interface | Streamlit (Python) |
| API | FastAPI + Pydantic |
| Banco | SQLite |
| Segurança | bcrypt (senhas), JWT (sessão), chave de API (dispositivos) |
| IA | Google Gemini (`google-genai`) + regras de palavras-chave |
| IoT | ESP32 simulado no Wokwi + simulador em Python |
| Dados | pandas (pipeline e funções analíticas) + Altair (gráficos) |
| DevOps | Git/GitHub, GitHub Actions, Docker Compose, pytest |
