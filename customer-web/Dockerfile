# Customer web: static SPA built with Vite, served by nginx.
# Build context is this folder:  docker build -t customer-web customer-web
# (on Railway, set the service Root Directory to customer-web).

# ---- build ----
FROM node:22-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the bundle at build time, like the Staff web. Railway passes
# service variables to the build as build args.
ARG VITE_BACKEND_API_URL
ENV VITE_BACKEND_API_URL=$VITE_BACKEND_API_URL
# Optional Customer accounts (US-078). The publishable key is public by design;
# never pass the service-role key here.
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_PUBLISHABLE_KEY=$VITE_SUPABASE_PUBLISHABLE_KEY

RUN npm run build

# ---- serve ----
FROM nginx:1.27-alpine

# The nginx image renders /etc/nginx/templates/*.template with envsubst at
# start-up, so the server listens on Railway's $PORT. 8080 is the local default.
ENV PORT=8080
# Same URL the bundle calls, for the CSP connect-src (nginx.conf.template).
ARG VITE_BACKEND_API_URL=http://127.0.0.1:8000
ENV BACKEND_ORIGIN=$VITE_BACKEND_API_URL
# Supabase Auth URL for the CSP connect-src. Empty when accounts are off; it must
# still be defined, or nginx's envsubst leaves "${SUPABASE_ORIGIN}" in the header.
ARG VITE_SUPABASE_URL=
ENV SUPABASE_ORIGIN=$VITE_SUPABASE_URL
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
