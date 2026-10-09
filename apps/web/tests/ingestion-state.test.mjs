import {test} from 'node:test';
import assert from 'node:assert/strict';
import {initialIngestion, ingestionReducer} from '../src/lib/ingestion-state.ts';

test('file and structured operations keep separate pending, errors and successes', () => {
  const upload = ingestionReducer(initialIngestion, {operation: 'file', status: 'start'});
  assert.equal(upload.file.pending, true);
  assert.equal(upload.structured, initialIngestion.structured);
  const both = ingestionReducer(upload, {operation: 'structured', status: 'start'});
  const failed = ingestionReducer(both, {operation: 'file', status: 'failure', message: 'Please retry.'});
  assert.equal(failed.file.pending, false);
  assert.equal(failed.file.error, 'Please retry.');
  assert.equal(failed.structured.pending, true);
  const saved = ingestionReducer(failed, {operation: 'structured', status: 'success', message: 'Row indexed'});
  assert.equal(saved.structured.result, 'Row indexed');
  assert.equal(saved.file, failed.file);
});

test('ingestion errors retain input guidance without chat wording or raw provider diagnostics', async () => {
  const {ingestionErrorMessage} = await import('../src/lib/ingestion-state.ts');
  const message = ingestionErrorMessage({code: 'provider_rate_limited', stage: 'embedding', detail: 'raw Gemini 429', retry_after_seconds: 46000}, 429);
  assert.match(message, /input is still selected/);
  assert.doesNotMatch(message, /answer|Gemini|429|46000/);
  assert.equal(ingestionErrorMessage({code: 'provider_unavailable'}, 401), null);
});
