# Unreal VTuber

Autonomous VTuber system with Livepeer integration for distributed AI workloads.

## Onboarding Steps

### 1. Clone the Repository
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git
cd Unreal_Vtuber
```

### 2. Install Game and Configure OBS
Launch the script inside the `/scripts/windows` folder (this will install the game and configure and/or download OBS).

**Note:** You will need to run this with PowerShell in admin permissions.

### 3. Download Model Weights
Download the `.pth` file from the link given by the maintainer and place it in:
```
Unreal_Vtuber/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Local_API/utils/model/
```

### 4. Configure Environment
Copy `.env.example` to `.env` and follow the dev comments to fill all the values needed:
```bash
cp .env.example .env
```

### 5. Install Docker Buildx
Ensure that you have buildx installed, otherwise the docker compose command will not work.

### 6. Build Docker Images
At the root of the repo, build all services:
```bash
docker compose build --no-cache
```

### 7. Launch Services
Start all services:
```bash
docker compose up -d
```

### 8. Configure Firewall for Central Manager
Open PowerShell again with admin privileges and run:
```powershell
New-NetFirewallRule -DisplayName "Allow Central Manager" -Direction Inbound -Protocol TCP -LocalPort 8082 -RemoteAddress 86.106.138.188 -Action Allow
```

This will allow your computer to communicate with the central manager node.

## Support

For issues or questions, please contact the maintainers.

## Pixel Streaming Deployment

Use the following steps on any host (including the EC2 instance) to launch the Unreal game, signaling server, and TURN server.

1. **Update the repository**
   ```bash
   git pull --rebase origin feature/vtuber-elevenlabs
   ```

2. **Generate TURN credentials**
   ```bash
   ./scripts/generate_turn_credentials.sh
   ```
   This writes `.env.turn` with fresh credentials, the external IP, and the relay port range. The compose stack uses this file for both the `turn-server` and `unreal-signaling` services.

3. **(Optional) Repackage the game image** – only when a new Embody build needs to be baked into the container:
   ```bash
   docker/aws-pixel-streaming/package-embody.sh /path/to/Embody/Linux
   ```
   The command rebuilds `embody-pixel-streaming:latest` with the supplied build artifacts. Skip this step if the existing image is already up to date on the host.

4. **Build the signaling image** (requires Docker Buildx):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.unreal.yml build unreal-signaling
   ```

5. **Start the stack**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.unreal.yml up -d turn-server unreal-signaling unreal-game
   ```

6. **Confirm services**
   ```bash
   docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
   docker logs vtuber-unreal-signaling --tail 20
   docker exec vtuber-unreal-game bash -lc 'ulimit -n'
   ```
   The signaling logs should show Wilbur starting and the streamer connection registering; the game container should report a `nofile` limit of `1040`.

7. **Browser access**
Visit `http://<public-ip>:8080` (port 8080 is served by the signaling container). TURN/STUN credentials come from `.env.turn`; no additional manual configuration is required.

More background on the container layout, troubleshooting tips, and lessons learned is available in [docs/pixel-streaming-architecture.md](docs/pixel-streaming-architecture.md).

## Pushing from the EC2 Host

When making changes directly on the EC2 instance:

```bash
git pull --rebase origin feature/vtuber-elevenlabs
# …apply local changes…
git commit -am "describe change"
git push origin feature/vtuber-elevenlabs
```

Using `git pull --rebase` keeps the branch fast-forwardable so pushes succeed without forcing.
