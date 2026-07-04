FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (layer cache)
COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* ./
RUN npm install --legacy-peer-deps

# Copy source only — node_modules stays from npm install above
COPY frontend/next.config.mjs frontend/tsconfig.json frontend/next-env.d.ts ./
COPY frontend/postcss.config.mjs frontend/tailwind.config.ts ./
COPY frontend/public ./public
COPY frontend/src ./src

ARG NEXT_PUBLIC_API_URL=http://localhost
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
