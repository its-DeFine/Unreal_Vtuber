import os
import time
import logging
import threading
from fastapi import FastAPI
import uvicorn

from .tool_registry import ToolRegistry
from .memory_manager import MemoryManager
from .clients.scb_client import SCBClient
from .clients.vtuber_client import VTuberClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "20"))
app = FastAPI()


def run_once(registry: ToolRegistry, memory: MemoryManager, scb: SCBClient, vtuber: VTuberClient):
    context = memory.get_recent_context()
    tool = registry.select_tool(context)
    if tool:
        result = tool(context)
        memory.store_memory(result)
        vtuber.post_message(result.get("message", ""))
        scb.publish_state(result)


def decision_loop(registry: ToolRegistry, memory: MemoryManager, scb: SCBClient, vtuber: VTuberClient):
    while True:
        start = time.time()
        run_once(registry, memory, scb, vtuber)
        duration = time.time() - start
        logging.info("cycle completed in %.2fs", duration)
        time.sleep(LOOP_INTERVAL)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    vtuber_endpoint = os.getenv("VTUBER_ENDPOINT", "http://localhost:8000/api")

    registry = ToolRegistry()
    registry.load_tools()
    memory = MemoryManager(db_url)
    scb = SCBClient(redis_url)
    vtuber = VTuberClient(vtuber_endpoint)

    thread = threading.Thread(target=decision_loop, args=(registry, memory, scb, vtuber), daemon=True)
    thread.start()
    logging.info("AutoGen agent started")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
