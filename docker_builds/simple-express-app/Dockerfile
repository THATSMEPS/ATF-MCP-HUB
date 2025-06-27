FROM node:24-alpine3.21

# Install git and grep
RUN apk add --no-cache git grep

# Set working directory
WORKDIR /app

# Clone the repository
RUN git clone https://github.com/udayvalera/simple-express-app.git .

# Install dependencies
RUN npm install

# Set default port
ENV DEFAULT_PORT=3000

# Set up entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'PORT=\3000' >> /entrypoint.sh && \
    echo 'echo "Using port: \3000"' >> /entrypoint.sh && \
    echo 'if [ -f "package.json" ]; then' >> /entrypoint.sh && \
    echo '  main_file=$(node -p "require(\"./package.json\").main || \"index.js\"")' >> /entrypoint.sh && \
    echo '  PORT=\3000 node "$main_file"' >> /entrypoint.sh && \
    echo 'else' >> /entrypoint.sh && \
    echo '  PORT=\3000 node index.js' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

EXPOSE $3000
CMD ["/entrypoint.sh"]
