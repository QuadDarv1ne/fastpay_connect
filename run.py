import os
import uvicorn
import logging

def run_app():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8080))

    logging.basicConfig(level=logging.INFO)
    logging.info(f"Starting server at {host}:{port}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True if os.getenv("ENV") == "development" else False
    )

if __name__ == "__main__":
    run_app()
