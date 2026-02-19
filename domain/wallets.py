from dataclasses import dataclass


@dataclass(frozen=True)
class Wallet:
    id: int
    name: str
    currency: str
    initial_balance: float
    system: bool = False
    allow_negative: bool = False
