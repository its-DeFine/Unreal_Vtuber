"""
Example script for the Reactive VTuber System
Demonstrates character management and external event handling
"""

import requests
import json
import time

# Base URL for the API
BASE_URL = "http://localhost:5001/api/v1/reactive"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


def test_character_management():
    """Test character management endpoints"""
    print_section("Character Management")
    
    # List available characters
    response = requests.get(f"{BASE_URL}/character/list")
    print(f"\nAvailable characters: {json.dumps(response.json(), indent=2)}")
    
    # Get current character
    response = requests.get(f"{BASE_URL}/character/current")
    if response.status_code == 200:
        print(f"\nCurrent character: {response.json()['name']}")
    else:
        print("\nNo character currently active")
    
    # Create a new character
    secretary_char = {
        "id": "demo_secretary",
        "name": "Alice",
        "role": "Executive Secretary",
        "personality_traits": ["professional", "efficient", "friendly"],
        "communication_style": "formal but warm",
        "emotional_range": "calm and supportive",
        "domain_expertise": ["scheduling", "email management", "task prioritization"],
        "response_patterns": {
            "email_notification": "You have a new email from {sender} about {subject}. It's marked as {priority} priority.",
            "meeting_reminder": "Your {meeting_type} with {attendees} is scheduled for {time}."
        },
        "behavioral_rules": [
            "Always prioritize urgent matters",
            "Be concise but informative",
            "Maintain professional boundaries"
        ]
    }
    
    response = requests.post(f"{BASE_URL}/character/create", json=secretary_char)
    if response.status_code == 201:
        print(f"\nCreated character: {response.json()['character']['name']}")
    
    # Switch to the new character
    response = requests.post(f"{BASE_URL}/character/load", json={"character_id": "demo_secretary"})
    if response.status_code == 200:
        print(f"\nSwitched to character: {response.json()['character']['name']}")


def test_external_events():
    """Test external event handling"""
    print_section("External Event Handling")
    
    # Test email event
    email_event = {
        "type": "email",
        "source": "gmail",
        "priority": "high",
        "data": {
            "sender": "CEO",
            "subject": "Quarterly Review Meeting",
            "preview": "Please prepare the Q3 financial reports..."
        }
    }
    
    print("\n1. Sending email notification...")
    response = requests.post(f"{BASE_URL}/example/email")
    if response.status_code == 200:
        print(f"Response: {response.json()['response']}")
    
    time.sleep(2)  # Wait between events
    
    # Test calendar event
    print("\n2. Sending calendar reminder...")
    response = requests.post(f"{BASE_URL}/example/calendar")
    if response.status_code == 200:
        print(f"Response: {response.json()['response']}")
    
    time.sleep(2)
    
    # Test chat interaction
    chat_message = {
        "message": "What's my schedule for today?"
    }
    
    print("\n3. Sending chat message...")
    response = requests.post(f"{BASE_URL}/event/chat", json=chat_message)
    if response.status_code == 200:
        print(f"Response: {response.json()['response']}")


def test_system_status():
    """Test system status endpoints"""
    print_section("System Status")
    
    # Get system status
    response = requests.get(f"{BASE_URL}/status")
    print(f"\nSystem status: {json.dumps(response.json(), indent=2)}")
    
    # Get configuration
    response = requests.get(f"{BASE_URL}/config")
    print(f"\nSystem configuration: {json.dumps(response.json(), indent=2)}")


def test_teacher_character():
    """Test teacher character interactions"""
    print_section("Teacher Character Demo")
    
    # Create teacher character
    teacher_char = {
        "id": "demo_teacher",
        "name": "Professor Agatha",
        "role": "Interactive Teacher",
        "personality_traits": ["patient", "encouraging", "knowledgeable"],
        "communication_style": "clear and educational",
        "emotional_range": "warm and supportive",
        "domain_expertise": ["mathematics", "physics", "general science"],
        "response_patterns": {
            "correct_answer": "Excellent work! {explanation}",
            "incorrect_answer": "Not quite, but you're on the right track. {hint}"
        },
        "behavioral_rules": [
            "Adapt explanations to student level",
            "Use examples and analogies",
            "Encourage questions",
            "Provide positive reinforcement"
        ]
    }
    
    response = requests.post(f"{BASE_URL}/character/create", json=teacher_char)
    if response.status_code == 201:
        print(f"\nCreated teacher character: {response.json()['character']['name']}")
    
    # Switch to teacher
    response = requests.post(f"{BASE_URL}/character/load", json={"character_id": "demo_teacher"})
    if response.status_code == 200:
        print(f"\nSwitched to: {response.json()['character']['name']}")
    
    # Test educational interactions
    questions = [
        "What is photosynthesis?",
        "Can you explain gravity in simple terms?",
        "How do computers work?"
    ]
    
    for question in questions:
        print(f"\nStudent asks: {question}")
        response = requests.post(f"{BASE_URL}/event/chat", json={"message": question})
        if response.status_code == 200:
            print(f"Teacher responds: {response.json()['response']}")
        time.sleep(3)  # Wait between questions


def main():
    """Run all tests"""
    print("🎭 Reactive VTuber System Demo")
    print("==============================")
    
    try:
        # Check if the system is running
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code != 200:
            print("❌ System is not running. Please start the NeuroSync Player first.")
            return
        
        # Run tests
        test_character_management()
        time.sleep(2)
        
        test_external_events()
        time.sleep(2)
        
        test_teacher_character()
        time.sleep(2)
        
        test_system_status()
        
        print("\n✅ Demo completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Make sure the NeuroSync Player is running.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 