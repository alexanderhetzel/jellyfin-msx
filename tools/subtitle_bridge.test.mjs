import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";
import assert from "node:assert/strict";
const code = readFileSync(new URL("../src/jellyfin_msx/templates/subtitle-bridge.js", import.meta.url), "utf8");
function fixture(hash) {
    let handler;
    const requests = [], notices = [];
    const window = { location: { hash } };
    function XHR() { requests.push(this); this.open = (method, url) => { this.method = method; this.url = url; }; this.send = () => {}; }
    runInNewContext(code, { window, XMLHttpRequest: XHR,
        TVXPluginTools: { onReady: fn => fn() },
        TVXInteractionPlugin: { setupHandler: h => { handler = h; }, init() {}, info: (...args) => notices.push(args) } });
    return { handler, requests, notices, window };
}
const hash = "#" + "s".repeat(43) + "/" + "2".repeat(32) + "/" + "3".repeat(32);
test("invalid context cannot fetch; unknown request cannot fetch", () => {
    const f = fixture("#invalid");
    let called = 0;
    f.handler.handleRequest("init", null, value => { assert.equal(value, null); called++; });
    f.handler.handleRequest("unknown", null, value => { assert.equal(value, null); called++; });
    assert.equal(called, 2); assert.equal(f.requests.length, 0);
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
