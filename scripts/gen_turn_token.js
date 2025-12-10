#!/usr/bin/env node
/**
 * Generate short-lived TURN credentials for coturn's static-auth-secret flow.
 *
 * Usage:
 *   TURN_SECRET=your_shared_secret [TTL_SECONDS=60] node scripts/gen_turn_token.js
 */
const crypto = require('crypto');

const secret = process.env.TURN_SECRET;
if (!secret) {
  console.error('Error: TURN_SECRET is required (shared secret from .env.turn).');
  process.exit(1);
}

const ttlSeconds = Number(process.env.TTL_SECONDS || 60);
const now = Math.floor(Date.now() / 1000);
const username = String(now + ttlSeconds);
const password = crypto.createHmac('sha1', secret).update(username).digest('base64');

console.log(
  JSON.stringify(
    {
      username,
      password,
      ttlSeconds,
      realm: process.env.TURN_REALM || 'embody.app',
    },
    null,
    2,
  ),
);
