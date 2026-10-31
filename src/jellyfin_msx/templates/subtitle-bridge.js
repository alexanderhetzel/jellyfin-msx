(function () {
    "use strict";
    var counts = { init: 0, video: 0, subtitle: 0, unknown: 0, subtitleFetch: 0, subtitleOk: 0, subtitleDenied: 0, subtitleOther: 0, subtitleUrlCallback: 0, subtitleNullCallback: 0 };
    function count(kind) {
        counts[kind] = Math.min(65535, counts[kind] + 1);
        var output = document.getElementById("subtitle-diagnostics");
        if (output) { output.textContent = JSON.stringify(counts); }
    }
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
        if (index !== undefined) { count("subtitleFetch"); }
        xhr.timeout = 18000;
        var settled = false;
        function isCurrent() {
            var current = context();
            return current && current.secret === ctx.secret && current.item === ctx.item && current.source === ctx.source;
        }
        function finish(value) {
            if (!isCurrent()) { value = null; }
            if (!settled) {
                settled = true;
                if (index !== undefined) { count(value ? "subtitleUrlCallback" : "subtitleNullCallback"); }
                callback(value);
            }
        }
        function failure() {
            if (settled) { return; }
            if (!isCurrent()) { finish(null); return; }
            finish(null);
            if (!isCurrent()) { return; }
            TVXInteractionPlugin.info("Subtitles unavailable. Select Off or Stop and reopen details.", false, true);
            var recovery = {
                type: "list", headline: "Subtitles unavailable", cache: false, reuse: false,
                template: { type: "default", layout: "0,0,8,1", color: "msx-glass" },
                items: [
                    { title: "Session expired or track unavailable", action: "info:Choose Off, or Stop and reopen details. Pair again if the session expired." },
                    { title: "Subtitle choices (choose Off)", action: "panel:request:player:subtitle" },
                    { title: "Stop playback", action: "player:stop" }
                ]
            };
            if (index !== undefined) {
                TVXInteractionPlugin.showPanel(recovery);
            } else {
                TVXInteractionPlugin.executeAction("player:stop");
                recovery.headline = "Playback unavailable";
                recovery.template.layout = "0,0,12,1";
                recovery.items = [
                    { title: "Session expired or video unavailable", action: "info:Pair again or reopen the item details to retry. No conversion was requested." },
                    { title: "Pair again", action: "content:" + window.location.origin + "/msx/pair.json" },
                    { title: "Back", action: "back" }
                ];
                TVXInteractionPlugin.showContent(recovery);
            }
        }
        xhr.onerror = failure;
        xhr.ontimeout = failure;
        xhr.onload = function () {
            try {
                if (index !== undefined) { count(xhr.status === 200 ? "subtitleOk" : xhr.status === 401 || xhr.status === 403 ? "subtitleDenied" : "subtitleOther"); }
                if (!isCurrent()) { finish(null); return; }
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
                if (id === "init") { count("init"); load("subtitle-playback.json", callback, false); }
                else if (id === "portal-video" || id === "video:portal-video") { count("video"); load("play.json", callback, true); }
                else if (subtitle && Number(subtitle[1]) <= 10000) { count("subtitle"); load(null, callback, false, Number(subtitle[1])); }
                else { count("unknown"); callback(null); }
            }
        });
        TVXInteractionPlugin.init();
    });
}());
