#!/bin/bash
# deploy.sh — run on the server after git clone/pull
set -e

echo "==> Installing system dependencies..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv

echo "==> Setting up virtualenv..."
cd /opt/reportsbot
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

echo "==> Installing systemd service..."
cp reportsbot.service /etc/systemd/system/reportsbot.service
systemctl daemon-reload
systemctl enable reportsbot
systemctl restart reportsbot

echo "==> Done! Status:"
systemctl status reportsbot --no-pager
