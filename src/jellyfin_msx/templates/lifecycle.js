(function () {
    "use strict";
    var events = ["video:load", "video:play", "video:pause", "video:stop", "video:seek", "video:restart", "video:speed", "app:suspend", "app:resume", "app:sleep", "app:awake", "app:connect", "app:disconnect"];
    function context() {
        var match = window.location.hash.match(/^#([A-Za-z0-9_-]{43})\/([a-fA-F0-9-]{32,36})\/([a-fA-F0-9-]{32,36})(?:\/([01])\/(-1|0|[1-9][0-9]{0,3}))?$/);
        return match && (match[5] === undefined || Number(match[5]) <= 1024) ? { secret: match[1], item_id: match[2], media_source_id: match[3], force: match[4] === "1", subtitle: match[5] === undefined ? -1 : Number(match[5]), hash: window.location.hash } : null;
    }
    function numbers(input) {
        var result = {};
        ["state", "position", "duration", "speed"].forEach(function (key) {
            var value = input && input[key];
            if (typeof value === "number" && isFinite(value) && value >= 0 && value <= 864000) {
                result[key] = Math.round(value * 1000) / 1000;
            }
        });
        if (input && typeof input.ended === "boolean") { result.ended = input.ended; }
        return result;
    }
    function create() {
        var active = null, epoch = 0, starting = null;
        function matches(g, info) { return info && info.properties && info.properties["portal:playback"] === g.id; }
        function current(g) { return active === g && g.epoch === epoch && window.location.hash === g.hash && Date.now() < g.expires; }
        function stop(g) {
            clearTimeout(g.poll); clearTimeout(g.sampleDeadline);
            g.sampling = false; g.pending = false;
        }
        function abandon(g) {
            stop(g); clearTimeout(g.retry); clearTimeout(g.life); g.closed = true; g.queue = [];
            if (g.xhr) { g.xhr.abort(); g.xhr = null; }
        }
        function send(g) {
            if (!current(g) || g.closed || g.xhr || g.retry || !g.queue.length) { return; }
            var batch = g.queue.slice(0, 16), body;
            do {
                body = JSON.stringify({ version: 1, playback_id: g.id, observations: batch });
                if (body.length <= 8192) { break; }
                batch.pop();
            } while (batch.length);
            if (!batch.length) { abandon(g); return; }
            var xhr = new XMLHttpRequest(), settled = false;
            g.xhr = xhr;
            xhr.open("POST", "/api/playback/observations");
            xhr.timeout = 5000;
            xhr.setRequestHeader("Authorization", "Bearer " + g.grant);
            xhr.setRequestHeader("Content-Type", "application/json");
            function finish(ok, fatal) {
                if (settled) { return; } settled = true;
                if (!current(g) || g.closed) { return; }
                g.xhr = null;
                if (ok) {
                    var sent = batch.map(function (row) { return row.seq; });
                    g.queue = g.queue.filter(function (row) { return sent.indexOf(row.seq) < 0; });
                    g.retries = 0;
                    if (!g.sampling && !g.queue.length) { abandon(g); return; }
                    send(g);
                } else if (fatal || g.retries >= 3) { abandon(g); }
                else {
                    var delay = [1000, 2000, 4000][g.retries++];
                    g.retry = setTimeout(function () { g.retry = null; send(g); }, delay);
                }
            }
            xhr.onload = function () { finish(xhr.status === 200, xhr.status >= 400 && xhr.status < 500 && xhr.status !== 429); };
            xhr.onerror = function () { finish(false, false); };
            xhr.ontimeout = xhr.onerror;
            xhr.send(body);
        }
        function enqueue(g, kind, name, data, target) {
            if (!current(g) || g.closed || g.seq >= 1000000) { return; }
            var row = { seq: ++g.seq, ms: Math.min(86400000, Math.max(0, Date.now() - g.started)), kind: kind, name: name, data: numbers(data) };
            if (typeof target === "number" && isFinite(target) && target >= 0 && target <= 864000) { row.target = Math.round(target * 1000) / 1000; }
            if (kind === "snapshot" && row.data.ended !== true && Date.now() - g.lastProgress < 10000 && !g.reconcile) {
                // Retain one latest ordinary sample without replacing an in-flight payload.
                var inflight = g.xhr ? 16 : 0;
                for (var i = g.queue.length - 1; i >= inflight; i--) {
                    if (g.queue[i].kind === "snapshot") { g.queue.splice(i, 1); break; }
                }
                if (g.queue.length >= 64) { abandon(g); return; }
                g.queue.push(row);
                return;
            }
            if (g.queue.length >= 64) {
                var removable = -1;
                for (var j = g.xhr ? 16 : 0; j < g.queue.length; j++) { if (g.queue[j].kind === "snapshot") { removable = j; break; } }
                if (removable >= 0) { g.queue.splice(removable, 1); }
                else { abandon(g); return; }
            }
            g.queue.push(row);
            if (kind === "snapshot") { g.lastProgress = Date.now(); }
            send(g);
        }
        function sample(g) {
            if (!current(g)) { abandon(g); return; }
            if (g.closed || !g.sampling) { return; }
            if (Date.now() - g.lastFresh > 45000 || Date.now() - g.started > 28800000) { abandon(g); return; }
            var pending = true, requested = Date.now();
            g.sampleDeadline = setTimeout(function () {
                if (!pending) { return; } pending = false;
                g.poll = setTimeout(function () { sample(g); }, 2000);
            }, 5000);
            TVXInteractionPlugin.requestData("video", function (result) {
                if (!pending || !current(g) || g.closed || !g.sampling) { return; }
                pending = false; clearTimeout(g.sampleDeadline);
                if (Date.now() - requested >= 5000 || Date.now() - g.lastFresh > 45000) {
                    if (Date.now() - g.lastFresh > 45000) { abandon(g); }
                    else { g.poll = setTimeout(function () { sample(g); }, 2000); }
                    return;
                }
                var data = numbers(result && result.video && result.video.data);
                g.correlated = !!matches(g, result && result.video && result.video.info);
                if (g.stopUntil && Date.now() > g.stopUntil) { g.stopUntil = 0; }
                if (g.correlated && data.state === 1 && g.stopUntil) {
                    enqueue(g, "event", "video:stop", {});
                    stop(g);
                    return;
                }
                if (g.correlated && data.duration > 0 && data.position !== undefined && (data.state === 2 || data.state === 3 || data.ended === true)) {
                    g.lastFresh = Date.now();
                    enqueue(g, "snapshot", "video", data);
                    if (g.reconcile && Date.now() >= g.reconcile) { g.reconcile = 0; }
                }
                g.poll = setTimeout(function () { sample(g); }, 2000);
            });
        }
        return {
            start: function (callback) {
                var ctx = context();
                if (!ctx) { callback(null); return; }
                if (starting && starting.hash === ctx.hash) {
                    if (starting.callbacks.length < 4) { starting.callbacks.push(callback); } else { callback(null); }
                    return;
                }
                if (active) { abandon(active); }
                var requestEpoch = ++epoch, xhr = new XMLHttpRequest(), requested = Date.now();
                var request = { hash: ctx.hash, callbacks: [callback] }, settled = false;
                starting = request;
                xhr.open("POST", "/api/playback/start"); xhr.timeout = 18000;
                xhr.setRequestHeader("Authorization", "Bearer " + ctx.secret);
                xhr.setRequestHeader("Content-Type", "application/json");
                function finish(value) {
                    if (settled) { return; } settled = true;
                    if (requestEpoch !== epoch || window.location.hash !== ctx.hash) { value = null; }
                    if (starting === request) { starting = null; }
                    request.callbacks.forEach(function (fn) { fn(value); });
                }
                xhr.onerror = function () { finish(null); }; xhr.ontimeout = xhr.onerror;
                xhr.onload = function () {
                    try {
                        if (xhr.status !== 200 || xhr.responseText.length > 100000 || requestEpoch !== epoch || window.location.hash !== ctx.hash || Date.now() - requested >= 18000) { finish(null); return; }
                        var value = JSON.parse(xhr.responseText);
                        if (!value || !/^[A-Za-z0-9_-]{43}$/.test(value.grant) || typeof value.playback_id !== "string" || !/^[A-Za-z0-9_-]{16,64}$/.test(value.playback_id) || typeof value.url !== "string" || value.url.indexOf("https://") !== 0 || typeof value.expires_in !== "number" || !isFinite(value.expires_in) || value.expires_in <= 0 || value.expires_in > 28800) { finish(null); return; }
                        var now = Date.now();
                        active = { epoch: requestEpoch, hash: ctx.hash, id: value.playback_id, grant: value.grant, expectedURL: value.url, correlated: false, expires: now + value.expires_in * 1000, started: now, lastFresh: now, lastProgress: 0, seq: 0, queue: [], retries: 0, sampling: true, reconcile: 0, stopUntil: 0 };
                        var generation = active;
                        generation.life = setTimeout(function () { abandon(generation); }, value.expires_in * 1000);
                        finish({ url: value.url, properties: { "portal:playback": value.playback_id } });
                        generation.poll = setTimeout(function () { sample(generation); }, 2000);
                    } catch (error) { finish(null); }
                };
                xhr.send(JSON.stringify({ item_id: ctx.item_id, media_source_id: ctx.media_source_id, force: ctx.force, subtitle: ctx.subtitle }));
            },
            handleEvent: function (event) {
                var g = active;
                if (!g || !current(g) || g.closed || !event || events.indexOf(event.event) < 0) { return; }
                // Load's attached data is the previous video, never a sample of this generation.
                if (event.event === "video:load") {
                    if (!matches(g, event.info)) { g.correlated = false; return; }
                    g.correlated = true;
                } else if (!g.correlated) { return; }
                if (event.event === "video:stop") {
                    // Controls have no media identifier. Confirm Stop against a fresh,
                    // generation-marked stopped sample; stale playing samples cannot terminate it.
                    g.stopUntil = Date.now() + 5000;
                    g.reconcile = g.stopUntil;
                    return;
                }
                enqueue(g, "event", event.event, event.event === "video:load" ? {} : event.data, event.position);
                if (["video:pause", "video:play", "video:seek", "video:restart"].indexOf(event.event) >= 0) { g.reconcile = Date.now() + 5000; }
            },
            dispose: function () { ++epoch; if (active) { abandon(active); } }
        };
    }
    window.PortalLifecycle = { create: create };
    if (document.getElementById("lifecycle-owner")) {
        TVXPluginTools.onReady(function () {
            var telemetry = create();
            TVXInteractionPlugin.setupHandler({
                init: function () {}, ready: function () {}, handleData: function () {},
                handleEvent: telemetry.handleEvent,
                handleRequest: function (id, data, callback) {
                    if (id === "init") {
                        callback({ type: "list", cache: false, reuse: false, headline: "Playback", template: { type: "default", layout: "0,0,12,1" }, items: [
                            { title: "Play original", action: "video:resolve:request:interaction:portal-video", properties: { "trigger:complete": "player:stop", "button:next:enable": "false", "button:prev:enable": "false" } },
                            { title: "Back to details", action: "back" }
                        ] });
                    } else if (id === "portal-video" || id === "video:portal-video") {
                        telemetry.start(function (value) {
                            callback(value);
                            if (!value) { TVXInteractionPlugin.info("Playback unavailable. Reopen details or pair again.", false, true); }
                        });
                    } else { callback(null); }
                }
            });
            TVXInteractionPlugin.init();
        });
    }
}());
