#!/usr/bin/env bash
# Stores the CI/CD configuration in GitHub. Secret values are piped straight from their source
# into `gh`, never written to disk or shown on screen.
#
# Prerequisites: run deploy/aws/bootstrap.sh first; `gh auth login`; admin AWS credentials;
#                deploy/github/variables.env filled in (copy from variables.env.example).
#
# Usage:  deploy/github/set-secrets.sh
# Env:    SKIP_AWS_KEYS=1  don't create new IAM access keys (e.g. when re-running)
#         SKIP_APP_KEYS=1  don't create app keys (the EC2 instance profile is used for S3 instead)
#         PREFIX=...       must match the bootstrap.sh prefix (default: medical-diagnostics)
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
VARS_FILE="$HERE/variables.env"
PREFIX=${PREFIX:-medical-diagnostics}
CI_USER=${CI_USER:-$PREFIX-ci}
APP_USER=${APP_USER:-$PREFIX-app}

[ -f "$VARS_FILE" ] || { echo "Missing $VARS_FILE (copy variables.env.example)" >&2; exit 1; }
# shellcheck disable=SC1090
set -a; source "$VARS_FILE"; set +a

echo "==> Repository variables (from variables.env)"
gh variable set -f "$VARS_FILE"

echo "==> OPENAI_API_KEY (paste it at the prompt; input is hidden)"
gh secret set OPENAI_API_KEY

create_keys() { # <iam-user> <secret-name-for-id> <secret-name-for-secret>
  local id secret
  read -r id secret < <(aws iam create-access-key --user-name "$1" \
    --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text) || true
  if [ -z "${secret:-}" ]; then
    echo "   failed to create an access key for $1 (does the user exist? IAM allows max 2 keys)" >&2
    exit 1
  fi
  printf '%s' "$id" | gh secret set "$2"
  printf '%s' "$secret" | gh secret set "$3"
  echo "   created access key $id for $1"
}

if [ "${SKIP_AWS_KEYS:-0}" != 1 ]; then
  echo "==> AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (IAM user $CI_USER, ECR push)"
  create_keys "$CI_USER" AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
  if [ "${SKIP_APP_KEYS:-0}" != 1 ]; then
    echo "==> APP_AWS_ACCESS_KEY_ID / APP_AWS_SECRET_ACCESS_KEY (IAM user $APP_USER, S3 uploads)"
    create_keys "$APP_USER" APP_AWS_ACCESS_KEY_ID APP_AWS_SECRET_ACCESS_KEY
  fi
fi

echo
gh secret list
gh variable list
