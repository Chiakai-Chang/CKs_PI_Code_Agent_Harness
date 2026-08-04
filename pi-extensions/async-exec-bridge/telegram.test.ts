import { test } from "node:test";
import assert from "node:assert/strict";
import { telegramTarget } from "./telegram.ts";

test("disabled by default — an outbound message is never sent unasked", () => {
  // This posts to a third-party service. Silently defaulting to on would send
  // the user's job labels off the machine without them ever asking for it.
  assert.equal(telegramTarget(false, { botToken: "t", allowedUserId: 1 }), null);
});

test("enabled with a usable config gives a target", () => {
  assert.deepEqual(telegramTarget(true, { botToken: "t", allowedUserId: 1 }), {
    botToken: "t",
    chatId: 1,
  });
});

test("enabled but not connected stays silent rather than erroring", () => {
  // pi-telegram writes this file itself; before the user has ever linked a
  // chat there is no allowedUserId. That is "not connected", not a fault.
  assert.equal(telegramTarget(true, { botToken: "t" }), null);
  assert.equal(telegramTarget(true, { allowedUserId: 1 }), null);
  assert.equal(telegramTarget(true, null), null);
});

test("a malformed config is treated as not connected", () => {
  // The file belongs to another package and its shape can change upstream, so
  // anything unexpected must degrade to silence, never to a throw.
  assert.equal(telegramTarget(true, { botToken: "", allowedUserId: 0 }), null);
  assert.equal(telegramTarget(true, { botToken: 5, allowedUserId: "x" } as never), null);
});
