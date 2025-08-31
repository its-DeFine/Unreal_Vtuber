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