"""Application dependencies for FastAPI dependency injection."""

from app.workers import GraphitiIngestWorker

# Global worker instance
graphiti_worker: GraphitiIngestWorker | None = None


def get_worker():
    """Dependency to get the GraphitiIngestWorker instance."""
    if graphiti_worker is None:
        raise RuntimeError('GraphitiIngestWorker not initialized')
    return graphiti_worker
