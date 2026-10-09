import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sessionToken } from '../src/lib/session.ts';
const result = (session, error = null) => ({data: {session}, error});
test('valid token, then expiry refresh and recovery', async () => {
  let calls = 0;
  const auth = {getSession: async () => result({access_token: 'old', expires_at: 1}), refreshSession: async () => {calls++; return result({access_token: 'new'});}};
  assert.equal(await sessionToken(auth, () => assert.fail('signed out')), 'new');
  assert.equal(calls, 1);
});
test('refresh rejection and absent session enter signed out', async () => {
  for (const failure of [result(null), result(null, {status: 400, message: 'invalid refresh token'})]) {
    let expired = false;
    const auth = {getSession: async () => result({access_token: 'old', expires_at: 1}), refreshSession: async () => failure};
    await assert.rejects(sessionToken(auth, () => {expired = true;}), /session expired/);
    assert.equal(expired, true);
  }
});
test('auth outage preserves identity and reports retry', async () => {
  const auth = {getSession: async () => result(null, {status: 503, message: 'offline'})};
  await assert.rejects(sessionToken(auth, () => assert.fail('outage is not expiry')), /temporarily unavailable/);
});
test('401 recovery uses one forced refresh', async () => {
  let calls = 0;
  const auth = {refreshSession: async () => {calls++;return result({access_token: 'recovered'});}};
  assert.equal(await sessionToken(auth, () => assert.fail(), true), 'recovered');
  assert.equal(calls, 1);
});

import { authDestination } from '../src/lib/auth-redirect.ts';
test('auth callback rejects external and malformed redirects', () => {
  for (const next of ['https://attacker.test', '//attacker.test', '/\\attacker.test', '/reset-password?evil=1', null]) {
    assert.equal(authDestination(next), '/dashboard');
  }
  assert.equal(authDestination('/reset-password'), '/reset-password');
});
