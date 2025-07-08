#!/bin/bash
set -e
PORT=${REACT_PORT:-5173}
HEADLESS=${HEADLESS:-true}

# Check if package.json exists and determine appropriate start command
if [ ! -f "/app/package.json" ]; then
    echo "Error: package.json not found in /app/"
    exit 1
fi

# Try to determine the correct start command
if grep -q "\"preview\"" /app/package.json; then
    START_CMD="npm run preview -- --host 0.0.0.0 --port $PORT"
elif grep -q "\"dev\"" /app/package.json; then
    START_CMD="npm run dev -- --host 0.0.0.0 --port $PORT"
elif grep -q "\"start\"" /app/package.json; then
    START_CMD="npm start"
else
    echo "Error: No suitable npm script found (preview, dev, or start)"
    exit 1
fi

# Use custom start command if provided
if [ -n "" ]; then
    START_CMD="npm run preview -- --host 0.0.0.0 --port $PORT"
fi

echo "Package.json contents:"
cat /app/package.json
echo ""
echo "Running: $START_CMD"

# Start React app in background and capture PID
bash -c "$START_CMD" > /app/preview.log 2>&1 &
APP_PID=$!

# Wait for port to be open with more detailed logging
echo "Waiting for React app on port $PORT..."
for i in {1..30}; do
  if nc -z localhost $PORT 2>/dev/null; then
    echo "Port $PORT is now open!"
    break
  fi
  echo "Attempt $i/30: Waiting for React app on port $PORT..."
  sleep 1
done

# Check if port is open and app is still running
if ! nc -z localhost $PORT 2>/dev/null; then
  echo "Preview server failed to start. App process status:"
  if kill -0 $APP_PID 2>/dev/null; then
    echo "App process is still running (PID: $APP_PID)"
  else
    echo "App process has died"
  fi
  echo ""
  echo "Preview log output:"
  cat /app/preview.log
  echo ""
  echo "Checking if React app built successfully..."
  if [ -d "/app/dist" ]; then
    echo "dist/ directory found"
    ls -la /app/dist/
  elif [ -d "/app/build" ]; then
    echo "build/ directory found"  
    ls -la /app/build/
  else
    echo "No dist/ or build/ directory found"
  fi
  exit 1
fi

echo "React app is running on port $PORT, starting Playwright tests..."

# Run Playwright test
cd /app
python /app/playwright_test.py

# Kill the React app process
if kill -0 $APP_PID 2>/dev/null; then
  kill $APP_PID
fi

# Copy results to mounted output directory
if [ -f "/app/test_results.json" ]; then
  cp /app/test_results.json /app/output/
  echo "Results copied to output directory"
else
  echo "No test results found"
  exit 1
fi
