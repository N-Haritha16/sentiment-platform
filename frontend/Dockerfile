# Build stage
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm config set registry https://registry.npmjs.org/ \
 && npm install

COPY . .

# IMPORTANT: Vite build
RUN npm run build

# Runtime stage
FROM node:18-alpine

WORKDIR /app

COPY --from=build /app/dist ./dist

RUN npm install -g serve

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
