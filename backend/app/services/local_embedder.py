"""Local embedder using sentence-transformers for offline embedding generation."""
import logging
from collections.abc import Iterable

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig

logger = logging.getLogger(__name__)


class LocalEmbedderConfig(EmbedderConfig):
    """Configuration for local embedder."""
    model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'  # Supports Chinese and English


class LocalEmbedder(EmbedderClient):
    """
    Local Embedder using sentence-transformers.
    
    This embedder runs locally without requiring API calls, suitable for:
    - Offline environments
    - Cost-sensitive applications
    - Privacy-focused deployments
    """

    def __init__(self, config: LocalEmbedderConfig | None = None):
        """
        Initialize the local embedder.
        
        Args:
            config: Configuration for the embedder
        """
        if config is None:
            config = LocalEmbedderConfig()
        
        self.config = config
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f'Loading local embedding model: {config.model_name}')
            self.model = SentenceTransformer(config.model_name)
            logger.info('Local embedding model loaded successfully')
        except ImportError:
            raise ImportError(
                'sentence-transformers is required for local embeddings. '
                'Install it with: pip install sentence-transformers'
            )

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float]:
        """
        Create embedding for a single input.
        
        Args:
            input_data: Text to embed
            
        Returns:
            Embedding vector
        """
        if isinstance(input_data, str):
            text = input_data
        elif isinstance(input_data, list) and len(input_data) > 0 and isinstance(input_data[0], str):
            text = input_data[0]
        else:
            raise ValueError(f'Unsupported input type: {type(input_data)}')
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Convert to list and truncate to configured dimension
        embedding_list = embedding.tolist()
        return embedding_list[: self.config.embedding_dim]

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        """
        Create embeddings for multiple inputs.
        
        Args:
            input_data_list: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Generate embeddings in batch for efficiency
        embeddings = self.model.encode(input_data_list, convert_to_numpy=True)
        
        # Convert to list and truncate to configured dimension
        return [
            embedding.tolist()[: self.config.embedding_dim]
            for embedding in embeddings
        ]
