from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DeliveryFinancialLine:
    route_id: str
    amount: float
    items: int


@dataclass
class FinancialReportDTO:
    date: str
    total_revenue: float
    lines: List[DeliveryFinancialLine]
    notes: Optional[str] = None
