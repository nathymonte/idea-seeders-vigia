# Área 3 · IoT: poste inteligente

Cada poste tem **3 sensores** e **1 atuador**:

| Componente | Pino (ESP32) | Função |
|---|---|---|
| Sensor de luz (LDR) | GPIO 34 | A lâmpada do poste está acesa? |
| Sensor de presença (PIR) | GPIO 27 | Tem gente passando? |
| Botão de pânico | GPIO 26 | Alguém pediu ajuda |
| LED vermelho | GPIO 2 | Acende quando o pânico é acionado |

Quando a API recebe uma leitura, ela aplica duas regras automáticas:
1. **Botão de pânico** abre uma ocorrência de **urgência alta** na fila do gestor.
2. **Luz apagada** abre uma ocorrência de **iluminação** (média se tem gente passando, baixa se não),
   sem repetir enquanto a anterior não for resolvida.

Há duas formas de rodar.

## Opção 1 · Simulador em Python (recomendado para a demo)

Com a API rodando, a partir da raiz do projeto:

```bash
python iot/simulador_poste.py --poste POSTE-003 --cenario apagado
python iot/simulador_poste.py --poste POSTE-005 --cenario panico --vezes 1
python iot/simulador_poste.py --cenario aleatorio --vezes 20 --intervalo 2
```

Saída esperada:

```
Simulando POSTE-003 (cenário: apagado) → http://localhost:8000
  ✔ POSTE-003 luz=APAGADA presença=não pânico=não → ocorrência(s) aberta(s): [41]
```

Depois, abra a **Fila de atendimento** (gestor) para ver as ocorrências criadas pelos sensores.

## Opção 2 · ESP32 no Wokwi (circuito)

1. Acesse <https://wokwi.com/projects/new/esp32>.
2. Substitua o conteúdo de `sketch.ino` e `diagram.json` pelos arquivos da pasta `wokwi/`.
3. Clique em ▶️. No Serial Monitor aparecem as leituras.
4. Para mexer nos sensores durante a simulação, clique neles:
   - **LDR:** arraste o controle de luz para baixo para simular a lâmpada queimada;
   - **PIR:** clique em "Simulate motion";
   - **botão:** clique no botão vermelho de pânico.

**Para o Wokwi mandar dados para a API**, a API precisa estar acessível pela internet, porque o
Wokwi roda na nuvem e não enxerga o `localhost` do seu PC:

1. Instale o [ngrok](https://ngrok.com/download) e rode `ngrok http 8000`.
2. Copie o endereço `https://....ngrok-free.app` para a constante `API_URL` do `sketch.ino`.

Sem o ngrok, a simulação continua funcionando e mostrando as leituras no Serial Monitor. Para a
demonstração, o simulador em Python já cobre a integração com a API.
