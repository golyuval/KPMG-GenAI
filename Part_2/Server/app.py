
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
import routes
from Core.logger_setup import get_logger
from routes import router

# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

# ------------- app -------------------------------------------------

app = FastAPI(title="HMO Chatbot", version="0.1-alpha")

# ------------- include routes --------------------------------------

app.include_router(router)

# ------------- startup ---------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("HMO Chatbot backend starting up...")
    logger.info("All endpoints loaded successfully")

# ------------- run -------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)