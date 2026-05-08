#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

DEPLOY_HOST="${DEPLOY_HOST:-185.50.38.175}"
DEPLOY_PORT="${DEPLOY_PORT:-3031}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_KEY="${DEPLOY_KEY:-$HOME/.ssh/neveshteh_github_actions_deploy_user}"
DEPLOY_APP_DIR="${DEPLOY_APP_DIR:-/var/www/neveshteh/app}"
REMOTE_SHAPEUP_DIR="${REMOTE_SHAPEUP_DIR:-$DEPLOY_APP_DIR/public-shapeup}"

if [[ ! -f "$DEPLOY_KEY" ]]; then
  echo "Deploy SSH key not found: $DEPLOY_KEY" >&2
  exit 1
fi

mkdocs build --strict

SHORT_SHA="$(git rev-parse --short HEAD)"
RELEASE_ID="$(date -u +%Y%m%d%H%M%S)-$SHORT_SHA"
REMOTE_RELEASE_DIR="$REMOTE_SHAPEUP_DIR/releases/$RELEASE_ID"
SSH_CMD=(ssh -p "$DEPLOY_PORT" -i "$DEPLOY_KEY" -o IdentitiesOnly=yes)

"${SSH_CMD[@]}" "$DEPLOY_USER@$DEPLOY_HOST" "mkdir -p '$REMOTE_RELEASE_DIR'"

rsync -az --delete \
  -e "${SSH_CMD[*]}" \
  "$ROOT_DIR/site/" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_RELEASE_DIR/"

"${SSH_CMD[@]}" "$DEPLOY_USER@$DEPLOY_HOST" <<REMOTE
set -euo pipefail
cd "$REMOTE_SHAPEUP_DIR"
ln -sfn "releases/$RELEASE_ID" current.next
mv -Tf current.next current
find releases -maxdepth 1 -mindepth 1 -type d | sort | head -n -5 | xargs -r rm -rf
REMOTE

echo "Shape Up deployed to $REMOTE_SHAPEUP_DIR/current"
