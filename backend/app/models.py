from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    FILLED_PAPER = "FILLED_PAPER"
    REJECTED = "REJECTED"


@dataclass
class MarketTick:
    symbol: str
    price: float
    timestamp: datetime
    sector: str = "Unknown"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: int
    requested_price: float
    timestamp: datetime
    reasoning_id: str


@dataclass
class Trade:
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    notional: float
    fees: float
    slippage: float
    status: OrderStatus
    timestamp: datetime
    reasoning_id: str
    rejection_reason: str | None = None


@dataclass
class Position:
    symbol: str
    quantity: int
    average_price: float
    sector: str = "Unknown"


@dataclass
class AgentDecision:
    symbol: str
    action: OrderSide | str
    confidence: float
    target_weight: float
    reasoning: list[str]
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
