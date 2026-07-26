---
name: tool-repair-guide
description: Defensive rules and self-healing specifications for LLM tool call argument repairs, runtime fallbacks, and prompt-cache friendly error guidance.
tools: read, grep, find, ls, bash
---

# Tool Call Self-Healing & Repair Layer Guide (工具呼叫自動修復指南)

This skill codifies the architectural rules for **transparent LLM tool-call repairs** and **execution-aware fallbacks** within the harness.

---

## 1. Core Principles

### 1. Structural Repairs vs Content Preservation
- **Rule**: Structural mistakes (paths wrapped in markdown links, stringified JSON arrays, boolean/number coercions, `null` fields) MUST be sanitized pre-execution.
- **NEVER-TOUCH BLACKLIST**: Content fields (`command`, `code`, `oldText`, `newText`, `text`) MUST NEVER be modified or mutated by structural sanitizers.

### 2. The 9 Canonical Field Repairs

| Repair Pattern | Trigger Condition | Canonical Transformation |
| :--- | :--- | :--- |
| **`clean-path`** | `path` contains Markdown link `[f.txt](http://...)` | Unwrap to relative path `"f.txt"` |
| **`parse-json`** | Array/object field passed as string `"[\"a\",\"b\"]"` | `JSON.parse()` to native array/object |
| **`wrap-object-as-array`** | Single object `{a:1}` passed to array field | Wrap as `[{a:1}]` |
| **`wrap-array`** | Bare string `"x"` passed to array field | Wrap as `["x"]` |
| **`split-string-to-array`**| Delimited string `"a, b"` passed to array field | Split to `["a", "b"]` |
| **`strip-extra-properties`**| Extra properties on structured array items | Filter item properties against schema |
| **`null-like-to-undefined`**| Field is `null` or `"null"` string | Omit field completely |
| **`coerce-boolean`** | String `"true"` / `"false"` for boolean field | Convert to native `true` / `false` |
| **`coerce-number`** | String `"42"` for numeric limit/offset | Convert to native integer `42` |

### 3. Execution-Aware Fallbacks & Relational Defaults
- **EISDIR Directory Read Fallback**: If a file-read tool encounters an `EISDIR` (path is a directory), return the directory listing (`📁 Directory: listing`) instead of throwing an unhandled exception.
- **Relational Defaults**: If a pagination tool receives `limit` without `offset`, inject `offset: 1` to prevent models from repeatedly reading line 0.
- **Content Hash Staleness Checks**: Cache file hashes on `read` and verify them before `edit` to detect file drift pre-execution.

### 4. Side-Channel Guidance (Cache-Friendly Error Recovery)
- **Prompt Cache Protection**: Error recovery guidance should be delivered via shallow `context` events or side-channel messages, NEVER by mutating the historical `tool_result` prefix. This ensures 100% prompt cache hit rates across turns.
- **Circuit Breakers**: Halt tool retries if 7+ consecutive identical tool failures occur, preventing infinite loop token burn.

---

## 2. Pre-Execution Sanitization Pipeline

```
[LLM Tool Call Event]
         │
  Is field in Content Blacklist (code/command/text)?
         │
   ┌─────┴─────┐
  YES         NO
   │           │
[Pass-Through] ├─► 1. Clean Markdown Paths
               ├─► 2. Parse Stringified JSON
               ├─► 3. Coerce Booleans & Numbers
               ├─► 4. Wrap Bare Strings/Objects to Arrays
               └─► 5. Omit Null-like Fields
                       │
             [Execute Tool Call]
```
