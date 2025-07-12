
# Compatibility layer for S2QueueOrchestrator
import asyncio
from shared.queue import enqueue_s2_processing

class S2QueueOrchestratorCompat:
    def __init__(self):
        pass
    
    async def enqueue_stimuli(self, stimuli_data):
        return await enqueue_s2_processing(stimuli_data)
