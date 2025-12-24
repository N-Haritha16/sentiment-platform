# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm config set registry https://registry.npmjs.org/ \
 && npm install \
      --fetch-retries=5 \
      --fetch-retry-factor=2 \
      --fetch-retry-mintimeout=20000 \
      --fetch-timeout=120000

# Copy the rest of the code (including index.html and src/)
COPY . .

# Build Vite app -> dist/
RUN npm run build

# Runtime stage: serve the built app
FROM node:18-alpine AS runtime

WORKDIR /app

# Copy built files
COPY --from=build /app/dist ./dist

# Install a tiny static file server
RUN npm install serve

# Serve dist on port 3000
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]
