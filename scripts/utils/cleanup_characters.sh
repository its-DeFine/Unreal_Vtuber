#!/bin/bash
# Unified character cleanup script - supports both S1 and S2 systems
# Usage: ./cleanup_characters.sh [S1|S2|both]

show_usage() {
    echo "Usage: $0 [S1|S2|both]"
    echo "  S1   - Setup characters for S1 system"
    echo "  S2   - Setup characters for S2 system"
    echo "  both - Setup characters for both systems"
    exit 1
}

cleanup_s1() {
    echo "Setting up S1 characters..."
    
    # Create S1 directory if it doesn't exist
    sudo mkdir -p /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S1
    
    # Define S1 characters (3 + default)
    local CHARACTERS_TO_KEEP=(
        "secretary_template.json"           # Default character
        "emma_teacher_template.json"        # Character 1
        "dr._house_doctor_template.json"    # Character 2
        "weatherman_template.json"          # Character 3
    )
    
    # Source and destination directories
    local SRC_DIR="/home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"
    local DEST_DIR="${SRC_DIR}/S1"
    
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
}

cleanup_s2() {
    echo "Setting up S2 characters..."
    
    # Create S2 directory if it doesn't exist
    sudo mkdir -p /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S2
    
    # Define S2 characters (3 + default)
    local CHARACTERS_TO_KEEP=(
        "secretary_template.json"              # Default character
        "professor_smith_teacher_template.json" # Character 1
        "dr._martinez_doctor_template.json"    # Character 2
        "testbot_coach_template.json"          # Character 3
    )
    
    # Source and destination directories
    local SRC_DIR="/home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"
    local DEST_DIR="${SRC_DIR}/S2"
    
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
}

# Main script logic
case "${1:-}" in
    "S1"|"s1")
        cleanup_s1
        ;;
    "S2"|"s2")
        cleanup_s2
        ;;
    "both"|"all")
        cleanup_s1
        echo ""
        cleanup_s2
        ;;
    *)
        show_usage
        ;;
esac

echo -e "\nCharacter cleanup completed successfully!"