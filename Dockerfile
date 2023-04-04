FROM python:3-alpine

WORKDIR /app

COPY config.yaml data.yaml setup.py media_downloader.py requirements.txt /app/
COPY module /app/mdoule
COPY utils /app/utils

RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
    && pip install --trusted-host pypi.python.org -r requirements.txt \
    && apk del .build-deps && rm -rf requirements.txt

CMD ["python", "media_downloader.py"]
