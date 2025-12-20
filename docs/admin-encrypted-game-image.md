# Admin: Encrypted Game Image Distribution

Orchestrators do **not** pull the proprietary game image from a registry. Instead, they download an **encrypted artifact** (typically from S3) and request a **short‑lived decryption lease** from the Payments backend using an admin-minted orchestrator license token.

This doc is the admin/operator runbook for:
- creating the encryption key (age)
- registering the decryption secret in Payments
- minting per-orchestrator tokens + granting access
- producing + publishing encrypted artifacts for each build

## 0) Prerequisites

- Access to the Payments backend admin token (`X-Admin-Token`)
- `age`, `curl`, and `python3` on your admin machine
- A trusted build machine with the packaged game image available locally (for producing artifacts)

## 1) Generate an `age` keypair (one-time per image_ref)

Generate and store the private key securely (never commit it):
```bash
age-keygen -o embody-ue-ps-enc-v1.agekey
age-keygen -y embody-ue-ps-enc-v1.agekey  # prints the public recipient (age1...)
```

## 2) Register the decryption secret in Payments

Payments stores the private `age` identity (base64) for a given `image_ref`. The `image_ref` is a Payments identifier (it may look like a container ref; orchestrators do not need registry access).

```bash
PAYMENTS_API_URL="http://<payments-host>:8081"
PAYMENTS_ADMIN_TOKEN="<X-Admin-Token>"
IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"

SECRET_B64="$(python3 - <<'PY'
import base64, pathlib
print(base64.b64encode(pathlib.Path("embody-ue-ps-enc-v1.agekey").read_bytes()).decode("ascii"))
PY
)"

curl -fsS -X PUT \
  -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"image_ref\":\"$IMAGE_REF\",\"secret_b64\":\"$SECRET_B64\"}" \
  "$PAYMENTS_API_URL/api/licenses/images"
```

## 3) Mint an orchestrator token + grant access

We recommend minting **one token per orchestrator** (rotate/revoke as needed).

```bash
ORCH_ID="<orchestrator-id>"  # must match what the orchestrator will configure

# 1) Mint a token
curl -fsS -X POST \
  -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
  "$PAYMENTS_API_URL/api/licenses/orchestrators/$ORCH_ID/tokens"

# 2) Grant access to the encrypted image
curl -fsS -X POST \
  -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"orchestrator_id\":\"$ORCH_ID\",\"image_ref\":\"$IMAGE_REF\"}" \
  "$PAYMENTS_API_URL/api/licenses/access/grant"
```

Send the orchestrator:
- the minted license token
- an encrypted artifact URL for the build they should run (next step)

## 4) Produce an encrypted artifact (per build)

On a trusted build machine (where the packaged game image exists locally):
```bash
./tools/encrypted-game-image/produce.sh \
  --image ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest \
  --recipient "age1..." \
  --out /tmp/embody-ue-ps.tar.zst.age
```

Upload the resulting `.tar.zst.age` to object storage (S3 recommended) and generate a URL:
- public URL, or
- presigned URL (recommended for limited exposure)

That URL is what orchestrators paste into the onboarding wizard as the “Encrypted artifact URL”.

## 5) Rollout / upgrade guidance

For a new build:
- produce a new encrypted artifact
- provide the new artifact URL to orchestrators (or trigger an automated rollout flow)

Orchestrators can upgrade by re-running the wizard or by using `tools/encrypted-game-image/rollout.sh`.

