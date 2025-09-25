# AWS Orchestrator Onboarding Guide

This page is for operators who need to spin up a fresh Unreal orchestrator EC2 instance using the automated provisioning script. It covers prerequisites, configuration, required AWS permissions, and the exact commands to run.

---

## 1. Prerequisites

### Workstation requirements
- Linux/macOS terminal (Bash-compatible).
- AWS CLI v2 installed (https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html).
- `ssh`, `scp`, `rsync`, `jq`, and `python3` available in `$PATH`.
- Access to the `autonomy` repo (the script lives under `autonomy/scripts`).

### AWS credentials
- Request IAM credentials that allow you to launch GPU instances. The key must have at least these EC2 permissions in the target region (`us-east-2`):
  - `DescribeInstances`, `DescribeSubnets`, `DescribeSecurityGroups`, `DescribeKeyPairs`
  - `CreateSecurityGroup`, `AuthorizeSecurityGroupIngress`
  - `CreateKeyPair`
  - `RunInstances`, `CreateTags`, `StopInstances`, `TerminateInstances`
- These commands launch `g5.xlarge` instances, which are service-limited. Ask your AWS admin to grant your account access to the G5 family before running the script.
- Export the keys before provisioning (temporary example):
  ```bash
  export AWS_ACCESS_KEY_ID=AKIA...
  export AWS_SECRET_ACCESS_KEY=...
  export AWS_DEFAULT_REGION=us-east-2
  ```
  Alternatively, configure a profile via `aws configure` and run the script with `AWS_PROFILE=name python3 ...`.

---

## 2. Configuration

Inside `autonomy/scripts/` you’ll find `provision_orchestrator.env.example`. Make a copy next to it:

```bash
cd autonomy/scripts
cp provision_orchestrator.env.example provision_orchestrator.env
```

Edit `provision_orchestrator.env` and fill in the required fields:

```
DEDICATED_CLIENT_IP=203.0.113.42    # IP that’s allowed to view Pixel Streaming / submit scripts
ADMIN_SOURCE_IP=203.0.113.50       # Your SSH management IP (only this address gets port 22)
PAYMENTS_BACKEND_IP=3.141.111.200  # Payments elastic IP
PAYMENTS_API_URL=http://3.141.111.200:8081
ORCHESTRATOR_ID=orch-alpha-test
ORCHESTRATOR_ADDRESS=0x...         # Payout wallet (checksummed Ethereum address)
ALLOW_DEDICATED_IP_SSH=false       # Set true if you want the client IP to reach SSH as well
ORCHESTRATOR_CONTACT_EMAIL=ops@example.com
ALLOCATE_ELASTIC_IP=false          # Set true to allocate and attach a fresh Elastic IP
#ELASTIC_IP_ALLOCATION_ID=eipalloc-xxxxxxxxxxxxxxxxx
```

Notes:
- The script defaults to subnet `subnet-0aad8738d8ac9fc25`, AMI `ami-0f09ef696435ff61a` (Ubuntu 22.04 + NVIDIA), and a 200 GB gp3 root volume. Override `AWS_SUBNET_ID`, `AWS_AMI_ID`, or `AWS_ROOT_VOLUME_GB` only if you know you need a different environment.
- Set `ALLOCATE_ELASTIC_IP=true` to automatically allocate a new Elastic IP and attach it to the orchestrator. Alternatively, provide `ELASTIC_IP_ALLOCATION_ID` to reuse an existing allocation.
- `ORCHESTRATOR_KEY_NAME` is the EC2 key pair label. If it doesn’t exist, the script creates it and writes the private key under `autonomy/scripts/<name>.pem`.
- `ALLOW_DEDICATED_IP_SSH=true` opens port 22 to the same client IP that accesses Pixel Streaming. Leave it false if you want SSH restricted solely to the admin IP.

---

## 3. Running the Provisioner

From the repo root:

```bash
cd autonomy
python3 scripts/provision_orchestrator.py
```

What happens:
1. Key pair: creates or reuses the key pair named in `ORCHESTRATOR_KEY_NAME`.
2. Security group: creates/updates the group `vtuber-orchestrator-autoprovision` with the correct ingress rules (8080/8888-8889/9876-9877/3478/19302-19303/40000-49999 to the dedicated client IP, 9090 to the payments backend IP, 22 to the admin IP ± dedicated IP if toggled).
3. Instance: launches a `g5.xlarge` instance in `us-east-2`, subnet `subnet-0aad8738d8ac9fc25`, AMI `ami-0f09ef696435ff61a`, with a 200 GB gp3 root volume (override via `AWS_ROOT_VOLUME_GB`). If Elastic IP allocation is enabled it attaches the existing or newly created address automatically.
4. Bootstrapping: installs OS updates, Docker, NVIDIA driver + container toolkit, reboot, rsyncs `Unreal_Vtuber`, generates TURN credentials, pulls images, starts `docker-compose.unreal.yml`.
5. Registration: runs `scripts/register_orchestrator.py --once` to register the orchestrator against `PAYMENTS_API_URL` with your ID/address (and contact email if set).
6. Output: prints the instance ID, public IP, security group ID, and key path.

Once the command finishes, you can SSH with:
```bash
ssh -i scripts/<key-name>.pem ubuntu@<public-ip>
```

---

## 4. Post-Provision Checklist

- Confirm Pixel Streaming UI: `http://<public-ip>:8080`
- Confirm script runner health: `curl http://<public-ip>:9877/health`
- Confirm payments entry: `curl http://3.141.111.200:8081/api/orchestrators | jq '.'` (look for your `orchestrator_id`).
- When testing is complete, terminate the instance:
  ```bash
  aws ec2 terminate-instances --instance-ids <id> --region us-east-2
  ```

Remember to resume the payments backend container (`docker compose -f backend/docker-compose.yml unpause payments-backend`) once you need payouts to flow again.

---

## 5. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Provision script fails with “UnauthorizedOperation” | IAM user lacks required permissions | Ask AWS admin to grant EC2 launch rights or use a role with broader access |
| Launch fails: “g5.xlarge not available” | Account/region lacks G5 quota | File a limit-increase request for G5 instances in `us-east-2` |
| SSH times out | Security group doesn’t allow your IP | Re-run the script with correct `ADMIN_SOURCE_IP` (or enable `ALLOW_DEDICATED_IP_SSH`) |
| Pixel Streaming not accessible from client | `DEDICATED_CLIENT_IP` incorrect | Update the env file and rerun provisioning or adjust the security group manually |
| Payments API still paused | Payments backend left paused after earlier tests | `ssh ubuntu@3.141.111.200` then `docker compose -f backend/docker-compose.yml unpause payments-backend` |

When in doubt, check CloudWatch or EC2 console logs for the instance, and tail the orchestrator containers:
```bash
ssh -i scripts/<key>.pem ubuntu@<public-ip>
sudo docker ps
sudo docker logs -f vtuber-unreal-game
sudo docker logs -f unreal_vtuber-vtuber-script-runner-1
```

This workflow should let any approved operator launch a ready-to-stream orchestrator without touching the AWS console.
