"""
Transfer ETH from Coinbase to deploy wallet via Coinbase Advanced Trade API.
Uses CDP Ed25519 key for authentication.
"""
import base64
import hashlib
import json
import sys
import time
import uuid

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric import ed25519


import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_ID = os.environ["CDP_API_KEY_ID"]
API_KEY_SECRET = os.environ["CDP_API_SECRET"]
BASE_URL = "https://api.coinbase.com"
DEPLOY_WALLET = os.environ.get("DEPLOY_WALLET", "0xB2Fae83de08b285cB3D6A77Ff520F6AD669D5f33")


def build_jwt(method, path):
    decoded = base64.b64decode(API_KEY_SECRET)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(decoded[:32])
    uri = f"{method} api.coinbase.com{path}"
    now = int(time.time())
    payload = {
        "sub": API_KEY_ID,
        "iss": "cdp",
        "aud": ["cdp_service"],
        "nbf": now,
        "exp": now + 120,
        "uris": [uri],
    }
    token = jwt.encode(
        payload, private_key, algorithm="EdDSA",
        headers={"kid": API_KEY_ID, "nonce": hashlib.sha256(uuid.uuid4().bytes).hexdigest()},
    )
    return token


def api_get(path, params=None):
    token = build_jwt("GET", path)
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params=params,
    )
    return resp


def api_post(path, body):
    token = build_jwt("POST", path)
    resp = requests.post(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
    )
    return resp


def main():
    # Step 1: List accounts to find ETH
    print("Listing Coinbase accounts...")
    resp = api_get("/api/v3/brokerage/accounts", {"limit": "50"})
    if not resp.ok:
        print(f"Error {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)

    data = resp.json()
    eth_account = None
    for acct in data.get("accounts", []):
        bal = acct.get("available_balance", {})
        val = float(bal.get("value", "0"))
        cur = bal.get("currency", "")
        if val > 0:
            print(f"  {acct['name']} | {cur} | {val}")
        if cur == "ETH" and val > 0:
            eth_account = acct

    if not eth_account:
        print("No ETH balance found on Coinbase!")
        sys.exit(1)

    eth_bal = float(eth_account["available_balance"]["value"])
    eth_uuid = eth_account["uuid"]
    print(f"\nETH account: {eth_uuid}")
    print(f"ETH balance: {eth_bal} ETH")

    # Step 2: Send 0.005 ETH to deploy wallet on Base
    send_amount = "0.005"
    print(f"\nSending {send_amount} ETH to {DEPLOY_WALLET} on Base...")

    # Create send request
    body = {
        "amount": send_amount,
        "currency": "ETH",
        "to": DEPLOY_WALLET,
        "network": "base",
        "idem": str(uuid.uuid4()),
    }

    # Use the v2 send endpoint
    send_path = f"/v2/accounts/{eth_uuid}/transactions"
    resp = api_post(send_path, {"type": "send", **body})

    if resp.ok:
        tx = resp.json()
        print(f"Transfer initiated!")
        print(json.dumps(tx, indent=2))
    else:
        print(f"Transfer error {resp.status_code}: {resp.text[:500]}")

        # Try alternative: crypto withdrawal via Advanced Trade
        print("\nTrying Advanced Trade withdrawal...")
        withdraw_path = "/api/v3/brokerage/withdrawals/crypto"
        withdraw_body = {
            "amount": send_amount,
            "asset": "ETH",
            "address": DEPLOY_WALLET,
            "network": "ethereum/base",
        }
        resp2 = api_post(withdraw_path, withdraw_body)
        if resp2.ok:
            print("Withdrawal initiated!")
            print(json.dumps(resp2.json(), indent=2))
        else:
            print(f"Withdrawal error {resp2.status_code}: {resp2.text[:500]}")


if __name__ == "__main__":
    main()
