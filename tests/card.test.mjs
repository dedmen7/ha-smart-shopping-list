// The shopping card: aisles in shop order, who and when, regulars, editing, the archive, the formula supply and the Dutch translation.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Window} from 'happy-dom';

const window = new Window({url: 'http://homeassistant.local:8123/lovelace/0'});
const RealDate = window.Date;
const now = '2026-11-19T18:40:00+01:00';
window.Date = class extends RealDate {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return new RealDate(now).getTime(); }
};
window.eval(fs.readFileSync(new URL('../custom_components/smart_shopping_list/frontend/smart-shopping-list-card.js', import.meta.url), 'utf8'));
const Card = window.customElements.get('smart-shopping-list-card');

const categories = ['produce', 'bread', 'meat_fish', 'dairy', 'frozen', 'pantry', 'drinks', 'baby', 'care', 'household', 'other'];
let attributes = {
  categories,
  items: [
    {id: 'a', name: 'melk', quantity: 2, category: 'dairy', added_by: 'Janou', added_at: '2026-11-19T08:00:00+01:00', done: false, done_by: null, done_at: null},
    {id: 'b', name: 'bananen', quantity: 1, category: 'produce', added_by: 'Tom', added_at: '2026-11-19T08:05:00+01:00', done: false, done_by: null, done_at: null},
    {id: 'c', name: 'brood', quantity: 1, category: 'bread', added_by: 'Tom', added_at: '2026-11-19T07:00:00+01:00', done: true, done_by: 'Janou', done_at: '2026-11-19T18:32:00+01:00'},
  ],
  regulars: [{name: 'luiers', category: 'baby', purchases: 4, last_bought: '2026-11-15T10:00:00+01:00'}],
  supply: {enabled: true, can_grams: 800, grams_per_100ml: 15, warn_days: 3, product_name: 'Flesvoeding', diary_entity: 'calendar.baby_feeding_diary', opened_at: '2026-11-13T09:00:00+01:00', left_grams: 260, days_left: 2.9, low: true},
};
let language = 'en';
const archive = [
  {id: 'x1', name: 'melk', quantity: 2, category: 'dairy', added_by: 'Tom', added_at: '2026-11-18T08:00:00+01:00', done_by: 'Tom', done_at: '2026-11-18T18:05:00+01:00'},
  {id: 'x2', name: 'brood', quantity: 1, category: 'bread', added_by: 'Janou', added_at: '2026-11-17T08:00:00+01:00', done_by: 'Janou', done_at: '2026-11-17T10:00:00+01:00'},
];
const calls = [];
let reject = null;
const hass = () => ({
  config: {language, time_zone: 'Europe/Amsterdam'}, locale: {language: 'en', time_format: '24'}, language: 'en',
  states: {'sensor.smart_shopping_list_status': {state: '2', attributes: structuredClone(attributes)}},
  callWS: async request => {
    calls.push([request.service, request.service_data]);
    if (reject) { const error = reject; reject = null; throw error; }
    return {response: request.service === 'get_archive' ? {items: structuredClone(archive)} : {}};
  },
});
const settle = () => new Promise(resolve => setTimeout(resolve, 0));
// Objects created inside the card come from its own window, so compare them as JSON.
const sameJson = (actual, expected) => assert.equal(JSON.stringify(actual), JSON.stringify(expected));
const lastCall = expected => sameJson(calls.at(-1), expected);
const card = new Card();
card.setConfig({});
window.document.body.append(card);
card.hass = hass();
const $ = selector => card.shadowRoot.querySelector(selector);
const $$ = selector => [...card.shadowRoot.querySelectorAll(selector)];

// Open items are grouped per aisle in shop order, with the quantity and who added them.
sameJson($$('.aisle').map(aisle => aisle.dataset.category), ['produce', 'dairy']);
sameJson($$('.aisle-head').map(head => head.textContent), ['Fruit & vegetables', 'Dairy & eggs']);
const milk = $('[data-category=dairy] li');
assert.equal(milk.querySelector('.name').textContent, '×2melk');
assert.equal(milk.querySelector('.meta').textContent, 'by Janou');
// Bought items show who bought them and when.
assert.equal($('#bought-title').textContent, 'Bought (1)');
assert.equal($('#bought li .meta').textContent, 'Bought by Janou · today 18:32');
assert.equal($('.note').textContent, 'Bought items move to the archive after a day.');
// Ticking, putting back and the regulars go through the integration.
milk.querySelector('.tick').click();
lastCall(['complete_item', {item_id: 'a'}]);
$('#bought li .tick').click();
lastCall(['reopen_item', {item_id: 'c'}]);
assert.match($('.chip').textContent, /^luiers 4 d ago$/);
$('.chip').click();
lastCall(['add_item', {text: 'luiers'}]);
// Adding from the field clears it after the integration accepted it; a refusal is shown and keeps the text.
$('#entry').value = '2x kaas';
$('#add-form').dispatchEvent(new window.Event('submit', {cancelable: true}));
await settle();
lastCall(['add_item', {text: '2x kaas'}]);
assert.equal($('#entry').value, '');
reject = Object.assign(new Error('Enter what you need.'), {translation_key: 'empty_entry'});
$('#entry').value = '2x';
$('#add-form').dispatchEvent(new window.Event('submit', {cancelable: true}));
await settle();
assert.equal($('#error').hidden, false);
assert.equal($('#error').textContent, 'Enter what you need.');
assert.equal($('#entry').value, '2x');
// The editor changes the quantity and the aisle, and removes an item.
$('[data-category=dairy] .more').click();
$('.editor [data-action=plus]').click();
lastCall(['update_item', {item_id: 'a', quantity: 3}]);
const aisle = $('.editor select');
aisle.value = 'baby';
aisle.dispatchEvent(new window.Event('change'));
lastCall(['update_item', {item_id: 'a', category: 'baby'}]);
$('.editor [data-action=remove]').click();
lastCall(['remove_item', {item_id: 'a'}]);
// The archive opens on request, grouped per day, and puts an item back on the list.
assert.equal($('#archive').hidden, true);
$('#archive-toggle').click();
await settle();
lastCall(['get_archive', {}]);
sameJson($$('#archive .day').map(day => day.textContent), ['Yesterday', 'Tuesday, November 17']);
assert.equal($('#archive li .meta').textContent, 'Tom · 18:05');
assert.equal($('#archive li .name').textContent, '×2melk');
$('#archive .again').click();
lastCall(['add_item', {text: '2x melk'}]);
assert.equal($('#archive-toggle').textContent, 'Hide archive');
// The formula supply warns when low and a new can starts a fresh count.
assert.equal($('#supply').classList.contains('low'), true);
assert.match($('#supply').textContent, /About 2 days left · 260 g/);
$('#supply [data-action=new-can]').click();
lastCall(['open_new_can', {}]);
$('#supply [data-action=supply-settings]').click();
$('#supply-can_grams').value = '900';
$('#supply form').dispatchEvent(new window.Event('submit', {cancelable: true}));
lastCall(['set_supply', {enabled: true, can_grams: 900, grams_per_100ml: 15, warn_days: 3, product_name: 'Flesvoeding', diary_entity: 'calendar.baby_feeding_diary'}]);
// A Home Assistant set to Dutch gets the Dutch card.
language = 'nl';
card.hass = hass();
assert.equal($('h2').textContent, 'Boodschappen');
sameJson($$('.aisle-head').map(head => head.textContent), ['Groente & fruit', 'Zuivel & eieren']);
assert.equal($('#bought li .meta').textContent, 'Gehaald door Janou · vandaag 18:32');
sameJson($$('#archive .day').map(day => day.textContent), ['Gisteren', 'Dinsdag 17 november']);
$('#archive-toggle').click();
assert.equal($('#archive').hidden, true);
assert.equal($('#archive-toggle').textContent, 'Archief bekijken');
assert.equal($('[data-category=dairy] li .meta').textContent, 'door Janou');
// An empty list says so and hides the regulars.
attributes = {...attributes, items: [], regulars: []};
card.hass = hass();
assert.equal($('.empty').textContent, 'Er staat niets op de lijst.');
assert.equal($('#regulars-section').hidden, true);
card.remove();
await window.happyDOM.cancelAsync(); await window.close();
console.log('Card PASS: aisles, who and when, regulars, editing, archive, formula supply, English and Dutch.');
