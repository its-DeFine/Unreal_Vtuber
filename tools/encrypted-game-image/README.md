# Encrypted Game Image (Docker) — v1

This folder contains helper scripts to distribute the Unreal game container as an **encrypted artifact** (instead of requiring GHCR credentials on the orchestrator).

## Format

We encrypt a Docker image tar stream with `age` (recipient mode). The Payments backend license service delivers the **age identity** (private key) for decryption.

```
docker save <image> | zstd | age -r <age1...>  =>  .tar.zst.age
```

Decryption is the reverse:

```
curl <artifact-url> | age --decrypt -i <identity> | zstd -d | docker load
```

The `secret_b64` returned by `POST /api/licenses/lease` is expected to be **base64(identity-file-bytes)**.

Important:
- `--image-ref` is a **Payments license identifier** (a string key). It does **not** need to exist as a Docker image in any registry.
- The proprietary game image should **not** be published to GHCR; orchestrators load it only from the encrypted artifact URL.

## Dependencies

- Producer: `docker`, `zstd`, `age`
- Consumer: `docker`, `zstd`, `age`, `curl`, `jq`

## Producer

Create an encrypted artifact from a locally-available Docker image:

```bash
./tools/encrypted-game-image/produce.sh \
  --image ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest \
  --recipient age1... \
  --out /tmp/embody-ue-ps.tar.zst.age
```

Notes:
- `--image` must exist **locally** on the producer machine. The tag does not need to exist in a registry.
- Orchestrators will run whatever image name/tag is embedded in the tar stream; the default compose expects `ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest`.

Upload with whatever mechanism you prefer (S3, GCS, etc.).

## Consumer (Orchestrator)

Download + decrypt + `docker load` using a Payments-issued lease:

```bash
./tools/encrypted-game-image/consume.sh \
  --payments-api-url http://<payments-host>:8081 \
  --orch-token-file /path/to/orchestrator-license-token.txt \
  --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1
```

### Orchestrator rollout helper

If you want an end-to-end “reload the game image and restart the stack” helper, use:

```bash
./tools/encrypted-game-image/rollout.sh \
  --payments-api-url http://<payments-host>:8081 \
  --orch-token-file /path/to/orchestrator-license-token.txt \
  --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1
```

This runs: `docker compose down` → `docker image rm` (game tag) → `consume.sh` → `docker compose up -d`.

## Notes

- These scripts intentionally avoid printing secrets, but you should still treat shell history and process lists with care.
- Use digest-based, content-addressed filenames for artifacts (recommended) so the payload can be cached safely.
- For production, configure the Payments backend to store an `artifact_s3_uri` per `image_ref` so it can mint a fresh presigned download URL per lease.
