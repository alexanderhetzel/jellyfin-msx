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
    function create(onFailure) {
        var active = null, epoch = 0, starting = null, attempts = 0;
        function failed(category) { if (onFailure) { onFailure(category); } }
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
            remaining: function () { return Math.max(0, 3 - attempts); },
            start: function (callback, source) {
                var ctx = context();
                if (!ctx) { callback(null); return; }
                if (starting && starting.hash === ctx.hash) {
                    if (starting.source !== (source || ctx.media_source_id)) { callback(null); return; }
                    if (starting.callbacks.length < 4) { starting.callbacks.push(callback); } else { callback(null); }
                    return;
                }
                if (attempts >= 3) { callback(null); failed("attempt_limit"); return; }
                attempts++;
                if (active) { abandon(active); }
                var requestEpoch = ++epoch, xhr = new XMLHttpRequest(), requested = Date.now();
                var request = { hash: ctx.hash, source: source || ctx.media_source_id, callbacks: [callback] }, settled = false;
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
                request.cancel = function () { xhr.abort(); finish(null); };
                xhr.onerror = function () { finish(null); if (requestEpoch === epoch && window.location.hash === ctx.hash) { failed("portal_connectivity"); } };
                xhr.ontimeout = function () { finish(null); if (requestEpoch === epoch && window.location.hash === ctx.hash) { failed("portal_timeout"); } };
                xhr.onload = function () {
                    try {
                        if (requestEpoch !== epoch || window.location.hash !== ctx.hash) { finish(null); return; }
                        if (Date.now() - requested >= 18000) { finish(null); failed("portal_timeout"); return; }
                        if (xhr.status !== 200) {
                            var category = "request_failed";
                            if (xhr.responseText.length <= 100000) {
                                try {
                                    var error = JSON.parse(xhr.responseText);
                                    if (error && ["negotiation_denied", "upstream_timeout", "upstream_connectivity", "authorization", "request_limited", "request_timeout"].indexOf(error.category) >= 0) { category = error.category; }
                                } catch (ignore) {}
                            }
                            finish(null); failed(category); return;
                        }
                        if (xhr.responseText.length > 100000) { finish(null); failed("request_failed"); return; }
                        var value = JSON.parse(xhr.responseText);
                        if (!value || !/^[A-Za-z0-9_-]{43}$/.test(value.grant) || typeof value.playback_id !== "string" || !/^[A-Za-z0-9_-]{16,64}$/.test(value.playback_id) || typeof value.url !== "string" || value.url.indexOf("https://") !== 0 || typeof value.expires_in !== "number" || !isFinite(value.expires_in) || value.expires_in <= 0 || value.expires_in > 28800) { finish(null); failed("request_failed"); return; }
                        var now = Date.now();
                        active = { epoch: requestEpoch, hash: ctx.hash, id: value.playback_id, grant: value.grant, expectedURL: value.url, correlated: false, expires: now + value.expires_in * 1000, started: now, lastFresh: now, lastProgress: 0, seq: 0, queue: [], retries: 0, sampling: true, reconcile: 0, stopUntil: 0 };
                        var generation = active;
                        generation.life = setTimeout(function () { abandon(generation); }, value.expires_in * 1000);
                        finish({ url: value.url, properties: { "portal:playback": value.playback_id } });
                        generation.poll = setTimeout(function () { sample(generation); }, 2000);
                    } catch (error) { finish(null); failed("request_failed"); }
                };
                xhr.send(JSON.stringify({ item_id: ctx.item_id, media_source_id: source || ctx.media_source_id, force: source ? false : ctx.force, subtitle: source ? -1 : ctx.subtitle }));
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
            dispose: function () { ++epoch; if (starting && starting.cancel) { starting.cancel(); } starting = null; if (active) { abandon(active); } },
            reset: function () { this.dispose(); attempts = 0; }
        };
    }
    window.PortalLifecycle = { create: create };
    if (document.getElementById("lifecycle-owner")) {
        TVXPluginTools.onReady(function () {
            var alternatives = [], optionsKnown = false, optionsRequest = null, uiEpoch = 0, lastCategory = "native_unknown";
            var descriptions = {
                native_unknown: "Native playback cause unavailable. Pause or silence does not identify a decoder or network failure.",
                negotiation_denied: "Playback negotiation denied. Use an eligible stored copy; conversion remains disabled by default.",
                upstream_timeout: "The Jellyfin request timed out. Retry after the server responds again.",
                upstream_connectivity: "The Jellyfin network transport failed. Check server connectivity, then retry.",
                portal_timeout: "The portal request timed out. This does not identify a native player failure.",
                portal_connectivity: "The portal request failed to connect. Restore connectivity, then retry.",
                authorization: "Access denied or session expired. Return to details or pair again.",
                request_limited: "Too many requests. Wait before reopening details.",
                request_timeout: "The portal request deadline expired. Retry later.",
                request_failed: "Playback request failed. Return to details or retry later.",
                attempt_limit: "Three play attempts used. Reopen details to try again."
            };
            function playRow(title, id) {
                return { title: title, action: "video:resolve:request:interaction:" + id, properties: {
                    "trigger:complete": "player:stop", "button:next:enable": "false", "button:prev:enable": "false",
                    "button:content:icon": "refresh", "button:content:action": "content:request:interaction:recovery"
                } };
            }
            function page(recovery) {
                var items = telemetry.remaining() > 0 ? [playRow(recovery ? "Retry original" : "Play original", "portal-video")] : [{ title: "Play attempt limit reached", action: "info:" + descriptions.attempt_limit }];
                if (recovery) {
                    items.unshift({ title: "Playback: " + lastCategory.replace(/_/g, " "), action: "info:" + descriptions[lastCategory] });
                    if (telemetry.remaining() > 0) { alternatives.forEach(function (source, index) { items.push(playRow("Try compatible stored alternative " + (index + 1) + " (unverified)", "alternative-" + index)); }); }
                    if (!alternatives.length) { items.push(optionsKnown ? { title: "No eligible stored alternative available", action: "info:Reopen details after adding an eligible HD stored copy. No automatic conversion is requested." } : { title: "Stored alternatives could not be checked", action: "info:Choose Playback recovery again to check when connectivity returns." }); }
                }
                items.push({ title: "Playback recovery / stored alternatives", action: "content:request:interaction:recovery" });
                items.push({ title: "Stop playback", action: "player:stop" });
                items.push({ title: "Back to details", action: "execute:request:interaction:details" });
                return { type: "list", cache: false, reuse: false, headline: recovery ? "Playback recovery" : "Playback", template: { type: "default", layout: "0,0,12,1" }, items: items };
            }
            var telemetry = create(function (category) {
                lastCategory = category;
                TVXInteractionPlugin.showContent(page(true));
            });
            function leave() {
                uiEpoch++;
                telemetry.dispose();
                if (optionsRequest) { optionsRequest.abort(); optionsRequest = null; }
                alternatives = []; optionsKnown = false;
            }
            function recovery(callback) {
                var ctx = context();
                if (!ctx || optionsRequest) { callback(page(true)); return; }
                var xhr = new XMLHttpRequest(), settled = false, requested = Date.now(), requestEpoch = uiEpoch;
                optionsRequest = xhr;
                xhr.open("POST", "/api/playback/options"); xhr.timeout = 5000;
                xhr.setRequestHeader("Authorization", "Bearer " + ctx.secret);
                xhr.setRequestHeader("Content-Type", "application/json");
                function finish() {
                    if (settled) { return; } settled = true;
                    if (optionsRequest === xhr) { optionsRequest = null; }
                    if (requestEpoch !== uiEpoch || window.location.hash !== ctx.hash) { callback(null); return; }
                    callback(page(true));
                }
                xhr.onerror = function () { if (requestEpoch === uiEpoch && window.location.hash === ctx.hash) { alternatives = []; optionsKnown = false; } finish(); }; xhr.ontimeout = xhr.onerror;
                xhr.onabort = finish;
                xhr.onload = function () {
                    if (settled || requestEpoch !== uiEpoch || window.location.hash !== ctx.hash) { finish(); return; }
                    alternatives = [];
                    optionsKnown = false;
                    if (xhr.status === 200 && xhr.responseText.length <= 10000 && Date.now() - requested < 5000) {
                        try {
                            var value = JSON.parse(xhr.responseText);
                            if (value && Array.isArray(value.alternatives) && value.alternatives.length <= 8 && value.alternatives.every(function (id) { return typeof id === "string" && /^[a-fA-F0-9-]{32,36}$/.test(id) && id !== ctx.media_source_id; })) { alternatives = value.alternatives; optionsKnown = true; }
                        } catch (ignore) {}
                    }
                    finish();
                };
                xhr.send(JSON.stringify({ item_id: ctx.item_id, media_source_id: ctx.media_source_id }));
            }
            TVXInteractionPlugin.setupHandler({
                init: function () {}, ready: function () {}, handleData: function () {},
                handleEvent: telemetry.handleEvent,
                handleRequest: function (id, data, callback) {
                    if (id === "init") {
                        leave(); telemetry.reset(); lastCategory = "native_unknown";
                        callback(page(false));
                    } else if (id === "details") {
                        var ctx = context();
                        leave();
                        TVXInteractionPlugin.executeAction("player:stop");
                        callback(ctx ? { action: "content:" + window.location.origin + "/msx/device/" + ctx.secret + "/detail.json?item_id=" + ctx.item_id } : { action: "back" });
                    } else if (id === "recovery") {
                        recovery(callback);
                    } else if (id === "portal-video" || id === "video:portal-video" || /^(video:)?alternative-[0-7]$/.test(id)) {
                        var alternate = id.match(/alternative-([0-7])$/), source = alternate ? alternatives[Number(alternate[1])] : undefined;
                        if (alternate && !source) { callback(null); return; }
                        TVXInteractionPlugin.executeAction("player:stop");
                        telemetry.start(function (value) {
                            if (value) { lastCategory = "native_unknown"; }
                            callback(value);
                        }, source);
                    } else { callback(null); }
                }
            });
            TVXInteractionPlugin.init();
        });
    }
}());
