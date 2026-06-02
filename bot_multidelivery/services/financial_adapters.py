"""Adapters to convert between DB models and FinancialReportDTO.

Placeholders assume DB model `DailyFinancialReportDB` exists in `bot_multidelivery.database`.
Implement actual field mappings here to centralize conversions.
"""
from typing import List
from bot_multidelivery.schemas.financial import FinancialReportDTO, DeliveryFinancialLine

try:
    from bot_multidelivery.database import DailyFinancialReportDB
except Exception:
    DailyFinancialReportDB = None  # type: ignore


def db_to_dto(db_obj) -> FinancialReportDTO:
    """Converte um objeto DB para FinancialReportDTO.

    Ajuste os campos conforme o schema real do DB.
    """
    if db_obj is None:
        raise ValueError("db_obj is None")

    lines = []
    # Exemplo de mapeamento: db_obj.lines -> lista de dicts
    for l in getattr(db_obj, "lines", []) or []:
        lines.append(DeliveryFinancialLine(route_id=str(l.get("route_id")), amount=float(l.get("amount", 0)), items=int(l.get("items", 0))))

    dto = FinancialReportDTO(
        date=getattr(db_obj, "date", ""),
        total_revenue=float(getattr(db_obj, "revenue", 0)),
        lines=lines,
        notes=getattr(db_obj, "notes", None),
    )
    return dto


def dto_to_db(dto: FinancialReportDTO):
    """Converte DTO para formato pronto para persistência (DB model ou dict).

    Retorna uma instância de `DailyFinancialReportDB` se disponível, ou dict.
    """
    # Map FinancialReportDTO to DB payload compatible with DailyFinancialReportDB
    payload = {
        "date": dto.date,
        "revenue": dto.total_revenue,
        # rollup: lines -> deliverer breakdown by route_id
        "deliverer_breakdown": {l.route_id: l.amount for l in dto.lines},
        "total_packages": sum(l.items for l in dto.lines) if dto.lines else 0,
        "total_deliveries": len(dto.lines) if dto.lines else 0,
        "expenses": [],
        "notes": dto.notes,
    }

    if DailyFinancialReportDB:
        # Exemplo: DailyFinancialReportDB(**payload)
        try:
            return DailyFinancialReportDB(**payload)
        except Exception:
            return payload
    return payload


def dto_from_report(report) -> FinancialReportDTO:
    """Cria um FinancialReportDTO a partir de um objeto DailyFinancialReport (ou dict)."""
    lines = []
    # Se tiver deliverer_breakdown, transformar em lines com items=0
    for route_id, amount in (getattr(report, "deliverer_breakdown", {}) or {}).items():
        lines.append(DeliveryFinancialLine(route_id=str(route_id), amount=float(amount), items=0))

    dto = FinancialReportDTO(
        date=getattr(report, "date", ""),
        total_revenue=float(getattr(report, "revenue", getattr(report, "revenue", 0) or getattr(report, "net_profit", 0) or 0)),
        lines=lines,
        notes=getattr(report, "notes", None)
    )
    return dto
