// P07-03 demo page: renders only the API response and maps rejections without inventing scores.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function load(fetchImpl) {
  const elements = new Map();
  const element = () => ({style: {}, hidden: true, textContent: '', src: '', listeners: {},
    addEventListener(name, fn) {this.listeners[name] = fn;}});
  const document = {getElementById(id) {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);}};
  class FormData {constructor() {this.fields = [];} append(...field) {this.fields.push(field);}}
  const context = {document, FormData, fetch: fetchImpl, String, Math, Error,
    URL: {createObjectURL: () => 'blob:preview', revokeObjectURL() {}}};
  const html = fs.readFileSync(path.join(__dirname, '../demo/index.html'), 'utf8');
  vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return {context, el: id => document.getElementById(id)};
}

test('render shows rounded score, server classification and face count', () => {
  const {context} = load();
  const view = context.render({realism_score: 82.4, classification: 'photographic_like', faces_anonymized: 1, model_version: 'x'});
  assert.equal(view.score, '82');
  assert.equal(view.width, '82.4%');
  assert.equal(view.label, '실제 착용 촬영과 유사한 이미지입니다.');
  assert.equal(view.faces, '얼굴 1개를 흰 원으로 가린 뒤 평가했습니다.');
  // 분류는 점수가 아니라 서버 값을 따른다: 높은 점수라도 synthetic_like면 그 문구다.
  const low = context.render({realism_score: 90, classification: 'synthetic_like', faces_anonymized: 0});
  assert.equal(low.label, '생성 이미지와 유사한 특성이 보입니다.');
  assert.equal(low.faces, '가린 얼굴 없음');
  assert.throws(() => context.render({realism_score: 50, classification: 'uncertain', faces_anonymized: 0}));
});

test('upload posts field image and fills the result', async () => {
  let sent;
  const {context, el} = load(async (url, options) => {
    sent = {url, options};
    return {ok: true, json: async () => ({realism_score: 0.4, classification: 'synthetic_like', faces_anonymized: 2})};
  });
  await context.submit({name: 'a.png'});
  assert.equal(sent.url, '/score');
  assert.equal(sent.options.method, 'POST');
  assert.equal(sent.options.body.fields[0][0], 'image');
  assert.equal(el('preview').src, 'blob:preview');
  assert.equal(el('preview').hidden, false);
  assert.equal(el('score').textContent, '0');
  assert.equal(el('result').hidden, false);
  assert.equal(el('error').hidden, true);
});

for (const [status, message] of [[400, '이미지 파일을 읽을 수 없습니다.'], [413, '파일이 너무 큽니다.'],
                                 [415, '지원하지 않는 이미지 형식입니다.'], [500, '점수를 계산하지 못했습니다(HTTP 500).']]) {
  test(`rejection ${status} shows a message and no score`, async () => {
    const {context, el} = load(async () => ({ok: false, status}));
    await context.submit({name: 'a.gif'});
    assert.equal(el('error').textContent, message);
    assert.equal(el('error').hidden, false);
    assert.equal(el('result').hidden, true);
    assert.equal(el('score').textContent, '');
  });
}

test('network failure or unknown classification shows a generic error', async () => {
  for (const fetchImpl of [async () => {throw new TypeError('offline');},
                           async () => ({ok: true, json: async () => ({realism_score: 50, classification: 'other', faces_anonymized: 0})})]) {
    const {context, el} = load(fetchImpl);
    await context.submit({name: 'a.png'});
    assert.equal(el('error').textContent, '점수를 계산하지 못했습니다.');
    assert.equal(el('result').hidden, true);
  }
});
