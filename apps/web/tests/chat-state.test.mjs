import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chatErrorMessage, appendTurn} from '../src/lib/chat-state.ts';

test('ordinary chat never renders upstream text, model IDs or long retry values', () => {
  for (const code of ['provider_rate_limited', 'provider_unavailable', 'provider_timeout', 'provider_invalid_response']) {
    const text = chatErrorMessage({code, detail: 'gemini-3.8-flash raw 503 stack', retry_after_seconds: 46080});
    assert.doesNotMatch(text, /gemini|503|stack|768|46080|rate-limit/i);
    assert.match(text, /try again|retry/i);
  }
});
test('access failures, safety and retrieval remain distinct from availability', () => {
  assert.match(chatErrorMessage({status: 403}), /does not permit/);
  assert.match(chatErrorMessage({code: 'session_expired'}), /Sign in/);
  assert.match(chatErrorMessage({code: 'provider_safety_block'}), /rephrasing/);
  assert.match(chatErrorMessage({code: 'retrieval_unavailable'}), /Authorized search/);
  assert.match(chatErrorMessage({code: 'provider_timeout'}), /too long/);
});
test('a repeated terminal SSE result cannot duplicate a user turn', () => {
  const turn = {query: 'hello', response: {request_id: 'one'}};
  const first = appendTurn([], turn);
  assert.equal(appendTurn(first, turn), first);
  assert.equal(appendTurn(first, {...turn, response: {request_id: 'two'}}).length, 2);
});

test('original-source grouping retains distinct OCR citations and never merges duplicate titles', async () => {
  const {groupCitations} = await import('../src/lib/chat-state.ts');
  const first = {citation_id: 'chunk-1', document_id: 'doc-a', title: 'Invoice', location: {image_id: 'scan', region: {x_min: 1}}};
  const second = {...first, citation_id: 'chunk-2', location: {image_id: 'scan', region: {x_min: 90}}};
  const groups = groupCitations([first, second, first, {...first, document_id: 'doc-b'}]);
  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0].citations, [first, second]);
});
