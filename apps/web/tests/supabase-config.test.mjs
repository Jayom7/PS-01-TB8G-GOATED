import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getSupabaseConfig, SupabaseConfigurationError } from '../src/lib/supabase/env.ts';

test('configuration rejects missing, blank and malformed inputs without exposing them', () => {
  const names = ['NEXT_PUBLIC_SUPABASE_URL', 'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY'];
  const previous = names.map((name) => process.env[name]);
  try {
    for (const [url, key] of [[undefined, 'test-key'], ['https://example.test', undefined], [' ', 'test-key'], ['https://example.test', ' '], ['malformed-url', 'test-key'], ['file:///private/config', 'test-key']]) {
      for (const [index, value] of [url, key].entries()) {
        if (value === undefined) delete process.env[names[index]];
        else process.env[names[index]] = value;
      }
      assert.throws(getSupabaseConfig, (error) => {
        assert.ok(error instanceof SupabaseConfigurationError);
        assert.equal(error.message, 'Workspace sign-in is not configured. Contact your workspace administrator.');
        return true;
      });
    }
    for (const url of ['http://127.0.0.1:54321', 'https://example.test']) {
      process.env[names[0]] = url;
      process.env[names[1]] = 'test-key';
      assert.deepEqual(getSupabaseConfig(), { url, publishableKey: 'test-key' });
    }
  } finally {
    names.forEach((name, index) => {
      if (previous[index] === undefined) delete process.env[name];
      else process.env[name] = previous[index];
    });
  }
});
