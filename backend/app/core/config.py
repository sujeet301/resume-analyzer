from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Resume Analyzer API"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "resume_analyzer"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_upload_size_mb: int = 10

    # Local semantic embedding model. It downloads model weights on first use.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Gemini is used for generative tasks. Set GEMINI_API_KEY in .env.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Adzuna credentials (register at developer.adzuna.com).
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # Set false to use the deterministic fallback if model download is unavailable.
    enable_semantic_embeddings: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return self.cors_origins

settings = Settings()
