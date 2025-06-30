"""
Simple configuration for MCP MITM Mem0.

Loads settings from environment variables and .env file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Required: Mem0 SaaS API key
    mem0_api_key: str = Field(..., description="Mem0 API key from https://app.mem0.ai")
    
    # Optional: Organization and project for multi-tenancy
    mem0_org_id: str | None = Field(None, description="Mem0 organization ID (optional)")
    mem0_project_id: str | None = Field(None, description="Mem0 project ID (optional)")

    # Optional settings
    debug: bool = Field(False, description="Enable debug mode")

    # MITM proxy settings
    mitm_host: str = Field("localhost", description="MITM proxy host")
    mitm_port: int = Field(8080, description="MITM proxy port")

    # MCP server settings
    mcp_name: str = Field("mcp-mitm-mem0", description="MCP server name")

    # User identification
    default_user_id: str = Field(
        "default_user", description="Default user ID for memories"
    )
    default_agent_id: str = Field(
        "claude-code", description="Default agent ID for memories"
    )
    
    # Memory organization
    memory_categories: list[dict[str, str]] = Field(
        default=[
            {"coding": "Programming languages, syntax, code examples, and development techniques"},
            {"debugging": "Error messages, troubleshooting steps, bug fixes, and debugging strategies"},  
            {"architecture": "System design decisions, architectural patterns, and technical design choices"},
            {"preferences": "User preferences, settings, and configuration choices"}
        ],
        description="Custom categories with descriptions for organizing memories"
    )


# Global settings instance
settings = Settings()
