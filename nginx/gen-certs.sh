#!/usr/bin/env bash
# Generates a self-signed TLS cert for local development.
# Output: nginx/certs/localhost.crt + localhost.key (gitignored — never commit)
set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/certs" && pwd)"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout "$CERT_DIR/localhost.key" \
  -out    "$CERT_DIR/localhost.crt" \
  -subj   "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Certs written to $CERT_DIR"
