# Frontend — TanStack Start (Nitro node-server)
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files from app/ and root .env.example for VITE_ vars
COPY app/package.json app/package-lock.json ./
COPY app/bun.lock ./
COPY .env.example .env

# Install deps (npm, since bun not guaranteed on Railway)
RUN npm ci

# Copy frontend source
COPY app/ .

# Override vite config to use node-server preset for Railway
ENV NITRO_PRESET=node-server

# Build (produces dist/server/ with a Node.js entry point)
RUN npm run build

# --- Production stage ---
FROM node:20-slim

WORKDIR /app

# Copy built output (nitro node-server outputs to .output/)
COPY --from=builder /app/.output ./.output
COPY --from=builder /app/package.json ./

EXPOSE 3000

# Nitro node-server entry point
CMD ["node", ".output/server/index.mjs"]
