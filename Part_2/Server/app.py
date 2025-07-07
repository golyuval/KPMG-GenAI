import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from Core.logger import get_logger, setup_logging
from routes import router
import uvicorn

# ------------- logger ----------------------------------------------

logger = get_logger(__name__)
setup_logging()

# ------------- app -------------------------------------------------

app = FastAPI(title="HMO Chatbot", version="0.1-alpha")

# ------------- include routes --------------------------------------

app.include_router(router)

# ------------- run -------------------------------------------------

if __name__ == "__main__":
    # If running directly, start with reload if possible
    # Note: --reload only works if 'app.py' is not imported as a module
    uvicorn.run(
        "Server.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        factory=False
    )