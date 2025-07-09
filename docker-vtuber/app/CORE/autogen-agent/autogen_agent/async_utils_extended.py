"""
Extended Async Utilities
Additional async helper functions for testing
"""

import asyncio
from typing import Any, Callable, List, TypeVar, Optional
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def run_async_with_timeout(coro, timeout: float) -> Any:
    """Run async coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Coroutine timed out after {timeout} seconds")
        raise


async def batch_process_async(
    items: List[T], 
    processor: Callable[[T], Any], 
    batch_size: int = 10
) -> List[Any]:
    """Process items in batches asynchronously"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_tasks = [processor(item) for item in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend(batch_results)
    
    return results


async def async_retry(
    func: Callable, 
    retries: int = 3, 
    delay: float = 1.0,
    backoff: float = 2.0
) -> Any:
    """Retry async function with exponential backoff"""
    last_exception = None
    current_delay = delay
    
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.error(f"All {retries} attempts failed")
    
    raise last_exception


# Export for compatibility
__all__ = ['run_async_with_timeout', 'batch_process_async', 'async_retry']