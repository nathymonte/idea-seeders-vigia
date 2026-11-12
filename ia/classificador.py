"""
Classificador de relatos do VigIA.

Recebe o texto livre de um cidadão e devolve:
    {"categoria": ..., "urgencia": ..., "justificativa": ..., "origem": "gemini" | "regras"}

Estratégia:
1. Tenta classificar com a API do Gemini (IA generativa + prompt em prompt.py).
2. Se não houver chave, internet ou a API falhar, usa regras de palavras-chave.
   Assim a solução continua útil mesmo sem conectividade ideal.

Uso pela linha de comando:
    python classificador.py "o poste da minha rua está apagado"
    python classificador.py --regras "o poste da minha rua está apagado"
"""

import json
import os
import sys
import time
import unicodedata

from prompt import CATEGORIAS, URGENCIAS, PROMPT_SISTEMA, montar_prompt_usuario

try:  # carrega o arquivo .env, se existir
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

MODELO_GEMINI = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
TAMANHO_MAXIMO = 1000  # caracteres


# --------------------------------------------------------------------------
# Validação
# --------------------------------------------------------------------------
def validar_texto(texto) -> str:
    """Valida a entrada do cidadão (prática de segurança: validação de entrada)."""
    if not isinstance(texto, str):
        raise ValueError("O relato precisa ser um texto.")
    texto = texto.strip()
    if len(texto) < 5:
        raise ValueError("O relato está vazio ou curto demais.")
    return texto[:TAMANHO_MAXIMO]


def validar_resultado(dados: dict) -> dict:
    """Garante que a IA devolveu valores permitidos."""
    categoria = str(dados.get("categoria", "")).strip().lower()
    urgencia = str(dados.get("urgencia", "")).strip().lower()
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoria inválida retornada: {categoria!r}")
    if urgencia not in URGENCIAS:
        raise ValueError(f"Urgência inválida retornada: {urgencia!r}")
    return {
        "categoria": categoria,
        "urgencia": urgencia,
        "justificativa": str(dados.get("justificativa", "")).strip(),
    }


# --------------------------------------------------------------------------
# Plano B: regras de palavras-chave (funciona offline)
# --------------------------------------------------------------------------
def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


# A ordem importa: a primeira categoria encontrada vence (da mais grave para a menos grave).
PALAVRAS_CATEGORIA = [
    ("assedio", ["assedi", "importun", "passou a mao", "me seguindo", "seguindo",
                 "cantada", "gracinha", "mexendo com", "carona"]),
    ("roubo_furto", ["roub", "furt", "assalt", "arromb", "levaram", "puxou",
                     "abordando", "abordad"]),
    ("vandalismo", ["pichad", "pichac", "picharam", "quebra", "quebrar", "destru",
                    "depred", "vandal"]),
    ("iluminacao", ["poste", "lampada", "luz", "escur", "iluminac", "breu", "apagad"]),
]

PALAVRAS_URGENCIA_ALTA = ["agora", "socorro", "arma", "faca", "revolver", "tiro",
                          "me seguindo", "acabei de", "faisca", "choque"]


def classificar_por_regras(texto: str) -> dict:
    texto = validar_texto(texto)
    normal = _normalizar(texto)

    categoria = "outros"
    for nome, palavras in PALAVRAS_CATEGORIA:
        if any(p in normal for p in palavras):
            categoria = nome
            break

    if any(p in normal for p in PALAVRAS_URGENCIA_ALTA):
        urgencia = "alta"
    elif categoria in ("roubo_furto", "assedio"):
        urgencia = "media"
    else:
        urgencia = "baixa"

    return {
        "categoria": categoria,
        "urgencia": urgencia,
        "justificativa": "Classificado por palavras-chave (modo sem IA).",
        "origem": "regras",
    }


# --------------------------------------------------------------------------
# IA generativa: Gemini
# --------------------------------------------------------------------------
_cliente = None


def _cliente_gemini():
    global _cliente
    if _cliente is None:
        chave = os.getenv("GEMINI_API_KEY")
        if not chave:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Crie o arquivo .env na raiz do projeto "
                "(copie o .env.example) e coloque a chave nele."
            )
        from google import genai  # importado aqui para o modo regras não depender do pacote
        from google.genai import types

        # timeout em milissegundos: a chamada nunca fica travada mais de 60 s
        _cliente = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=60_000))
    return _cliente


def classificar_com_gemini(texto: str, tentativas: int = 4) -> dict:
    from google.genai import types

    texto = validar_texto(texto)
    cliente = _cliente_gemini()
    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            resposta = cliente.models.generate_content(
                model=MODELO_GEMINI,
                contents=montar_prompt_usuario(texto),
                config=types.GenerateContentConfig(
                    system_instruction=PROMPT_SISTEMA,
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            resultado = validar_resultado(json.loads(resposta.text))
            resultado["origem"] = "gemini"
            return resultado
        except Exception as erro:  # limite de requisições, JSON inválido etc.
            ultimo_erro = erro
            print(f"[tentativa {tentativa + 1}/{tentativas}] {erro}", file=sys.stderr)
            if tentativa < tentativas - 1:
                espera = 5 * 2 ** tentativa  # 5 s, 10 s, 20 s...
                print(f"    nova tentativa em {espera} s", file=sys.stderr)
                time.sleep(espera)
    raise RuntimeError(f"Gemini falhou após {tentativas} tentativas: {ultimo_erro}")


# --------------------------------------------------------------------------
# Função principal usada pelo resto do sistema
# --------------------------------------------------------------------------
def classificar(texto: str, usar_ia: bool = True, tentativas: int = 4) -> dict:
    """Classifica com o Gemini e, se não der, cai para as regras.

    A API usa tentativas=1 para o cidadão não ficar esperando: se o Gemini
    não responder de primeira, as regras assumem na hora.
    Com VIGIA_USAR_IA=0 no .env, a IA fica desligada (útil em testes e no CI).
    """
    if os.getenv("VIGIA_USAR_IA", "1") == "0":
        usar_ia = False
    if usar_ia:
        try:
            return classificar_com_gemini(texto, tentativas=tentativas)
        except ValueError:
            raise  # entrada inválida: não adianta tentar as regras
        except Exception as erro:
            print(f"[aviso] usando regras: {erro}", file=sys.stderr)
    return classificar_por_regras(texto)


if __name__ == "__main__":
    argumentos = sys.argv[1:]
    usar_ia = True
    if argumentos and argumentos[0] == "--regras":
        usar_ia = False
        argumentos = argumentos[1:]
    if not argumentos:
        print('Uso: python classificador.py [--regras] "texto do relato"')
        sys.exit(1)
    try:
        resultado = classificar(" ".join(argumentos), usar_ia=usar_ia)
    except ValueError as erro:
        print(f"Erro: {erro}")
        sys.exit(1)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
