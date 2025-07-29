"""Entry point for Alpha AI server."""

import uvicorn
from alpha_ai.server import app
from alpha_ai.settings import settings


def main():
    """Run the Alpha AI server."""
    uvicorn.run(
        "alpha_ai.server:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )


if __name__ == "__main__":
    main()