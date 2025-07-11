#!/bin/bash
# Script to organize characters into S1 and S2 folders (3 characters + default each)

echo "Character Organization Script"
echo "============================"

# Base directory
BASE_DIR="/home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters"

# Check current characters
echo -e "\nCurrent characters in main directory:"
ls -1 "${BASE_DIR}"/*.json 2>/dev/null | xargs -n1 basename

# Since we can't create directories due to permissions, let's at least show what would be organized
echo -e "\n\nProposed S1 characters (3 + default):"
echo "- secretary_template.json (default)"
echo "- emma_teacher_template.json"
echo "- dr._house_doctor_template.json"
echo "- weatherman_template.json"

echo -e "\n\nProposed S2 characters (3 + default):"
echo "- secretary_template.json (default)"
echo "- professor_smith_teacher_template.json"
echo "- dr._martinez_doctor_template.json"
echo "- testbot_coach_template.json"

echo -e "\n\nNote: Cannot create S1/S2 directories due to permission restrictions."
echo "The characters directory is owned by root and requires sudo access."

# Alternative: Create a temporary structure to show the organization
TEMP_DIR="/tmp/character_organization"
mkdir -p "${TEMP_DIR}/S1" "${TEMP_DIR}/S2"

# S1 characters
echo -e "\n\nCreating temporary organization structure in ${TEMP_DIR}..."
for char in "secretary_template.json" "emma_teacher_template.json" "dr._house_doctor_template.json" "weatherman_template.json"; do
    if [ -f "${BASE_DIR}/${char}" ]; then
        cp "${BASE_DIR}/${char}" "${TEMP_DIR}/S1/" 2>/dev/null
        echo "Copied ${char} to temporary S1"
    fi
done

# S2 characters
for char in "secretary_template.json" "professor_smith_teacher_template.json" "dr._martinez_doctor_template.json" "testbot_coach_template.json"; do
    if [ -f "${BASE_DIR}/${char}" ]; then
        cp "${BASE_DIR}/${char}" "${TEMP_DIR}/S2/" 2>/dev/null
        echo "Copied ${char} to temporary S2"
    fi
done

echo -e "\n\nTemporary structure created:"
echo "S1 contents:"
ls -1 "${TEMP_DIR}/S1/"
echo -e "\nS2 contents:"
ls -1 "${TEMP_DIR}/S2/"

echo -e "\n\nTo complete the organization, run with sudo:"
echo "sudo mkdir -p ${BASE_DIR}/S1 ${BASE_DIR}/S2"
echo "sudo cp ${TEMP_DIR}/S1/* ${BASE_DIR}/S1/"
echo "sudo cp ${TEMP_DIR}/S2/* ${BASE_DIR}/S2/"