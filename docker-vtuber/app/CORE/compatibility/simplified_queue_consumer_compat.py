
# Compatibility layer for SimplifiedQueueConsumer  
from shared.bootstrap import get_bootstrap
from shared.processing import StimuliProcessor

class SimplifiedQueueConsumerCompat:
    def __init__(self):
        pass
    
    async def start_consuming(self):
        bootstrap = get_bootstrap()
        processor = bootstrap.get_service(StimuliProcessor)
        # Legacy consumer logic would be handled by unified processor
        pass
