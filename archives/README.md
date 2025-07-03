# Archives Directory

This directory contains archived/deprecated code that was removed from the main codebase but preserved for historical reference.

## Archive Structure

### 2025-01-02/
Date of archival: January 2, 2025

#### BYOC_OLD/
- **Original Location**: `/decide/BYOC_OLD/`
- **Description**: Complete "Bring Your Own Compute" system implementation
- **Reason for Archival**: Marked as OLD, all files last modified June 29, 2025
- **Notable Features**:
  - Orchestrator registration pattern
  - Web3/blockchain payment integration
  - Audio recording capabilities
  - Worker capacity management

#### orchestrator-legacy/
- **Original Location**: `/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/orchestrator/legacy/`
- **Description**: Legacy orchestrator implementations (V1 and V2)
- **Files Archived**:
  - `autonomous_orchestrator.py` - Original V1 implementation
  - `autonomous_orchestrator_v2.py` - V2 with enhanced features (deprecated)
  - `autonomous_orchestrator_wrapper.py` - Transitional compatibility layer
  - `reactive_orchestrator.py` - Experimental reactive approach
  - `reactive_example.py` - Example implementation
  - `reactive_api_routes.py` - API routes for reactive system
- **Reason for Archival**: Superseded by AutoGen V3 implementation

## Archival Policy

Code is archived rather than deleted when it:
1. Contains unique implementation patterns worth preserving
2. May be needed for reference or recovery
3. Represents significant development effort
4. Contains features that might be reimplemented in the future

## Recovery

To recover archived code:
```bash
git mv archives/YYYY-MM-DD/component_name original/location/
```

Note: Ensure the code is still compatible with the current system before restoring.