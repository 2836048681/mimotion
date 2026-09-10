#!/usr/bin/env bash
set -euo pipefail

release_dir="${1:-/tmp/mimotion-release-20260910}"
app_dir="/opt/mimotion"
config_dir="/etc/mimotion"
data_dir="/var/lib/mimotion"

id mimotion >/dev/null 2>&1 || useradd --system --home-dir "$data_dir" --shell /usr/sbin/nologin mimotion
install -d -o mimotion -g mimotion -m 0750 "$app_dir" "$data_dir"
install -d -o root -g root -m 0750 "$config_dir"

cp -a "$release_dir"/. "$app_dir"/
chown -R mimotion:mimotion "$app_dir"

if [[ ! -x "$app_dir/.venv/bin/pip" ]]; then
  rm -rf "$app_dir/.venv"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
  python3 -m venv "$app_dir/.venv"
fi
"$app_dir/.venv/bin/python" -m pip install --disable-pip-version-check -r "$app_dir/requirements.txt"

if [[ ! -f "$config_dir/mimotion.env" ]]; then
  CONFIG_DIR="$config_dir" DATA_DIR="$data_dir" python3 - <<'PY'
import os
import secrets
import string
from pathlib import Path

alphabet = string.ascii_letters + string.digits
token_key = "".join(secrets.choice(alphabet) for _ in range(16))
content = "\n".join(
    [
        f"MIMOTION_DATA_DIR={os.environ['DATA_DIR']}",
        f"MIMOTION_TOKEN_FILE={os.environ['DATA_DIR']}/encrypted_tokens.data",
        f"MIMOTION_MASTER_KEY={secrets.token_hex(32)}",
        f"MIMOTION_TOKEN_AES_KEY={token_key}",
        "",
    ]
)
path = Path(os.environ["CONFIG_DIR"]) / "mimotion.env"
path.write_text(content, encoding="utf-8")
path.chmod(0o600)
PY
fi

install -o root -g root -m 0644 "$app_dir/deploy/mimotion-web.service" /etc/systemd/system/mimotion-web.service
install -o root -g root -m 0644 "$app_dir/deploy/mimotion-run.service" /etc/systemd/system/mimotion-run.service
install -o root -g root -m 0644 "$app_dir/deploy/mimotion-run.timer" /etc/systemd/system/mimotion-run.timer

systemctl daemon-reload
systemctl disable --now mimotion-run.timer >/dev/null 2>&1 || true
systemctl enable --now mimotion-web.service
