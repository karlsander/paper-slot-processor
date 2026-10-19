import test from 'node:test';
import assert from 'node:assert/strict';
import { Revision, restoreParameters } from './state.js';

test('a late result cannot replace the latest edit', async () => {
  const revision = new Revision();
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  let visible;
  const old = revision.next();
  const oldResponse = pending.then(() => { if (revision.current(old)) visible = 'old'; });
  const current = revision.next();
  if (revision.current(current)) visible = 'current';
  release();
  await oldResponse;
  assert.equal(visible, 'current');
});

test('restoring saved values rejects obsolete and invalid settings', () => {
  const config = { defaults: { width: 120, chambers: 2, base: true }, fields: [
    { id: 'width', type: 'number', min: 40, max: 170 },
    { id: 'chambers', type: 'integer', min: 1, max: 2 },
    { id: 'base', type: 'boolean' }
  ] };
  assert.deepEqual(restoreParameters({ width: 146.5, chambers: 1, base: false, old: 99 }, config), { width: 146.5, chambers: 1, base: false });
  for (const width of ['125', Infinity, NaN, null, 999, true]) {
    assert.deepEqual(restoreParameters({ width, chambers: 1.5, base: 'false' }, config), config.defaults);
  }
  assert.deepEqual(restoreParameters(null, config), config.defaults);
});
