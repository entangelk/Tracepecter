// P07-03 demo page: renders only the API response and maps rejections without inventing scores.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '../demo/index.html'), 'utf8');

function load(fetchImpl) {
  // 초기 hidden 상태는 마크업의 hidden 속성을 따른다.
  const hiddenIds = new Set([...html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*\bhidden\b[^>]*>/g)].map(m => m[1]));
  const elements = new Map();
  const element = id => ({style: {}, hidden: hiddenIds.has(id), textContent: '', src: '', listeners: {},
    addEventListener(name, fn) {this.listeners[name] = fn;}});
  const document = {getElementById(id) {if (!elements.has(id)) elements.set(id, element(id)); return elements.get(id);}};
  class FormData {constructor() {this.fields = [];} append(...field) {this.fields.push(field);}}
  let objectUrls = 0;
  const context = {document, FormData, fetch: fetchImpl, String, Math, Error,
    URL: {createObjectURL: () => `blob:preview${++objectUrls}`, revokeObjectURL() {}}};
  vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return {context, el: id => document.getElementById(id)};
}

const ok = result => async () => ({ok: true, json: async () => result});
const REAL = {realism_score: 85.54, classification: 'photographic_like', faces_anonymized: 0};

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
  assert.equal(el('preview').src, 'blob:preview1');
  assert.equal(el('preview').hidden, false);
  assert.equal(el('score').textContent, '0');
  assert.equal(el('result').hidden, false);
  assert.equal(el('error').hidden, true);
});

for (const [status, message] of [[400, '이미지 파일을 읽을 수 없습니다.'], [413, '파일 크기나 이미지 해상도가 너무 큽니다.'],
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

test('score display uses Math.round, not floor or ceil', () => {
  const {context} = load();
  for (const [score, shown] of [[85.54, '86'], [85.4, '85'], [23.5, '24'], [0.4, '0'], [99.6, '100']]) {
    assert.equal(context.render({realism_score: score, classification: 'synthetic_like', faces_anonymized: 0}).score, shown);
  }
});

test('initial state shows notices area only: result, error and preview hidden', () => {
  const {el} = load();
  assert.equal(el('result').hidden, true);
  assert.equal(el('error').hidden, true);
  assert.equal(el('preview').hidden, true);
  assert.equal(el('faces').hidden, false);
});

test('rejection after a success hides the previous score', async () => {
  let respond = ok(REAL);
  const {context, el} = load((...args) => respond(...args));
  await context.submit({name: 'real.jpg'});
  assert.equal(el('result').hidden, false);
  respond = async () => ({ok: false, status: 400});
  await context.submit({name: 'bad.txt'});
  assert.equal(el('result').hidden, true);
  assert.equal(el('error').hidden, false);
});

test('a late response from an earlier upload does not overwrite the latest screen', async () => {
  const pending = [];
  const {context, el} = load(() => new Promise(resolve => pending.push(resolve)));
  const first = context.submit({name: 'real.jpg'});
  const second = context.submit({name: 'bad.txt'});
  pending[1]({ok: false, status: 400});
  await second;
  pending[0]({ok: true, json: async () => REAL});
  await first;
  assert.equal(el('result').hidden, true);
  assert.equal(el('score').textContent, '');
  assert.equal(el('error').textContent, '이미지 파일을 읽을 수 없습니다.');
  assert.equal(el('preview').src, 'blob:preview2');
});

test('a late failure from an earlier upload does not replace the latest result', async () => {
  const pending = [];
  const {context, el} = load(() => new Promise((resolve, reject) => pending.push({resolve, reject})));
  const first = context.submit({name: 'a.png'});
  const second = context.submit({name: 'real.jpg'});
  pending[1].resolve({ok: true, json: async () => REAL});
  await second;
  pending[0].reject(new TypeError('offline'));
  await first;
  assert.equal(el('result').hidden, false);
  assert.equal(el('error').hidden, true);
});

test('preview that cannot be decoded is replaced by a placeholder message', () => {
  const {el} = load();
  el('preview').hidden = false;
  el('placeholder').hidden = true;
  el('preview').listeners.error();
  assert.equal(el('preview').hidden, true);
  assert.equal(el('placeholder').hidden, false);
  assert.equal(el('placeholder').textContent, '미리보기를 표시할 수 없습니다');
});
