const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const test = require("node:test");
const assert = require("node:assert/strict");
const code = readFileSync(require("node:path").join(__dirname, "../src/jellyfin_msx/templates/lifecycle.js"), "utf8");
const hash = "#" + "s".repeat(43) + "/" + "2".repeat(32) + "/" + "3".repeat(32);
function fixture(initial = hash) {
    let now = 100000, next = 0, handler;
    const timers = new Map(), requests = [], samples = [], notices = [];
    const window = { location: { hash: initial } };
    function later(fn, delay) { const id = ++next; timers.set(id, { fn, time: now + delay }); return id; }
    function tick(ms) {
        const end = now + ms;
        for (;;) {
            const due = [...timers].filter(([, t]) => t.time <= end).sort((a, b) => a[1].time - b[1].time)[0];
            if (!due) break;
            timers.delete(due[0]); now = due[1].time; due[1].fn();
        }
        now = end;
    }
    function XHR() {
        requests.push(this); this.headers = {};
        this.open = (method, url) => { this.method = method; this.url = url; };
        this.setRequestHeader = (key, value) => { this.headers[key] = value; };
        this.send = body => { this.body = JSON.parse(body); };
        this.abort = () => { this.aborted = true; };
        this.respond = (status, data) => { this.status = status; this.responseText = JSON.stringify(data); this.onload(); };
    }
    runInNewContext(code, { window, document: { getElementById: () => ({}) }, Date: { now: () => now },
        setTimeout: later, clearTimeout: id => timers.delete(id), XMLHttpRequest: XHR,
        TVXPluginTools: { onReady: fn => fn() }, TVXInteractionPlugin: {
            setupHandler: value => { handler = value; }, init() {}, info: value => notices.push(value),
            requestData: (id, fn) => { assert.equal(id, "video"); samples.push(fn); }
        } });
    return { window, requests, samples, timers, tick, jump: ms => { now += ms; }, handler, notices, telemetry: window.PortalLifecycle.create() };
}
function start(f, correlate = true, id = "p".repeat(32)) {
    let result;
    f.telemetry.start(value => { result = value; });
    f.requests.at(-1).respond(200, { grant: "g".repeat(43), playback_id: id, url: "https://media.test/original?ApiKey=synthetic", expires_in: 28800, duration: 30, start_position: 0 });
    assert.equal(result.url, "https://media.test/original?ApiKey=synthetic");
    assert.equal(result.properties["portal:playback"], id);
    if (correlate) {
        f.telemetry.handleEvent({ event: "video:load", info: { properties: { "portal:playback": id } } });
        f.requests.at(-1).respond(200, {});
    }
}
function sample(f, position, state = 2, extra = {}) {
    f.samples.at(-1)({ video: { info: { properties: { "portal:playback": "p".repeat(32) } }, data: { state, position, duration: 30, speed: 1, ...extra } } });
}
test("invalid context and unknown requests never fetch", () => {
    const f = fixture("#invalid");
    f.telemetry.start(value => assert.equal(value, null));
    f.handler.handleRequest("unknown", null, value => assert.equal(value, null));
    assert.equal(f.requests.length, 0);
});
test("start authenticates fixed endpoint and keeps credentials out of body", () => {
    const f = fixture(); start(f);
    const req = f.requests[0];
    assert.equal(req.url, "/api/playback/start"); assert.equal(req.method, "POST");
    assert.equal(req.headers.Authorization, "Bearer " + "s".repeat(43));
    assert.deepEqual(req.body, { item_id: "2".repeat(32), media_source_id: "3".repeat(32), force: false, subtitle: -1, resume: false });
    assert.equal(f.requests.length, 2);
});

test("saved Resume returns documented fixed native position without fabricating samples", () => {
    const f = fixture(hash + "/0/-1/resume"); let result;
    f.telemetry.start(value => { result = value; });
    assert.equal(f.requests[0].body.resume, true);
    f.requests[0].respond(200, { grant: "g".repeat(43), playback_id: "p".repeat(32), url: "https://media.test/original", expires_in: 900, duration: 30, start_position: 8.25 });
    assert.equal(result.properties["resume:position"], "8.25");
    assert.equal(result.properties["portal:playback"], "p".repeat(32));
    assert.equal(f.requests.length, 1);
    let page; f.handler.handleRequest("init", null, value => { page = value; });
    assert.equal(page.items[0].title, "Resume saved progress");
});

test("Start over always emits explicit zero and rejects a nonzero backend result", () => {
    const f = fixture(hash + "/0/-1/start"); start(f);
    assert.equal(f.requests[0].body.resume, false);
    let result;
    f.telemetry.start(value => { result = value; });
    f.requests.at(-1).respond(200, { grant: "g".repeat(43), playback_id: "q".repeat(32), url: "https://media.test/original", expires_in: 900, duration: 30, start_position: 8 });
    assert.equal(result, null);
});

test("untrusted native positions fail closed and do not start sampling", () => {
    for (const position of [undefined, null, "8", true, -1, 30, 864001, Infinity, NaN]) {
        const f = fixture(hash + "/0/-1/resume"); let result;
        f.telemetry.start(value => { result = value; });
        f.requests[0].respond(200, { grant: "g".repeat(43), playback_id: "p".repeat(32), url: "https://media.test/original", expires_in: 900, duration: 30, start_position: position });
        assert.equal(result, null); f.tick(10000);
        assert.equal(f.samples.length, 0);
    }
});
test("simultaneous resolution single-flights; changed context drops response", () => {
    const f = fixture(); let calls = 0;
    f.telemetry.start(value => { assert.equal(value, null); calls++; });
    f.telemetry.start(value => { assert.equal(value, null); calls++; });
    assert.equal(f.requests.length, 1);
    f.window.location.hash = hash.replace("2", "4");
    f.requests[0].respond(200, { grant: "g".repeat(43), playback_id: "p".repeat(32), url: "https://media.test/original", expires_in: 28800 });
    assert.equal(calls, 2); f.tick(2000); assert.equal(f.samples.length, 0);
});
test("load never relabels previous attached media; snapshots are separately sanitized", () => {
    const f = fixture(); start(f);
    f.telemetry.handleEvent({ event: "video:load", info: { properties: { "portal:playback": "p".repeat(32) } }, data: { position: 29, duration: 30, ended: true, url: "private" } });
    let req = f.requests.at(-1);
    assert.deepEqual(req.body.observations[0].data, {});
    assert.equal(req.headers.Authorization, "Bearer " + "g".repeat(43));
    req.respond(200, {});
    f.tick(2000); sample(f, 1, 2, { url: "private", title: "private", state: 2 });
    req = f.requests.at(-1);
    assert.equal(req.body.observations[0].kind, "snapshot");
    assert.equal(req.body.observations[0].name, "video");
    assert.equal(JSON.stringify(req.body).includes("private"), false);
    assert.equal(req.timeout, 5000);
});
test("late video samples from replaced generations cannot be uploaded", () => {
    const f = fixture(); start(f); f.tick(2000);
    const old = f.samples.at(-1); start(f);
    const count = f.requests.length; old({ video: { data: { state: 2, position: 20, duration: 30 } } });
    assert.equal(f.requests.length, count);
});
test("Stop requires a fresh marked stopped sample and retains last safe position", () => {
    const f = fixture(); start(f); f.tick(2000); const old = f.samples.at(-1);
    f.telemetry.handleEvent({ event: "video:stop", data: { state: 2, position: 7, duration: 30 } });
    old({ video: { info: { properties: { "portal:playback": "p".repeat(32) } }, data: { state: 1, position: 0, duration: 0 } } });
    const terminal = f.requests.at(-1).body.observations.at(-1);
    assert.equal(terminal.name, "video:stop"); assert.deepEqual(terminal.data, {});
    f.requests.at(-1).respond(200, {});
    f.tick(60000); assert.equal(f.samples.length, 1); assert.equal(f.timers.size, 0);
});
test("network retries preserve payload, respect backoff and terminate after three retries", () => {
    const f = fixture(); start(f);
    f.telemetry.handleEvent({ event: "video:pause", data: { state: 2, position: 7, duration: 30 } });
    const body = JSON.stringify(f.requests.at(-1).body);
    for (const delay of [1000, 2000, 4000]) {
        const count = f.requests.length; f.requests.at(-1).onerror();
        f.tick(delay - 1); assert.equal(f.requests.length, count); f.tick(1);
        assert.equal(JSON.stringify(f.requests.at(-1).body), body);
    }
    f.requests.at(-1).onerror(); const count = f.requests.length;
    f.tick(120000); assert.equal(f.requests.length, count); assert.equal(f.timers.size, 0);
});
test("control flooding cannot grow pending queue beyond bound or continue sampling", () => {
    const f = fixture(); start(f);
    for (let i = 0; i < 1000; i++) f.telemetry.handleEvent({ event: "video:seek", position: 5, data: { position: 1, duration: 30, state: 2 } });
    assert.equal(f.requests.length, 3); assert.equal(f.requests.at(-1).aborted, true);
    f.tick(120000); assert.equal(f.samples.length, 0); assert.equal(f.timers.size, 0);
});
test("missing or invalid samples expire without progress or fabricated app events", () => {
    const f = fixture(); start(f);
    for (let i = 0; i < 24; i++) { f.tick(2000); if (f.samples.length) f.samples.at(-1)({ video: { data: { state: 3, position: 0, duration: 0 } } }); }
    f.tick(10000); assert.equal(f.requests.length, 2); assert.equal(f.timers.size, 0);
});
test("unknown visibility does not pause fresh playing samples", () => {
    const f = fixture(); start(f); f.tick(2000); sample(f, 1);
    f.requests.at(-1).respond(200, {});
    f.telemetry.handleEvent({ event: "visibilitychange", data: { hidden: true } });
    f.tick(10000); sample(f, 11);
    assert.equal(f.requests.at(-1).body.observations.at(-1).data.state, 2);
});
test("four-hundred denial fails closed without retries or notices containing response", () => {
    const f = fixture(); start(f);
    f.telemetry.handleEvent({ event: "video:play", data: { state: 3, position: 7, duration: 30 } });
    f.requests.at(-1).respond(401, { detail: "private upstream data" });
    f.tick(60000); assert.equal(f.requests.length, 3); assert.equal(f.timers.size, 0); assert.equal(f.notices.length, 0);
});
test("optional force/subtitle context is explicit and strictly bounded", () => {
    const f = fixture(hash + "/1/7"); start(f);
    assert.equal(f.requests[0].body.force, true); assert.equal(f.requests[0].body.subtitle, 7);
    for (const suffix of ["/1/1025", "/2/7", "/1/007", "/1/-2", "/1/Infinity"]) {
        const invalid = fixture(hash + suffix); invalid.telemetry.start(value => assert.equal(value, null));
        assert.equal(invalid.requests.length, 0);
    }
});
test("ordinary progress coalesces while controls retain their separate observations", () => {
    const f = fixture(); start(f); f.tick(2000); sample(f, 1); f.requests.at(-1).respond(200, {});
    const count = f.requests.length;
    for (const pos of [3, 5, 7]) { f.tick(2000); sample(f, pos); }
    assert.equal(f.requests.length, count);
    f.telemetry.handleEvent({ event: "video:seek", data: { state: 2, position: 7, duration: 30 }, position: 12 });
    const rows = f.requests.at(-1).body.observations;
    assert.equal(rows.length, 2); assert.equal(rows[0].data.position, 7); assert.equal(rows[1].target, 12);
});
test("nonfinite or coerced public data never becomes a numeric position", () => {
    const f = fixture(); start(f); f.tick(2000);
    f.samples.at(-1)({ video: { info: { properties: { "portal:playback": "p".repeat(32) } }, data: { state: 2, duration: 30, position: "8" } } });
    assert.equal(f.requests.length, 2);
    f.telemetry.handleEvent({ event: "video:seek", position: Infinity, data: { state: 2, position: NaN, duration: Infinity, speed: -1, ended: "true" } });
    const row = f.requests.at(-1).body.observations[0];
    assert.deepEqual(row.data, { state: 2 }); assert.equal("target" in row, false);
});
test("late callbacks cannot defeat elapsed deadlines when browser timers are delayed", () => {
    const f = fixture(); start(f); f.tick(2000); f.jump(6000); sample(f, 10);
    assert.equal(f.requests.length, 2);
    const lateStart = fixture(); let result = "pending";
    lateStart.telemetry.start(value => { result = value; }); lateStart.jump(18000);
    lateStart.requests[0].respond(200, { grant: "g".repeat(43), playback_id: "p".repeat(32), url: "https://media.test/original", expires_in: 28800 });
    assert.equal(result, null);
});
test("expiry bounds the client even when delayed timers have not executed", () => {
    const f = fixture(); start(f); f.jump(28800001);
    f.telemetry.handleEvent({ event: "video:play", data: { state: 3, position: 8, duration: 30 } });
    assert.equal(f.requests.length, 2);
    f.telemetry.dispose(); assert.equal(f.timers.size, 0);
});
test("native resolver returns a generation property and uses documented interaction action", () => {
    const f = fixture(); let page;
    f.handler.handleRequest("init", null, value => { page = value; });
    assert.equal(page.items[0].action, "video:resolve:request:interaction:portal-video");
    start(f, false);
    for (const name of ["video:pause", "video:seek", "video:stop", "app:suspend"]) {
        f.telemetry.handleEvent({ event: name, position: 10, data: { state: 2, duration: 30, position: 7 } });
    }
    assert.equal(f.requests.length, 1);
    f.tick(2000); sample(f, 1);
    assert.equal(f.requests.length, 2);
    f.requests.at(-1).respond(200, {});
    f.telemetry.handleEvent({ event: "video:pause", data: { state: 2, duration: 30, position: 1 } });
    assert.equal(f.requests.at(-1).body.observations[0].name, "video:pause");
});
test("a different loaded generation disables controls and cannot copy ended data", () => {
    const f = fixture(); start(f); const before = f.requests.length;
    f.telemetry.handleEvent({ event: "video:load", info: { properties: { "portal:playback": "other" } }, data: { state: 2, duration: 30, position: 30, ended: true } });
    f.telemetry.handleEvent({ event: "video:stop", data: { state: 2, duration: 30, position: 30, ended: true } });
    assert.equal(f.requests.length, before);
    f.tick(2000);
    f.samples.at(-1)({ video: { info: { properties: { "portal:playback": "other" } }, data: { state: 2, duration: 30, position: 10 } } });
    assert.equal(f.requests.length, before);
});
test("replay requires a new property even when item, source and numeric state match", () => {
    const f = fixture(); start(f); f.tick(2000); const stale = f.samples.at(-1);
    start(f, false, "q".repeat(32)); const before = f.requests.length;
    stale({ video: { info: { properties: { "portal:playback": "p".repeat(32) } }, data: { state: 2, position: 7, duration: 30 } } });
    f.tick(2000); sample(f, 7);
    f.telemetry.handleEvent({ event: "video:stop", data: { state: 2, position: 7, duration: 30 } });
    assert.equal(f.requests.length, before);
    f.tick(2000);
    f.samples.at(-1)({ video: { info: { properties: { "portal:playback": "q".repeat(32) } }, data: { state: 2, position: 7, duration: 30 } } });
    assert.equal(f.requests.at(-1).body.playback_id, "q".repeat(32));
});
test("missing generation property cannot renew fresh numeric samples or lease", () => {
    const f = fixture(); start(f, false);
    for (let i = 0; i < 24; i++) {
        f.tick(2000);
        if (f.samples.length) f.samples.at(-1)({ video: { data: { state: 2, position: i, duration: 30 } } });
    }
    f.tick(10000); assert.equal(f.requests.length, 1); assert.equal(f.timers.size, 0);
});
test("Stop during an upload backoff preserves bounded terminal retry", () => {
    const f = fixture(); start(f); f.tick(2000);
    f.telemetry.handleEvent({ event: "video:pause", data: { state: 2, position: 7, duration: 30 } });
    f.requests.at(-1).onerror();
    f.telemetry.handleEvent({ event: "video:stop", data: { state: 3, position: 7, duration: 30 } });
    sample(f, 0, 1, { duration: 0 });
    const count = f.requests.length;
    f.tick(999); assert.equal(f.requests.length, count); f.tick(1);
    assert.equal(f.requests.at(-1).body.observations.at(-1).name, "video:stop");
    f.requests.at(-1).respond(200, {}); f.tick(60000);
    assert.equal(f.timers.size, 0); assert.equal(f.samples.length, 1);
});
test("late old Stop cannot terminate a current marked playing generation", () => {
    const f = fixture(); start(f);
    f.telemetry.handleEvent({ event: "video:stop", data: { state: 2, position: 29, duration: 30 } });
    assert.equal(f.requests.length, 2);
    for (const pos of [1, 3, 5, 7]) {
        f.tick(2000); sample(f, pos);
        if (f.requests.at(-1).url === "/api/playback/observations") f.requests.at(-1).respond(200, {});
    }
    const rows = f.requests.filter(req => req.body.observations).flatMap(req => req.body.observations);
    assert.equal(rows.some(row => row.name === "video:stop"), false);
    assert.equal(rows.some(row => row.kind === "snapshot" && row.data.position === 5), true);
    assert.equal(f.samples.length, 4); assert.ok(f.timers.size > 0);
});
test("Stop whose player loses generation info falls back to lease, never reset zero", () => {
    const f = fixture(); start(f);
    f.telemetry.handleEvent({ event: "video:stop", data: { state: 2, position: 7, duration: 30 } });
    for (let i = 0; i < 24; i++) {
        f.tick(2000);
        if (f.samples.length) f.samples.at(-1)({ video: { info: {}, data: { state: 1, position: 0, duration: 0 } } });
    }
    f.tick(10000); assert.equal(f.requests.length, 2); assert.equal(f.timers.size, 0);
});
test("generation-marked ended snapshots remain observations even in stopped state", () => {
    const f = fixture(); start(f); f.tick(2000); sample(f, 30, 1, { ended: true });
    const row = f.requests.at(-1).body.observations[0];
    assert.equal(row.kind, "snapshot"); assert.equal(row.data.ended, true); assert.equal(row.data.position, 30);
});
test("fresh marked ended evidence uploads immediately within the progress coalescing window", () => {
    const f = fixture(); start(f); f.tick(2000); sample(f, 28);
    f.requests.at(-1).respond(200, {}); const before = f.requests.length;
    f.tick(2000); sample(f, 30, 1, { ended: true });
    assert.equal(f.requests.length, before + 1);
    const row = f.requests.at(-1).body.observations.at(-1);
    assert.equal(row.kind, "snapshot"); assert.equal(row.data.ended, true); assert.equal(row.data.position, 30);
});
