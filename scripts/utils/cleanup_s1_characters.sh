#!/bin/bash
# Cleanup script for S1 characters - keeps only 3 characters + default

# Create S1 directory if it doesn't exist
sudo mkdir -p /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S1

# Define the characters to keep (3 + default)
CHARACTERS_TO_KEEP=(
    "secretary_template.json"           # Default character
    "emma_teacher_template.json"        # Character 1
    "dr._house_doctor_template.json"    # Character 2
    "weatherman_template.json"          # Character 3
)

# Source directory
SRC_DIR="/home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"
# Destination directory
DEST_DIR="${SRC_DIR}/S1"

# Copy selected characters to S1
for char in "${CHARACTERS_TO_KEEP[@]}"; do
    if [ -f "${SRC_DIR}/${char}" ]; then
        echo "Copying ${char} to S1..."
        sudo cp "${SRC_DIR}/${char}" "${DEST_DIR}/"
    else
        echo "Warning: ${char} not found!"
    fi
done

# List the contents of S1
echo -e "\nS1 directory contents:"
ls -la "${DEST_DIR}/"