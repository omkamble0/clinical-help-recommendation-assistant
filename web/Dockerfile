# ==============================================================================
# AegisMed Clinical AI - Production Frontend Web Container
# Multi-stage Next.js static export served via high-performance Nginx Alpine
# ==============================================================================

# Stage 1: Build Next.js application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies cleanly
COPY package*.json ./
RUN npm ci

# Copy source code and build
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 2: Minimalist High-Performance Nginx Alpine Runner (~25MB)
FROM nginx:alpine AS runner

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration (gzip, caching, reverse proxy, security headers)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static export from builder stage
COPY --from=builder /app/out /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
