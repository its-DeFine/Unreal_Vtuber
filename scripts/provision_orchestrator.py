#!/usr/bin/env python3
"""Provision a fresh Unreal orchestrator EC2 host and bootstrap the full stack.

Steps performed:
  1. Load configuration from an .env-style file (see provision_orchestrator.env.example).
  2. Ensure the requested EC2 key pair and security group exist (creating them if needed).
  3. Launch a GPU-enabled Ubuntu instance with the supplied AMI/subnet and wait for it to be reachable.
  4. Install Docker, NVIDIA drivers, and the NVIDIA container toolkit on the instance.
  5. Sync the required project files, generate TURN credentials, launch the docker-compose stack,
     and register the orchestrator with the remote payments backend.

Requirements on the workstation running this script:
  * AWS CLI v2 configured (we rely on aws CLI commands under the hood).
  * ssh, scp, rsync, jq, and tar available in PATH.
  * The configuration .env must provide at least the variables listed in REQUIRED_CONFIG.

The script is intentionally verbose and will exit on the first error.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / "scripts" / "provision_orchestrator.env"
REQUIRED_CONFIG = {
    "AWS_REGION",
    "AWS_SUBNET_ID",
    "AWS_AMI_ID",
    "AWS_INSTANCE_TYPE",
    "ORCHESTRATOR_KEY_NAME",
    "DEDICATED_CLIENT_IP",
    "ADMIN_SOURCE_IP",
    "PAYMENTS_BACKEND_IP",
    "PAYMENTS_API_URL",
    "ORCHESTRATOR_ID",
    "ORCHESTRATOR_ADDRESS",
}
DEFAULT_SECURITY_GROUP_NAME = "vtuber-orchestrator-autoprovision"
DEFAULT_INSTANCE_NAME = "vtuber-unreal-orchestrator"
SSH_USER = "ubuntu"
DEFAULTS = {
    "AWS_SUBNET_ID": "subnet-0aad8738d8ac9fc25",
    "AWS_AMI_ID": "ami-0f09ef696435ff61a",
}
INSTALL_SNIPPET = """set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y build-essential dkms linux-headers-$(uname -r) curl wget git python3 python3-pip python3-requests rsync unzip jq
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
sudo apt-get install -y nvidia-driver-535
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[bootstrap] nvidia-smi unavailable after driver install" >&2
fi
DIST=$(. /etc/os-release; echo "$ID$VERSION_ID")
KEYRING=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o ${KEYRING}
curl -s -L https://nvidia.github.io/libnvidia-container/${DIST}/libnvidia-container.list | \
  sed "s#deb https://#deb [signed-by=${KEYRING}] https://#" | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update -y
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker || true
sudo systemctl restart docker
sudo apt-get install -y docker-compose-plugin
"""


def info(msg: str) -> None:
    print(f"[provision] {msg}")


def run(cmd: Iterable[str], *, capture_output: bool = False, check: bool = True, text: bool = True) -> subprocess.CompletedProcess:
    info(f"exec: {' '.join(cmd)}")
    return subprocess.run(list(cmd), capture_output=capture_output, check=check, text=text)


def load_env(path: Path) -> Dict[str, str]:
    config: Dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"Config file {path} does not exist")
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"Invalid line in {path}: {line}")
        key, value = stripped.split("=", 1)
        config[key.strip()] = value.strip()
    for key, value in DEFAULTS.items():
        config.setdefault(key, value)
    return config


def ensure_requirements(config: Dict[str, str]) -> None:
    missing = sorted(k for k in REQUIRED_CONFIG if not config.get(k))
    if missing:
        raise SystemExit(f"Missing required configuration keys: {', '.join(missing)}")


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_key_pair(config: Dict[str, str], output_dir: Path) -> Path:
    key_name = config["ORCHESTRATOR_KEY_NAME"]
    key_path = output_dir / f"{key_name}.pem"

    describe = run(
        [
            "aws",
            "ec2",
            "describe-key-pairs",
            "--key-names",
            key_name,
            "--region",
            config["AWS_REGION"],
        ],
        capture_output=True,
        check=False,
    )
    if describe.returncode == 0:
        info(f"Reusing existing key pair {key_name}")
        if not key_path.exists():
            info(f"Warning: AWS key exists but {key_path} is missing. Provide the private key before proceeding.")
            raise SystemExit(1)
        key_path.chmod(0o600)
        return key_path

    info(f"Creating new key pair {key_name}")
    create = run(
        [
            "aws",
            "ec2",
            "create-key-pair",
            "--key-name",
            key_name,
            "--query",
            "KeyMaterial",
            "--output",
            "text",
            "--region",
            config["AWS_REGION"],
        ],
        capture_output=True,
    )
    key_path.write_text(create.stdout)
    key_path.chmod(0o600)
    info(f"Saved private key to {key_path}")
    return key_path


def lookup_vpc_id(config: Dict[str, str]) -> str:
    if config.get("AWS_VPC_ID"):
        return config["AWS_VPC_ID"]
    result = run(
        [
            "aws",
            "ec2",
            "describe-subnets",
            "--subnet-ids",
            config["AWS_SUBNET_ID"],
            "--query",
            "Subnets[0].VpcId",
            "--output",
            "text",
            "--region",
            config["AWS_REGION"],
        ],
        capture_output=True,
    )
    vpc_id = result.stdout.strip()
    if not vpc_id or vpc_id == "None":
        raise SystemExit("Unable to determine VPC ID for subnet")
    return vpc_id


def ensure_security_group(config: Dict[str, str], vpc_id: str) -> str:
    sg_name = config.get("AWS_SECURITY_GROUP_NAME", DEFAULT_SECURITY_GROUP_NAME)
    region = config["AWS_REGION"]
    describe = run(
        [
            "aws",
            "ec2",
            "describe-security-groups",
            "--filters",
            f"Name=group-name,Values={sg_name}",
            f"Name=vpc-id,Values={vpc_id}",
            "--query",
            "SecurityGroups[0].GroupId",
            "--output",
            "text",
            "--region",
            region,
        ],
        capture_output=True,
        check=False,
    )
    sg_id = describe.stdout.strip()
    if describe.returncode != 0 or not sg_id or sg_id == "None":
        info(f"Creating security group {sg_name}")
        create = run(
            [
                "aws",
                "ec2",
                "create-security-group",
                "--group-name",
                sg_name,
                "--description",
                "Unreal VTuber orchestrator",
                "--vpc-id",
                vpc_id,
                "--region",
                region,
            ],
            capture_output=True,
        )
        sg_id = json.loads(create.stdout)["GroupId"]
    else:
        info(f"Reusing security group {sg_name} ({sg_id})")

    dedicated_ip = config["DEDICATED_CLIENT_IP"] + "/32"
    admin_ip = config["ADMIN_SOURCE_IP"] + "/32"
    backend_ip = config["PAYMENTS_BACKEND_IP"] + "/32"
    allow_dedicated_ssh = parse_bool(config.get("ALLOW_DEDICATED_IP_SSH"))

    ip_permissions = [
        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": admin_ip, "Description": "SSH admin"}]},
        {"IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "Pixel streaming UI"}]},
        {"IpProtocol": "tcp", "FromPort": 8888, "ToPort": 8889, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "Pixel streaming signaling"}]},
        {"IpProtocol": "tcp", "FromPort": 9876, "ToPort": 9877, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "VTuber worker APIs"}]},
        {"IpProtocol": "tcp", "FromPort": 3478, "ToPort": 3478, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "TURN TCP"}]},
        {"IpProtocol": "udp", "FromPort": 3478, "ToPort": 3478, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "TURN UDP"}]},
        {"IpProtocol": "udp", "FromPort": 19302, "ToPort": 19303, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "STUN fallback"}]},
        {"IpProtocol": "udp", "FromPort": 40000, "ToPort": 49999, "IpRanges": [{"CidrIp": dedicated_ip, "Description": "TURN relays"}]},
        {"IpProtocol": "tcp", "FromPort": 9090, "ToPort": 9090, "IpRanges": [{"CidrIp": backend_ip, "Description": "Payments health polling"}]},
    ]

    if allow_dedicated_ssh:
        ip_permissions.append(
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": dedicated_ip, "Description": "SSH (dedicated client)"}],
            }
        )

    permissions_json = json.dumps(ip_permissions)
    run(
        [
            "aws",
            "ec2",
            "authorize-security-group-ingress",
            "--group-id",
            sg_id,
            "--ip-permissions",
            permissions_json,
            "--region",
            region,
        ],
        check=False,
    )

    return sg_id


def launch_instance(config: Dict[str, str], sg_id: str, key_name: str, user_data: str) -> str:
    region = config["AWS_REGION"]
    name_tag = config.get("AWS_INSTANCE_NAME", DEFAULT_INSTANCE_NAME)
    root_size_gb = int(config.get("AWS_ROOT_VOLUME_GB", "200"))
    block_device_mappings = json.dumps(
        [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeSize": root_size_gb,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": True,
                },
            }
        ]
    )
    run_args = [
        "aws",
        "ec2",
        "run-instances",
        "--image-id",
        config["AWS_AMI_ID"],
        "--instance-type",
        config["AWS_INSTANCE_TYPE"],
        "--key-name",
        key_name,
        "--security-group-ids",
        sg_id,
        "--subnet-id",
        config["AWS_SUBNET_ID"],
        "--associate-public-ip-address",
        "--count",
        "1",
        "--region",
        region,
        "--block-device-mappings",
        block_device_mappings,
        "--tag-specifications",
        f"ResourceType=instance,Tags=[{{Key=Name,Value={name_tag}}}]",
        "--user-data",
        user_data,
    ]
    result = run(run_args, capture_output=True)
    data = json.loads(result.stdout)
    instance_id = data["Instances"][0]["InstanceId"]
    info(f"Launched instance {instance_id}")
    return instance_id


def wait_for_instance(instance_id: str, region: str) -> Dict[str, str]:
    info("Waiting for instance to enter running state...")
    run(["aws", "ec2", "wait", "instance-running", "--instance-ids", instance_id, "--region", region])
    info("Instance is running; waiting for status checks...")
    run(["aws", "ec2", "wait", "instance-status-ok", "--instance-ids", instance_id, "--region", region])
    desc = run(
        [
            "aws",
            "ec2",
            "describe-instances",
            "--instance-ids",
            instance_id,
            "--query",
            "Reservations[0].Instances[0].{PublicIp:PublicIpAddress,PrivateIp:PrivateIpAddress,AvailabilityZone:Placement.AvailabilityZone}",
            "--output",
            "json",
        ],
        capture_output=True,
    )
    return json.loads(desc.stdout)


def maybe_allocate_elastic_ip(
    config: Dict[str, str],
    instance_id: str,
    region: str,
) -> Optional[Dict[str, str]]:
    allocation_id = config.get("ELASTIC_IP_ALLOCATION_ID")
    allocate_new = parse_bool(config.get("ALLOCATE_ELASTIC_IP"))

    if not allocation_id and not allocate_new:
        return None

    if allocation_id:
        info(f"Associating existing Elastic IP allocation {allocation_id}")
    else:
        info("Allocating new Elastic IP")
        allocate = run(
            [
                "aws",
                "ec2",
                "allocate-address",
                "--domain",
                "vpc",
                "--region",
                region,
            ],
            capture_output=True,
        )
        data = json.loads(allocate.stdout)
        allocation_id = data["AllocationId"]
        info(f"Allocated Elastic IP {data['PublicIp']} ({allocation_id})")

    run(
        [
            "aws",
            "ec2",
            "associate-address",
            "--instance-id",
            instance_id,
            "--allocation-id",
            allocation_id,
            "--region",
            region,
        ]
    )

    desc = run(
        [
            "aws",
            "ec2",
            "describe-instances",
            "--instance-ids",
            instance_id,
            "--query",
            "Reservations[0].Instances[0].{PublicIp:PublicIpAddress,PrivateIp:PrivateIpAddress,AvailabilityZone:Placement.AvailabilityZone}",
            "--output",
            "json",
            "--region",
            region,
        ],
        capture_output=True,
    )

    details = json.loads(desc.stdout)
    details["AllocationId"] = allocation_id
    return details


def wait_for_ssh(ip: str, key_path: Path) -> None:
    info("Waiting for SSH to become available...")
    deadline = time.time() + 900  # 15 minutes
    while True:
        if time.time() > deadline:
            raise SystemExit("Timed out waiting for SSH")
        proc = subprocess.run(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-i",
                str(key_path),
                f"{SSH_USER}@{ip}",
                "echo ssh-ready",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if proc.returncode == 0:
            info("SSH connectivity confirmed")
            return
        info("SSH not yet ready; sleeping 10s")
        time.sleep(10)


def ssh(ip: str, key_path: Path, command: str) -> None:
    run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            str(key_path),
            f"{SSH_USER}@{ip}",
            command,
        ]
    )


def sync_project(ip: str, key_path: Path, remote_path: str, excludes: Iterable[str]) -> None:
    args = [
        "rsync",
        "-az",
        "--delete",
        "--rsync-path=mkdir -p {remote} && rsync".format(remote=remote_path),
    ]
    for pattern in excludes:
        args.extend(["--exclude", pattern])
    args.extend(["-e", f"ssh -o StrictHostKeyChecking=no -i {key_path}"])
    args.append(str(REPO_ROOT) + "/")
    args.append(f"{SSH_USER}@{ip}:{remote_path}/")
    run(args)


def write_remote_file(ip: str, key_path: Path, remote_path: str, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(content)
        temp_path = Path(tmp.name)
    try:
        run(
            [
                "scp",
                "-o",
                "StrictHostKeyChecking=no",
                "-i",
                str(key_path),
                str(temp_path),
                f"{SSH_USER}@{ip}:{remote_path}",
            ]
        )
    finally:
        temp_path.unlink(missing_ok=True)


def reboot_and_wait(ip: str, key_path: Path) -> None:
    info("Rebooting instance to activate NVIDIA drivers")
    subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            str(key_path),
            f"{SSH_USER}@{ip}",
            "sudo reboot || true",
        ],
        check=False,
        text=True,
    )
    time.sleep(10)
    wait_for_ssh(ip, key_path)


def create_env_files(config: Dict[str, str]) -> Dict[str, str]:
    orchestrator_env = {
        "ORCHESTRATOR_ID": config["ORCHESTRATOR_ID"],
        "ORCHESTRATOR_ADDRESS": config["ORCHESTRATOR_ADDRESS"],
        "PAYMENTS_API_URL": config["PAYMENTS_API_URL"],
    }
    if config.get("ORCHESTRATOR_CONTACT_EMAIL"):
        orchestrator_env["ORCHESTRATOR_CONTACT_EMAIL"] = config["ORCHESTRATOR_CONTACT_EMAIL"]
    orches_env_content = "\n".join(f"{k}={v}" for k, v in orchestrator_env.items()) + "\n"
    return {".env": orches_env_content}


def orchestrator_registration_command(config: Dict[str, str]) -> str:
    pieces = [
        f"PAYMENTS_API_URL={config['PAYMENTS_API_URL']}",
        f"ORCHESTRATOR_ID={config['ORCHESTRATOR_ID']}",
        f"ORCHESTRATOR_ADDRESS={config['ORCHESTRATOR_ADDRESS']}",
        "MONITORED_SERVICES=vtuber-unreal-game,vtuber-unreal-signaling,vtuber-turn-server",
        "ORCHESTRATOR_HEALTH_TIMEOUT=5",
    ]
    return " ".join(pieces) + " python3 scripts/register_orchestrator.py --once"


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a GPU orchestrator EC2 instance")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to provisioning .env file")
    parser.add_argument("--skip-sync", action="store_true", help="Skip rsync of project files (assumes remote already prepared)")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    config = load_env(env_path)
    ensure_requirements(config)

    key_path = ensure_key_pair(config, REPO_ROOT / "scripts")
    vpc_id = lookup_vpc_id(config)
    sg_id = ensure_security_group(config, vpc_id)

    user_data_script = textwrap.dedent(f"""
    #!/bin/bash
    {INSTALL_SNIPPET}
    """).strip()

    instance_id = launch_instance(config, sg_id, config["ORCHESTRATOR_KEY_NAME"], user_data_script)
    details = wait_for_instance(instance_id, config["AWS_REGION"])
    public_ip = details["PublicIp"]
    info(f"Instance {instance_id} reachable at {public_ip}")

    elastic_details = maybe_allocate_elastic_ip(config, instance_id, config["AWS_REGION"])
    allocation_id = None
    if elastic_details:
        public_ip = elastic_details.get("PublicIp", public_ip)
        allocation_id = elastic_details.get("AllocationId")
        info(f"Elastic IP associated; updated public IP: {public_ip}")

    wait_for_ssh(public_ip, key_path)
    reboot_and_wait(public_ip, key_path)

    ssh(public_ip, key_path, "sudo dpkg --configure -a || true")
    ssh(
        public_ip,
        key_path,
        "sudo apt-get update -y && sudo apt-get install -y linux-modules-extra-$(uname -r) nvidia-driver-535",
    )
    toolkit_script = textwrap.dedent(
        """
        set -e
        export DEBIAN_FRONTEND=noninteractive
        DIST=$(. /etc/os-release; echo $ID$VERSION_ID)
        sudo mkdir -p /usr/share/keyrings
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/$DIST/libnvidia-container.list | sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#" | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        sudo apt-get update -y
        sudo apt-get install -y nvidia-container-toolkit
        sudo systemctl restart docker
        """
    ).strip()
    write_remote_file(public_ip, key_path, "~/install-toolkit.sh", toolkit_script)
    ssh(public_ip, key_path, "bash ~/install-toolkit.sh && rm ~/install-toolkit.sh")
    ssh(public_ip, key_path, "sudo apt-get install -y docker-compose-plugin")

    if not args.skip_sync:
        excludes = [".git", "private_creator", "generated_scripts", "__pycache__"]
        remote_root = "~/Unreal_Vtuber"
        sync_project(public_ip, key_path, remote_root, excludes)
    else:
        info("Skipping project sync as requested")

    env_files = create_env_files(config)
    for filename, content in env_files.items():
        write_remote_file(public_ip, key_path, f"~/Unreal_Vtuber/{filename}", content)

    daemon_config = textwrap.dedent(
        """
        {
          "runtimes": {
            "nvidia": {
              "path": "nvidia-container-runtime",
              "runtimeArgs": []
            }
          },
          "default-runtime": "nvidia"
        }
        """
    ).strip()
    write_remote_file(public_ip, key_path, "~/daemon.json", daemon_config)
    ssh(public_ip, key_path, "sudo mv ~/daemon.json /etc/docker/daemon.json && sudo systemctl restart docker")

    ssh(public_ip, key_path, "cd ~/Unreal_Vtuber && ./scripts/generate_turn_credentials.sh")
    ssh(public_ip, key_path, "sudo docker network create vtuber_network || true")
    ssh(public_ip, key_path, "cd ~/Unreal_Vtuber && sudo docker compose -f docker-compose.unreal.yml pull")
    ssh(public_ip, key_path, "cd ~/Unreal_Vtuber && sudo docker compose -f docker-compose.unreal.yml up -d")
    ssh(public_ip, key_path, f"cd ~/Unreal_Vtuber && {orchestrator_registration_command(config)}")

    info("Provisioning complete")
    print(
        textwrap.dedent(
            f"""
            --------------------------------------------------------
            Instance ID     : {instance_id}
            Public IP       : {public_ip}
            Elastic IP ID   : {allocation_id or 'n/a'}
            Security Group  : {sg_id}
            SSH Key         : {key_path}

            The orchestrator stack is running on the new instance.
            Pixel Streaming ports are restricted to {config['DEDICATED_CLIENT_IP']}.
            Payments backend health polling allowed from {config['PAYMENTS_BACKEND_IP']}.

            Remember to resume the payments backend container once testing is ready.
            --------------------------------------------------------
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
