(function () {
    "use strict";
    function context() {
        var match = window.location.hash.match(/^#([A-Za-z0-9_-]{43})\/([a-fA-F0-9-]{32,36})\/([a-fA-F0-9-]{32,36})$/);
        return match ? { secret: match[1], item: match[2], source: match[3] } : null;
    }
    function load(endpoint, callback, wrapped) {
        var ctx = context();
        if (!ctx) { callback(null); return; }
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "/msx/device/" + ctx.secret + "/" + endpoint + "?item_id=" + ctx.item + "&media_source_id=" + ctx.source);
        xhr.timeout = 18000;
        function failure() {
            TVXInteractionPlugin.info("Subtitles unavailable. Select Off or Stop and reopen details.", false, true);
            callback(null);
        }
        xhr.onerror = failure;
        xhr.ontimeout = failure;
        xhr.onload = function () {
            try {
                var current = context();
                if (!current || current.secret !== ctx.secret || current.item !== ctx.item || current.source !== ctx.source) { callback(null); return; }
                if (xhr.status !== 200 || xhr.responseText.length > 100000) { failure(); return; }
                var value = JSON.parse(xhr.responseText);
                if (wrapped) {
                    if (!value.response || value.response.status !== 200 || !value.response.data || typeof value.response.data.url !== "string") { failure(); return; }
                    callback(value.response.data);
                } else if (value && Array.isArray(value.items)) {
                    callback(value);
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
                if (id === "init") { load("subtitle-playback.json", callback, false); }
                else if (id === "portal-video" || id === "video:portal-video") { load("play.json", callback, true); }
                else { callback(null); }
            }
        });
        TVXInteractionPlugin.init();
    });
}());
