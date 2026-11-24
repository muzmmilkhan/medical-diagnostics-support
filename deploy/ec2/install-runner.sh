#!/usr/bin/env bash
# Installs a GitHub Actions self-hosted runner on this EC2 instance as a systemd service.
# Run on the instance after setup.sh, as the user that owns the deployment (e.g. ec2-user).
#
# 1. On your laptop, get a registration token (valid for 1 hour):
#      gh api -X POST repos/<owner>/<repo>/actions/runners/registration-token --jq .token
# 2. On the instance:
#      RUNNER_TOKEN=<token> bash install-runner.sh <owner>/<repo>
#
# Env: RUNNER_LABELS (default "production"; self-hosted,Linux,<arch> are added automatically)
#      RUNNER_NAME   (default: hostname)
#      RUNNER_DIR    (default: ~/actions-runner)
set -euo pipefail

REPO=${1:?usage: RUNNER_TOKEN=<token> $0 <owner>/<repo>}
: "${RUNNER_TOKEN:?Set RUNNER_TOKEN to a runner registration token}"
RUNNER_DIR=${RUNNER_DIR:-$HOME/actions-runner}
RUNNER_NAME=${RUNNER_NAME:-$(hostname -s)}
RUNNER_LABELS=${RUNNER_LABELS:-production}

if ! id -nG "$USER" | grep -qw docker; then
  echo "$USER is not in the docker group. Run setup.sh first." >&2
  exit 1
fi

case "$(uname -m)" in
  x86_64) arch=x64 ;;
  aarch64) arch=arm64 ;;
  *) echo "Unsupported CPU architecture: $(uname -m)" >&2; exit 1 ;;
esac

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [ ! -x ./config.sh ]; then
  version=$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
    https://github.com/actions/runner/releases/latest)
  version=${version##*/v}
  echo "==> Downloading actions/runner v$version ($arch)"
  curl -fsSL -o runner.tar.gz \
    "https://github.com/actions/runner/releases/download/v${version}/actions-runner-linux-${arch}-${version}.tar.gz"
  tar xzf runner.tar.gz
  rm runner.tar.gz
  sudo ./bin/installdependencies.sh || sudo dnf install -y libicu || true
fi

if [ -f .runner ]; then
  echo "==> Runner already configured; to re-register run: ./config.sh remove --token <token>"
else
  echo "==> Registering runner '$RUNNER_NAME' with labels: $RUNNER_LABELS"
  ./config.sh --unattended \
    --url "https://github.com/$REPO" \
    --token "$RUNNER_TOKEN" \
    --name "$RUNNER_NAME" \
    --labels "$RUNNER_LABELS" \
    --work _work
fi

[ -f .service ] || sudo ./svc.sh install "$USER"
sudo ./svc.sh start
sudo ./svc.sh status || true

echo "Runner installed. It should show as 'Idle' under Settings > Actions > Runners."
