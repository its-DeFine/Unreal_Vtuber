# S1/S2 Routing Fix Report

## Summary

Fixed the routing logic in the GraphFlow External Stimuli System to ensure proper S1/S2 routing, especially preventing trader stimuli from going to S1.

## Issues Found

### 1. Emergency Override Not Checking S2-Specific Metadata
The emergency override system was not checking for S2-specific metadata fields like:
- `character_id` (e.g., "trader")
- `character_type` (e.g., "trader") 
- `team_type` (e.g., "trader")
- `processing_mode` (e.g., "s2_only")
- `force_s2` flag
- `target_systems` array

### 2. Decision Matrix Rule Priorities
The S2-specific routing rules in the decision matrix had lower priorities than some general rules, causing incorrect routing.

### 3. Keyword Matching Issues
- The word "hi" was matching inside "this" due to substring matching
- Analysis-only requests were being incorrectly routed to S1

## Changes Made

### 1. Enhanced Emergency Override (`/app/CORE/graphflow-stimuli-system/config/emergency_override.py`)

#### Added S2-Specific Character Detection
```python
# S2-specific character types that MUST go to S2 only
self.s2_only_characters = [
    "trader", "trader_character", "financial_expert", "market_analyst"
]

# S2 team types
self.s2_team_types = [
    "trader", "streamer", "teacher", "researcher", "analyst"
]
```

#### Added S2 Routing Logic (Highest Priority)
```python
# Force S2-only routing for specific characters
if any(s2_char in character_id for s2_char in self.s2_only_characters):
    return ProcessingDecision.ANALYSIS_ONLY

# Check explicit S2 routing metadata
if processing_mode == "s2_only":
    return ProcessingDecision.ANALYSIS_ONLY

if metadata.get('target_systems') == ["s2"]:
    return ProcessingDecision.ANALYSIS_ONLY
```

#### Fixed Word Boundary Matching
```python
# Use word boundary matching for short words like "hi"
if len(keyword) <= 2:
    if re.search(rf'\b{keyword}\b', content_lower):
        has_speech_keyword = True
```

### 2. Updated Decision Matrix Rule Priorities (`/app/CORE/graphflow-stimuli-system/src/config/decision_matrix.py`)

- Moved S2-specific rules to priority 95-99 (highest in admin_override category)
- Lowered general admin rules to priority 86-90
- Added new rule for S2 source detection

### 3. Created Comprehensive Test Suite (`/scripts/test_routing_fix.py`)

Created a test suite with 10 test scenarios covering:
- Direct speech requests → S1 (AVATAR_AND_ANALYSIS)
- Trader character analysis → S2 only (ANALYSIS_ONLY)
- S2-only processing mode → S2 only (ANALYSIS_ONLY)
- Educational content with speech → Both S1+S2
- Force S2 flags → S2 only
- Analysis-only keywords → S2 only

## Test Results

### Routing Test Results
```
✅ 10/10 tests passed (100%)
- Direct speech requests correctly go to S1
- Trader stimuli NEVER go to S1 (always S2 only)
- S2-specific metadata correctly routes to S2
- Hybrid requests (speech + analysis) go to both
- Analysis-only requests go to S2
```

### S2 Character Teams Test Results
```
S1: 4/4 tests passed (100%) - Routing is working correctly
S2: 0/4 tests passed (0%) - Different issue: S2 teams failing with EOF errors
```

## Remaining Issues

While the routing is now fixed, there's a separate issue with S2 processing:

1. **S2 Container Health**: The autogen_agent container is unhealthy
2. **EOF Errors**: All S2 teams are failing with "EOF when reading a line" errors
3. **API Errors**: The `/api/stimuli/receive` endpoint returns 422 errors
4. **Queue Processing**: The queue consumer is not polling properly

## Recommendations

1. **Routing**: ✅ Fixed - The emergency override now correctly routes S2-specific stimuli
2. **S2 Processing**: Needs separate investigation for the EOF errors
3. **Monitoring**: Add logging to track routing decisions in production
4. **Testing**: Run the test suite regularly to ensure routing remains correct

## Key Routing Rules Summary

1. **S2 Only (ANALYSIS_ONLY)**:
   - Character ID/type contains "trader"
   - `processing_mode: "s2_only"`
   - `force_s2: true`
   - `target_systems: ["s2"]`
   - Pure analysis keywords without speech

2. **S1+S2 (AVATAR_AND_ANALYSIS)**:
   - Speech keywords (speak, say, voice, etc.)
   - User interactions
   - Admin requests
   - High priority (unless trader)
   - Hybrid requests (speech + analysis)

3. **Fallback**: AVATAR_AND_ANALYSIS for reliability