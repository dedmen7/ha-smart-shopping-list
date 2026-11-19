"""Texts the integration writes itself, in English with translations per Home Assistant language."""

from datetime import datetime

from .shopping import Item

TEXTS = {
    'en': {
        'supply_added_by': 'Supply check', 'added_by': 'Added by {name}', 'bought_by': 'Bought by {name} · {when}', 'bought': 'Bought · {when}',
        'months': ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'),
    },
    'nl': {
        'supply_added_by': 'Voorraadcheck', 'added_by': 'Toegevoegd door {name}', 'bought_by': 'Gehaald door {name} · {when}', 'bought': 'Gehaald · {when}',
        'months': ('jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'),
    },
}


def _table(language: str) -> dict:
    return TEXTS.get(language.split('-')[0].lower(), TEXTS['en'])


def text(language: str, key: str) -> str:
    return _table(language)[key]


def item_description(item: Item, *, language: str, now: datetime) -> str | None:
    """Who added an open item, or who bought it and when; the day is named when it was not today. Times are local."""
    table = _table(language)
    if not item.done:
        return None if item.added_by is None else table['added_by'].format(name=item.added_by)
    if item.done_at is None:
        return None
    moment = item.done_at.astimezone(now.tzinfo)
    when = moment.strftime('%H:%M')
    if moment.date() != now.date():
        when = str(moment.day) + ' ' + table['months'][moment.month - 1] + ' ' + when
    if item.done_by is None:
        return table['bought'].format(when=when)
    return table['bought_by'].format(name=item.done_by, when=when)
