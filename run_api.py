"""
KisanOS API Runner.
Usage: python run_api.py
"""

import os
import uvicorn
from backend.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=settings.DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()
