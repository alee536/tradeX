# Development frontend image for 24TradeX (Vite dev server)
FROM node:22-bookworm-slim

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml ./
COPY frontend/lib ./lib

RUN pnpm install --frozen-lockfile

COPY frontend ./

EXPOSE 5173

ENV VITE_API_PROXY_TARGET=http://backend:8000

CMD ["pnpm", "run", "dev"]
