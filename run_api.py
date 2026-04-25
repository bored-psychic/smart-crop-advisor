"""
KisanOS API Runner.
Usage: python run_api.py
"""

import uvicorn
from backend.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()
