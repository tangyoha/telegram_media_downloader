FROM python:3.11.2-alpine As compile-image

WORKDIR /app

COPY requirements.txt /app/

RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
    && pip install --trusted-host pypi.python.org -r requirements.txt \
    && apk del .build-deps && rm -rf requirements.txt

# install rclone
RUN apk add --no-cache ca-certificates && \
    wget https://downloads.rclone.org/rclone-current-linux-amd64.zip && \
    unzip rclone-current-linux-amd64.zip && \
    mv rclone-*-linux-amd64/rclone /app/rclone && \
    rm -rf rclone-*-linux-amd64 && \
    rm -rf rclone-current-linux-amd64.zip

FROM python:3.11.2-alpine As runtime-image

WORKDIR /app

COPY --from=tangyoha/telegram_media_downloader_compile:latest /app/rclone /app/rclone/rclone

COPY --from=tangyoha/telegram_media_downloader_compile:latest /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY config.yaml data.yaml setup.py media_downloader.py /app/
COPY module /app/module
COPY utils /app/utils

CMD ["python", "media_downloader.py"]
