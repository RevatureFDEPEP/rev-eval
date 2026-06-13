#!/bin/bash

# Startup script for reporting-and-analytics-service.
# Stateless aggregator (no database of its own) — just start the API.

echo "🚀 Starting Reporting & Analytics Service..."
exec python main.py
