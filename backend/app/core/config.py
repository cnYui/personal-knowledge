from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_PATH = Path(__file__).resolve().parents[2] / '.env'


class Settings(BaseSettings):
    database_url: str = "postgresql://pkb_user:pkb_password@localhost:5432/personal_knowledge_base"
    upload_dir: str = "backend/uploads/images"
    knowledge_graph_base_url: str = "http://localhost:8001"
    multimodal_provider: str = "mock"
    multimodal_api_key: str = ""
    ocr_enabled: bool = True

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Runtime model routing
    dialog_provider: str = "deepseek"
    dialog_api_key: str = ""
    dialog_base_url: str = "https://api.deepseek.com/v1"
    dialog_model: str = "deepseek-chat"
    knowledge_build_provider: str = "deepseek"
    knowledge_build_api_key: str = ""
    knowledge_build_base_url: str = "https://api.deepseek.com/v1"
    knowledge_build_model: str = "deepseek-chat"

    # Relationship text deduplication (semantic near-duplicate filtering)
    graph_relation_dedup_threshold: float = 0.93

    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")


settings = Settings()


def refresh_settings() -> Settings:
    """Reload settings from the backing env file into the shared singleton."""
    reloaded = Settings()
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(reloaded, field_name))
    return settings
