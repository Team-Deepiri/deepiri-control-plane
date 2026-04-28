FROM ghcr.io/team-deepiri/deepiri-base:18-alpine

COPY shared/deepiri-shared-utils/package*.json /shared/deepiri-shared-utils/
COPY shared/deepiri-shared-utils/tsconfig.json /shared/deepiri-shared-utils/
COPY shared/deepiri-shared-utils/src /shared/deepiri-shared-utils/src
# Copy service package files
COPY backend/deepiri-notification-service/package*.json ./
COPY backend/deepiri-notification-service/tsconfig.json ./

# SINGLE atomic install
RUN npm config set fetch-retries 5 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-retry-maxtimeout 120000 \
 && npm config set fetch-timeout 300000 \
 && cd /shared/deepiri-shared-utils \
 && npm install --legacy-peer-deps \
 && npm run build \
 && cd /app \
 && npm install --legacy-peer-deps \
 && npm cache clean --force

# Source
COPY backend/deepiri-notification-service/src ./src

# Build
RUN npm run build

RUN mkdir -p logs \
 && chown -R nodejs:nodejs /app

USER nodejs

EXPOSE 5005

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5005/health || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/bin/dumb-init", "--", "node", "dist/server.js"]
