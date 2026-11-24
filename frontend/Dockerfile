FROM node:22-alpine

WORKDIR /app

RUN corepack enable

# rewrite правила next.js запекаются на этапе сборки поэтому адрес бэкенда нужен до pnpm build
ARG BACKEND_ORIGIN=http://localhost:8000
ENV BACKEND_ORIGIN=$BACKEND_ORIGIN

# публичный адрес сайта: ссылка входа должна вести на тот же хост куда вернётся google
# next.js инлайнит NEXT_PUBLIC_* на этапе сборки поэтому тоже build-arg
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# рантайм без root
USER node

EXPOSE 3000

CMD ["pnpm", "start"]
