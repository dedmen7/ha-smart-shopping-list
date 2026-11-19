# Changelog

## 0.2.0

- Bought items move to an archive a day after they were bought, automatically. The archive keeps a year.
- The card shows the day with the time ("today 18:32", "yesterday 09:10", "17 Nov 10:00") and has an archive view per day, with a button to put an item back on the list.
- New action `smart_shopping_list.get_archive`. `smart_shopping_list.clear_done` now archives bought items instead of deleting them; the card no longer has a clear button.

## 0.1.0

- First version: a shared shopping list that records who added and who bought each item and when, aisles in shop order with remembered categories, quantities and merged duplicates, regulars with when they were last bought, an optional formula supply check based on a feeding diary, a to-do entity, a status sensor and the bundled dashboard card. English with a Dutch translation.
