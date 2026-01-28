FROM node:20-alpine

WORKDIR /app

# Install serve for static file serving
RUN npm install -g serve

# Copy built files
COPY dist/ ./dist/

EXPOSE 5183

CMD ["serve", "-s", "dist", "-l", "5183"]
