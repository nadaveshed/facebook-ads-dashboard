FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# Create assets directory
RUN mkdir -p /app/assets

# Expose port
EXPOSE 3001

# Start the server
CMD ["npm", "start"]
