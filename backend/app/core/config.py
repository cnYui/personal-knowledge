from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "backend/uploads/images"
    knowledge_graph_base_url: str = "http://localhost:8001"
    multimodal_provider: str = "mock"
    multimodal_api_key: str = ""
    ocr_enabled: bool = True

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # OpenAI (for Graphiti)
    openai_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
