"""Shopping rules: entries, merging duplicates, aisles, who and when, and the regulars to re-add."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.smart_shopping_list.shopping import (
    ListError,
    ShoppingState,
    add_item,
    categorize,
    clear_done,
    complete_item,
    parse_entry,
    regulars,
    remove_item,
    reopen_item,
    update_item,
)

AMSTERDAM = ZoneInfo('Europe/Amsterdam')
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=AMSTERDAM)


def ids() -> object:
    counter = iter(range(1, 1000))
    return lambda: 'item-' + str(next(counter))


def added(state: ShoppingState, text: str, *, by: str = 'Tom', at: datetime = NOW, new_id: object = None) -> ShoppingState:
    return add_item(state, text=text, by=by, now=at, new_id=new_id or ids())


@pytest.mark.parametrize(('text', 'expected'), [
    ('melk', (1, 'melk')), ('2 melk', (2, 'melk')), ('2x melk', (2, 'melk')), ('3 × bananen', (3, 'bananen')),
    ('  Volkoren brood  ', (1, 'Volkoren brood')), ('melk 2', (1, 'melk 2')), ('0 melk', (1, '0 melk')),
])
def test_an_entry_may_start_with_a_quantity(text: str, expected: tuple[int, str]) -> None:
    assert parse_entry(text) == expected


@pytest.mark.parametrize('text', ['', '   ', '2x', 'x' * 101])
def test_an_empty_or_too_long_entry_is_refused(text: str) -> None:
    with pytest.raises(ListError):
        parse_entry(text)


@pytest.mark.parametrize(('name', 'category'), [
    ('Bananen', 'produce'), ('halfvolle melk', 'dairy'), ('Volkoren brood', 'bread'), ('kipfilet', 'meat_fish'),
    ('Flesvoeding', 'baby'), ('Luiers maat 2', 'baby'), ('wc-papier', 'household'), ('Tandpasta', 'care'),
    ('Spa rood', 'drinks'), ('pindakaas', 'pantry'), ('diepvriespizza', 'frozen'), ('Batterijen', 'household'), ('Verjaardagskaart', 'other'),
    ('milk', 'dairy'), ('diapers', 'baby'),
])
def test_items_are_sorted_into_aisles(name: str, category: str) -> None:
    assert categorize(name, remembered={}) == category


def test_a_remembered_aisle_beats_the_keyword_guess() -> None:
    assert categorize('Melkpoeder', remembered={'melkpoeder': 'baby'}) == 'baby'


def test_adding_records_who_and_when_and_the_aisle() -> None:
    state = added(ShoppingState(), '2x melk')
    item = state.items[0]
    assert (item.name, item.quantity, item.category, item.added_by, item.added_at, item.done) == ('melk', 2, 'dairy', 'Tom', NOW, False)


def test_adding_something_already_open_raises_the_quantity_instead_of_a_second_line() -> None:
    new_id = ids()
    state = added(ShoppingState(), 'Melk', new_id=new_id)
    state = added(state, '2 melk', by='Janou', new_id=new_id)
    assert len(state.items) == 1
    assert (state.items[0].name, state.items[0].quantity, state.items[0].added_by) == ('Melk', 3, 'Tom')


def test_completing_records_who_and_when_and_counts_the_purchase() -> None:
    state = added(ShoppingState(), 'melk')
    done = complete_item(state, item_id='item-1', by='Janou', now=NOW + timedelta(hours=2))
    item = done.items[0]
    assert (item.done, item.done_by, item.done_at) == (True, 'Janou', NOW + timedelta(hours=2))
    assert done.products['melk'].purchases == 1
    assert done.products['melk'].last_bought == NOW + timedelta(hours=2)


def test_adding_a_bought_item_again_opens_a_new_line() -> None:
    new_id = ids()
    state = complete_item(added(ShoppingState(), 'melk', new_id=new_id), item_id='item-1', by='Tom', now=NOW)
    state = added(state, 'melk', by='Janou', new_id=new_id)
    assert [(item.item_id, item.done) for item in state.items] == [('item-1', True), ('item-2', False)]


def test_reopening_clears_who_bought_it_and_takes_back_the_purchase() -> None:
    state = complete_item(added(ShoppingState(), 'melk'), item_id='item-1', by='Tom', now=NOW)
    reopened = reopen_item(state, item_id='item-1')
    assert (reopened.items[0].done, reopened.items[0].done_by, reopened.items[0].done_at) == (False, None, None)
    assert reopened.products['melk'].purchases == 0


def test_moving_an_item_to_another_aisle_is_remembered() -> None:
    new_id = ids()
    state = update_item(added(ShoppingState(), 'Melkpoeder', new_id=new_id), item_id='item-1', category='baby')
    assert state.items[0].category == 'baby'
    state = remove_item(state, item_id='item-1')
    assert added(state, 'melkpoeder', new_id=new_id).items[0].category == 'baby'


def test_an_unknown_aisle_or_quantity_is_refused() -> None:
    state = added(ShoppingState(), 'melk')
    with pytest.raises(ListError):
        update_item(state, item_id='item-1', category='garden')
    with pytest.raises(ListError):
        update_item(state, item_id='item-1', quantity=0)
    with pytest.raises(ListError):
        complete_item(state, item_id='item-9', by='Tom', now=NOW)


def test_clearing_removes_only_bought_items_and_keeps_the_history() -> None:
    new_id = ids()
    state = added(added(ShoppingState(), 'melk', new_id=new_id), 'brood', new_id=new_id)
    state = clear_done(complete_item(state, item_id='item-1', by='Tom', now=NOW))
    assert [item.name for item in state.items] == ['brood']
    assert state.products['melk'].purchases == 1


def test_regulars_are_the_most_bought_items_not_already_on_the_list() -> None:
    new_id = ids()
    state = ShoppingState()
    for day, name in enumerate(['melk', 'melk', 'melk', 'brood', 'brood', 'bananen']):
        state = added(state, name, new_id=new_id)
        open_item = next(item for item in state.items if not item.done)
        state = clear_done(complete_item(state, item_id=open_item.item_id, by='Tom', now=NOW + timedelta(days=day)))
    state = added(state, 'brood', new_id=new_id)
    assert [(regular.name, regular.purchases) for regular in regulars(state, limit=8)] == [('melk', 3), ('bananen', 1)]
    assert regulars(state, limit=1)[0].last_bought == NOW + timedelta(days=2)
