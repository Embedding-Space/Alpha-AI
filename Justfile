# Start the stack
up:
    cd frontend && npm install && npm run build
    docker compose build
    docker compose up -d
