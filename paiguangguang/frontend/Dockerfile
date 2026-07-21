FROM node:20-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS builder
WORKDIR /app
ARG NEXT_PUBLIC_BACKEND_URL=
ARG NEXT_PUBLIC_CHATBOT_ENABLED=true
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}
ENV NEXT_PUBLIC_CHATBOT_ENABLED=${NEXT_PUBLIC_CHATBOT_ENABLED}
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs
COPY --from=builder --chown=nextjs:nextjs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nextjs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nextjs /app/.next ./.next
COPY --from=builder --chown=nextjs:nextjs /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/next.config.mjs ./next.config.mjs
USER nextjs
EXPOSE 3000
CMD ["npm", "start"]
