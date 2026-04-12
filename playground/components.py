"""Realistic ML-pipeline components used as instantiation targets."""

from __future__ import annotations

from typing import Any


class Tokenizer:
    """Text tokenizer — leaf component."""

    def __init__(self, vocab_size: int = 30000, lowercase: bool = False) -> None:
        self.vocab_size = vocab_size
        self.lowercase = lowercase

    def __repr__(self) -> str:
        return f"Tokenizer(vocab_size={self.vocab_size}, lowercase={self.lowercase})"


class Encoder:
    """Transformer encoder — leaf component."""

    def __init__(self, dim: int = 256, num_layers: int = 4, dropout: float = 0.0) -> None:
        self.dim = dim
        self.num_layers = num_layers
        self.dropout = dropout

    def __repr__(self) -> str:
        return f"Encoder(dim={self.dim}, num_layers={self.num_layers}, dropout={self.dropout})"


class Decoder:
    """Transformer decoder — leaf component."""

    def __init__(self, dim: int = 256, num_layers: int = 4) -> None:
        self.dim = dim
        self.num_layers = num_layers

    def __repr__(self) -> str:
        return f"Decoder(dim={self.dim}, num_layers={self.num_layers})"


class Pipeline:
    """Composite: encoder + decoder + tokenizer."""

    def __init__(
        self,
        encoder: Any = None,
        decoder: Any = None,
        tokenizer: Any = None,
    ) -> None:
        self.encoder = encoder
        self.decoder = decoder
        self.tokenizer = tokenizer

    def __repr__(self) -> str:
        return f"Pipeline(\n  encoder={self.encoder},\n  decoder={self.decoder},\n  tokenizer={self.tokenizer}\n)"


class TrainingLoop:
    """Top-level orchestrator — tests deep recursive nesting."""

    def __init__(
        self,
        pipeline: Any = None,
        optimizer: Any = None,
        epochs: int = 10,
    ) -> None:
        self.pipeline = pipeline
        self.optimizer = optimizer
        self.epochs = epochs

    def __repr__(self) -> str:
        return f"TrainingLoop(\n  pipeline={self.pipeline},\n  optimizer={self.optimizer},\n  epochs={self.epochs}\n)"


def create_optimizer(lr: float, weight_decay: float = 0.0) -> dict[str, float]:
    """Factory function target — returns optimizer config dict."""
    return {"lr": lr, "weight_decay": weight_decay}
