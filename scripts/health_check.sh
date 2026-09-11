#!/usr/bin/env bash
# Bash health check runner for WSL / Linux environment
set -e

echo "=== CogniNet-6G Linux Environment Health Check ==="
python3 scripts/health_check.py
