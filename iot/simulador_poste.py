"""
Simulador de poste inteligente (mock dos sensores).

Faz o mesmo que o ESP32 do Wokwi: lê 3 sensores e manda para a API.
  - Sensor de luz (LDR): a lâmpada do poste está acesa?
  - Sensor de presença (PIR): tem gente passando?
  - Botão de pânico: alguém pediu ajuda?

Uso (com a API rodando):
    python iot/simulador_poste.py                                  # POSTE-001, cenário normal
    python iot/simulador_poste.py --poste POSTE-003 --cenario apagado
    python iot/simulador_poste.py --poste POSTE-005 --cenario panico --vezes 1
    python iot/simulador_poste.py --cenario aleatorio --vezes 20 --intervalo 2

Cenários:
    normal     luz acesa, movimento aleatório
    apagado    lâmpada queimada (a API abre uma ocorrência de iluminação)
    panico     botão de pânico pressionado (a API abre uma ocorrência de urgência alta)
    aleatorio  sorteia entre os três, como num dia real
"""

import argparse
import os
import random
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

API_URL = os.getenv("API_URL", "http://localhost:8000")
IOT_API_KEY = os.getenv("IOT_API_KEY", "vigia-iot-dev")


def ler_sensores(cenario: str) -> dict:
    if cenario == "aleatorio":
        cenario = random.choices(["normal", "apagado", "panico"], weights=[85, 12, 3])[0]
    return {
        "luz_ligada": cenario != "apagado",
        "presenca": random.random() < 0.5,
        "panico": cenario == "panico",
    }


def enviar(codigo_poste: str, leitura: dict) -> None:
    corpo = {"codigo_poste": codigo_poste, **leitura}
    try:
        resposta = requests.post(f"{API_URL}/sensores/leituras", json=corpo,
                                 headers={"X-API-Key": IOT_API_KEY}, timeout=10)
    except requests.ConnectionError:
        print(f"  ✖ API fora do ar em {API_URL}")
        return
    estado = (f"luz={'acesa' if leitura['luz_ligada'] else 'APAGADA'} "
              f"presença={'sim' if leitura['presenca'] else 'não'} "
              f"pânico={'SIM' if leitura['panico'] else 'não'}")
    if resposta.ok:
        criadas = resposta.json()["ocorrencias_criadas"]
        extra = f" → ocorrência(s) aberta(s): {criadas}" if criadas else ""
        print(f"  ✔ {codigo_poste} {estado}{extra}")
    else:
        print(f"  ✖ {resposta.status_code}: {resposta.json().get('detail')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simula um poste inteligente do VigIA.")
    parser.add_argument("--poste", default="POSTE-001", help="Código do poste (POSTE-001 a POSTE-008)")
    parser.add_argument("--cenario", default="normal", choices=["normal", "apagado", "panico", "aleatorio"])
    parser.add_argument("--vezes", type=int, default=5, help="Quantas leituras enviar")
    parser.add_argument("--intervalo", type=float, default=3, help="Segundos entre leituras")
    args = parser.parse_args()

    print(f"Simulando {args.poste} (cenário: {args.cenario}) → {API_URL}")
    for i in range(args.vezes):
        enviar(args.poste, ler_sensores(args.cenario))
        if i < args.vezes - 1:
            time.sleep(args.intervalo)
