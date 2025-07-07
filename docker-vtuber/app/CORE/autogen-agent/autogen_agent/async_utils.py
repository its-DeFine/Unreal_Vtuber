"""
Async utilities for robust event loop and database operation handling
"""

import asyncio
import logging
import threading
import functools
from typing import Any, Callable, Coroutine, Optional


class AsyncContextManager:
    """
    Manages async operations safely across threads and event loops
    """
    
    def __init__(self):
        self._loop = None
        self._thread = None
        self._shutdown_event = asyncio.Event()
        
    async def run_in_context(self, coro: Coroutine) -> Any:
        """
        Run a coroutine safely in the managed async context
        """
        try:
            return await coro
        except Exception as e:
            logging.error(f"❌ [ASYNC_CONTEXT] Error in async operation: {e}")
            raise
    
    def run_async_safe(self, coro: Coroutine) -> Any:
        """
        Run async operation safely, handling event loop context
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_running_loop()
            # If we're in an event loop, create a task
            task = loop.create_task(self.run_in_context(coro))
            return task
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(self.run_in_context(coro))
    
    async def shutdown(self):
        """
        Gracefully shutdown async context
        """
        self._shutdown_event.set()
        logging.info("✅ [ASYNC_CONTEXT] Async context shutdown completed")


def async_safe_wrapper(func):
    """
    Decorator to make async functions safer with event loop handling
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logging.warning(f"⚠️ [ASYNC_SAFE] Event loop closed, skipping operation: {func.__name__}")
                return None
            raise
        except Exception as e:
            logging.error(f"❌ [ASYNC_SAFE] Error in {func.__name__}: {e}")
            raise
    
    return wrapper


def run_with_timeout(coro: Coroutine, timeout: float = 30.0) -> Optional[Any]:
    """
    Run coroutine with timeout and error handling
    """
    try:
        return asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logging.warning(f"⚠️ [ASYNC_TIMEOUT] Operation timed out after {timeout}s")
        return None
    except Exception as e:
        logging.error(f"❌ [ASYNC_TIMEOUT] Error in timed operation: {e}")
        return None


class SafeAsyncThread:
    """
    Thread-safe async operation runner with proper cleanup
    """
    
    def __init__(self, thread_name: str = "SafeAsyncThread"):
        self.thread_name = thread_name
        self.loop = None
        self.thread = None
        self._shutdown = False
        
    def start(self):
        """Start the async thread"""
        if self.thread and self.thread.is_alive():
            return
            
        self.thread = threading.Thread(target=self._run_loop, name=self.thread_name, daemon=True)
        self.thread.start()
        
        # Wait for loop to be ready
        while self.loop is None:
            threading.Event().wait(0.01)
    
    def _run_loop(self):
        """Run the event loop in this thread"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run until shutdown
            self.loop.run_forever()
            
        finally:
            # Clean shutdown
            try:
                # Cancel all pending tasks
                pending = asyncio.all_tasks(self.loop)
                if pending:
                    logging.info(f"🔄 [SAFE_ASYNC_THREAD] Cancelling {len(pending)} pending tasks")
                    for task in pending:
                        task.cancel()
                    
                    # Wait for cancellation
                    self.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception as e:
                logging.warning(f"⚠️ [SAFE_ASYNC_THREAD] Cleanup warning: {e}")
            finally:
                try:
                    self.loop.close()
                except Exception as e:
                    logging.warning(f"⚠️ [SAFE_ASYNC_THREAD] Loop close warning: {e}")
    
    def run_coro(self, coro: Coroutine) -> Any:
        """
        Run a coroutine in this thread's event loop
        """
        if self._shutdown:
            logging.warning("⚠️ [SAFE_ASYNC_THREAD] Thread is shutting down, skipping operation")
            return None
            
        if not self.loop:
            self.start()
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=30.0)
        except Exception as e:
            logging.error(f"❌ [SAFE_ASYNC_THREAD] Error running coroutine: {e}")
            return None
    
    def shutdown(self):
        """Shutdown the async thread gracefully"""
        if self._shutdown:
            return
            
        self._shutdown = True
        
        if self.loop and not self.loop.is_closed():
            # Schedule shutdown
            asyncio.run_coroutine_threadsafe(self._async_shutdown(), self.loop)
            
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
    
    async def _async_shutdown(self):
        """Async shutdown operations"""
        logging.info(f"🛑 [SAFE_ASYNC_THREAD] Shutting down {self.thread_name}")
        self.loop.stop()


# Global safe async thread for shared operations
_global_async_thread = None


def get_global_async_thread() -> SafeAsyncThread:
    """Get or create global async thread for safe operations"""
    global _global_async_thread
    
    if _global_async_thread is None:
        _global_async_thread = SafeAsyncThread("GlobalAsyncThread")
        _global_async_thread.start()
    
    return _global_async_thread


def run_async_safely(coro: Coroutine) -> Any:
    """
    Run async operation safely using global async thread
    """
    thread = get_global_async_thread()
    return thread.run_coro(coro)


def shutdown_async_utils():
    """
    Shutdown async utilities gracefully
    """
    global _global_async_thread
    
    if _global_async_thread:
        _global_async_thread.shutdown()
        _global_async_thread = None
        logging.info("✅ [ASYNC_UTILS] Async utilities shutdown completed")