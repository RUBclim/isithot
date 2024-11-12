FROM python:3.13-slim-bookworm

RUN : \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        wait-for-it \
        wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY ./web/requirements.txt web-requirements.txt
COPY ./web/isithot/requirements.txt isithot-requirements.txt

ENV \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_CACHE=1

RUN pip install wheel uv
RUN uv pip install --system -r isithot-requirements.txt -r web-requirements.txt

COPY web web
COPY database database

RUN pybabel compile -d web/isithot/translations
