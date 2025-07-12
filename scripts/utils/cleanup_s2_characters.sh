#!/bin/bash
# Cleanup script for S2 characters - keeps only 3 characters + default

# Create S2 directory if it doesn't exist
sudo mkdir -p /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S2

# Define the characters to keep (3 + default)
CHARACTERS_TO_KEEP=(
    "secretary_template.json"              # Default character
    "professor_smith_teacher_template.json" # Character 1
    "dr._martinez_doctor_template.json"    # Character 2
    "testbot_coach_template.json"          # Character 3
)

# Source directory
SRC_DIR="/home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"
# Destination directory
DEST_DIR="${SRC_DIR}/S2"

# Copy selected characters to S2
for char in "${CHARACTERS_TO_KEEP[@]}"; do
    if [ -f "${SRC_DIR}/${char}" ]; then
        echo "Copying ${char} to S2..."
        sudo cp "${SRC_DIR}/${char}" "${DEST_DIR}/"
    else
        echo "Warning: ${char} not found!"
    fi
done

# List the contents of S2
echo -e "\nS2 directory contents:"
ls -la "${DEST_DIR}/"