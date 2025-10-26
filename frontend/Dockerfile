# Multi-stage build for Next.js frontend

# Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Runtime stage
FROM node:18-alpine AS runtime

# Set working directory
WORKDIR /app

# Install production dependencies only
RUN npm install -g next

# Copy built application from builder stage
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production

# Start the application
CMD ["node", "server.js"]