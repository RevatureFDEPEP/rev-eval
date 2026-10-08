#!/usr/bin/env bash
# Start the Rev-Eval stack with Docker Compose and wait until Nginx serves it.
#
#   ./start.sh              base stack: only Nginx publishes ports (https://localhost)
#   ./start.sh --dev        add docker-compose.dev.yml: direct service, database and MinIO ports
#   ./start.sh --no-build   reuse existing images (combine with --dev if needed)
set -euo pipefail

cd "$(dirname "$0")"

files=(-f docker-compose.yml)
build=(--build)
for arg in "$@"; do
    case "$arg" in
        --dev) files+=(-f docker-compose.dev.yml) ;;
        --no-build) build=() ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop (or Colima) and try again." >&2
    exit 1
fi

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example (local development defaults)."
fi

docker compose "${files[@]}" up -d "${build[@]}"

echo "Waiting for https://localhost/health through Nginx ..."
for _ in $(seq 1 60); do
    if curl -skf https://localhost/health > /dev/null; then
        echo "Rev-Eval is up: https://localhost (self-signed certificate)"
        echo "Smoke test: ./scripts/smoke.sh   Stop: docker compose down"
        exit 0
    fi
    sleep 5
done

echo "The stack did not become healthy in time. Check: docker compose ps; docker compose logs" >&2
exit 1
