ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

ARG ADDON_VERSION=unknown
COPY jeeves/ ./jeeves/
COPY entrypoint.py ./

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
