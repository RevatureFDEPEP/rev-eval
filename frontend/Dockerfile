# Frontend Dockerfile (Multi-stage for development and production)

# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Run development server
# The dev script in package.json includes -H 0.0.0.0 for Docker compatibility
CMD ["pnpm", "dev"]


# Production build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build-time environment variables (NEXT_PUBLIC_* vars must be set at build time)
# These are baked into the JavaScript bundle for client-side use
ARG NEXT_PUBLIC_API_GATEWAY_URL
ARG NEXT_PUBLIC_WORKOS_REDIRECT_URI
ARG NEXT_PUBLIC_INTERVIEW_WS_URL

ENV NEXT_PUBLIC_API_GATEWAY_URL=$NEXT_PUBLIC_API_GATEWAY_URL
ENV NEXT_PUBLIC_WORKOS_REDIRECT_URI=$NEXT_PUBLIC_WORKOS_REDIRECT_URI
ENV NEXT_PUBLIC_INTERVIEW_WS_URL=$NEXT_PUBLIC_INTERVIEW_WS_URL

# Build the application
RUN pnpm build


# Production runtime stage
FROM node:20-alpine AS production

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install production dependencies only
RUN pnpm install --prod --frozen-lockfile

# Copy built application from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
# Note: next.config.js is optional in Next.js 16

# Create a non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001 && \
    chown -R nextjs:nodejs /app

USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Run the application
CMD ["pnpm", "start"]