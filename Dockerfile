FROM python:3.11.9-alpine As compile-image

WORKDIR /app

COPY requirements.txt /app/

RUN apk add --no-cache --virtual .build-deps \
    gcc g++ musl-dev git \
    cmake make pkgconfig \
    linux-headers \
    jpeg-dev zlib-dev \
    && pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt \
    && apk del .build-deps && rm -rf requirements.txt

RUN apk add --no-cache rclone

FROM python:3.11.9-alpine As runtime-image

WORKDIR /app

COPY --from=tangyoha/telegram_media_downloader_compile:latest /usr/bin/rclone /app/rclone/rclone

COPY --from=tangyoha/telegram_media_downloader_compile:latest /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY config.yaml data.yaml setup.py media_downloader.py /app/
COPY module /app/module
COPY utils /app/utils

CMD ["python", "media_downloader.py"]
