# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Optional, List, Dict

# ==================== AUTH & TEAM ====================
class DelivererInput(BaseModel):
    name: str
    telegram_id: int
    is_partner: bool = False

# ==================== SESSIONS ====================
class StartSessionInput(BaseModel):
    date: Optional[str] = None
    period: str = "manhã"
    base_address: Optional[str] = None
    base_lat: Optional[float] = None
    base_lng: Optional[float] = None

class FinalizeSessionInput(BaseModel):
    session_id: Optional[str] = None
    revenue: Optional[float] = None
    extra_revenue: float = 0.0
    other_costs: float = 0.0
    expenses: Optional[List[Dict[str, object]]] = None

# ==================== ROUTES & OPTIMIZATION ====================
class RouteValueInput(BaseModel):
    value: float
    session_id: Optional[str] = None

class OptimizeInput(BaseModel):
    num_deliverers: int
    session_id: Optional[str] = None

class AssignRouteInput(BaseModel):
    route_id: str
    deliverer_id: int
    session_id: Optional[str] = None

# ==================== SEPARATION ====================
class SeparationScanInput(BaseModel):
    barcode: str
    session_id: Optional[str] = None

# ==================== TRANSFERS ====================
class TransferRequestInput(BaseModel):
    package_ids: List[str]
    from_deliverer_id: int
    to_deliverer_id: int
    reason: str

class TransferApprovalInput(BaseModel):
    transfer_id: str
    approved: bool
    admin_id: int
    admin_name: str
    rejection_reason: Optional[str] = None
