"""Convert the list to and from the JSON stored in Home Assistant's .storage folder."""

from dataclasses import asdict
from datetime import datetime
from typing import Any

from .shopping import Item, Product, ShoppingState
from .supply import SupplySettings


def to_stored(*, state: ShoppingState, supply: SupplySettings, opened_at: datetime | None, listed_for: datetime | None) -> dict[str, Any]:
    return {
        'items': [{**asdict(item), 'added_at': item.added_at.isoformat(), 'done_at': _iso(item.done_at)} for item in state.items],
        'products': {key: {**asdict(product), 'last_bought': _iso(product.last_bought)} for key, product in state.products.items()},
        'supply': asdict(supply),
        'opened_at': _iso(opened_at),
        'listed_for': _iso(listed_for),
    }


def from_stored(data: dict[str, Any]) -> tuple[ShoppingState, SupplySettings, datetime | None, datetime | None]:
    items = tuple(Item(**{**item, 'added_at': _moment(item['added_at']), 'done_at': _optional(item.get('done_at'))}) for item in data.get('items', []))
    products = {key: Product(**{**product, 'last_bought': _optional(product.get('last_bought'))}) for key, product in data.get('products', {}).items()}
    supply = SupplySettings(**data.get('supply', {}))
    return ShoppingState(items=items, products=products), supply, _optional(data.get('opened_at')), _optional(data.get('listed_for'))


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat()


def _optional(value: str | None) -> datetime | None:
    return None if value is None else _moment(value)


def _moment(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError('A stored moment has no time zone.')
    return moment
