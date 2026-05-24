# Optimized Development Dockerfile for Next.js
FROM node:18-alpine

WORKDIR /app

# Install dependencies first (leverage cache)
COPY package.json package-lock.json* ./
RUN npm install

# Copy application code
COPY . .

# Environment variables for development
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development

# Expose port
EXPOSE 3000

# Next.js dev server
CMD ["npm", "run", "dev"]
