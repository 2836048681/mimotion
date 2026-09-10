#!/usr/bin/env python3
"""Create a Cloudflare Access app and an email allow policy using cloudflared's local certificate."""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_ROOT = "https://api.cloudflare.com/client/v4"


def load_credentials(cert_path: Path) -> tuple[str, str]:
    text = cert_path.read_text(encoding="utf-8")
    match = re.search(
        r"-----BEGIN ARGO TUNNEL TOKEN-----\s*(.*?)\s*-----END ARGO TUNNEL TOKEN-----",
        text,
        re.S,
    )
    if not match:
        raise RuntimeError("cloudflared cert.pem 格式无法识别")
    payload = json.loads(base64.b64decode("".join(match.group(1).split())))
    return payload["accountID"], payload["apiToken"]


def api_request(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        API_ROOT + path,
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare API {exc.code}: {detail}") from exc
    if not result.get("success"):
        raise RuntimeError(f"Cloudflare API 请求失败：{result.get('errors')}")
    return result


def ensure_access(account_id: str, token: str, domain: str, email: str) -> None:
    apps_path = f"/accounts/{account_id}/access/apps"
    apps = api_request(token, "GET", apps_path).get("result", [])
    app = next((item for item in apps if item.get("domain") == domain), None)
    if app is None:
        app = api_request(
            token,
            "POST",
            apps_path,
            {
                "name": "MiMotion Console",
                "domain": domain,
                "type": "self_hosted",
                "session_duration": "24h",
                "app_launcher_visible": False,
                "auto_redirect_to_identity": False,
            },
        )["result"]
        print(f"created app: {app['id']}")
    else:
        print(f"existing app: {app['id']}")

    policies_path = f"{apps_path}/{app['id']}/policies"
    policies = api_request(token, "GET", policies_path).get("result", [])
    expected_name = "Allow owner email"
    existing = next((item for item in policies if item.get("name") == expected_name), None)
    policy_payload = {
        "name": expected_name,
        "decision": "allow",
        "precedence": 1,
        "include": [{"email": {"email": email}}],
        "exclude": [],
        "require": [],
    }
    if existing is None:
        policy = api_request(token, "POST", policies_path, policy_payload)["result"]
        print(f"created policy: {policy['id']}")
    else:
        api_request(token, "PUT", f"{policies_path}/{existing['id']}", policy_payload)
        print(f"updated policy: {existing['id']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert", type=Path, default=Path.home() / ".cloudflared" / "cert.pem")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--inspect-organization", action="store_true")
    args = parser.parse_args()
    account_id, token = load_credentials(args.cert)
    if args.inspect_organization:
        result = api_request(token, "GET", f"/accounts/{account_id}/access/organizations")
        organization = result.get("result") or {}
        print(
            json.dumps(
                {key: organization.get(key) for key in ("name", "auth_domain", "created_at")},
                ensure_ascii=False,
            )
        )
        return
    ensure_access(account_id, token, args.domain, args.email)


if __name__ == "__main__":
    main()
