# évolvé web image for one npm workspace (apps/citizen, later apps/counselor). SIMULATED, synthetic data only.
# Build context = repo root: the apps import packages/ui and design/tokens.css (docs/09 §2).
FROM node:22-slim

ARG APP_WORKSPACE=evolve-citizen
ARG NEXT_PUBLIC_API=http://localhost:8000
ENV NEXT_PUBLIC_API=${NEXT_PUBLIC_API} \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /repo
COPY package.json package-lock.json ./
COPY packages/ packages/
COPY apps/ apps/
COPY design/ design/
RUN npm ci --no-audit --no-fund

EXPOSE 3000 3001
# Dev server on purpose for the demo: no build step to break on stage. Swap for `next build && next start`
# once the G4 Lighthouse run is done against a production build.
CMD ["sh", "-c", "npm run dev -w ${APP_WORKSPACE} -- --hostname 0.0.0.0"]
