FROM node:24-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY frontend ./
ARG VITE_API_BASE_URL=same-origin
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm build

FROM nginx:1.29-alpine

ENV CAG_GATEWAY_UPSTREAM=host.docker.internal:8000

COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
