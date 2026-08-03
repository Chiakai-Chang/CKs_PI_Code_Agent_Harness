import { closeSync, openSync, readSync, statSync } from "node:fs";
import { tailBytes } from "./envelope.ts";

/** Read at most `max` bytes from the END of a capture file.
 *
 *  The whole file can be CAPTURE_MAX_BYTES (8 MiB); the envelope only ever
 *  injects ENVELOPE_TAIL_BYTES (4 KiB) of it. Reading the file whole just to
 *  throw away 99.95% of it is a cost paid on every completion, so seek instead.
 *  The result is still passed through tailBytes, which aligns the start to a
 *  character boundary — seeking to an arbitrary byte offset lands mid-character
 *  as readily as slicing does. */
export function readTail(path: string, max: number): string {
  let fd: number | undefined;
  try {
    const size = statSync(path).size;
    const start = Math.max(0, size - max);
    const length = size - start;
    if (length === 0) return "";
    const buf = Buffer.allocUnsafe(length);
    fd = openSync(path, "r");
    const read = readSync(fd, buf, 0, length, start);
    // Align on the RAW buffer, before decoding. Decoding first would turn a
    // truncated leading character into U+FFFD, and a 3-byte replacement char
    // can fit inside the budget and survive any later trim.
    let from = 0;
    if (start > 0) {
      while (from < read && (buf[from] & 0xc0) === 0x80) from++;
    }
    return tailBytes(buf.subarray(from, read).toString("utf8"), max);
  } catch {
    // No capture on disk: the job may have been killed before writing.
    return "";
  } finally {
    if (fd !== undefined) {
      try {
        closeSync(fd);
      } catch {
        // Already closed.
      }
    }
  }
}
