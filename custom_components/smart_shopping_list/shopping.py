"""The shopping list: entries, merging duplicates, aisles, who added and bought what, and the regulars."""

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

MAXIMUM_NAME_LENGTH = 100
MAXIMUM_QUANTITY = 99
ARCHIVE_AFTER = timedelta(days=1)
ARCHIVE_KEEP = timedelta(days=365)

# Aisles in shop order; the first matching keyword wins, so the more specific aisles come first.
CATEGORIES = ('produce', 'bread', 'meat_fish', 'dairy', 'frozen', 'pantry', 'drinks', 'baby', 'care', 'household', 'other')
KEYWORDS = {
    'baby': ('flesvoeding', 'nutrilon', 'kruidvat baby', 'luier', 'billendoek', 'babyvoeding', 'speen', 'babyshampoo', 'diaper', 'formula', 'baby'),
    'care': ('tandpasta', 'tandenborstel', 'shampoo', 'conditioner', 'zeep', 'douchegel', 'deodorant', 'deo', 'scheer', 'toothpaste', 'soap', 'paracetamol', 'pleister'),
    'household': ('wc-papier', 'wc papier', 'wc', 'toiletpapier', 'keukenrol', 'afwas', 'vaatwas', 'wasmiddel', 'wasverzachter', 'vuilniszak', 'afvalzak', 'schoonmaak', 'allesreiniger', 'batterij', 'toilet paper', 'detergent', 'trash bag'),
    'produce': ('appel', 'banan', 'peer', 'peren', 'sinaasappel', 'mandarijn', 'citroen', 'limoen', 'druif', 'druiven', 'aardbei', 'blauwe bes', 'framboz', 'tomaat', 'tomaten', 'komkommer', 'paprika', 'sla', 'spinazie', 'ui', 'uien', 'knoflook', 'wortel', 'aardappel', 'broccoli', 'bloemkool', 'courgette', 'champignon', 'avocado', 'prei', 'andijvie', 'boontjes', 'fruit', 'groente', 'apple', 'banana', 'tomato', 'cucumber', 'lettuce', 'onion', 'garlic', 'carrot', 'potato', 'vegetable'),
    'bread': ('brood', 'bolletje', 'broodje', 'croissant', 'beschuit', 'cracker', 'wrap', 'krentenbol', 'pistolet', 'bread', 'bagel'),
    'meat_fish': ('kip', 'gehakt', 'vlees', 'biefstuk', 'ham', 'worst', 'rookworst', 'spek', 'shoarma', 'zalm', 'vis', 'tonijn', 'garnal', 'chicken', 'beef', 'meat', 'fish', 'salmon', 'bacon'),
    'dairy': ('melk', 'yoghurt', 'kwark', 'kaas', 'boter', 'room', 'slagroom', 'ei', 'eieren', 'vla', 'karnemelk', 'milk', 'yogurt', 'cheese', 'butter', 'cream', 'egg'),
    'frozen': ('diepvries', 'ijs', 'pizza', 'frietjes', 'patat', 'frozen', 'ice cream'),
    'pantry': ('pasta', 'spaghetti', 'macaroni', 'rijst', 'meel', 'suiker', 'olie', 'saus', 'soep', 'koffie', 'thee', 'hagelslag', 'pindakaas', 'jam', 'muesli', 'cornflakes', 'havermout', 'koek', 'chips', 'noten', 'kruiden', 'zout', 'peper', 'rice', 'flour', 'sugar', 'oil', 'sauce', 'coffee', 'tea', 'cereal'),
    'drinks': ('water', 'spa', 'sap', 'cola', 'bier', 'wijn', 'frisdrank', 'limonade', 'ranja', 'juice', 'beer', 'wine', 'soda'),
}
QUANTITY_PREFIX = re.compile(r'^\s*(\d{1,2})\s*[x×]?\s+(\S.*)$', re.IGNORECASE)


class ListError(ValueError):
    """A refused change; `key` is the translation key, the message is the English text."""

    MESSAGES = {
        'empty_entry': 'Enter what you need.',
        'entry_too_long': 'Keep an item under 100 characters.',
        'invalid_quantity': 'Choose a quantity from 1 to 99.',
        'invalid_category': 'Choose one of the aisles.',
        'item_not_found': 'This item was changed or removed. Refresh the list.',
    }

    def __init__(self, key: str) -> None:
        super().__init__(self.MESSAGES[key])
        self.key = key


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    quantity: int
    category: str
    added_by: str | None
    added_at: datetime
    done: bool = False
    done_by: str | None = None
    done_at: datetime | None = None


@dataclass(frozen=True)
class Product:
    """What the list remembers about a product across shopping trips."""

    name: str
    category: str
    purchases: int = 0
    last_bought: datetime | None = None


@dataclass(frozen=True)
class ShoppingState:
    items: tuple[Item, ...] = ()
    products: dict[str, Product] | None = None
    archive: tuple[Item, ...] = ()

    def __post_init__(self) -> None:
        if self.products is None:
            object.__setattr__(self, 'products', {})


def parse_entry(text: str) -> tuple[int, str]:
    entry = ' '.join(str(text).split())
    match = QUANTITY_PREFIX.match(entry)
    quantity, name = (int(match.group(1)), match.group(2).strip()) if match and int(match.group(1)) > 0 else (1, entry)
    if not name or re.fullmatch(r'\d{1,2}\s*[x×]', name, re.IGNORECASE) or re.fullmatch(r'\d+[x×]?', entry, re.IGNORECASE):
        raise ListError('empty_entry')
    if len(name) > MAXIMUM_NAME_LENGTH:
        raise ListError('entry_too_long')
    return quantity, name


def categorize(name: str, *, remembered: dict[str, str]) -> str:
    key = product_key(name)
    if key in remembered:
        return remembered[key]
    for category, words in KEYWORDS.items():
        if any(re.search(r'(?<![a-zà-ÿ])' + re.escape(word), key) for word in words):
            return category
    return 'other'


def add_item(state: ShoppingState, *, text: str, by: str | None, now: datetime, new_id: Callable[[], str]) -> ShoppingState:
    quantity, name = parse_entry(text)
    key = product_key(name)
    open_same = next((item for item in state.items if not item.done and product_key(item.name) == key), None)
    if open_same is not None:
        merged = replace(open_same, quantity=min(MAXIMUM_QUANTITY, open_same.quantity + quantity))
        return replace(state, items=_swap(state.items, merged))
    remembered = {product_key(product.name): product.category for product in state.products.values()}
    item = Item(item_id=new_id(), name=name, quantity=quantity, category=categorize(name, remembered=remembered), added_by=by, added_at=now)
    return replace(state, items=(*state.items, item))


def complete_item(state: ShoppingState, *, item_id: str, by: str | None, now: datetime) -> ShoppingState:
    item = _find(state, item_id)
    if item.done:
        return state
    key = product_key(item.name)
    known = state.products.get(key, Product(name=item.name, category=item.category))
    product = replace(known, name=item.name, category=item.category, purchases=known.purchases + 1, last_bought=now)
    done = replace(item, done=True, done_by=by, done_at=now)
    return replace(state, items=_swap(state.items, done), products={**state.products, key: product})


def reopen_item(state: ShoppingState, *, item_id: str) -> ShoppingState:
    item = _find(state, item_id)
    if not item.done:
        return state
    key = product_key(item.name)
    products = dict(state.products)
    if key in products:
        products[key] = replace(products[key], purchases=max(0, products[key].purchases - 1))
    reopened = replace(item, done=False, done_by=None, done_at=None)
    return replace(state, items=_swap(state.items, reopened), products=products)


def update_item(state: ShoppingState, *, item_id: str, name: str | None = None, quantity: int | None = None, category: str | None = None) -> ShoppingState:
    item = _find(state, item_id)
    if quantity is not None and (isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAXIMUM_QUANTITY):
        raise ListError('invalid_quantity')
    if category is not None and category not in CATEGORIES:
        raise ListError('invalid_category')
    new_name = item.name if name is None else parse_entry(name)[1]
    changed = replace(item, name=new_name, quantity=item.quantity if quantity is None else quantity, category=category or item.category)
    products = dict(state.products)
    if category is not None:
        key = product_key(new_name)
        known = products.get(key, Product(name=new_name, category=category))
        products[key] = replace(known, category=category)
    return replace(state, items=_swap(state.items, changed), products=products)


def remove_item(state: ShoppingState, *, item_id: str) -> ShoppingState:
    _find(state, item_id)
    return replace(state, items=tuple(item for item in state.items if item.item_id != item_id))


def archive_bought(state: ShoppingState, *, now: datetime, after: timedelta = ARCHIVE_AFTER) -> ShoppingState:
    """Moves items bought at least `after` ago to the archive, newest first, and forgets archived items older than a year."""
    due = [item for item in state.items if item.done and item.done_at is not None and item.done_at <= now - after]
    kept = tuple(item for item in state.archive if item.done_at is not None and item.done_at >= now - ARCHIVE_KEEP)
    if not due and kept == state.archive:
        return state
    archive = tuple(sorted((*due, *kept), key=lambda item: item.done_at, reverse=True))
    due_ids = {item.item_id for item in due}
    return replace(state, items=tuple(item for item in state.items if item.item_id not in due_ids), archive=archive)


def clear_done(state: ShoppingState, *, now: datetime) -> ShoppingState:
    """Archives every bought item right away."""
    return archive_bought(state, now=now, after=timedelta(0))


def regulars(state: ShoppingState, *, limit: int) -> list[Product]:
    on_list = {product_key(item.name) for item in state.items if not item.done}
    bought = [product for key, product in state.products.items() if product.purchases > 0 and key not in on_list]
    return sorted(bought, key=lambda product: (-product.purchases, product.name.casefold()))[:limit]


def product_key(name: str) -> str:
    return ' '.join(name.casefold().split())


def _find(state: ShoppingState, item_id: str) -> Item:
    for item in state.items:
        if item.item_id == item_id:
            return item
    raise ListError('item_not_found')


def _swap(items: tuple[Item, ...], changed: Item) -> tuple[Item, ...]:
    return tuple(changed if item.item_id == changed.item_id else item for item in items)
