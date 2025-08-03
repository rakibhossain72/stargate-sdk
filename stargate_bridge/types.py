from dataclasses import dataclass
from typing import List, Optional, Dict, Any




@dataclass
class QuoteParams:
    """Parameters for requesting a Stargate quote."""
    src_token: str
    dst_token: str
    src_address: str
    dst_address: str
    src_chain_key: str
    dst_chain_key: str
    src_amount: str
    dst_amount_min: str


@dataclass
class TransactionData:
    """Transaction data structure."""
    to: str
    data: str
    value: str = "0"


@dataclass
class RouteStep:
    """A single step in a Stargate route."""
    transaction: TransactionData