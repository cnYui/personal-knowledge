from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Graph extraction LLM provider
    graph_llm_provider: str = "deepseek"

    # OpenAI-compatible settings (legacy StepFun compatible)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.stepfun.com/v1"

    # DeepSeek API settings
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Relationship text deduplication (semantic near-duplicate filtering)
    graph_relation_dedup_threshold: float = 0.93

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
