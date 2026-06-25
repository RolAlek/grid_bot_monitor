FROM python:3.13-slim-bookworm AS build_env

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/requirements.txt && \
    python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt


FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgcc-s1 \
    libstdc++6 && \
    rm -rf /var/lib/apt/lists/*

ARG USERNAME=appuser
ARG USER_UID=10001
ARG USER_GID=$USER_UID

RUN addgroup --gid $USER_GID $USERNAME && \
    adduser --uid $USER_UID --ingroup $USERNAME --disabled-password --gecos "" $USERNAME && \
    mkdir -p /data && chown $USERNAME:$USERNAME /data

COPY --from=build_env /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    TZ="Europe/Moscow"

USER $USERNAME

WORKDIR /app

COPY ./source ./source
COPY ./alembic.ini .

CMD ["python", "-m", "source.main"]
