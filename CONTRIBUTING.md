# Contributing

Issues and pull requests are welcome.

## Before you open a pull request

1. Describe the behaviour you want to change in an issue first when it changes how items merge, which aisle they get or when formula is added; households rely on these.
2. Add or change a test that fails without your change. The rules in `shopping.py` and `supply.py` have plain Python tests; the integration has tests in `tests/test_integration.py` and the card in `tests/card.test.mjs`.
3. Run the checks:

```bash
python -m pip install pytest-homeassistant-custom-component
python -m pytest
```

```bash
npm install
npm run test:card
```

## Translations and aisles

Service and setup texts are in `custom_components/smart_shopping_list/translations/`, the card texts in `frontend/smart-shopping-list-card.js` and the product keywords per aisle in `shopping.py`. A new language or better keywords are a good first contribution.
