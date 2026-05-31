# Coolify (and local) builds: mirror SoLoTV catalog + package SoLoKodi repo at image build time.
# Mirrored ZIPs are not in git (.gitignore); they are fetched during docker build.

FROM python:3.12-alpine AS builder

WORKDIR /build

RUN apk add --no-cache ca-certificates

COPY scripts ./scripts
COPY src ./src
COPY public ./public

RUN python3 scripts/build_repo.py \
    && python3 scripts/verify_repo.py

# Build the rebranded SoLoTV build(s) from the Diggz foundation and publish our
# own build list. SOLOTV_TARGETS picks the Kodi target(s); leave empty to build
# every target in src/solotv_build/build.json (downloads ~166MB each). Default
# builds all targets so builds.xml lists every Kodi version (K21 + K22).
ARG SOLOTV_TARGETS=
RUN python3 scripts/build_solotv_build.py ${SOLOTV_TARGETS}

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/public /usr/share/nginx/html

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz || exit 1
