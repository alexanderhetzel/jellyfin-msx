import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";
import assert from "node:assert/strict";
const code = readFileSync(new URL("../src/jellyfin_msx/templates/subtitle-bridge.js", import.meta.url), "utf8");
function fixture(hash, options = {}) {
    let handler;
    const requests = [], notices = [], readers = [], panels = [], contents = [], actions = [];
    const window = { location: { hash, origin: "https://portal.test" } };
    const diagnosticOutput = { textContent: "" };
    const document = { getElementById: id => id === "subtitle-diagnostics" ? diagnosticOutput : null };
    function XHR() { requests.push(this); this.open = (method, url) => { this.method = method; this.url = url; }; this.send = () => {}; this.headers = {}; this.getResponseHeader = name => this.headers[name] || null; }
    function FixtureBlob(parts, options) { this.text = parts.join(""); this.type = options.type; }
    function Reader() { readers.push(this); this.readAsDataURL = blob => { this.result = "data:" + blob.type + ";base64," + Buffer.from(blob.text).toString("base64"); if (!options.deferRead) this.onload(); }; }
    runInNewContext(code, { window, document, XMLHttpRequest: XHR, Blob: FixtureBlob, FileReader: options.noReader ? undefined : Reader,
        TVXPluginTools: { onReady: fn => fn() },
        TVXInteractionPlugin: { setupHandler: h => { handler = h; }, init() {}, info: (...args) => notices.push(args), showPanel: value => panels.push(value), showContent: value => contents.push(value), executeAction: value => actions.push(value) } });
    return { handler, requests, notices, window, readers, panels, contents, actions, diagnosticOutput };
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
        assert.equal(f.panels.length, 1);
        assert.equal(f.panels[0].items[1].action, "panel:request:player:subtitle");
        assert.equal(f.panels[0].items[2].action, "player:stop");
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
        assert.deepEqual(f.actions, ["player:stop"]);
        assert.equal(f.contents[0].headline, "Playback unavailable");
        assert.equal(f.contents[0].items[1].action, "content:https://portal.test/msx/pair.json");
    }
});
test("stale XHR and reader failures cannot interrupt a newer context", () => {
    for (const event of ["onerror", "ontimeout", "reader-error", "reader-abort"]) {
        const f = fixture(hash, { deferRead: true }); let calls = 0;
        f.handler.handleRequest("portal-subtitle-7", null, value => { assert.equal(value, null); calls++; });
        const xhr = f.requests[0];
        if (event.startsWith("reader-")) {
            xhr.status = 200; xhr.responseText = "WEBVTT\n"; xhr.headers["Content-Type"] = "text/vtt"; xhr.onload();
        }
        f.window.location.hash = hash.replace("2", "4");
        if (event.startsWith("reader-")) f.readers[0][event === "reader-error" ? "onerror" : "onabort"]();
        else xhr[event]();
        assert.equal(calls, 1);
        assert.equal(f.notices.length + f.panels.length + f.contents.length + f.actions.length, 0);
    }
});
test("failure callback changing context suppresses every recovery side effect", () => {
    for (const id of ["portal-video", "portal-subtitle-7", "init"]) {
        const f = fixture(hash); let calls = 0;
        f.handler.handleRequest(id, null, value => { assert.equal(value, null); calls++; f.window.location.hash = "#invalid"; });
        f.requests[0].onerror(); f.requests[0].ontimeout();
        assert.equal(calls, 1);
        assert.equal(f.notices.length + f.panels.length + f.contents.length + f.actions.length, 0);
    }
});
test("diagnostics contain only fixed bounded counters, never request or response material", () => {
    const f = fixture(hash);
    f.handler.handleRequest("private unexpected ID", { secret: "private data" }, () => {});
    f.handler.handleRequest("portal-subtitle-7", null, () => {});
    const xhr = f.requests[0]; xhr.status = 200; xhr.responseText = "WEBVTT\n"; xhr.headers["Content-Type"] = "text/vtt"; xhr.onload();
    const counts = JSON.parse(f.diagnosticOutput.textContent);
    assert.deepEqual(counts, { init: 0, video: 0, subtitle: 1, unknown: 1, subtitleFetch: 1, subtitleOk: 1, subtitleDenied: 0, subtitleOther: 0, subtitleDataCallback: 1, subtitleNullCallback: 0 });
    for (let i = 0; i < 65536; i++) f.handler.handleRequest("private unexpected ID", null, () => {});
    assert.equal(JSON.parse(f.diagnosticOutput.textContent).unknown, 65535);
    assert.ok(!f.diagnosticOutput.textContent.includes("private"));
    assert.ok(!f.diagnosticOutput.textContent.includes("WEBVTT"));
    assert.ok(!f.diagnosticOutput.textContent.includes("portal.test"));
});
