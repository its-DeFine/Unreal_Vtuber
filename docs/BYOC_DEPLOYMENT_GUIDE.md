# Livepeer BYOC Deployment Runbook

This guide captures the steps we follow to bring up the Livepeer BYOC (Bring Your Own Compute) stack for the Unreal VTuber deployment. Use it as a checklist whenever we spin up or repair an environment so we do not repeat past misconfigurations.

---

## 1. Prerequisites
- **Access credentials**: Ensure the EC2 keypair and AWS IAM keys in `aws-pixel-streaming/.env` are up to date.
- **Docker + NVIDIA**: The EC2 host must have Docker, the NVIDIA container toolkit, and the proper NVIDIA drivers installed.
- **Repo layout**: The remote instance should have `Unreal_Vtuber/` checked out. This folder mirrors `autonomy/` in the repository.
- **Public IP**: Confirm the public IP of the EC2 instance (e.g. `18.188.126.223`). We reuse it in multiple configs.

## 2. Open the network path
1. Locate the security group attached to the EC2 instance.
2. Add (or verify) an inbound rule for TCP `9995` from the expected client CIDRs. When testing, we typically allow `0.0.0.0/0` with the description `Livepeer orchestrator`.
3. Confirm the rule is active:
   ```bash
   curl -vk https://<public-ip>:9995/process/token -m 10
   ```
   A `400 Must have eth address...` response means the socket is reachable and TLS works.

## 3. Configure the orchestrator
1. Copy the template env if needed:
   ```bash
   cd ~/Unreal_Vtuber
   [ -f .env ] || cp .example.env .env
   ```
   Then update `.env` (or the values you export in your automation) with the orchestrator settings:
   ```ini
   # Public URL and secret used by workers
   LIVEPEER_ORCH_URL=https://<public-ip>:9995
   LIVEPEER_ORCH_SECRET=orch-secret

   # Ethereum configuration
   ETH_RPC_URL=https://arb1.arbitrum.io/rpc
   ETH_PASSWORD=<keystore-password>
   ETH_ADDRESS=<orchestrator-eth-address>
   ETH_ORCH_ADDRESS=<orchestrator-eth-address>

   # Pricing / gas controls
   PRICE_PER_UNIT=0
   TICKET_EV=0
   MAX_GAS_PRICE=1000000000
   AUTO_ADJUST_PRICE=false

   # Ports
   ORCHESTRATOR_PORT=9995
   ```
   Any value omitted falls back to the defaults baked into `docker-compose.livepeer.yml`.
2. Place your Livepeer keystore JSON under `Unreal_Vtuber/config/keystore/` and create `Unreal_Vtuber/config/ethpass` containing **only** the keystore password. The compose file mounts these into `/root/.lpData/keystore` and `/root/.lpData/.ethpass` respectively, so the container automatically unlocks the account at start.
   - Need a fresh throwaway wallet? Run `scripts/generate_livepeer_wallet.sh` (from the repo root) to create a new keystore + password pair, then fund the produced address with a small amount of Arbitrum ETH so the orchestrator can redeem tickets.
3. Start or restart the orchestrator stack:
   ```bash
   cd ~/Unreal_Vtuber
   sudo docker compose -f docker-compose.livepeer.yml up -d
   ```
4. Validate:
   ```bash
   sudo docker compose -f docker-compose.livepeer.yml ps
   sudo docker compose -f docker-compose.livepeer.yml logs livepeer-orchestrator --tail=50
   ```
   Look for the line `Generating cert for <public-ip>` and confirm `RPC` is listening on `:9995`.

## 4. Configure the worker
1. Update `Unreal_Vtuber/.env`:
   ```ini
   LIVEPEER_ORCH_URL=https://<public-ip>:9995
   LIVEPEER_ORCH_SECRET=orch-secret
   CAPABILITY_NAME=agent-net
   ```
   If the orchestrator uses a self-signed cert, add `LIVEPEER_ORCH_SKIP_VERIFY=true` (only for testing) so registration succeeds.
2. Recreate the worker to pick up changes:
   ```bash
   sudo docker compose up -d --force-recreate livepeer-worker
   ```
3. Check the registration logs:
   ```bash
   sudo docker compose logs livepeer-worker --tail=100
   ```
   Ensure the worker reports the correct `ORCH_URL` and does not warn about certificate mismatch (unless `SKIP_VERIFY` is enabled).

## 5. Gateway integration
1. In `backend_logic/docker-compose-gateway.yml` (or corresponding deployment), ensure the gateway uses the same orchestrator URL and secret, or provides the Livepeer `Livepeer-Eth-Address` + signature headers.
2. When using the shared secret path, run the gateway with `-orchSecret=orch-secret` or set `ORCH_SECRET` in its environment.
3. After restarting the gateway, submit a test job and monitor the output:
   ```bash
   docker compose -f backend_logic/docker-compose-gateway.yml logs -f gateway
   ```
   A successful handshake shows `Received job token from uri=https://<public-ip>:9995` with a subsequent `200` response from `/process/request/...`.

## 6. Verification checklist
- [ ] `curl https://<public-ip>:9995/process/token -m 10` returns HTTP `400` (authentication missing) instead of timing out.
- [ ] `sudo docker compose -f docker-compose.livepeer.yml ps` lists `livepeer-orchestrator` as `Up` with port `0.0.0.0:9995->9995`.
- [ ] `sudo docker compose logs livepeer-worker` shows connection to `https://<public-ip>:9995` with no registration warnings.
- [ ] Gateway logs show job tokens retrieved and requests posted to `https://<public-ip>:9995`.

## 7. Troubleshooting reference
- **`connect: connection refused` to `https://0.0.0.0:9995`** – Double-check `LIVEPEER_ORCH_URL` / `ORCHESTRATOR_PORT` in `.env` and recreate the orchestrator container.
- **`Failed to get token ... err=<nil>`** – The request reached the orchestrator, but Livepeer auth headers are missing. Provide the broadcaster ETH signature or align `orchSecret`.
- **Worker warns about unverified HTTPS** – Either install a valid cert chain or set `LIVEPEER_ORCH_SKIP_VERIFY=true` until a proper certificate is issued.
- **Gateway still times out** – Double-check the security group, and ensure no intermediate firewall blocks TCP `9995`.

## 8. Operational reminders
- After config edits, always `docker compose down && up -d` to ensure mounts refresh.
- Keep test audio assets (e.g. `sample-15s.mp3`) handy for job validation.
- Document any CIDR restrictions or credential changes directly in this runbook to keep the team aligned.
