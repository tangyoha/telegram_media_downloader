FROM python:latest

WORKDIR /app

COPY . /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt


CMD ["python", "media_downloader.py"]
