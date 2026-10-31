(function () {
    "use strict";
    function context() {
        var match = window.location.hash.match(/^#([A-Za-z0-9_-]{43})\/([a-fA-F0-9-]{32,36})\/([a-fA-F0-9-]{32,36})$/);
        return match ? { secret: match[1], item: match[2], source: match[3] } : null;
    }
    function load(endpoint, callback, wrapped, index) {
        var ctx = context();
        if (!ctx) { callback(null); return; }
        var xhr = new XMLHttpRequest();
        var resource = "/api/device/" + ctx.secret + "/subtitles/" + ctx.item + "/" + ctx.source + "/" + index + ".vtt";
        xhr.open("GET", index !== undefined ? resource : "/msx/device/" + ctx.secret + "/" + endpoint + "?item_id=" + ctx.item + "&media_source_id=" + ctx.source);
        xhr.timeout = 18000;
        var settled = false;
        function finish(value) {
            if (!settled) { settled = true; callback(value); }
        }
        function failure() {
            if (settled) { return; }
            TVXInteractionPlugin.info("Subtitles unavailable. Select Off or Stop and reopen details.", false, true);
            finish(null);
        }
        xhr.onerror = failure;
        xhr.ontimeout = failure;
        xhr.onload = function () {
            try {
                var current = context();
                if (!current || current.secret !== ctx.secret || current.item !== ctx.item || current.source !== ctx.source) { finish(null); return; }
                if (xhr.status !== 200 || xhr.responseText.length > (index !== undefined ? 1048576 : 100000)) { failure(); return; }
                if (index !== undefined) {
                    if ((xhr.getResponseHeader("Content-Type") || "").split(";")[0].toLowerCase() !== "text/vtt") { failure(); return; }
                    finish({ url: window.location.origin + resource });
                    return;
                }
                var value = JSON.parse(xhr.responseText);
                if (wrapped) {
                    if (!value.response || value.response.status !== 200 || !value.response.data || typeof value.response.data.url !== "string") { failure(); return; }
                    finish(value.response.data);
                } else if (value && Array.isArray(value.items)) {
                    finish(value);
                } else { failure(); }
            } catch (error) { failure(); }
        };
        xhr.send();
    }
    TVXPluginTools.onReady(function () {
        TVXInteractionPlugin.setupHandler({
            init: function () {}, ready: function () {}, handleEvent: function () {},
            handleData: function () {},
            handleRequest: function (id, data, callback) {
                var subtitle = typeof id === "string" ? id.match(/^(?:subtitle:)?portal-subtitle-(0|[1-9][0-9]{0,4})$/) : null;
                if (id === "init") { load("subtitle-playback.json", callback, false); }
                else if (id === "portal-video" || id === "video:portal-video") { load("play.json", callback, true); }
                else if (subtitle && Number(subtitle[1]) <= 10000) { load(null, callback, false, Number(subtitle[1])); }
                else { callback(null); }
            }
        });
        TVXInteractionPlugin.init();
    });
}());
