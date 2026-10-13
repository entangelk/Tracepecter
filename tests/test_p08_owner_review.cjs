// Export must reject incomplete reviews and preserve both visible and invisible labels.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

for (const filename of ['recall_labels_owner.csv', 'recall_labels_owner_sd35.csv']) {
test(`owner page exports ${filename} only after every image is labelled`, () => {
  const elements = new Map();
  function element() {
    return {style: {}, children: [], append(...items) {this.children.push(...items);},
      setAttribute() {}, querySelectorAll() {return this.children.filter(x => x.onclick);},
      click() {this.clicked = true;}};
  }
  const document = {
    querySelector(id) {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    createElement() {return element();},
  };
  let exported;
  let download;
  const context = {document, Blob, setTimeout() {}, URL: {
    createObjectURL(blob) {exported = blob; return 'blob:review';}, revokeObjectURL() {},
  }};
  const create = document.createElement;
  document.createElement = tag => {const el = create(); if (tag === 'a') download = el; return el;};
  const html = fs.readFileSync(path.join(__dirname, '../scripts/p08_owner_review.html'), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace('/*CASES*/null', JSON.stringify([{image_id: 'a', image: ''}, {image_id: 'b', image: ''}]))
    .replace('/*DOWNLOAD_NAME*/"recall_labels_owner.csv"', JSON.stringify(filename));
  vm.runInNewContext(script, context);
  const save = document.querySelector('#save');
  save.onclick();
  assert.equal(exported, undefined);
  const cards = document.querySelector('#cases').children;
  cards[0].children[1].children[1].onclick();
  save.onclick();
  assert.equal(exported, undefined);
  cards[1].children[1].children[2].onclick();
  save.onclick();
  assert.equal(download.download, filename);
  assert.equal(download.clicked, true);
  return exported.text().then(csv => assert.equal(csv, 'image_id,owner_face_visible\na,1\nb,0\n'));
});
}
