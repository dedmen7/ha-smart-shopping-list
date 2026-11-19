# Smart Shopping List for Home Assistant

[![Validate](https://github.com/dedmen7/ha-smart-shopping-list/actions/workflows/validate.yml/badge.svg)](https://github.com/dedmen7/ha-smart-shopping-list/actions/workflows/validate.yml)
[![Tests](https://github.com/dedmen7/ha-smart-shopping-list/actions/workflows/tests.yml/badge.svg)](https://github.com/dedmen7/ha-smart-shopping-list/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

A shared shopping list for a household. Everyone adds to the same list, and the list shows who added an item, who bought it and when. Items are sorted by aisle, the things you buy every week come back with one tap, and an optional formula check puts baby formula on the list before the can runs out.

> **Status:** early. Built for a two-parent household doing the shopping together. The interface is English with a Dutch translation; the aisle guessing knows common English and Dutch product names. More languages and aisles are welcome as contributions.

## Features

- **Who and when** – every item remembers who added it and who ticked it off at what time ("Bought by Janou · today 18:32"). The user comes from the Home Assistant login, also when ticking from the standard to-do card or the phone app.
- **Aisles** – items are grouped in shop order: fruit & vegetables, bread, meat & fish, dairy & eggs, frozen, pantry, drinks, baby, personal care, household, other. The aisle is guessed from the name; move an item to another aisle once and the list remembers it for that product.
- **Quantities** – type `2x milk`, `2 milk` or `3 × bananas`. Adding something that is already open raises the quantity instead of adding a second line.
- **Archive** – bought items move to the archive a day after they were bought. The archive keeps a year, grouped per day with who bought what and when, and puts an item back on the list with one tap.
- **Regulars** – the products you buy most often, with when they were last bought, as chips above the list. One tap puts them back.
- **Formula supply (optional)** – reads the bottles from the [Baby Feeding](https://github.com/dedmen7/ha-baby-feeding) diary (or any calendar with events named like `70 ml`), estimates how many days the open can lasts and adds formula to the list when it gets low, once per can.
- **Dashboard card** – shipped with the integration and loaded on every dashboard; there is no resource to add.
- **To-do entity** – `todo.smart_shopping_list` works with the standard to-do card, voice assistants and the `todo.*` actions.

## Requirements

Home Assistant 2026.7.0 or later.

## Installation

### HACS (recommended)

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/dedmen7/ha-smart-shopping-list` with type **Integration**.
3. Install **Smart Shopping List** and restart Home Assistant.

### Manual

Copy `custom_components/smart_shopping_list` into the `custom_components` folder of your Home Assistant configuration and restart.

## Configuration

Go to **Settings → Devices & services → Add integration → Smart Shopping List**. There is nothing to fill in.

Under **Configure** you can give each Home Assistant user the name the list should show, for example `Tom` for a user called `Smolenaers`. Empty fields use the user's own name.

## Dashboard card

```yaml
type: custom:smart-shopping-list-card
```

Add items in the field at the top, tap the circle to tick an item off, and tap the item for quantity, aisle and remove. Bought items stay under **Bought** for a day and then move to the archive; **Show archive** lists them per day. When the formula check is on, the card shows the estimate and a **New can opened** button; its settings sit behind the gear in that panel.

## Entities

| Entity | Content |
|---|---|
| `todo.smart_shopping_list` | The list as a to-do list, with `2× milk` style summaries and who/when in the description |
| `sensor.smart_shopping_list_status` | Number of open items, with the items, aisles, regulars and formula supply as attributes, used by the card |

Entity IDs are always English; names and messages follow the Home Assistant language (English, or Dutch).

## Actions

| Action | Purpose |
|---|---|
| `smart_shopping_list.add_item` | Add an item (`text`, for example `2x milk`); merges into an open item with the same name |
| `smart_shopping_list.complete_item` | Tick an item off (`item_id`) as the calling user |
| `smart_shopping_list.reopen_item` | Put a bought item back on the list (`item_id`) |
| `smart_shopping_list.update_item` | Change `name`, `quantity` (1–99) or `category` of an item |
| `smart_shopping_list.remove_item` | Remove an item (`item_id`) |
| `smart_shopping_list.clear_done` | Move all bought items to the archive now instead of after a day |
| `smart_shopping_list.get_archive` | Return the archive of the last year, newest first (`items` with name, quantity, aisle, who added and who bought it, and when) |
| `smart_shopping_list.set_supply` | Formula check: `enabled`, `can_grams`, `grams_per_100ml`, `warn_days`, `product_name`, `diary_entity` |
| `smart_shopping_list.open_new_can` | Start counting a new can from now |
| `smart_shopping_list.refresh_supply` | Recalculate the formula estimate now |

Every action except `get_archive` can return `{"open_items": n}`. Refused changes return a translated message.

## Formula supply

The estimate is simple on purpose:

- **Used** = millilitres given since the can was opened × grams of powder per 100 ml.
- **Per day** = the average of the last seven days that have feeds.
- **Days left** = (can size − used) ÷ per day.

When the days left fall to the warning threshold (three by default), the product is added to the list in the baby aisle, once per can. Tap **New can opened** when you start a new can. Check the can size and the powder per 100 ml on your own formula: the defaults (800 g, 15 g per 100 ml) are only a starting point.

## Translations

The card, the entities and messages follow the Home Assistant system language. English is the default and Dutch is included. Add a language with a file in `translations/`, a table in `texts.py`, an entry in `SHOPPING_TEXT` in the card and, if you like, product keywords in `shopping.py`.

## Privacy

Everything stays in your Home Assistant. The list is stored in `.storage/smart_shopping_list`. Names of who added or bought something are the display names of your Home Assistant users. The large card attributes are excluded from the recorder.

## Development

```bash
python -m pip install pytest-homeassistant-custom-component
python -m pytest
```

```bash
npm install
npm run test:card
```

The list rules live in plain Python (`shopping.py`, `supply.py`) and are tested without Home Assistant; `test_integration.py` covers the integration in a running Home Assistant. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
