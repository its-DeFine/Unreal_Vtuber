#!/bin/bash
# Final script to complete character cleanup with sudo commands

echo "Character Cleanup Summary"
echo "========================"
echo
echo "This script will organize characters into S1 and S2 directories"
echo "Each directory will contain 3 unique characters + 1 default (secretary)"
echo
echo "S1 Characters:"
echo "  - secretary_template.json (default)"
echo "  - emma_teacher_template.json (teacher)"
echo "  - dr._house_doctor_template.json (doctor)"
echo "  - weatherman_template.json (weatherman)"
echo
echo "S2 Characters:"
echo "  - secretary_template.json (default)"
echo "  - professor_smith_teacher_template.json (teacher)"
echo "  - dr._martinez_doctor_template.json (doctor)"
echo "  - testbot_coach_template.json (coach)"
echo
echo "To complete the cleanup, run these commands with sudo access:"
echo
echo "# Create directories"
echo "sudo mkdir -p /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S1"
echo "sudo mkdir -p /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S2"
echo
echo "# Copy characters from temporary location"
echo "sudo cp /tmp/character_organization/S1/* /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S1/"
echo "sudo cp /tmp/character_organization/S2/* /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S2/"
echo
echo "# Set proper permissions"
echo "sudo chown -R geo:geo /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S1"
echo "sudo chown -R geo:geo /home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/S2"
echo
echo "Files not included in S1/S2 (will remain in main directory):"
echo "  - test_character.json"
echo "  - templates/ directory"