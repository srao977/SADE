from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedObservation:
    entity_id: str
    event_time: float
    receive_time: float
    sequence_id: int
    price: float
    volume: float
    bid: float | None = None
    ask: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    session: str = "REGULAR"
    source_quality: float = 1.0
    availability_mask: dict[str, bool] | None = None

    def with_defaults(self) -> "NormalizedObservation":
        mask = dict(self.availability_mask or {})
        mask.setdefault("price", True)
        mask.setdefault("volume", self.volume is not None)
        mask.setdefault("bid", self.bid is not None)
        mask.setdefault("ask", self.ask is not None)
        return NormalizedObservation(
            entity_id=self.entity_id,
            event_time=float(self.event_time),
            receive_time=float(self.receive_time),
            sequence_id=int(self.sequence_id),
            price=float(self.price),
            volume=float(self.volume),
            bid=None if self.bid is None else float(self.bid),
            ask=None if self.ask is None else float(self.ask),
            bid_size=None if self.bid_size is None else float(self.bid_size),
            ask_size=None if self.ask_size is None else float(self.ask_size),
            session=self.session,
            source_quality=float(self.source_quality),
            availability_mask=mask,
        )


def assert_causal_sequence(previous: NormalizedObservation | None, current: NormalizedObservation) -> None:
    if previous is None:
        return
    if current.event_time < previous.event_time:
        raise ValueError("OUT_OF_ORDER_EVENT_TIME")
    if current.sequence_id <= previous.sequence_id:
        raise ValueError("NON_MONOTONIC_SEQUENCE")

