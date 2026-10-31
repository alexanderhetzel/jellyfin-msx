import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";
import assert from "node:assert/strict";
const code = readFileSync(new URL("../src/jellyfin_msx/templates/subtitle-bridge.js", import.meta.url), "utf8");
function fixture(hash, options = {}) {
    let handler;
    const requests = [], notices = [], readers = [];
    const window = { location: { hash, origin: "https://portal.test" } };
    function XHR() { requests.push(this); this.open = (method, url) => { this.method = method; this.url = url; }; this.send = () => {}; this.headers = {}; this.getResponseHeader = name => this.headers[name] || null; }
    function FixtureBlob(parts, options) { this.text = parts.join(""); this.type = options.type; }
    function Reader() { readers.push(this); this.readAsDataURL = blob => { this.result = "data:" + blob.type + ";base64," + Buffer.from(blob.text).toString("base64"); if (!options.deferRead) this.onload(); }; }
    runInNewContext(code, { window, XMLHttpRequest: XHR, Blob: FixtureBlob, FileReader: options.noReader ? undefined : Reader,
        TVXPluginTools: { onReady: fn => fn() },
        TVXInteractionPlugin: { setupHandler: h => { handler = h; }, init() {}, info: (...args) => notices.push(args) } });
    return { handler, requests, notices, window, readers };
}
const hash = "#" + "s".repeat(43) + "/" + "2".repeat(32) + "/" + "3".repeat(32);
test("invalid context cannot fetch; unknown request cannot fetch", () => {
    const f = fixture("#invalid");
    let called = 0;
    f.handler.handleRequest("init", null, value => { assert.equal(value, null); called++; });
    f.handler.handleRequest("unknown", null, value => { assert.equal(value, null); called++; });
    assert.equal(called, 2); assert.equal(f.requests.length, 0);
});
test("subtitle IDs validate only fixed authenticated resource paths", () => {
    const f = fixture(hash); let value;
    f.handler.handleRequest("subtitle:portal-subtitle-7", null, result => { value = result; });
    const xhr = f.requests[0];
    assert.equal(xhr.url, "/api/device/" + "s".repeat(43) + "/subtitles/" + "2".repeat(32) + "/" + "3".repeat(32) + "/7.vtt");
    const payload = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nGrüße, ÄÖÜ äöü ß\n";
    xhr.status = 200; xhr.responseText = payload; xhr.headers["Content-Type"] = "text/vtt; charset=utf-8"; xhr.onload();
    assert.ok(value.url.startsWith("data:text/vtt;charset=utf-8;base64,"));
    assert.equal(Buffer.from(value.url.split(",")[1], "base64").toString(), payload);
    assert.equal(f.requests.length, 1); // No second native bearer fetch after validation.
    assert.equal(f.notices.length, 0);
});
test("expired, missing and invalid subtitle responses give one fixed notice", () => {
    for (const status of [401, 403, 404, 200]) {
        const f = fixture(hash); let calls = 0;
        f.handler.handleRequest("portal-subtitle-18", null, result => { assert.equal(result, null); calls++; });
        const xhr = f.requests[0]; xhr.status = status; xhr.responseText = "private upstream text";
        xhr.headers["Content-Type"] = "text/html"; xhr.onload(); xhr.onerror();
        assert.equal(calls, 1); assert.equal(f.notices.length, 1);
        assert.ok(f.notices[0][0].includes("Select Off or Stop"));
    }
});
test("invalid subtitle IDs never construct a request", () => {
    const f = fixture(hash);
    for (const id of ["portal-subtitle-10001", "portal-subtitle--1", "portal-subtitle-01", "portal-subtitle-7/elsewhere", "https://other.test/"]) {
        f.handler.handleRequest(id, null, result => assert.equal(result, null));
    }
    assert.equal(f.requests.length, 0);
});
test("asynchronous private cue conversion cannot release bytes to a changed context", () => {
    const f = fixture(hash, { deferRead: true }); let value = "pending";
    f.handler.handleRequest("portal-subtitle-7", null, result => { value = result; });
    const xhr = f.requests[0]; xhr.status = 200; xhr.responseText = "WEBVTT\n";
    xhr.headers["Content-Type"] = "text/vtt"; xhr.onload();
    assert.equal(value, "pending");
    f.window.location.hash = hash.replace("2", "4"); f.readers[0].onload();
    assert.equal(value, null);
});
test("missing data-URL support fails clearly without a bearer-URL fallback", () => {
    const f = fixture(hash, { noReader: true }); let value;
    f.handler.handleRequest("portal-subtitle-7", null, result => { value = result; });
    const xhr = f.requests[0]; xhr.status = 200; xhr.responseText = "WEBVTT\n";
    xhr.headers["Content-Type"] = "text/vtt"; xhr.onload();
    assert.equal(value, null); assert.equal(f.notices.length, 1);
});
test("one MiB UTF-8 payload fits the bounded data URL, oversize and bad reader results fail", () => {
    const f = fixture(hash); let value;
    const payload = "ä".repeat(524288);
    assert.equal(Buffer.byteLength(payload), 1048576);
    f.handler.handleRequest("portal-subtitle-7", null, result => { value = result; });
    const xhr = f.requests[0]; xhr.status = 200; xhr.responseText = payload; xhr.headers["Content-Type"] = "text/vtt"; xhr.onload();
    assert.ok(value.url.length <= 1400000);
    assert.equal(Buffer.from(value.url.split(",")[1], "base64").toString(), payload);
    const oversized = fixture(hash); let rejected;
    oversized.handler.handleRequest("portal-subtitle-7", null, result => { rejected = result; });
    const large = oversized.requests[0]; large.status = 200; large.responseText = "x".repeat(1048577); large.onload();
    assert.equal(rejected, null); assert.equal(oversized.readers.length, 0);
    const bad = fixture(hash, { deferRead: true });
    bad.handler.handleRequest("portal-subtitle-7", null, result => { rejected = result; });
    const request = bad.requests[0]; request.status = 200; request.responseText = "WEBVTT\n"; request.headers["Content-Type"] = "text/vtt"; request.onload();
    bad.readers[0].result = "data:text/vtt;base64," + "x".repeat(1400000); bad.readers[0].onload();
    assert.equal(rejected, null); assert.equal(bad.notices.length, 1);
});
test("media goes through same-origin normal resolver, not a vendor query", () => {
    const f = fixture(hash);
    let value;
    f.handler.handleRequest("video:portal-video", null, result => { value = result; });
    const xhr = f.requests[0];
    assert.ok(xhr.url.startsWith("/msx/device/"));
    assert.ok(xhr.url.includes("/play.json?item_id="));
    assert.equal(xhr.timeout, 18000);
    xhr.status = 200; xhr.responseText = JSON.stringify({ response: { status: 200, data: { url: "https://media.test/stream?ApiKey=synthetic" } } }); xhr.onload();
    assert.equal(value.url, "https://media.test/stream?ApiKey=synthetic");
    assert.equal(f.notices.length, 0);
});
test("stale context rejects old response without releasing it", () => {
    const f = fixture(hash); let value = "pending";
    f.handler.handleRequest("init", null, result => { value = result; });
    const xhr = f.requests[0];
    f.window.location.hash = hash.replace("2", "4");
    xhr.status = 200; xhr.responseText = JSON.stringify({ items: [] }); xhr.onload();
    assert.equal(value, null);
});
test("HTTP and wrapped authorization failures show fixed recovery notice", () => {
    for (const status of [401, 200]) {
        const f = fixture(hash); let value;
        f.handler.handleRequest("portal-video", null, result => { value = result; });
        const xhr = f.requests[0]; xhr.status = status;
        xhr.responseText = JSON.stringify({ response: { status: 401, message: "private upstream text" } }); xhr.onload();
        assert.equal(value, null); assert.equal(f.notices.length, 1);
        assert.ok(!f.notices[0][0].includes("private upstream"));
    }
});
