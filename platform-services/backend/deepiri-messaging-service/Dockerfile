# Build shared-utils first
FROM node:20-alpine AS shared-utils-builder
WORKDIR /shared-utils
COPY shared/deepiri-shared-utils/package*.json ./
COPY shared/deepiri-shared-utils/tsconfig.json ./
COPY shared/deepiri-shared-utils/src ./src

RUN rm -f package-lock.json && rm -f package-lock.json && npm install --legacy-peer-deps && \
    npm run build && \
    npm cache clean --force

# Build main service
FROM ghcr.io/team-deepiri/deepiri-base:20-alpine

# Copy package files
COPY backend/deepiri-messaging-service/package*.json ./
COPY backend/deepiri-messaging-service/tsconfig.json ./

# Install dependencies, including shared-utils from GitHub Packages
RUN --mount=type=secret,id=github_token \
    { echo "@team-deepiri:registry=https://npm.pkg.github.com"; \
      echo "//npm.pkg.github.com/:_authToken=$(cat /run/secrets/github_token)"; \
    } > .npmrc \
 && npm install --legacy-peer-deps \
 && npm cache clean --force \
 && echo "@team-deepiri:registry=https://npm.pkg.github.com" > .npmrc
# Copy built shared-utils
COPY --from=shared-utils-builder /shared-utils /shared-utils

# Install dependencies (including shared-utils as file dependency)
RUN rm -f package-lock.json && rm -f package-lock.json && npm install --legacy-peer-deps file:/shared-utils && \
    npm cache clean --force

# Copy source code
COPY backend/deepiri-messaging-service/src ./src
COPY backend/deepiri-messaging-service/prisma ./prisma

# Generate Prisma client
RUN npx prisma generate

# Build TypeScript
RUN npm run build

# Expose port
EXPOSE 5009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5009/health || exit 1

# Start server
CMD ["npm", "start"]
