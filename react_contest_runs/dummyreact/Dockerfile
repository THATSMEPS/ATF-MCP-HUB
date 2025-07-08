FROM mcr.microsoft.com/playwright/python:v1.44.0-focal

# Install Node.js and other dependencies
RUN apt-get update &&     apt-get install -y curl netcat &&     curl -fsSL https://deb.nodesource.com/setup_current.x | bash - &&     apt-get install -y nodejs &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package files first for better caching
COPY code/package*.json /app/
RUN npm install

# Copy rest of the code
COPY code/ /app/
COPY run_all.sh /app/run_all.sh

# Install Python dependencies
RUN pip install --upgrade pip && pip install playwright
RUN playwright install --with-deps

# Build the React app if build command is provided
RUN if [ -f package.json ] && grep -q "\"build\"" package.json; then npm run build; fi

# Ensure run_all.sh is executable
RUN chmod +x /app/run_all.sh

# Create output directory for volume mounting
RUN mkdir -p /app/output
VOLUME /app/output

EXPOSE 5173

CMD ["/bin/bash", "/app/run_all.sh"]