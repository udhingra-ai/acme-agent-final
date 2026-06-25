# Stage 1 — build the React app
FROM node:20-alpine AS builder
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2 — nginx with TLS + built React app
FROM nginx:alpine
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -subj "/CN=localhost/O=Acme Local Dev/C=US" \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem && \
    chmod 600 /etc/nginx/ssl/key.pem && \
    rm -f /etc/nginx/conf.d/default.conf

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/acme.conf
