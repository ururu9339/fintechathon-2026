FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build:web
EXPOSE 3000
CMD ["npx", "--yes", "serve", "dist", "-l", "3000"]
