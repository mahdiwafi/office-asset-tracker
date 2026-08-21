# Runtime image for the frontend, hosted on Azure Container Apps.
#
# Two stages: the build stage compiles the Next.js app with the
# NEXT_PUBLIC_* values baked in (that is what they are FOR — the SPA must
# carry them publicly; the API trusts the token, never the app). The
# runtime stage ships only the `standalone` output: server.js plus the
# minimal node_modules, the static assets, and public/. No node_modules
# install at runtime, no dev server — exactly what `output: 'standalone'`
# in next.config.ts was prepared for.

FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_ENTRA_CLIENT_ID
ARG NEXT_PUBLIC_ENTRA_TENANT_ID
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_ENTRA_CLIENT_ID=$NEXT_PUBLIC_ENTRA_CLIENT_ID \
    NEXT_PUBLIC_ENTRA_TENANT_ID=$NEXT_PUBLIC_ENTRA_TENANT_ID \
    NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE

RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

# The standalone server listens on PORT (default 3000) — the container
# app's ingress target port is 3000 to match.
CMD ["node", "server.js"]
