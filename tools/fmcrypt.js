#!/usr/bin/env node
// FM Pulse UAE data encryption helper (AES-256-GCM). The key is never stored in this repo.
// Usage: FMK=<base64 32-byte key> node tools/fmcrypt.js enc <plain.json> <out.json>
//        FMK=<base64 32-byte key> node tools/fmcrypt.js dec <enc.json> <plain.json>
// Encrypted files have the shape {"v":1,"i":"<base64 iv>","c":"<base64 ciphertext+tag>"}.
const crypto = require("crypto"), fs = require("fs");
const [, , mode, inp, out] = process.argv;
const key = Buffer.from(process.env.FMK || "", "base64");
if (key.length !== 32) { console.error("FMK must be a base64-encoded 32-byte key"); process.exit(1); }
if (mode === "enc") {
  const pt = fs.readFileSync(inp);
  JSON.parse(pt.toString("utf8")); // must be valid JSON
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv("aes-256-gcm", key, iv);
  const ct = Buffer.concat([c.update(pt), c.final(), c.getAuthTag()]);
  fs.writeFileSync(out, JSON.stringify({ v: 1, i: iv.toString("base64"), c: ct.toString("base64") }));
} else if (mode === "dec") {
  const o = JSON.parse(fs.readFileSync(inp, "utf8"));
  const buf = Buffer.from(o.c, "base64");
  const d = crypto.createDecipheriv("aes-256-gcm", key, Buffer.from(o.i, "base64"));
  d.setAuthTag(buf.subarray(buf.length - 16));
  fs.writeFileSync(out, Buffer.concat([d.update(buf.subarray(0, buf.length - 16)), d.final()]));
} else {
  console.error("usage: FMK=<key> node tools/fmcrypt.js enc|dec <in> <out>"); process.exit(1);
}
