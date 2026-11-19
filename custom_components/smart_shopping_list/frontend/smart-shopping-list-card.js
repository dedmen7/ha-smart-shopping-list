/* Dashboard card for Smart Shopping List: the list per aisle, regulars to re-add, who and when, the archive and the formula supply. */
const SHOPPING_TEXT = {
  en: {
    title: 'Shopping', placeholder: 'What do you need? e.g. 2x milk', add: 'Add', regulars: 'Often bought', bought: 'Bought',
    empty: 'Nothing on the list.', by: 'by {name}', boughtBy: 'Bought by {name} · {when}', bought_unknown: 'Bought · {when}', lastBought: '{days} d ago', today: 'today', yesterday: 'yesterday', todayTitle: 'Today', yesterdayTitle: 'Yesterday',
    archiveNote: 'Bought items move to the archive after a day.', showArchive: 'Show archive', hideArchive: 'Hide archive', archive: 'Archive',
    archiveEmpty: 'Nothing in the archive yet.', loading: 'Loading…', again: 'Add {name} again', archiveMeta: '{name} · {time}',
    edit: 'Edit', remove: 'Remove', done: 'Done', quantity: 'Quantity', aisle: 'Aisle', putBack: 'Put back on the list',
    supply: 'Formula', supplyLeft: 'About {days} days left · {grams} g', supplyUnknown: '{grams} g left', supplyLow: 'Running low', newCan: 'New can opened',
    supplySettings: 'Formula settings', track: 'Track formula', canGrams: 'Can size · g', perHundred: 'Powder per 100 ml · g', warnDays: 'Warn days ahead',
    productName: 'Name on the list', save: 'Save', notOpened: 'Tap "New can opened" when you open a can.', error: 'This did not work. Try again.',
    cat_produce: 'Fruit & vegetables', cat_bread: 'Bread', cat_meat_fish: 'Meat & fish', cat_dairy: 'Dairy & eggs', cat_frozen: 'Frozen', cat_pantry: 'Pantry',
    cat_drinks: 'Drinks', cat_baby: 'Baby', cat_care: 'Personal care', cat_household: 'Household', cat_other: 'Other',
  },
  nl: {
    title: 'Boodschappen', placeholder: 'Wat moet er gehaald worden? bv. 2x melk', add: 'Toevoegen', regulars: 'Vaak gehaald', bought: 'Gehaald',
    empty: 'Er staat niets op de lijst.', by: 'door {name}', boughtBy: 'Gehaald door {name} · {when}', bought_unknown: 'Gehaald · {when}', lastBought: '{days} d geleden', today: 'vandaag', yesterday: 'gisteren', todayTitle: 'Vandaag', yesterdayTitle: 'Gisteren',
    archiveNote: 'Gehaalde items gaan na een dag naar het archief.', showArchive: 'Archief bekijken', hideArchive: 'Archief verbergen', archive: 'Archief',
    archiveEmpty: 'Het archief is nog leeg.', loading: 'Laden…', again: '{name} weer op de lijst', archiveMeta: '{name} · {time}',
    edit: 'Aanpassen', remove: 'Verwijderen', done: 'Klaar', quantity: 'Aantal', aisle: 'Afdeling', putBack: 'Terug op de lijst',
    supply: 'Flesvoeding', supplyLeft: 'Nog ongeveer {days} dagen · {grams} g', supplyUnknown: 'Nog {grams} g', supplyLow: 'Bijna op', newCan: 'Nieuw blik geopend',
    supplySettings: 'Flesvoeding instellen', track: 'Flesvoeding bijhouden', canGrams: 'Inhoud blik · g', perHundred: 'Poeder per 100 ml · g', warnDays: 'Dagen vooraf waarschuwen',
    productName: 'Naam op de lijst', save: 'Opslaan', notOpened: 'Tik op "Nieuw blik geopend" als je een blik opent.', error: 'Dit is niet gelukt. Probeer opnieuw.',
    cat_produce: 'Groente & fruit', cat_bread: 'Brood', cat_meat_fish: 'Vlees & vis', cat_dairy: 'Zuivel & eieren', cat_frozen: 'Diepvries', cat_pantry: 'Houdbaar',
    cat_drinks: 'Dranken', cat_baby: 'Baby', cat_care: 'Verzorging', cat_household: 'Huishouden', cat_other: 'Overig',
    error_empty_entry: 'Vul in wat je nodig hebt.', error_entry_too_long: 'Houd een item onder de 100 tekens.', error_invalid_quantity: 'Kies een aantal van 1 tot en met 99.',
    error_item_not_found: 'Dit item is gewijzigd of verwijderd. Vernieuw de lijst.', error_invalid_supply: 'Controleer de flesvoeding-instellingen.',
  },
};
const AISLE_ICONS = {
  produce: 'mdi:food-apple-outline', bread: 'mdi:baguette', meat_fish: 'mdi:food-drumstick-outline', dairy: 'mdi:cheese', frozen: 'mdi:snowflake',
  pantry: 'mdi:pasta', drinks: 'mdi:bottle-soda-classic-outline', baby: 'mdi:baby-bottle-outline', care: 'mdi:lotion-outline', household: 'mdi:spray-bottle', other: 'mdi:dots-horizontal-circle-outline',
};
const STATUS_ENTITY = 'sensor.smart_shopping_list_status';

class SmartShoppingListCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: 'open'});
    this._editing = null;
    this._showSettings = false;
    this._signature = '';
    this._archive = null;
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;--accent:var(--sh-accent,var(--primary-color,#d88959));--ink:var(--primary-text-color,#e8e2dc);--muted:var(--secondary-text-color,#a8a19a);--line:var(--ha-card-border-color,var(--divider-color,#383638));--surface:var(--ha-card-background,var(--card-background-color,#1c1c1e));--soft:color-mix(in srgb,var(--ink) 5%,var(--surface));--ok:var(--sh-ok,var(--success-color,#9bb783));--warn:var(--sh-alert,var(--error-color,#c96a54))}
        *{box-sizing:border-box}
        ha-card{padding:16px;color:var(--ink);font:14px var(--ha-font-family-body,system-ui,sans-serif)}
        [hidden]{display:none!important}
        header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:12px}
        h2{margin:0;font-size:20px;font-weight:600}
        .count{color:var(--muted);font-size:13px}
        form{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;margin-bottom:12px}
        input,select{width:100%;min-width:0;height:44px;border:1px solid var(--line);border-radius:8px;padding:0 12px;background:var(--surface);color:var(--ink);font:inherit;font-size:16px}
        button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:44px;border:1px solid var(--line);border-radius:8px;padding:0 14px;background:var(--soft);color:var(--ink);font:inherit;font-weight:600;cursor:pointer;-webkit-tap-highlight-color:transparent}
        button.primary{background:var(--accent);border-color:var(--accent);color:var(--text-primary-color,#21120a)}
        button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
        .label{margin:16px 0 8px;font-size:12px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;color:var(--muted)}
        .chips{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}
        .chip{flex:none;min-height:40px;border-radius:20px;padding:0 14px;font-weight:500}
        .chip small{color:var(--muted);font-weight:400}
        .aisle{margin-top:14px}
        .aisle-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;color:var(--muted);font-size:13px;font-weight:600}
        .aisle-head ha-icon{--mdc-icon-size:18px;color:var(--accent)}
        ul{list-style:none;margin:0;padding:0;border:1px solid var(--line);border-radius:10px;overflow:hidden}
        li{display:grid;grid-template-columns:44px minmax(0,1fr) auto;align-items:center;gap:6px;min-height:56px;padding:4px 8px 4px 4px;border-top:1px solid var(--line);background:var(--surface)}
        li:first-child{border-top:0}
        .tick{width:44px;height:44px;border:0;background:transparent;padding:0}
        .tick span{display:block;width:24px;height:24px;margin:auto;border:2px solid var(--muted);border-radius:50%}
        li.done .tick span{border-color:var(--ok);background:var(--ok)}
        .name{font-size:16px;line-height:1.3;overflow-wrap:anywhere}
        .meta{font-size:12px;color:var(--muted);margin-top:2px}
        li.done .name{text-decoration:line-through;color:var(--muted)}
        .qty{display:inline-block;min-width:28px;margin-right:6px;padding:1px 7px;border-radius:10px;background:color-mix(in srgb,var(--accent) 18%,var(--surface));color:var(--accent);font-size:13px;font-weight:700;text-align:center}
        .more{min-height:40px;padding:0 10px;border:0;background:transparent;color:var(--muted)}
        .editor{display:grid;grid-template-columns:auto minmax(0,1fr);gap:8px 12px;align-items:center;padding:12px;border-top:1px solid var(--line);background:var(--soft)}
        .editor label{font-size:13px;color:var(--muted)}
        .stepper{display:grid;grid-template-columns:44px 60px 44px;gap:6px}
        .stepper output{display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:600}
        .editor .actions{grid-column:1/-1;display:flex;gap:8px;justify-content:flex-end}
        .empty{padding:18px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);text-align:center}
        details{margin-top:14px}
        summary{cursor:pointer;color:var(--muted);font-weight:600;padding:8px 0}
        .note{margin:8px 0 0;color:var(--muted);font-size:12px}
        .archive-toggle{margin-top:8px;width:100%}
        .day{margin:14px 0 6px;color:var(--muted);font-size:13px;font-weight:600}
        span.tick{display:flex;align-items:center}
        .again{min-width:44px;padding:0;font-size:20px;color:var(--accent)}
        .supply{margin-top:18px;padding:14px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}
        .supply.low{border-color:var(--warn);background:color-mix(in srgb,var(--warn) 10%,var(--surface))}
        .supply-head{display:flex;justify-content:space-between;gap:10px;align-items:center;font-weight:600}
        .bar{height:6px;margin:10px 0;border-radius:3px;background:var(--line);overflow:hidden}
        .bar span{display:block;height:100%;background:var(--accent)}
        .supply.low .bar span{background:var(--warn)}
        .supply-actions{display:flex;gap:8px;flex-wrap:wrap}
        .settings{display:grid;grid-template-columns:minmax(0,1fr) 140px;gap:8px 12px;align-items:center;margin-top:12px}
        .settings label{font-size:13px;color:var(--muted)}
        .error{margin-top:8px;color:var(--warn);font-size:13px}
      </style>
      <ha-card>
        <header><h2 data-text="title"></h2><span class="count" id="count"></span></header>
        <form id="add-form"><input id="entry" list="known" autocomplete="off" enterkeyhint="done"><button class="primary" type="submit" data-text="add"></button><datalist id="known"></datalist></form>
        <div class="error" id="error" role="alert" hidden></div>
        <section id="regulars-section"><div class="label" data-text="regulars"></div><div class="chips" id="regulars"></div></section>
        <div id="aisles"></div>
        <details id="bought-section"><summary id="bought-title"></summary><ul id="bought"></ul></details>
        <p class="note" data-text="archiveNote"></p><button class="archive-toggle" id="archive-toggle" type="button" data-action="archive"></button><section id="archive" hidden></section>
        <section class="supply" id="supply" hidden></section>
      </ha-card>`;
    this.$ = id => this.shadowRoot.getElementById(id);
    this.$('add-form').addEventListener('submit', event => { event.preventDefault(); this._add(this.$('entry').value); });
    this.shadowRoot.addEventListener('click', event => this._onClick(event));
  }

  setConfig(config) { this._config = config || {}; }
  getCardSize() { return 6; }
  getGridOptions() { return {columns: 12, rows: 'auto'}; }

  set hass(hass) {
    this._hass = hass;
    const status = hass.states[STATUS_ENTITY];
    const listSignature = JSON.stringify([status?.state, status?.attributes]);
    const signature = JSON.stringify([this._lang(), listSignature, this._editing, this._showSettings, this._archive]);
    if (signature === this._signature) return;
    if (Array.isArray(this._archive) && listSignature !== this._listSignature && this._listSignature !== undefined) this._loadArchive();
    this._listSignature = listSignature;
    this._signature = signature;
    this._render();
  }

  _lang() { return String(this._hass?.config?.language || this._hass?.language || 'en').toLowerCase().startsWith('nl') ? 'nl' : 'en'; }
  _locale() { return this._lang() === 'nl' ? 'nl-NL' : (this._hass?.locale?.language || 'en-GB'); }
  _t(key, values = {}) {
    const text = SHOPPING_TEXT[this._lang()][key] ?? SHOPPING_TEXT.en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ''));
  }
  _attributes() { return this._hass?.states[STATUS_ENTITY]?.attributes || {items: [], regulars: [], categories: [], supply: {}}; }

  _when(value) {
    const moment = new Date(value), now = new Date();
    const timeZone = this._hass?.config?.time_zone || undefined;
    const format = this._hass?.locale?.time_format;
    const hourCycle = format === '12' ? 'h12' : format === '24' ? 'h23' : undefined;
    const time = moment.toLocaleTimeString(this._locale(), {hour: '2-digit', minute: '2-digit', hourCycle, timeZone});
    const relative = this._relativeDay(moment, now);
    if (relative) return this._t(relative) + ' ' + time;
    return moment.toLocaleDateString(this._locale(), {day: 'numeric', month: 'short', timeZone}) + ' ' + time;
  }

  _time(value) {
    const format = this._hass?.locale?.time_format;
    const hourCycle = format === '12' ? 'h12' : format === '24' ? 'h23' : undefined;
    return new Date(value).toLocaleTimeString(this._locale(), {hour: '2-digit', minute: '2-digit', hourCycle, timeZone: this._hass?.config?.time_zone || undefined});
  }

  _dayKey(date) { return date.toLocaleDateString('en-CA', {timeZone: this._hass?.config?.time_zone || undefined}); }

  /** 'today' or 'yesterday' in the Home Assistant time zone, otherwise null. */
  _relativeDay(moment, now) {
    const day = this._dayKey(moment);
    if (day === this._dayKey(now)) return 'today';
    if (day === this._dayKey(new Date(now.getTime() - 86400000))) return 'yesterday';
    return null;
  }

  _dayTitle(value) {
    const moment = new Date(value);
    const relative = this._relativeDay(moment, new Date());
    if (relative) return this._t(relative + 'Title');
    const title = moment.toLocaleDateString(this._locale(), {weekday: 'long', day: 'numeric', month: 'long', timeZone: this._hass?.config?.time_zone || undefined});
    return title.charAt(0).toUpperCase() + title.slice(1);
  }

  _render() {
    const attributes = this._attributes();
    for (const element of this.shadowRoot.querySelectorAll('[data-text]')) element.textContent = this._t(element.dataset.text);
    this.$('entry').placeholder = this._t('placeholder');
    const open = (attributes.items || []).filter(item => !item.done), bought = (attributes.items || []).filter(item => item.done);
    this.$('count').textContent = open.length ? String(open.length) : '';
    this.$('known').replaceChildren(...(attributes.regulars || []).map(regular => Object.assign(document.createElement('option'), {value: regular.name})));
    this._renderRegulars(attributes.regulars || []);
    this._renderAisles(open, attributes.categories || []);
    this.$('bought-section').hidden = !bought.length;
    this.$('bought-title').textContent = this._t('bought') + ' (' + bought.length + ')';
    this.$('bought').replaceChildren(...bought.slice().sort((a, b) => Date.parse(b.done_at) - Date.parse(a.done_at)).map(item => this._row(item)));
    this.$('archive-toggle').textContent = this._t(this._archive === null ? 'showArchive' : 'hideArchive');
    this._renderArchive();
    this._renderSupply(attributes.supply || {});
  }

  _renderArchive() {
    const panel = this.$('archive');
    panel.hidden = this._archive === null;
    if (panel.hidden) return;
    if (this._archive === 'loading') { panel.replaceChildren(Object.assign(document.createElement('div'), {className: 'empty', textContent: this._t('loading')})); return; }
    if (!this._archive.length) { panel.replaceChildren(Object.assign(document.createElement('div'), {className: 'empty', textContent: this._t('archiveEmpty')})); return; }
    const days = [];
    for (const item of this._archive) {
      const key = this._dayKey(new Date(item.done_at));
      if (!days.length || days.at(-1).key !== key) days.push({key, at: item.done_at, items: []});
      days.at(-1).items.push(item);
    }
    panel.replaceChildren(...days.flatMap(day => {
      const list = document.createElement('ul');
      list.append(...day.items.map(item => this._archiveRow(item)));
      return [Object.assign(document.createElement('div'), {className: 'day', textContent: this._dayTitle(day.at)}), list];
    }));
  }

  _archiveRow(item) {
    const row = Object.assign(document.createElement('li'), {className: 'done archived'});
    const tick = Object.assign(document.createElement('span'), {className: 'tick'});
    tick.append(document.createElement('span'));
    const body = document.createElement('div');
    const name = Object.assign(document.createElement('div'), {className: 'name'});
    if (item.quantity > 1) name.append(Object.assign(document.createElement('span'), {className: 'qty', textContent: '×' + item.quantity}));
    name.append(item.name);
    const time = this._time(item.done_at);
    const meta = Object.assign(document.createElement('div'), {className: 'meta', textContent: item.done_by ? this._t('archiveMeta', {name: item.done_by, time}) : time});
    body.append(name, meta);
    const again = Object.assign(document.createElement('button'), {className: 'again', type: 'button', textContent: '+'});
    again.dataset.action = 'again';
    again.dataset.text = (item.quantity > 1 ? item.quantity + 'x ' : '') + item.name;
    again.setAttribute('aria-label', this._t('again', {name: item.name}));
    row.append(tick, body, again);
    return row;
  }

  async _loadArchive() {
    if (this._archive === null) this._archive = 'loading';
    this._refresh();
    try {
      const result = await this._hass.callWS({type: 'call_service', domain: 'smart_shopping_list', service: 'get_archive', service_data: {}, return_response: true});
      if (this._archive !== null) this._archive = result?.response?.items || [];
    } catch (error) {
      this._archive = null;
      this.$('error').textContent = this._t('error');
      this.$('error').hidden = false;
    }
    this._refresh();
  }

  _renderRegulars(regulars) {
    this.$('regulars-section').hidden = !regulars.length;
    this.$('regulars').replaceChildren(...regulars.map(regular => {
      const chip = Object.assign(document.createElement('button'), {className: 'chip', type: 'button'});
      chip.dataset.action = 'regular';
      chip.dataset.name = regular.name;
      chip.append(regular.name);
      if (regular.last_bought) {
        const days = Math.floor((Date.now() - Date.parse(regular.last_bought)) / 86400000);
        chip.append(' ', Object.assign(document.createElement('small'), {textContent: days < 1 ? this._t('today') : this._t('lastBought', {days})}));
      }
      return chip;
    }));
  }

  _renderAisles(open, categories) {
    const container = this.$('aisles');
    if (!open.length) { container.replaceChildren(Object.assign(document.createElement('div'), {className: 'empty', textContent: this._t('empty')})); return; }
    const order = categories.length ? categories : Object.keys(AISLE_ICONS);
    container.replaceChildren(...order.filter(category => open.some(item => item.category === category)).map(category => {
      const section = Object.assign(document.createElement('section'), {className: 'aisle'});
      section.dataset.category = category;
      const head = Object.assign(document.createElement('div'), {className: 'aisle-head'});
      head.append(Object.assign(document.createElement('ha-icon'), {icon: AISLE_ICONS[category] || AISLE_ICONS.other}), this._t('cat_' + category));
      const list = document.createElement('ul');
      list.append(...open.filter(item => item.category === category).map(item => this._row(item)));
      section.append(head, list);
      return section;
    }));
  }

  _row(item) {
    const row = document.createElement('li');
    row.className = item.done ? 'done' : '';
    row.dataset.id = item.id;
    const tick = Object.assign(document.createElement('button'), {className: 'tick', type: 'button'});
    tick.dataset.action = item.done ? 'reopen' : 'complete';
    tick.setAttribute('aria-label', item.done ? this._t('putBack') : item.name);
    tick.append(document.createElement('span'));
    const body = document.createElement('div');
    const name = Object.assign(document.createElement('div'), {className: 'name'});
    if (item.quantity > 1) name.append(Object.assign(document.createElement('span'), {className: 'qty', textContent: '×' + item.quantity}));
    name.append(item.name);
    const meta = Object.assign(document.createElement('div'), {className: 'meta'});
    meta.textContent = item.done ? (item.done_by ? this._t('boughtBy', {name: item.done_by, when: this._when(item.done_at)}) : this._t('bought_unknown', {when: this._when(item.done_at)}))
      : (item.added_by ? this._t('by', {name: item.added_by}) : '');
    body.append(name, meta);
    const more = Object.assign(document.createElement('button'), {className: 'more', type: 'button', textContent: '⋯'});
    more.dataset.action = 'edit';
    more.setAttribute('aria-label', this._t('edit'));
    row.append(tick, body, item.done ? document.createElement('span') : more);
    if (this._editing === item.id && !item.done) {
      const wrapper = document.createDocumentFragment();
      wrapper.append(row, this._editor(item));
      return wrapper;
    }
    return row;
  }

  _editor(item) {
    const editor = Object.assign(document.createElement('li'), {className: 'editor'});
    editor.dataset.id = item.id;
    const categories = this._attributes().categories || Object.keys(AISLE_ICONS);
    editor.innerHTML = `<label></label><div class="stepper"><button type="button" data-action="minus">−</button><output></output><button type="button" data-action="plus">+</button></div><label></label><select></select><div class="actions"><button type="button" data-action="remove"></button><button type="button" class="primary" data-action="close"></button></div>`;
    const [quantityLabel, aisleLabel] = editor.querySelectorAll('label');
    quantityLabel.textContent = this._t('quantity');
    aisleLabel.textContent = this._t('aisle');
    editor.querySelector('output').textContent = String(item.quantity);
    const select = editor.querySelector('select');
    select.setAttribute('aria-label', this._t('aisle'));
    select.append(...categories.map(category => Object.assign(document.createElement('option'), {value: category, textContent: this._t('cat_' + category), selected: category === item.category})));
    select.addEventListener('change', () => this._call('update_item', {item_id: item.id, category: select.value}));
    editor.querySelector('[data-action=remove]').textContent = this._t('remove');
    editor.querySelector('[data-action=close]').textContent = this._t('done');
    return editor;
  }

  _renderSupply(supply) {
    const panel = this.$('supply');
    panel.hidden = !supply.enabled && !this._showSettings && !this._config?.show_supply_settings;
    if (panel.hidden) return;
    panel.classList.toggle('low', Boolean(supply.low));
    const head = Object.assign(document.createElement('div'), {className: 'supply-head'});
    head.append(this._t('supply'), supply.low ? Object.assign(document.createElement('span'), {textContent: this._t('supplyLow')}) : '');
    const detail = document.createElement('div');
    detail.className = 'meta';
    let bar = null;
    if (supply.enabled && supply.opened_at) {
      detail.textContent = supply.days_left == null ? this._t('supplyUnknown', {grams: supply.left_grams}) : this._t('supplyLeft', {days: Math.max(0, Math.floor(supply.days_left)), grams: supply.left_grams});
      bar = Object.assign(document.createElement('div'), {className: 'bar'});
      const fill = document.createElement('span');
      fill.style.width = Math.max(0, Math.min(100, supply.left_grams / supply.can_grams * 100)) + '%';
      bar.append(fill);
    } else if (supply.enabled) {
      detail.textContent = this._t('notOpened');
    }
    const actions = Object.assign(document.createElement('div'), {className: 'supply-actions'});
    if (supply.enabled) actions.append(Object.assign(document.createElement('button'), {type: 'button', textContent: this._t('newCan'), className: 'primary'}));
    if (supply.enabled) actions.lastChild.dataset.action = 'new-can';
    const toggle = Object.assign(document.createElement('button'), {type: 'button', textContent: this._t('supplySettings')});
    toggle.dataset.action = 'supply-settings';
    actions.append(toggle);
    panel.replaceChildren(...[head, detail, bar, actions, this._showSettings ? this._supplySettings(supply) : null].filter(Boolean));
  }

  _supplySettings(supply) {
    const form = Object.assign(document.createElement('form'), {className: 'settings'});
    const fields = [['enabled', 'track', 'checkbox'], ['can_grams', 'canGrams', 'number'], ['grams_per_100ml', 'perHundred', 'number'], ['warn_days', 'warnDays', 'number'], ['product_name', 'productName', 'text']];
    for (const [name, label, type] of fields) {
      const id = 'supply-' + name;
      form.append(Object.assign(document.createElement('label'), {htmlFor: id, textContent: this._t(label)}));
      const input = Object.assign(document.createElement('input'), {id, name, type});
      if (type === 'checkbox') input.checked = Boolean(supply.enabled); else input.value = supply[name] ?? '';
      if (name === 'grams_per_100ml') input.step = '0.1';
      form.append(input);
    }
    const save = Object.assign(document.createElement('button'), {type: 'submit', className: 'primary', textContent: this._t('save')});
    save.style.gridColumn = '1/-1';
    form.append(save);
    form.addEventListener('submit', event => {
      event.preventDefault();
      const value = name => form.elements[name];
      this._call('set_supply', {
        enabled: value('enabled').checked, can_grams: Number(value('can_grams').value), grams_per_100ml: Number(value('grams_per_100ml').value),
        warn_days: Number(value('warn_days').value), product_name: value('product_name').value.trim(), diary_entity: supply.diary_entity || 'calendar.baby_feeding_diary',
      }).then(ok => { if (ok) { this._showSettings = false; this._signature = ''; this.hass = this._hass; } });
    });
    return form;
  }

  _onClick(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const id = button.closest('[data-id]')?.dataset.id;
    const item = (this._attributes().items || []).find(entry => entry.id === id);
    const actions = {
      regular: () => this._call('add_item', {text: button.dataset.name}),
      complete: () => this._call('complete_item', {item_id: id}),
      reopen: () => this._call('reopen_item', {item_id: id}),
      edit: () => { this._editing = this._editing === id ? null : id; this._refresh(); },
      close: () => { this._editing = null; this._refresh(); },
      remove: () => { this._editing = null; return this._call('remove_item', {item_id: id}); },
      minus: () => item && item.quantity > 1 && this._call('update_item', {item_id: id, quantity: item.quantity - 1}),
      plus: () => item && item.quantity < 99 && this._call('update_item', {item_id: id, quantity: item.quantity + 1}),
      'new-can': () => this._call('open_new_can', {}),
      'supply-settings': () => { this._showSettings = !this._showSettings; this._refresh(); },
      again: () => this._call('add_item', {text: button.dataset.text}),
      archive: () => { if (this._archive === null) return this._loadArchive(); this._archive = null; this._refresh(); },
    };
    actions[button.dataset.action]?.();
  }

  _refresh() { this._signature = ''; if (this._hass) this.hass = this._hass; }

  async _add(text) {
    if (!text.trim()) return;
    if (await this._call('add_item', {text})) this.$('entry').value = '';
  }

  async _call(service, data) {
    this.$('error').hidden = true;
    try {
      await this._hass.callWS({type: 'call_service', domain: 'smart_shopping_list', service, service_data: data, return_response: true});
      return true;
    } catch (error) {
      const key = error?.translation_key ? 'error_' + error.translation_key : null;
      this.$('error').textContent = key && SHOPPING_TEXT[this._lang()][key] ? this._t(key) : (error?.message || this._t('error'));
      this.$('error').hidden = false;
      return false;
    }
  }
}

if (!customElements.get('smart-shopping-list-card')) customElements.define('smart-shopping-list-card', SmartShoppingListCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === 'smart-shopping-list-card')) {
  window.customCards.push({type: 'smart-shopping-list-card', name: 'Smart Shopping List', description: 'Shared shopping list per aisle with regulars, who and when, and a formula supply check.'});
}
