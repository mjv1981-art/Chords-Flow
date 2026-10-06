FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js jsconfig.json postcss.config.js tailwind.config.js ./
COPY src ./src
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 bayanflow
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY server ./server
COPY --from=frontend /build/dist ./dist
COPY scripts/start-web.sh ./scripts/start-web.sh
USER bayanflow
EXPOSE 8000
CMD ["bash", "scripts/start-web.sh"]
