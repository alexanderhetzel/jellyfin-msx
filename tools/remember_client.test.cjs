"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {Client, key} = require("../src/jellyfin_msx/templates/remember.js");
const old = "a".repeat(43), next = "b".repeat(43), session = "c".repeat(43);
const raw = (renewal = old, generation = 2) => JSON.stringify({schema:1, renewal, generation, expires:2000});
function lab(initial = null) {
    const state = {value:initial, pages:[], requests:[], writes:0, silent:false};
    const storage = {isReady:()=>true, get:()=>state.value,
        set:(_,value)=>{state.writes++; if (!state.silent) state.value=value;},
        remove:()=>{state.value=null;}};
    state.client = new Client({origin:"https://portal.test", now:()=>1000,
        storage:()=>storage, render:p=>state.pages.push(p),
        request:(method,path,body,callback)=>state.requests.push({method,path,body,callback})});
    state.reply = (data,error=null) => state.requests.shift().callback(error,data);
    return state;
}
test("new generation must be written and exactly verified before library request",()=>{
    const x=lab(raw()); x.client.run("boot");
    assert.equal(x.requests[0].path,"/api/device-authorization/renew");
    x.reply({renewal:next,generation:3,expires:2000,session});
    assert.equal(x.value,raw(next,3)); assert.equal(x.writes,1);
    assert.equal(x.requests[0].path,"/msx/device/"+session+"/home.json");
    x.reply({headline:"Jellyfin libraries",items:[]});
    assert.equal(x.pages.at(-1).headline,"Jellyfin libraries");
    assert(!JSON.stringify(x.pages).includes(next));
});
test("silent storage no-op never opens libraries and cleans fresh authority",()=>{
    const x=lab(raw()); x.silent=true; x.client.run("boot");
    x.reply({renewal:next,generation:3,expires:2000,session});
    assert.equal(x.value,raw());
    assert(x.requests.every(r=>!r.path.endsWith("home.json")));
    assert(x.requests[0].path.endsWith("logout.json"));
    assert.equal(x.pages.at(-1).headline,"Remembered sign-in unavailable");
});
test("new response cannot reuse old value or skip generation",()=>{
    for (const auth of [{renewal:old,generation:3},{renewal:next,generation:2},{renewal:next,generation:4}]) {
        const x=lab(raw()); x.client.run("boot");
        x.reply({...auth,session,expires:2000});
        assert.equal(x.writes,0); assert.equal(x.value,raw());
        assert(x.requests.every(r=>!r.path.endsWith("home.json")));
    }
});
test("timeout preserves record and prevents silent same-instance renewal retry",()=>{
    const x=lab(raw()); x.client.run("boot"); x.reply(null,{status:0});
    assert.equal(x.value,raw()); assert.equal(x.requests.length,0);
    x.client.run("boot"); assert.equal(x.requests.length,0);
});
test("losing context must not delete or overwrite winner's changed record",()=>{
    for (const deny of [true,false]) {
        const x=lab(raw()); x.client.run("boot"); x.value=raw(next,3);
        if (deny) x.reply(null,{status:401});
        else x.reply({renewal:"d".repeat(43),generation:3,expires:2000,session});
        assert.equal(x.value,raw(next,3)); assert.equal(x.writes,0);
        assert(x.requests.every(r=>!r.path.endsWith("home.json")));
    }
});
test("definitive unchanged rejection removes only stale owned record",()=>{
    const x=lab(raw()); x.client.run("boot"); x.reply(null,{status:401});
    assert.equal(x.value,null); assert.equal(x.requests.length,0);
});
test("early losing denial can safely force winner to re-pair",()=>{
    const x=lab(raw()); x.client.run("boot");
    x.value=null; // Another context removed the still-old record after a definitive 401.
    x.reply({renewal:next,generation:3,expires:2000,session});
    assert.equal(x.value,null); assert.equal(x.writes,0);
    assert(x.requests[0].path.endsWith("logout.json"));
    assert(x.requests.every(r=>!r.path.endsWith("home.json")));
});
test("malformed or expired local state never dispatches renewal",()=>{
    for (const value of ["bad", "{}", JSON.stringify({schema:1,renewal:old,generation:1,expires:999})]) {
        const x=lab(value); x.client.run("boot");
        assert.equal(x.requests.length,0); assert.equal(x.value,value);
    }
});
test("missing record starts ordinary pending pair and Continue waits for authentication",()=>{
    const x=lab(); x.client.run("boot");
    assert.equal(x.requests[0].path,"/api/device-authorization/pair");
    const pair = {headline:"Pair this TV",pages:[{items:[{title:"Continue after pairing",
        action:"content:https://portal.test/msx/device/"+session+"/pairing.json"}]}]};
    x.reply({session,page:pair});
    assert.equal(x.pages.at(-1).pages[0].items[0].action,"interaction:commit");
    x.client.run("continue");
    x.reply({paired:false,page:{headline:"Waiting for pairing",items:[]}});
    assert.equal(x.requests.length,0); assert.equal(x.value,null);
    assert.equal(x.pages.at(-1).headline,"Waiting for pairing");
    x.client.run("continue"); x.reply({paired:true});
    assert.equal(x.requests[0].path,"/api/device-authorization/enroll");
    x.reply({renewal:next,generation:0,expires:2000});
    assert.equal(x.value,raw(next,0));
    assert(x.requests[0].path.endsWith("home.json"));
});
test("singleflight ignores duplicate controls and ownership has no background renew",()=>{
    const x=lab(raw()); x.client.run("boot"); x.client.run("boot"); x.client.run("pair");
    assert.equal(x.requests.length,1);
    x.reply({renewal:next,generation:3,expires:2000,session});
    x.reply({headline:"Jellyfin libraries",items:[]});
    assert.equal(x.requests.length,0); assert.equal(key,"jellyfin-msx.authorization.v1");
});
test("malformed pending page leaves usable recovery instead of throwing",()=>{
    const x=lab(); x.client.run("boot"); x.reply({session,page:{headline:"Pair",items:[]}});
    x.client.run("continue"); x.reply({paired:false,page:null});
    assert.equal(x.pages.at(-1).headline,"Remembered sign-in unavailable");
    assert.equal(x.client.busy,false);
});
test("browser adapter readiness and duplicate XHR callbacks remain bounded",()=>{
    const vm=require("node:vm"), fs=require("node:fs");
    let handler; const requests=[], pages=[];
    class XHR {
        open(method,path){this.path=path; this.status=200;}
        setRequestHeader(){}
        send(){requests.push(this);}
    }
    const scope={window:{location:{origin:"https://portal.test"}}, Date:{now:()=>1000000},
        XMLHttpRequest:XHR, setTimeout:()=>{throw new Error("unexpected retry");},
        TVXPluginTools:{onReady:fn=>fn()},
        TVXServices:{storage:{isReady:()=>true,get:()=>null}},
        TVXInteractionPlugin:{setupHandler:h=>{handler=h;}, init:()=>handler.ready(),
            showContent:value=>pages.push(value)}};
    vm.runInNewContext(fs.readFileSync(require.resolve("../src/jellyfin_msx/templates/remember.js"),"utf8"),scope);
    assert.equal(requests.length,1); handler.ready(); assert.equal(requests.length,1);
    requests[0].responseText=JSON.stringify({session,page:{headline:"Pair",items:[]}});
    requests[0].onload(); const count=pages.length;
    requests[0].onload(); requests[0].onerror(); assert.equal(pages.length,count);
});
