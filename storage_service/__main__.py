import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "storage_service.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("STORAGE_SERVICE_PORT", "9000")),
    )
