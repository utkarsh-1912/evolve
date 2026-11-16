# évolvé production image for one Next.js workspace (citizen / counselor / eval-dashboard). SIMULATED, synthetic data.
# Build context = repo root (npm workspaces: apps import packages/ui and design/).
# NEXT_PUBLIC_API is inlined at build time, so it is a build arg.
# `--ignore-scripts` skips the eval dashboard's `prebuild` (python sync_evidence.py): the image ships the
# committed apps/eval-dashboard/data/*.json, so run `npm run sync -w evolve-eval-dashboard` before deploying.
FROM node:22-slim AS build
ARG APP_WORKSPACE=evolve-citizen
ARG NEXT_PUBLIC_API
ENV NEXT_PUBLIC_API=${NEXT_PUBLIC_API} \
    NEXT_TELEMETRY_DISABLED=1
WORKDIR /repo
COPY package.json package-lock.json ./
COPY packages/ packages/
COPY apps/ apps/
COPY design/ design/
RUN npm ci --no-audit --no-fund
RUN test -n "$NEXT_PUBLIC_API" && npm run build --ignore-scripts -w ${APP_WORKSPACE}

FROM node:22-slim
ARG APP_WORKSPACE=evolve-citizen
ENV APP_WORKSPACE=${APP_WORKSPACE} \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
WORKDIR /repo
COPY --from=build /repo /repo
EXPOSE 3000 3001 3002
# Each workspace's `start` script pins its port (3000 / 3001 / 3002).
CMD ["sh", "-c", "npm run start -w ${APP_WORKSPACE} -- --hostname 0.0.0.0"]
