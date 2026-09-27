# Frontend — TanStack Start (Nitro node-server)
FROM node:20-slim AS builder

WORKDIR /app

# Railway automatically passes service env vars as Docker build args.
# Declare them so Vite can embed VITE_* into the client bundle at build time.
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ARG VITE_SUPABASE_PROJECT_ID
ARG VITE_BACKEND_API_URL
ARG VITE_CUSTOMER_WEB_URL
ARG BACKEND_API_URL

ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_PUBLISHABLE_KEY=$VITE_SUPABASE_PUBLISHABLE_KEY
ENV VITE_SUPABASE_PROJECT_ID=$VITE_SUPABASE_PROJECT_ID
ENV VITE_BACKEND_API_URL=$VITE_BACKEND_API_URL
ENV VITE_CUSTOMER_WEB_URL=$VITE_CUSTOMER_WEB_URL
ENV BACKEND_API_URL=$BACKEND_API_URL
ENV NITRO_PRESET=node-server

# Copy package files
COPY app/package.json app/package-lock.json ./
COPY app/bun.lock ./

# Install deps
RUN npm ci

# Copy frontend source
COPY app/ .

# Build (nitro node-server → .output/)
RUN npm run build

# --- Production stage ---
FROM node:20-slim

WORKDIR /app

# Runtime env vars (Railway injects these at runtime too)
ENV NODE_ENV=production
ENV NITRO_HOST=0.0.0.0
ENV NITRO_PORT=3000

# Copy built output
COPY --from=builder /app/.output ./.output

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
