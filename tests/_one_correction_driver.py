"""Driver source for the single-correction test, kept out of the test file.

The JS is generated rather than written by hand, and it lives here so the
escaping is done once. Three attempts at embedding it inline turned an escape
into a real newline inside a single-quoted JS string, and each time the test
failed for a reason that had nothing to do with what it was checking.
"""

import json

TEMPLATE = """
import * as mod from %(entry)s;
const h = {}; const sent = [];
const pi = {
  on: (e, fn) => { (h[e] ||= []).push(fn); },
  sendMessage: (m) => sent.push(m.customType),
  registerTool: () => {}, registerCommand: () => {}, registerShortcut: () => {},
};
mod.default(pi);
const ctx = { cwd: process.cwd(), hasUI: false, ui: { notify: () => {}, setStatus: () => {} } };

for (const fn of h['tool_result'] || [])
  await fn({ toolName: 'write', input: { path: 'status.txt' },
             content: [{ type: 'text', text: 'C.A.S.E. transition guard: blocked' }],
             isError: true }, ctx);

for (const fn of h['turn_end'] || [])
  await fn({ message: { content: [{ type: 'text', text: %(reply)s }] }, toolResults: [] }, ctx);

process.stdout.write(JSON.stringify({ sent }));
"""

# A reply that would match BOTH guards: it opens with the compaction envelope
# and it also claims the change that was just refused.
REPLY = (
    "<analysis>\n"
    "Let me chronologically analyze the conversation: "
    "已將 status.txt 改為 DONE"
)


def source(entry_url):
    return TEMPLATE % {"entry": json.dumps(entry_url), "reply": json.dumps(REPLY)}
