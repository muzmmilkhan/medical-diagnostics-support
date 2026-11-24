#!/usr/bin/env bash
# Run once on a fresh EC2 instance (Amazon Linux 2023 or Ubuntu).
# Installs what the app and the self-hosted GitHub runner need: Docker Engine, the Compose and
# Buildx plugins, git, and curl.
#   scp -i key.pem deploy/ec2/*.sh ec2-user@<host>:~ && ssh -i key.pem ec2-user@<host> 'bash setup.sh'
set -euo pipefail

case "$(uname -m)" in
  x86_64) docker_arch=amd64 ;;
  aarch64) docker_arch=arm64 ;;
  *) echo "Unsupported CPU architecture: $(uname -m)" >&2; exit 1 ;;
esac

if command -v dnf >/dev/null 2>&1; then
  # Amazon Linux 2023: the distro docker package ships without the compose/buildx plugins.
  sudo dnf install -y docker git tar gzip
  plugin_dir=/usr/local/lib/docker/cli-plugins
  sudo mkdir -p "$plugin_dir"

  sudo curl -fsSL -o "$plugin_dir/docker-compose" \
    "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)"

  buildx_tag=$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
    https://github.com/docker/buildx/releases/latest)
  buildx_tag=${buildx_tag##*/}
  sudo curl -fsSL -o "$plugin_dir/docker-buildx" \
    "https://github.com/docker/buildx/releases/download/${buildx_tag}/buildx-${buildx_tag}.linux-${docker_arch}"

  sudo chmod +x "$plugin_dir/docker-compose" "$plugin_dir/docker-buildx"
elif command -v apt-get >/dev/null 2>&1; then
  # Ubuntu/Debian: Docker's convenience script includes the compose and buildx plugins.
  sudo apt-get update -y
  sudo apt-get install -y git curl
  curl -fsSL https://get.docker.com | sudo sh
else
  echo "Unsupported distribution: install Docker, compose, buildx and git manually." >&2
  exit 1
fi

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
sudo docker compose version
sudo docker buildx version

echo "Docker is ready. Next: install the GitHub runner with install-runner.sh (see deploy/README.md)."
