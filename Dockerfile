# Imagem única do VigIA: a mesma imagem roda a API e as telas (muda só o comando).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /vigia

# Dependências primeiro: o Docker reaproveita esta camada quando só o código muda
COPY app/requirements.txt app/requirements.txt
RUN pip install -r app/requirements.txt

COPY . .

# Segurança: não rodar como root dentro do container
# /data guarda o banco SQLite; dados/lake guarda o data lake (os dois viram volumes no compose)
RUN useradd --create-home vigia \
    && mkdir -p /data /vigia/dados/lake \
    && chown -R vigia:vigia /vigia /data
USER vigia

EXPOSE 8000 8501
