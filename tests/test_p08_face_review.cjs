// The owner page must refuse incomplete or uncovered>visible rows and export both counts.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('face review page exports only complete valid counts', () => {
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
  let exported, download;
  const context = {document, Blob, setTimeout() {}, URL: {
    createObjectURL(blob) {exported = blob; return 'blob:review';}, revokeObjectURL() {},
  }};
  const create = document.createElement;
  document.createElement = tag => {const el = create(); if (tag === 'a') download = el; return el;};
  const html = fs.readFileSync(path.join(__dirname, '../scripts/p08_face_review.html'), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace('/*CASES*/null', JSON.stringify([{image_id: 'a', image: ''}, {image_id: 'b', image: ''}]));
  vm.runInNewContext(script, context);
  const save = document.querySelector('#save');
  const cards = document.querySelector('#cases').children;
  // card children: [image button, id, visible row, uncovered row]; row children: [label, 0..4]
  const pick = (card, row, value) => cards[card].children[2 + row].children[1 + value].onclick();
  pick(0, 0, 1); pick(0, 1, 0);
  save.onclick();
  assert.equal(exported, undefined);           // b 미표시
  pick(1, 0, 1); pick(1, 1, 2);
  save.onclick();
  assert.equal(exported, undefined);           // 남은 얼굴 2 > 보이는 얼굴 1
  pick(1, 1, 1);
  save.onclick();
  assert.equal(download.download, 'face_review_owner.csv');
  return exported.text().then(csv => assert.equal(csv, 'image_id,visible_faces,uncovered_visible_faces\na,1,0\nb,1,1\n'));
});
