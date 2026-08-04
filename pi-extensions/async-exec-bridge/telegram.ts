import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

/** The shape this reads out of pi-telegram's own config. Deliberately partial:
 *  the file belongs to another package and may grow fields or change them. */
export interface TelegramConfig {
  botToken?: unknown;
  allowedUserId?: unknown;
}

export interface TelegramTarget {
  botToken: string;
  chatId: number;
}

/** Pure. Decides whether a sideband message can be sent, and to whom.
 *
 *  Two gates, both deliberate:
 *
 *  - `enabled` is opt-in and defaults to false in harness-config. This sends a
 *    message to a third-party service over the network; turning that on by
 *    merely detecting a config file would move the user's job labels off their
 *    machine without them ever asking.
 *  - Anything missing or the wrong type reads as "not connected" and returns
 *    null. pi-telegram writes this file itself and only records
 *    `allowedUserId` once a chat has been linked, so an absent field is the
 *    normal not-yet-connected state — not an error worth reporting, and never
 *    a reason to disturb job state. */
export function telegramTarget(enabled: boolean, config: TelegramConfig | null): TelegramTarget | null {
  if (!enabled || config === null) return null;
  const { botToken, allowedUserId } = config;
  if (typeof botToken !== "string" || botToken.length === 0) return null;
  if (typeof allowedUserId !== "number" || !Number.isFinite(allowedUserId) || allowedUserId === 0) {
    return null;
  }
  // In a private chat the user id is the chat id, which is the only
  // conversation pi-telegram will accept messages from anyway.
  return { botToken, chatId: allowedUserId };
}

/** pi-telegram's config. Returns null if absent or unreadable — it is a package
 *  the user may simply not have installed. */
export function readTelegramConfig(): TelegramConfig | null {
  try {
    return JSON.parse(
      readFileSync(join(homedir(), ".pi", "agent", "telegram.json"), "utf-8"),
    ) as TelegramConfig;
  } catch {
    return null;
  }
}

/** Fire and forget. Never awaited by the caller, never throws, and cannot
 *  affect job state: the job files on disk stay the source of truth, and a
 *  notification is a courtesy on the side. */
export function sendTelegram(target: TelegramTarget, text: string): void {
  try {
    void fetch(`https://api.telegram.org/bot${target.botToken}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: target.chatId, text }),
    }).catch(() => {
      // Offline, rate limited, revoked token — all the same here: silence.
    });
  } catch {
    // fetch itself unavailable; nothing to do and nothing worth saying.
  }
}
