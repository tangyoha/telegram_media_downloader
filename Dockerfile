FROM python:3.11.9-alpine AS build

WORKDIR /app

# Build deps for pip packages that need compilation
RUN apk add --no-cache --virtual .build-deps gcc musl-dev

# Install python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install rclone (runtime binary)
RUN apk add --no-cache rclone

# (optional) clean build deps to keep build stage smaller
RUN apk del .build-deps


FROM python:3.11.9-alpine AS runtime

WORKDIR /app

# Copy installed deps & rclone from build stage
COPY --from=build /usr/bin/rclone /usr/bin/rclone
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy app source code (from build context: repo files)
COPY . /app

CMD ["python", "media_downloader.py"]

