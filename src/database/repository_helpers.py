from sqlalchemy.sql.operators import ilike_op

from domain.models import Base


def _prepare_filters_for_strings(model: Base, fields: list[str], search_key: str) -> list:
    """Готовит фильтры для поиска по тексту"""
    search_filter = list()
    for field in fields:
        atr = getattr(model, field)
        search_filter.append(ilike_op(atr, f"%{search_key}%"))
        search_filter.append(ilike_op(atr, f"%{search_key.capitalize()}%"))
        search_filter.append(ilike_op(atr, f"%{search_key.upper()}%"))
    return search_filter
