/* Independently authored public-MS​​X API client. Never log authorization state. */
(function () {
    "use strict";
    var KEY = "jellyfin-msx.authorization.v1";
    var SECRET = /^[A-Za-z0-9_-]{43}$/;

    function page(headline, items) {
        return {type: "list", headline: headline, cache: false, reuse: false, restore: false,
            template: {type: "default", layout: "0,0,12,1"}, items: items};
    }
    function control(title, operation) {
        return {title: title, action: "interaction:commit", data: {operation: operation}};
    }
    function validPage(value) {
        return value && typeof value === "object" && typeof value.headline === "string" &&
            (Array.isArray(value.items) || Array.isArray(value.pages));
    }
    function Client(deps) {
        this.deps = deps;
        this.busy = false;
        this.started = false;
        this.blocked = false;
        this.pending = null;
        this.session = null;
        this.last = page("Opening Jellyfin", [control("Check device memory", "boot")]);
    }
    Client.prototype.show = function (value) {
        this.last = value;
        this.deps.render(value);
    };
    Client.prototype.raw = function () {
        var storage = this.deps.storage();
        if (!storage || !storage.isReady()) { throw new Error("memory"); }
        var value = storage.get(KEY, null);
        if (value !== null && (typeof value !== "string" || value.length > 2048)) {
            throw new Error("memory");
        }
        return value;
    };
    Client.prototype.record = function (raw) {
        var value = JSON.parse(raw);
        if (!value || Object.keys(value).sort().join(",") !== "expires,generation,renewal,schema" ||
                value.schema !== 1 || typeof value.renewal !== "string" || !SECRET.test(value.renewal) ||
                typeof value.generation !== "number" || value.generation < 0 ||
                Math.floor(value.generation) !== value.generation || value.generation > 1000000000 ||
                typeof value.expires !== "number" || !isFinite(value.expires) ||
                value.expires <= this.deps.now()) { throw new Error("record"); }
        return value;
    };
    Client.prototype.recovery = function (message, retryHome) {
        this.busy = false;
        var items = [{title: message, action: "info:" + message}];
        if (retryHome && this.session) { items.push(control("Retry libraries", "home")); }
        items.push(control("Create new code", "pair"));
        items.push({title: "Pair without remembering", action: "content:" + this.deps.origin + "/msx/pair.json"});
        this.show(page("Remembered sign-in unavailable", items));
    };
    Client.prototype.unchanged = function (before) {
        try { return this.raw() === before; } catch (ignore) { return false; }
    };
    Client.prototype.remove = function (before) {
        if (this.raw() !== before) { throw new Error("conflict"); }
        this.deps.storage().remove(KEY);
        if (this.raw() !== null) { throw new Error("memory"); }
    };
    Client.prototype.cleanup = function (session) {
        // Best effort only; server authorization/generation checks still apply.
        if (typeof session === "string" && SECRET.test(session)) {
            this.deps.request("GET", "/msx/device/" + session + "/logout.json", null, function () {});
        }
    };
    Client.prototype.save = function (auth, before, expectedGeneration) {
        var previous = before === null ? null : this.record(before);
        if (!auth || typeof auth.renewal !== "string" || !SECRET.test(auth.renewal) ||
                auth.generation !== expectedGeneration ||
                (previous && previous.renewal === auth.renewal)) { throw new Error("response"); }
        var next = {schema: 1, renewal: auth.renewal, generation: auth.generation, expires: auth.expires};
        var encoded = JSON.stringify(next);
        this.record(encoded);
        if (this.raw() !== before) { throw new Error("conflict"); }
        this.deps.storage().set(KEY, encoded);
        // Presence is insufficient: verify the exact new value AND its generation privately.
        if (this.raw() !== encoded || this.record(this.raw()).generation !== expectedGeneration) {
            throw new Error("memory");
        }
    };
    Client.prototype.home = function () {
        var self = this;
        if (!this.session || !SECRET.test(this.session)) {
            this.recovery("Sign in again to open your libraries."); return;
        }
        this.deps.request("GET", "/msx/device/" + this.session + "/home.json", null, function (error, data) {
            self.busy = false;
            if (error || !validPage(data) || data.response) {
                self.recovery("Libraries could not be loaded. Retry or pair again.", true); return;
            }
            self.pending = null;
            self.show(data);
            // No background renewal, observers or claim of permanent interaction ownership.
        });
    };
    Client.prototype.pairPage = function (value) {
        if (!validPage(value)) {
            this.recovery("Pairing information could not be loaded. Create a new code."); return;
        }
        var self = this;
        function rewrite(items) {
            (items || []).forEach(function (item) {
                if (item.action === "content:" + self.deps.origin + "/msx/device/" + self.pending + "/pairing.json") {
                    item.action = "interaction:commit"; item.data = {operation: "continue"};
                } else if (item.action === "content:" + self.deps.origin + "/msx/pair.json") {
                    item.action = "interaction:commit"; item.data = {operation: "pair"};
                }
            });
        }
        rewrite(value.items);
        (value.pages || []).forEach(function (entry) { rewrite(entry.items); });
        value.restore = false;
        this.busy = false;
        this.show(value);
    };
    Client.prototype.pair = function (explicit) {
        var self = this;
        try {
            var before = this.raw();
            if (explicit && before !== null) { this.remove(before); }
            if (!explicit && before !== null) { throw new Error("conflict"); }
        } catch (ignore) {
            this.recovery("Device memory could not be cleared. Pair without remembering."); return;
        }
        this.blocked = false;
        this.session = null;
        this.deps.request("POST", "/api/device-authorization/pair", {}, function (error, data) {
            if (error || !data || !SECRET.test(data.session) || !data.page) {
                self.recovery("Pairing could not be started. Try Create new code again."); return;
            }
            self.pending = data.session;
            self.pendingRaw = null;
            self.pairPage(data.page);
        });
    };
    Client.prototype.continuePair = function () {
        var self = this;
        if (!this.pending || !this.unchanged(this.pendingRaw)) {
            this.recovery("Another context changed sign-in. Reopen Jellyfin before continuing."); return;
        }
        this.deps.request("POST", "/api/device-authorization/status", {session: this.pending}, function (error, data) {
            if (error || !data || typeof data.paired !== "boolean") {
                self.recovery("Pairing expired or could not be checked. Create a new code."); return;
            }
            if (!data.paired) { self.pairPage(data.page); return; }
            self.deps.request("POST", "/api/device-authorization/enroll", {session: self.pending}, function (failure, auth) {
                if (failure) {
                    self.recovery("Sign-in could not be saved. Create a new code to re-pair."); return;
                }
                try { self.save(auth, self.pendingRaw, 0); }
                catch (ignore) {
                    self.cleanup(self.pending);
                    self.recovery("New sign-in was not verified in memory. Re-pair this context."); return;
                }
                self.session = self.pending;
                self.home();
            });
        });
    };
    Client.prototype.boot = function () {
        if (this.deps.onBoot) { this.deps.onBoot(); }
        var self = this, before, record;
        if (this.blocked) {
            this.recovery("A previous renewal was uncertain. Create a new code to re-pair."); return;
        }
        try {
            before = this.raw();
            if (before === null) { this.pair(false); return; }
            record = this.record(before);
        } catch (ignore) {
            this.recovery("Device memory is unavailable, expired or invalid. Re-pair this context."); return;
        }
        this.deps.request("POST", "/api/device-authorization/renew", {renewal: record.renewal}, function (error, auth) {
            if (error) {
                self.blocked = true;
                if (!self.unchanged(before)) {
                    self.recovery("Another context changed sign-in. Reopen Jellyfin."); return;
                }
                // Clear only this exact stale record after a definitive denial, never on timeout.
                if (error.status === 401) { try { self.remove(before); } catch (ignore) {} }
                self.recovery("Sign-in could not be restored. Create a new code to re-pair."); return;
            }
            try {
                if (!auth || typeof auth.session !== "string" || !SECRET.test(auth.session)) {
                    throw new Error("response");
                }
                self.save(auth, before, record.generation + 1);
            } catch (ignore) {
                self.blocked = true;
                self.cleanup(auth && auth.session);
                self.recovery("New sign-in was not verified in memory. Re-pair this context."); return;
            }
            self.session = auth.session;
            self.home();
        });
    };
    Client.prototype.run = function (operation) {
        if (this.busy || ["boot", "pair", "continue", "home"].indexOf(operation) < 0) { return; }
        this.busy = true;
        this.show(page("Opening Jellyfin", [{title: "Please wait", action: "info:Checking sign-in."}]));
        if (operation === "pair") { this.pair(true); }
        else if (operation === "continue") { this.continuePair(); }
        else if (operation === "home") { this.home(); }
        else { this.boot(); }
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {Client: Client, key: KEY};
        return;
    }
    // Fixed RAM-only boundary flags; never include authorization or context values.
    var lifecycle = 1;
    function mark(flag) {
        lifecycle |= flag;
        try { document.documentElement.setAttribute("data-jellyfin-msx-lifecycle", String(lifecycle)); }
        catch (ignore) {} // Diagnostics must not change authorization behavior.
    }
    mark(2);
    TVXPluginTools.onReady(function () {
        mark(4);
        var client = new Client({origin: window.location.origin,
            now: function () { return Date.now() / 1000; },
            storage: function () { return TVXServices.storage; },
            onBoot: function () { mark(32); },
            render: function (value) { mark(64); TVXInteractionPlugin.showContent(value); },
            request: function (method, path, data, callback) {
                var xhr = new XMLHttpRequest(), done = false;
                function complete(error, value) {
                    if (done) { return; } done = true; callback(error, value);
                }
                xhr.open(method, path, true);
                xhr.withCredentials = false;
                xhr.timeout = 15000;
                if (method === "POST") { xhr.setRequestHeader("Content-Type", "application/json"); }
                xhr.onload = function () {
                    if (xhr.status !== 200) { complete({status: xhr.status}); return; }
                    try {
                        if (xhr.responseText.length > 2000000) { throw new Error("response"); }
                        complete(null, JSON.parse(xhr.responseText));
                    } catch (ignore) { complete({status: 0}); }
                };
                xhr.onerror = xhr.ontimeout = xhr.onabort = function () { complete({status: 0}); };
                try { xhr.send(data === null ? null : JSON.stringify(data)); }
                catch (ignore) { complete({status: 0}); }
            }});
        TVXInteractionPlugin.setupHandler({
            init: function () {},
            ready: function () {
                mark(16);
                if (client.started) { return; } client.started = true;
                var attempts = 0;
                function start() {
                    var storage = TVXServices.storage, ready = false;
                    try { ready = storage && storage.isReady(); } catch (ignore) {}
                    if (ready) { client.run("boot"); }
                    else if (++attempts < 50) { setTimeout(start, 100); }
                    else { client.recovery("Device memory is unavailable. Pair without remembering."); }
                }
                start();
            },
            handleData: function (data) { client.run(data && data.data && data.data.operation); },
            handleRequest: function (id, data, callback) { callback(client.last); }
        });
        mark(8);
        TVXInteractionPlugin.init();
    });
}());
