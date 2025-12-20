# Admin: Encrypted Game Image Distribution

Orchestrators do **not** pull the proprietary game image from a registry. Instead, they download an **encrypted artifact** (typically from S3) and request a **short‑lived decryption lease** from the Payments backend.

The intended onboarding experience:
- Orchestrator runs the wizard and pastes a **one-time invite code** (wallet-bound).
- Payments mints a license token + returns a **fresh presigned download URL per lease**.
- Orchestrators never paste expiring S3 URLs.

This doc is the admin/operator runbook for:
- creating the encryption key (`age`)
- producing + publishing encrypted artifacts for each build
- registering the decryption secret + artifact location in Payments
- issuing wallet-bound invite codes

## 0) Prerequisites

- Access to the Payments backend admin token (`X-Admin-Token`)
- `age`, `curl`, and `python3` on your admin machine
- A trusted build machine with the packaged game image available locally (for producing artifacts)
- Payments host has AWS credentials/role with `s3:GetObject` for the artifact bucket (so it can presign)
- Payments host configured with `PAYMENTS_LICENSE_ARTIFACT_REGION` (and optionally `PAYMENTS_LICENSE_ARTIFACT_PRESIGN_SECONDS`)

## 1) Generate an `age` keypair (one-time per `image_ref`)

Generate and store the private key securely (never commit it):
```bash
age-keygen -o embody-ue-ps-enc-v1.agekey
age-keygen -y embody-ue-ps-enc-v1.agekey  # prints the public recipient (age1...)
```

## 2) Produce an encrypted artifact (per build) and upload to S3

On a trusted build machine (where the packaged game image exists locally):
```bash
./tools/encrypted-game-image/produce.sh \
  --image ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest \
  --recipient "age1..." \
  --out /tmp/embody-ue-ps.tar.zst.age
```

Upload the resulting `.tar.zst.age` to S3 and note the S3 URI:
```text
s3://<bucket>/<path>/embody-ue-ps.tar.zst.age
```

## 3) Register the decryption secret + artifact location in Payments

Payments stores:
- the private `age` identity (base64) for a given `image_ref`
- the `artifact_s3_uri` (so it can mint a fresh presigned URL per lease)

```bash
PAYMENTS_API_URL="http://<payments-host>:8081"
PAYMENTS_ADMIN_TOKEN="<X-Admin-Token>"
IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"
ARTIFACT_S3_URI="s3://<bucket>/<path>/embody-ue-ps.tar.zst.age"

SECRET_B64="$(python3 - <<'PY'
import base64, pathlib
print(base64.b64encode(pathlib.Path("embody-ue-ps-enc-v1.agekey").read_bytes()).decode("ascii"))
PY
)"

curl -fsS -X PUT \
  -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"image_ref\":\"$IMAGE_REF\",\"secret_b64\":\"$SECRET_B64\",\"artifact_s3_uri\":\"$ARTIFACT_S3_URI\"}" \
  "$PAYMENTS_API_URL/api/licenses/images"
```

## 4) Create a wallet-bound invite code

Invite codes are single-use and bound to the orchestrator’s payout wallet (`0x...`).

```bash
PAYOUT_WALLET="0x1111111111111111111111111111111111111111"

curl -fsS -X POST \
  -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"image_ref\":\"$IMAGE_REF\",\"bound_address\":\"$PAYOUT_WALLET\",\"ttl_seconds\":604800,\"note\":\"onboarding\"}" \
  "$PAYMENTS_API_URL/api/licenses/invites"
```

Send the orchestrator:
- the invite `code` from the response
- the Embody edge/gateway IP(s) they should allowlist (closest region; can be comma-separated)

They will run the onboarding wizard and paste that code.

## 5) Rollout / upgrade guidance

For a new build:
- produce + upload a new encrypted artifact
- update `artifact_s3_uri` for the same `image_ref` (or use a new `image_ref` if you want strict version pinning)

Orchestrators can upgrade by re-running the wizard or by using `tools/encrypted-game-image/rollout.sh`.
