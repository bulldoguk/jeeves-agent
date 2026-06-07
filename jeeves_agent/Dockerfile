ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

ARG ADDON_VERSION=unknown
COPY jeeves/ ./jeeves/
COPY entrypoint.py ./

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
