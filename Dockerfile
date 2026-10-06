FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; \
    npm ci --no-audit --no-fund
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
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --no-cache-dir -r server/requirements.txt
COPY --chown=10001:10001 server ./server
COPY --from=frontend --chown=10001:10001 /build/dist ./dist
COPY --chown=10001:10001 scripts/start-web.sh ./scripts/start-web.sh
USER bayanflow
EXPOSE 8000
CMD ["bash", "scripts/start-web.sh"]
