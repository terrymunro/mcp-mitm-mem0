"""
Simple configuration for MCP MITM Mem0.

Loads settings from environment variables and .env file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )

    # Required: Mem0 SaaS API key
    mem0_api_key: str = Field(..., description="Mem0 API key from https://app.mem0.ai")
    
    # Optional settings
    debug: bool = Field(False, description="Enable debug mode")
    
    # MITM proxy settings
    mitm_host: str = Field("localhost", description="MITM proxy host")
    mitm_port: int = Field(8080, description="MITM proxy port")
    
    # MCP server settings
    mcp_name: str = Field("memory-service", description="MCP server name")
    
    # User identification
    default_user_id: str = Field("default_user", description="Default user ID for memories")


# Global settings instance
settings = Settings()