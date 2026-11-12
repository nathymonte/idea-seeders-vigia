# Área 3 · MVP, IoT e experiência digital: documentação para o PDF

## 1. Protótipo: 5 telas funcionais (1 pt)

| # | Tela | Perfil |
|---|---|---|
| 1 | Entrar / Criar conta | Todos |
| 2 | Novo relato (com a classificação da IA na hora) | Cidadão |
| 3 | Minhas ocorrências | Cidadão |
| 4 | Fila de atendimento priorizada | Gestor |
| 5 | Postes inteligentes (mapa + tabela) | Todos |

> 📸 Um print de cada tela.

## 2. IoT: 3 sensores (1 pt)

LDR (luz da lâmpada), PIR (presença) e botão de pânico, em um ESP32 simulado no Wokwi
(`iot/wokwi/`) e em um simulador Python (`iot/simulador_poste.py`) que envia leituras reais para a API.

> 📸 Print do circuito no Wokwi + print do terminal do simulador.

## 3. Fluxo funcional completo (1 pt)

**Cenário:** a Maria volta da faculdade à noite pelo Grajaú.

1. O poste **POSTE-003** detecta que a lâmpada queimou e envia a leitura para a API.
   → A API abre sozinha uma ocorrência de **iluminação**.
2. A Maria entra no app (**tela 1**) e relata em **Novo relato** (**tela 2**):
   *"tem um homem me seguindo desde o ponto de ônibus, a rua tá escura"*.
   → A IA classifica na hora como **assédio · urgência alta** e o app mostra os telefones 190/153.
3. A gestora da subprefeitura entra (**tela 1**) e vê a **Fila de atendimento** (**tela 4**): o relato
   da Maria está no topo, seguido da ocorrência do poste. Ela passa os dois para **Em atendimento**.
4. Em **Postes inteligentes** (**tela 5**), ela confere o POSTE-003 em vermelho no mapa e manda a
   equipe da Ilume. Depois da troca, marca a ocorrência como **Resolvida**.
5. A Maria vê em **Minhas ocorrências** (**tela 3**) o status atualizado.

> 📸 Um print por passo. É esse mesmo roteiro que vale gravar no vídeo pitch.

Comandos para reproduzir:

```bash
python iot/simulador_poste.py --poste POSTE-003 --cenario apagado --vezes 1
# depois: telas no navegador, com cidadao@vigia.com e gestor@vigia.com
```

## 4. Arquitetura (1 pt)

Ver [`arquitetura.md`](arquitetura.md). Exportar o diagrama pelo mermaid.live e colar aqui.
