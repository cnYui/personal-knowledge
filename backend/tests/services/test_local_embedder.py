import asyncio
import sys
from types import ModuleType

import pytest

from app.services.local_embedder import LocalEmbedder, LocalEmbedderConfig


class FakeVector:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return list(self._values)


class FakeSentenceTransformer:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def encode(self, input_data, convert_to_numpy=True):
        if isinstance(input_data, list):
            return [FakeVector([0.1, 0.2, 0.3]), FakeVector([0.4, 0.5, 0.6])]
        return FakeVector([0.1, 0.2, 0.3])


def test_local_embedder_aligns_dimension_with_loaded_model(monkeypatch):
    fake_module = ModuleType('sentence_transformers')
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, 'sentence_transformers', fake_module)

    config = LocalEmbedderConfig(model_name='fake-model')

    assert config.embedding_dim == 1024

    embedder = LocalEmbedder(config=config)

    embedding = asyncio.run(embedder.create('hello'))

    assert embedding == [0.1, 0.2, 0.3]
    assert embedder.config.embedding_dim == 3
