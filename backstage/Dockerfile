# Backstage image, built entirely inside Docker (no Node.js needed on your laptop).
# Based on the multi-stage build from https://backstage.io/docs/deployment/docker
# No apt packages needed: the SQLite driver (better-sqlite3) ships prebuilt binaries.
# No BuildKit-only syntax, so Terraform's Docker provider can build it too.
# Build:  docker build -t idp-backstage:local backstage/      (takes ~10 minutes the first time)

# ---- 1. install all dependencies (only re-runs when package.json/yarn.lock change)
FROM node:22-bookworm-slim AS packages
WORKDIR /app
COPY backstage.json package.json yarn.lock .yarnrc.yml ./
COPY .yarn ./.yarn
COPY packages packages
COPY plugins plugins
# keep only the package.json files so this layer caches well
RUN find packages plugins \! -name "package.json" -mindepth 2 -maxdepth 2 -exec rm -rf {} \+

FROM node:22-bookworm-slim AS build
USER node
WORKDIR /app
COPY --from=packages --chown=node:node /app .
RUN yarn install --immutable
COPY --chown=node:node . .
# type-check, then build the frontend + backend bundles
RUN yarn tsc && yarn --cwd packages/backend build
RUN mkdir packages/backend/dist/skeleton packages/backend/dist/bundle \
    && tar xzf packages/backend/dist/skeleton.tar.gz -C packages/backend/dist/skeleton \
    && tar xzf packages/backend/dist/bundle.tar.gz -C packages/backend/dist/bundle

# ---- 2. small runtime image with production dependencies only
FROM node:22-bookworm-slim
USER node
WORKDIR /app
ENV NODE_ENV=production NODE_OPTIONS="--no-node-snapshot"
COPY --from=build --chown=node:node /app/.yarn ./.yarn
COPY --from=build --chown=node:node /app/.yarnrc.yml /app/backstage.json ./
COPY --from=build --chown=node:node /app/yarn.lock /app/package.json /app/packages/backend/dist/skeleton/ ./
RUN yarn workspaces focus --all --production && rm -rf "$(yarn cache clean)"
COPY --from=build --chown=node:node /app/packages/backend/dist/bundle/ ./
COPY --chown=node:node app-config*.yaml ./
COPY --chown=node:node catalog ./catalog

EXPOSE 7007
CMD ["node", "packages/backend", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]
