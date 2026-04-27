"""Local embedder using sentence-transformers for offline embedding generation."""
import asyncio
import hashlib
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
        self.model = None
        self._use_fallback = False
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f'Loading local embedding model: {config.model_name}')
            self.model = SentenceTransformer(config.model_name)
            self._sync_embedding_dimension_with_model()
            logger.info('Local embedding model loaded successfully')
        except ImportError:
            logger.warning(
                'sentence-transformers is unavailable; falling back to deterministic '
                'hash-based embeddings for local startup'
            )
            self._use_fallback = True

    def _sync_embedding_dimension_with_model(self) -> None:
        """Align configured embedding dimension with the loaded model's real output size."""
        if self.model is None:
            return

        detected_dimension = None
        get_dimension = getattr(self.model, 'get_sentence_embedding_dimension', None)

        if callable(get_dimension):
            detected_dimension = get_dimension()

        if not detected_dimension:
            probe_embedding = self.model.encode('dimension probe', convert_to_numpy=True)
            detected_dimension = len(probe_embedding.tolist())

        self.config = self.config.model_copy(update={'embedding_dim': int(detected_dimension)})
        logger.info('Aligned local embedding dimension to model output: %s', self.config.embedding_dim)

    def _fallback_embedding(self, text: str) -> list[float]:
        """Generate a deterministic placeholder embedding when the model is unavailable."""
        dimension = self.config.embedding_dim
        values: list[float] = []
        seed = text.encode('utf-8')

        while len(values) < dimension:
            seed = hashlib.sha256(seed).digest()
            for byte in seed:
                values.append((byte / 255.0) * 2.0 - 1.0)
                if len(values) >= dimension:
                    break

        return values

    def _encode_sync(self, input_data: str | list[str]):
        if self.model is None:
            raise RuntimeError('Local embedding model is not initialized')
        return self.model.encode(input_data, convert_to_numpy=True)

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
        if self._use_fallback:
            return self._fallback_embedding(text)

        embedding = await asyncio.to_thread(self._encode_sync, text)

        return embedding.tolist()

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        """
        Create embeddings for multiple inputs.
        
        Args:
            input_data_list: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Generate embeddings in batch for efficiency
        if self._use_fallback:
            return [self._fallback_embedding(text) for text in input_data_list]

        embeddings = await asyncio.to_thread(self._encode_sync, input_data_list)

        return [embedding.tolist() for embedding in embeddings]
