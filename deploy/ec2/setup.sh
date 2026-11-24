#!/usr/bin/env bash
# Run once on a fresh EC2 instance (Amazon Linux 2023 or Ubuntu) to install Docker + Compose.
#   scp deploy/ec2/setup.sh ec2-user@<host>:~ && ssh ec2-user@<host> 'bash setup.sh'
set -euo pipefail

if command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y docker
  plugin_dir=/usr/local/lib/docker/cli-plugins
  sudo mkdir -p "$plugin_dir"
  sudo curl -fsSL -o "$plugin_dir/docker-compose" \
    "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)"
  sudo chmod +x "$plugin_dir/docker-compose"
elif command -v apt-get >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
else
  echo "Unsupported distribution: install Docker and the compose plugin manually." >&2
  exit 1
fi

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
sudo docker compose version

echo "Docker is ready. Log out and back in so '$USER' can run docker without sudo."
