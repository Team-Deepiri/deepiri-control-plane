FROM ghcr.io/team-deepiri/deepiri-base:18-alpine

# Copy service package files
COPY backend/deepiri-engagement-service/package*.json ./
COPY backend/deepiri-engagement-service/tsconfig.json ./

# SINGLE atomic install (this is the critical fix)
RUN --mount=type=secret,id=github_token \
    { echo "@team-deepiri:registry=https://npm.pkg.github.com"; \
      echo "//npm.pkg.github.com/:_authToken=$(cat /run/secrets/github_token)"; \
    } > .npmrc \
 && npm config set fetch-retries 5 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-retry-maxtimeout 120000 \
 && npm config set fetch-timeout 300000 \
 && npm install --legacy-peer-deps \
 && npm cache clean --force \
 && echo "@team-deepiri:registry=https://npm.pkg.github.com" > .npmrc
 && rm -f package-lock.json && npm install --legacy-peer-deps \
 && npm run build

# ===============================
# Build engagement-service
# ===============================
FROM node:18-alpine
WORKDIR /app

RUN apk add --no-cache curl dumb-init openssl bash

# Copy K8s env loader scripts
COPY --chown=root:root shared/scripts/load-k8s-env.sh /usr/local/bin/load-k8s-env.sh
COPY --chown=root:root shared/scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/load-k8s-env.sh /usr/local/bin/docker-entrypoint.sh

# Copy service package files (lock is committed for reproducible installs)
COPY backend/deepiri-engagement-service/package.json ./
COPY backend/deepiri-engagement-service/package-lock.json ./
COPY backend/deepiri-engagement-service/tsconfig.json ./

# Copy built shared-utils to the path declared in package.json
# (file:../../shared/deepiri-shared-utils resolves from /app to /shared/deepiri-shared-utils)
COPY --from=shared-utils-builder /shared-utils /shared/deepiri-shared-utils

# Deterministic install from committed lock
# --install-links is required so file: deps (shared-utils) are installed as
# real packages instead of symlinks, matching how the lock was generated.
RUN npm config set fetch-retries 5 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-retry-maxtimeout 120000 \
 && npm config set fetch-timeout 300000 \
 && npm ci --legacy-peer-deps --install-links \
 && npm cache clean --force

# Prisma schema (needed for generate during build)
COPY backend/deepiri-engagement-service/prisma ./prisma

# Source
COPY backend/deepiri-engagement-service/src ./src

# Build (includes prisma generate)
RUN npm run build

RUN mkdir -p logs \
 && chown -R nodejs:nodejs /app

USER nodejs

EXPOSE 5003

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5003/health || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/bin/dumb-init", "--", "node", "dist/server.js"]
