from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    # Database
    DATABASE_URL: str

    # Authentication (optional for MCP-only deployment)
    BETTER_AUTH_SECRET: str = ""
    BETTER_AUTH_URL: str = "http://localhost:3000"  # Better Auth frontend URL for JWKS

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Environment
    ENVIRONMENT: str = "development"

    # Connection Pooling (for database)
    DB_POOL_SIZE: int = 5
    DB_POOL_MAX_OVERFLOW: int = 10

    # OpenAI Configuration (optional for MCP-only deployment)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_API_TIMEOUT: int = 30

    # MCP Server Configuration
    # MCP server URL - separate service deployment
    # Production: https://evolution-todo-mcp.onrender.com
    # Development: http://localhost:8001
    MCP_SERVER_URL: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 100

    @property
    def mcp_server_url(self) -> str:
        """
        Get MCP server URL.

        Returns MCP_SERVER_URL if set, otherwise defaults to localhost:8001.

        Returns:
            str: MCP server URL
        """
        if self.MCP_SERVER_URL:
            return self.MCP_SERVER_URL

        # Default: Local MCP server on port 8001
        return "http://localhost:8001"


# Create a single instance of settings
settings = Settings()