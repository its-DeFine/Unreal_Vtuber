# Persona-Aware Tool System Documentation

## 🎯 Overview

The Persona-Aware Tool System provides character-specific tool access control, mission-based operations, and seamless S1/S2 character state synchronization. This system ensures that different character personas only have access to tools appropriate to their expertise and mission objectives.

## 🏗️ Architecture Components

### Core Components

1. **Character State Manager** (`character_state_manager.py`)
   - Synchronizes character state between S1 and S2 systems
   - Manages character missions and operational modes
   - Provides character context for tool selection

2. **Persona-Aware Tool Registry** (`persona_aware_tool_registry.py`)
   - Extends base tool registry with persona-based access control
   - Restricts tool availability based on character persona
   - Provides persona-aware tool scoring and selection

3. **Mission System**
   - Mission templates for different persona types
   - Operational mode management (autonomous, reactive, hybrid)
   - Target outcomes and success metrics

4. **Admin Character Tool Integration**
   - Notifies S2 systems of character changes
   - Updates tool availability when characters switch
   - Maintains character state consistency

## 🎭 Character Personas and Tool Access

### Doctor Persona
- **Mission**: Medical Information and Health Guidance
- **Operational Mode**: Reactive
- **Available Tools**:
  - `medical_information_tool` - Medical information and health guidance
  - `health_assessment_tool` - Health assessments and evaluations
  - `wellness_recommendation_tool` - Wellness and lifestyle recommendations
  - `symptom_analysis_tool` - Symptom analysis and medical guidance
  - `medication_information_tool` - Medication information and safety
  - `admin_character_tool` - Universal character management
  - `goal_management_tools` - Universal goal management
  - `core_evolution_tool` - Universal system evolution

### Teacher Persona
- **Mission**: Educational Instruction and Learning Support
- **Operational Mode**: Hybrid
- **Available Tools**:
  - `educational_content_tool` - Educational content and learning guidance
  - `learning_assessment_tool` - Learning assessments and evaluations
  - `curriculum_planning_tool` - Curriculum planning and development
  - `study_guidance_tool` - Study guidance and learning support
  - `knowledge_verification_tool` - Knowledge verification and testing
  - `admin_character_tool` - Universal character management
  - `goal_management_tools` - Universal goal management
  - `core_evolution_tool` - Universal system evolution

### Chef Persona
- **Mission**: Culinary Expertise and Cooking Guidance
- **Operational Mode**: Reactive
- **Available Tools**:
  - `recipe_generation_tool` - Recipe generation and cooking instructions
  - `ingredient_analysis_tool` - Ingredient analysis and nutrition
  - `cooking_technique_tool` - Cooking techniques and methods
  - `nutrition_information_tool` - Nutrition information and guidance
  - `meal_planning_tool` - Meal planning and dietary guidance
  - `admin_character_tool` - Universal character management
  - `goal_management_tools` - Universal goal management
  - `core_evolution_tool` - Universal system evolution

### Coach Persona
- **Mission**: Fitness Coaching and Wellness Motivation
- **Operational Mode**: Autonomous
- **Available Tools**:
  - `workout_planning_tool` - Workout planning and fitness guidance
  - `fitness_assessment_tool` - Fitness assessments and evaluations
  - `motivation_tool` - Motivational support and encouragement
  - `goal_tracking_tool` - Goal tracking and progress monitoring
  - `exercise_instruction_tool` - Exercise instruction and form guidance
  - `admin_character_tool` - Universal character management
  - `goal_management_tools` - Universal goal management
  - `core_evolution_tool` - Universal system evolution

### Librarian Persona
- **Mission**: Information Organization and Research Support
- **Operational Mode**: Hybrid
- **Available Tools**:
  - `research_tool` - Research assistance and information gathering
  - `information_organization_tool` - Information organization and management
  - `fact_checking_tool` - Fact checking and verification
  - `knowledge_discovery_tool` - Knowledge discovery and exploration
  - `citation_tool` - Citation and reference management
  - `admin_character_tool` - Universal character management
  - `goal_management_tools` - Universal goal management
  - `core_evolution_tool` - Universal system evolution

## 🔄 Character State Synchronization

### S1 to S2 Synchronization Flow

```
S1 Character Change → Admin Character Tool → S2 Notification → Character State Manager → Tool Registry Update
```

1. **Character Change in S1**: User switches character via admin command
2. **Admin Tool Processing**: Admin character tool processes the switch
3. **S2 Notification**: Tool notifies S2 systems of the change
4. **State Manager Update**: Character state manager syncs with S1
5. **Tool Registry Update**: Persona-aware tool registry updates available tools

### Character State Data Structure

```python
@dataclass
class CharacterState:
    character_id: str
    character_name: str
    role: str
    personality_traits: List[str]
    domain_expertise: List[str]
    behavioral_rules: List[str]
    mission: Optional[CharacterMission] = None
    available_tools: Set[str] = field(default_factory=set)
    last_sync: Optional[datetime] = None
    is_active: bool = False
```

### Mission Configuration

```python
@dataclass
class CharacterMission:
    mission_id: str
    title: str
    description: str
    objectives: List[str]
    target_outcomes: List[str]
    success_metrics: List[str]
    available_tools: List[str]
    priority_contexts: List[str]
    operational_mode: str  # autonomous, reactive, hybrid
```

## 🔧 Tool Access Control

### Persona-Specific Tool Mappings

The system maintains mappings of allowed and restricted tools for each persona:

```python
self.persona_tool_mappings = {
    "doctor": {
        "allowed_tools": ["medical_information_tool", "health_assessment_tool", ...],
        "restricted_tools": ["recipe_generation_tool", "cooking_technique_tool", ...],
        "priority_boost": 0.3
    },
    # ... other personas
}
```

### Universal Tools

Some tools are available to all personas:
- `admin_character_tool` - Character management
- `goal_management_tools` - Goal system
- `core_evolution_tool` - System evolution
- `variable_tool_calls` - Dynamic tool selection

### Tool Selection Algorithm

1. **Persona Check**: Verify tool is allowed for current persona
2. **Base Score**: Calculate base tool relevance score
3. **Persona Boost**: Apply persona-specific priority boost
4. **Mission Context**: Boost tools relevant to character mission
5. **Operational Mode**: Adjust based on character's operational mode
6. **Selection**: Choose highest scoring available tool

## 🎯 Mission-Based Operations

### Operational Modes

#### Autonomous Mode
- **Behavior**: Proactive tool selection and execution
- **Tool Priority**: Goal management and evolution tools boosted
- **Use Case**: Characters that actively pursue objectives (Coach)

#### Reactive Mode
- **Behavior**: Responds to user input and stimuli
- **Tool Priority**: Character-specific tools boosted
- **Use Case**: Characters that provide on-demand expertise (Doctor, Chef)

#### Hybrid Mode
- **Behavior**: Combines autonomous and reactive behaviors
- **Tool Priority**: Balanced tool selection
- **Use Case**: Characters that both respond and proactively assist (Teacher, Librarian)

### Mission Objectives and Outcomes

Each persona has specific mission objectives and target outcomes:

**Doctor Mission Example**:
- **Objectives**: Provide medical information, health guidance, patient education
- **Target Outcomes**: Improved health awareness, better understanding of conditions
- **Success Metrics**: Information accuracy, patient satisfaction, behavior changes

## 📡 API Endpoints

### Character State Status
```http
GET /api/persona/status

Response:
{
  "persona_system_active": true,
  "timestamp": "2025-07-08T19:49:38.000Z",
  "tool_registry": {
    "persona_awareness_enabled": true,
    "current_persona": "doctor",
    "available_tools_for_persona": ["medical_information_tool", ...],
    "persona_tool_count": 8
  },
  "character_manager": {
    "manager_active": true,
    "current_character": {
      "character_name": "Dr. House",
      "role": "Medical Professional",
      "operational_mode": "reactive",
      "mission_active": true
    }
  }
}
```

### Admin Character Management
```http
POST /api/stimuli/receive
Content-Type: application/json

{
  "stimuli_id": "character_switch_001",
  "content": "admin: switch character Dr. House",
  "source": "admin_console",
  "priority": "high"
}
```

## 🧪 Testing Framework

### Test Coverage

The system includes comprehensive tests for:

1. **Character State Manager**
   - Mission template loading
   - Character state updates
   - Persona type determination
   - Tool availability calculation

2. **Persona-Aware Tool Registry**
   - Tool restriction enforcement
   - Persona-based tool selection
   - Scoring algorithm accuracy
   - Tool availability queries

3. **Admin Tool Integration**
   - Character change notifications
   - S2 system updates
   - Command parsing accuracy
   - Template generation

4. **Mission System**
   - Mission template validation
   - Operational mode handling
   - Objective tracking
   - Success metric calculation

### Running Tests

```bash
# Run persona-aware tool system tests
python3 test_persona_aware_tools.py

# Expected output:
# ✅ All tests completed successfully!
# 🎯 Persona-Aware Tool System Features Verified:
#    • Character state synchronization between S1 and S2
#    • Mission-based tool access control
#    • Persona-specific tool availability
#    • Admin character change notifications
#    • Tool selection with persona awareness
#    • Character template generation
```

## 🛠️ Implementation Examples

### Creating a New Persona-Specific Tool

```python
# tools/medical_information_tool.py
async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """Medical information tool - restricted to doctor persona"""
    
    # Log persona-specific usage
    logger.info("🏥 [MEDICAL_TOOL] Medical information tool executed by doctor persona")
    
    # Extract medical query
    content = context.get("content", "")
    character_name = context.get("character_name", "Doctor")
    
    # Generate medical guidance
    medical_response = generate_medical_guidance(content, character_name)
    
    return {
        "success": True,
        "response": medical_response,
        "tool_used": "medical_information_tool",
        "persona_required": "doctor"
    }
```

### Adding Character Change Notification

```python
# In admin_character_tool.py
async def execute_admin_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
    if command_type == "switch_character":
        # Execute S1 character switch
        result = await self.switch_character_in_s1(character_id)
        
        if result["success"]:
            # Notify S2 systems of character change
            await self.notify_s2_character_change(character_id)
            
            response = f"✅ Successfully switched to character '{character_name}'!"
            response += f"\n🔄 S2 systems updated for persona-aware tool access"
            return {"success": True, "response": response, "s2_notified": True}
```

## 🔧 Configuration and Customization

### Adding New Persona Types

1. **Define Mission Template**:
```python
# In character_state_manager.py
self.mission_templates["scientist"] = CharacterMission(
    mission_id="scientific_research",
    title="Scientific Research and Analysis",
    description="Provide scientific information and research guidance",
    objectives=["Conduct research", "Analyze data", "Explain concepts"],
    available_tools=["research_tool", "data_analysis_tool", "lab_equipment_tool"],
    priority_contexts=["research", "science", "experiment", "analysis"],
    operational_mode="hybrid"
)
```

2. **Configure Tool Mappings**:
```python
# In persona_aware_tool_registry.py
self.persona_tool_mappings["scientist"] = {
    "allowed_tools": ["research_tool", "data_analysis_tool", "lab_equipment_tool"],
    "restricted_tools": ["recipe_generation_tool", "medical_information_tool"],
    "priority_boost": 0.25
}
```

3. **Create Persona-Specific Tools**:
```python
# tools/research_tool.py
async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """Research tool - restricted to scientist persona"""
    return {"success": True, "persona_required": "scientist"}
```

### Modifying Operational Modes

Operational modes can be customized in the tool selection algorithm:

```python
# In persona_aware_tool_registry.py
def _calculate_tool_score_with_persona(self, tool_name: str, context: dict, ...):
    operational_mode = self.character_state_manager.get_operational_mode()
    
    if operational_mode == "autonomous":
        # Boost autonomous tools
        if tool_name in ["goal_management_tools", "core_evolution_tool"]:
            base_score += 0.15
    elif operational_mode == "reactive":
        # Boost character-specific tools
        if tool_name in allowed_tools:
            base_score += 0.1
```

## 📊 Performance and Monitoring

### Metrics Tracked

- **Tool Selection Accuracy**: Percentage of correct persona-tool matches
- **Character State Sync Success**: S1/S2 synchronization success rate
- **Mission Objective Progress**: Tracking toward mission goals
- **Tool Usage Patterns**: Analysis of tool usage by persona
- **Operational Mode Effectiveness**: Performance by operational mode

### Monitoring Commands

```bash
# Check persona system status
curl -s http://localhost:8200/api/persona/status | jq .

# Monitor admin operations
curl -s http://localhost:8200/api/admin/control-panel | jq '.admin_operations'

# Check tool availability
curl -s http://localhost:8200/api/stimuli/tools | jq '.available_tools'
```

## 🚀 Benefits and Use Cases

### Key Benefits

1. **Expertise Authenticity**: Tools match character expertise
2. **Mission Alignment**: Tool selection supports character objectives
3. **Operational Flexibility**: Multiple operational modes for different personas
4. **Seamless Integration**: Transparent S1/S2 synchronization
5. **Scalable Architecture**: Easy addition of new personas and tools

### Use Cases

1. **Educational Content**: Teacher persona provides learning-focused tools
2. **Medical Guidance**: Doctor persona offers health-related assistance
3. **Culinary Expertise**: Chef persona delivers cooking and nutrition tools
4. **Fitness Coaching**: Coach persona provides motivation and workout tools
5. **Research Support**: Librarian persona offers information and research tools

## 🔗 Integration with Existing Systems

### Admin Command Processing Integration

The persona-aware tool system integrates seamlessly with the existing admin command processing system:

- **Silent Character Changes**: Tool availability updates without speech
- **Announced Changes**: Character changes with speech notification
- **Control Panel Monitoring**: Track persona changes and tool updates

### Stimuli Processing Integration

The system enhances stimuli processing with persona awareness:

- **Context-Aware Tool Selection**: Tools chosen based on character mission
- **Priority Context Matching**: Mission-relevant stimuli get priority
- **Operational Mode Adaptation**: Tool behavior adapts to character mode

This persona-aware tool system provides a sophisticated foundation for character-specific AI interactions while maintaining the flexibility and power of the underlying AutoGen framework.