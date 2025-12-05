# AWS Orchestrator Onboarding Guide

Use this guide to bring up a fresh Unreal VTuber orchestrator on AWS now that the
old `provision_orchestrator.py` helper is removed. These steps assume a
g4dn-class GPU instance in `us-east-2`; adjust to your region as needed.

---

## 1. Prerequisites

- AWS account with permissions to launch **g4dn.xlarge** (or better) and manage security groups/Elastic IPs.
- Admin IP for SSH access; optional dedicated client IP if you plan to expose Pixel Streaming externally (otherwise use SSH tunnels).
- Payments backend reachable at `http://3.141.111.200:8081` (or your override).
- Local tools for initial login: `ssh`, `scp/rsync`, and (optional) `aws` CLI if you prefer CLI over console.

---

## 2. Launch the GPU instance

- AMI: Ubuntu 22.04 LTS with NVIDIA-compatible kernel (latest Canonical AMI works with the container toolkit).
- Instance type: `g4dn.xlarge` (NVIDIA T4, 16 GB RAM).
- Storage: 200 GB gp3 root volume (increase if you keep many recordings).
- Networking/security group:
  - Allow **SSH (22/tcp)** from your admin IP only.
  - Allow forwarder `3.150.172.153` to **8080, 8888, 8889, 9876, 9877 (tcp)** and **3478, 49160-49200 (udp)**.
  - Allow payments backend `3.141.111.200` to **9090 (tcp)**.
  - If you expose Pixel Streaming publicly, scope `8080/8888/8889` to the viewer IPs; otherwise keep them closed and use SSH tunnels.
- Allocate/associate an Elastic IP so the orchestrator keeps a stable address.

---

## 3. Install base dependencies on the host

SSH in (`ssh -i <key>.pem ubuntu@<elastic-ip>`) and run:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release jq python3 python3-venv

# Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER

# NVIDIA driver + container toolkit
sudo apt-get install -y nvidia-driver-525 nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Log out/in (or `newgrp docker`) so your user can run Docker.

---

## 4. Deploy Unreal VTuber

```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git
cd Unreal_Vtuber

# Generate TURN credentials (writes .env.turn)
./scripts/generate_turn_credentials.sh

# Copy and fill orchestrator env
cp orchestrator.env.example .env
```

Update `.env` with:
- `PAYMENTS_API_URL=http://3.141.111.200:8081` (or your backend)
- `ORCHESTRATOR_ID`, `ORCHESTRATOR_ADDRESS`, `PUBLIC_IP` (Elastic IP)
- `ORCHESTRATOR_HEALTH_URL=http://<elastic-ip>:9090/health`
- `VTUBER_ALLOWED_ADDRESSES=3.150.172.153` (forwarder)
- Optional metadata: `ORCHESTRATOR_CONTACT_EMAIL`, etc.

Start the stack:

```bash
docker network create vtuber_network 2>/dev/null || true
docker compose -f docker-compose.unreal.yml up -d
```

Register with payments:

```bash
PAYMENTS_API_URL=http://3.141.111.200:8081 \
ORCHESTRATOR_ID=<id> \
ORCHESTRATOR_ADDRESS=<wallet> \
python3 scripts/register_orchestrator.py
```

---

## 5. Verify and maintain

- Pixel UI: `http://<elastic-ip>:8080`
- Runner: `curl http://<elastic-ip>:9877/health`
- Orchestrator monitor: `curl http://<elastic-ip>:9090/health`
- Payments registry: `curl http://3.141.111.200:8081/api/orchestrators | jq '.'`
- Rotate TURN creds with `./scripts/generate_turn_credentials.sh` then `docker compose -f docker-compose.unreal.yml restart vtuber-turn-server`.
- Stop stack: `docker compose -f docker-compose.unreal.yml down`
- When done, terminate the EC2 instance to avoid GPU charges.

---

## 6. Notes

- The legacy `provision_orchestrator.py` automation has been removed; bring your
  own Terraform/CLI scripts if you want to recreate that flow.
- Keep SSH locked to your admin IP and avoid exposing Pixel Streaming ports to
  the internet unless strictly required.
