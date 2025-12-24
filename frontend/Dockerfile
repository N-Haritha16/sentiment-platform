FROM node:18-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:18-alpine AS runtime
WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install serve
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]
