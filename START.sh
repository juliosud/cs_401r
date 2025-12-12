#!/bin/bash

# Startup script for Referral Email System UI

echo "=========================================="
echo "Starting Referral Email System"
echo "=========================================="

# Check if in correct directory
if [ ! -f "START.sh" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Auto-configure webhook URL if .env doesn't exist
if [ ! -f "client/.env" ]; then
    echo "Configuring webhook URL from AWS..."
    WEBHOOK_URL=$(aws cloudformation describe-stacks \
        --stack-name referral-email-system \
        --query 'Stacks[0].Outputs[?OutputKey==`WebhookURL`].OutputValue' \
        --output text \
        --region us-east-1 2>/dev/null)
    
    if [ -n "$WEBHOOK_URL" ]; then
        echo "VITE_WEBHOOK_URL=$WEBHOOK_URL" > client/.env
        echo "✓ Webhook URL configured: $WEBHOOK_URL"
    else
        echo "⚠ Could not fetch webhook URL from AWS. Using local dev mode."
        echo "VITE_WEBHOOK_URL=http://localhost:8000/webhook" > client/.env
    fi
fi

# Start Flask backend in background
echo "Starting Flask backend server (port 8000)..."
python3 server/app.py &
FLASK_PID=$!

# Wait for backend to start
sleep 2

# Check if client/node_modules exists
if [ ! -d "client/node_modules" ]; then
    echo "Installing client dependencies..."
    cd client
    npm install
    cd ..
fi

# Start React frontend
echo "Starting React frontend (port 3000)..."
cd client
npm run dev &
VITE_PID=$!
cd ..

echo ""
echo "=========================================="
echo "✓ System Started!"
echo "=========================================="
echo ""
echo "Backend API:  http://localhost:8000"
echo "Frontend UI:  http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "kill $FLASK_PID $VITE_PID 2>/dev/null; exit" INT
wait
