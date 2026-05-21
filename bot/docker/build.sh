#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."
docker build -t hashtag-ideas-bot:latest .
echo "OK: hashtag-ideas-bot:latest"
echo "Next: docker compose run --rm -it bot python main.py --login"
echo "       docker compose up -d"
