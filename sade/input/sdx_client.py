"""
Module/File Name: sade/input/sdx_client.py
Date Created / Migrated: August 25, 2026
Purpose:
    Provide SADE-owned gRPC client integration for SDX V1.1.
Executive Overview:
    This module is a direct migration of previously validated Python SDX
    client behavior into the independent SADE repository.
Role in SADE:
    Input transport adapter for bounded StreamVectors ingestion.
Inputs:
    Endpoint, entities, and stream bounds.
Outputs:
    SDX controller responses and MarketVector streams.
Parameters / Configuration:
    DEFAULT_ENDPOINT and per-call timeout values.
Persistent State:
    gRPC channel and stubs for data/controller services.
External Dependencies:
    grpc, generated sdx.v1 protobuf bindings packaged under SADE.
Main Callers / Consumers:
    sade.adaptive_pipeline.pipeline
Important Assumptions:
    SDX service contract remains compatible with V1.1 bindings.
Scientific Provenance:
    Input transport adapted from previously validated SDX client behavior.
Explicit Exclusions / What This Module Does NOT Do:
    - No scientific computation
    - No output serialization
    - No fallback to external repositories
Failure / Error Behavior:
    gRPC errors propagate to callers for explicit failure handling.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Optional

import grpc

_THIS_DIR = Path(__file__).resolve().parent
_GENERATED_ROOT = _THIS_DIR / "generated"
if str(_GENERATED_ROOT) not in sys.path:
    sys.path.insert(0, str(_GENERATED_ROOT))

loaded_sdx = sys.modules.get("sdx")
if loaded_sdx is not None and hasattr(loaded_sdx, "__path__"):
    generated_sdx_path = str(_GENERATED_ROOT / "sdx")
    if generated_sdx_path not in loaded_sdx.__path__:
        loaded_sdx.__path__.insert(0, generated_sdx_path)

from sdx.v1 import sdx_pb2, sdx_pb2_grpc


DEFAULT_ENDPOINT = "localhost:50051"


@dataclass(frozen=True)
class StreamVectorRecord:
    """Typed record view over SDX MarketVector fields."""

    entity_id: str
    source_row_index: int
    source_timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class SadeSdxClient:
    """SADE-owned SDX V1.1 gRPC client.

    Args:
        endpoint: SDX gRPC endpoint address.

    Raises:
        RuntimeError: if client stubs are unavailable after connect.
    """

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT) -> None:
        self.endpoint = endpoint
        self._channel: Optional[grpc.Channel] = None
        self._data_stub: Optional[sdx_pb2_grpc.SDXDataServiceStub] = None
        self._controller_stub: Optional[sdx_pb2_grpc.SDXControllerServiceStub] = None

    def connect(self) -> None:
        """Open channel and initialize service stubs once."""
        if self._channel is not None:
            return
        self._channel = grpc.insecure_channel(self.endpoint)
        self._data_stub = sdx_pb2_grpc.SDXDataServiceStub(self._channel)
        self._controller_stub = sdx_pb2_grpc.SDXControllerServiceStub(self._channel)

    def close(self) -> None:
        """Close channel and clear stubs."""
        if self._channel is None:
            return
        self._channel.close()
        self._channel = None
        self._data_stub = None
        self._controller_stub = None

    def configure_router(self, entities: Iterable[str], timeout_seconds: Optional[float] = None) -> sdx_pb2.ConfigureRouterResponse:
        return self._controller().ConfigureRouter(
            sdx_pb2.ConfigureRouterRequest(entities=list(entities)),
            timeout=timeout_seconds,
        )

    def get_router_status(self, timeout_seconds: Optional[float] = None) -> sdx_pb2.GetRouterStatusResponse:
        return self._controller().GetRouterStatus(
            sdx_pb2.GetRouterStatusRequest(),
            timeout=timeout_seconds,
        )

    def get_source_status(self, timeout_seconds: Optional[float] = None) -> sdx_pb2.GetSourceStatusResponse:
        return self._controller().GetSourceStatus(
            sdx_pb2.GetSourceStatusRequest(),
            timeout=timeout_seconds,
        )

    def start_stream(self, entities: Iterable[str], max_vectors_per_entity: int, timeout_seconds: Optional[float] = None):
        """Create and start StreamVectors RPC call."""
        request = sdx_pb2.StreamRequest(
            entities=list(entities),
            max_vectors_per_entity=max_vectors_per_entity,
        )
        return self._data().StreamVectors(request, timeout=timeout_seconds)

    def stream_vectors(self, entities: Iterable[str], max_vectors_per_entity: int, timeout_seconds: Optional[float] = None) -> Iterator[sdx_pb2.MarketVector]:
        """Yield MarketVectors from StreamVectors RPC call."""
        stream = self.start_stream(entities=entities, max_vectors_per_entity=max_vectors_per_entity, timeout_seconds=timeout_seconds)
        for vector in stream:
            yield vector

    @staticmethod
    def cancel_stream(stream) -> None:
        """Cancel an active stream call."""
        stream.cancel()

    @staticmethod
    def to_record(vector: sdx_pb2.MarketVector) -> StreamVectorRecord:
        """Convert protobuf vector to dataclass record."""
        return StreamVectorRecord(
            entity_id=vector.entity_id,
            source_row_index=vector.source_row_index,
            source_timestamp=vector.source_timestamp,
            open=vector.open,
            high=vector.high,
            low=vector.low,
            close=vector.close,
            volume=vector.volume,
        )

    def _data(self) -> sdx_pb2_grpc.SDXDataServiceStub:
        """Return data stub, connecting on first use."""
        self.connect()
        if self._data_stub is None:
            raise RuntimeError("SDX data stub is unavailable")
        return self._data_stub

    def _controller(self) -> sdx_pb2_grpc.SDXControllerServiceStub:
        """Return controller stub, connecting on first use."""
        self.connect()
        if self._controller_stub is None:
            raise RuntimeError("SDX controller stub is unavailable")
        return self._controller_stub
