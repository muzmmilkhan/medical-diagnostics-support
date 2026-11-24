# syntax=docker/dockerfile:1

# ---- Build stage: static assets are platform-independent, so build natively ----
FROM --platform=$BUILDPLATFORM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

# ---- Runtime stage: unprivileged nginx serving the SPA and proxying /api ----
FROM nginxinc/nginx-unprivileged:alpine AS runtime
ENV BACKEND_URL=http://backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
