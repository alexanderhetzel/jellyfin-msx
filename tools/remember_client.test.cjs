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

function browserLab(initial = raw()) {
    const vm=require("node:vm"), fs=require("node:fs");
    let handler, sdkReady, timerId=0;
    const timers=new Map(), state={value:initial,requests:[],pages:[],replies:[],now:1000000,silent:false,storageReady:true};
    class XHR {
        open(method,path){this.path=path;this.status=200;}
        setRequestHeader(){}
        send(){state.requests.push(this);}
    }
    const scope={window:{location:{origin:"https://portal.test"}},Date:{now:()=>state.now},
        XMLHttpRequest:XHR,setTimeout:(fn,delay)=>{timers.set(++timerId,{fn,at:state.now+delay});return timerId;},
        clearTimeout:id=>timers.delete(id),TVXPluginTools:{onReady:fn=>{sdkReady=fn;}},
        TVXServices:{storage:{isReady:()=>state.storageReady,get:()=>state.value,
            set:(_,v)=>{if(!state.silent)state.value=v;},remove:()=>{state.value=null;}}},
        TVXInteractionPlugin:{setupHandler:h=>{handler=h;},init:()=>{},showContent:p=>state.pages.push(p)}};
    vm.runInNewContext(fs.readFileSync(require.resolve("../src/jellyfin_msx/templates/remember.js"),"utf8"),scope);
    state.sdk=()=>sdkReady(); state.ready=()=>handler.ready();
    state.request=id=>handler.handleRequest(id,null,p=>state.replies.push(p));
    state.init=()=>state.request("init");
    state.control=operation=>handler.handleData({data:{operation}});
    state.reply=(value)=>{const r=state.requests.shift();r.responseText=JSON.stringify(value);r.onload();return r;};
    state.tick=ms=>{const until=state.now+ms; for(;;){const due=[...timers.entries()].filter(([,t])=>t.at<=until).sort((a,b)=>a[1].at-b[1].at)[0];if(!due)break;state.now=due[1].at;timers.delete(due[0]);due[1].fn();}state.now=until;};
    return state;
}

test("init returns one terminal page only after renewal save and home, never progress",()=>{
    const x=browserLab(); x.sdk(); x.ready(); x.init();
    assert.equal(x.requests.length,1); assert.equal(x.replies.length,0);
    assert.equal(x.pages.length,0);
    x.reply({renewal:next,generation:3,expires:2000,session});
    assert.equal(x.value,raw(next,3)); assert.equal(x.replies.length,0);
    const last=x.reply({headline:"Jellyfin libraries",items:[]});
    assert.equal(x.replies.length,1); assert.equal(x.replies[0].headline,"Jellyfin libraries");
    last.onload(); assert.equal(x.replies.length,1); assert.equal(x.pages.length,0);
});

test("delayed SDK readiness and concurrent init cannot dispatch duplicate renewal",()=>{
    const x=browserLab(); x.sdk(); x.init(); x.init();
    assert.equal(x.requests.length,0); assert.equal(x.replies.length,1);assert.equal(x.replies[0],null);
    x.ready(); x.ready(); assert.equal(x.requests.length,1);
});

test("init save failure responds with recovery without requesting libraries",()=>{
    const x=browserLab();x.silent=true;x.sdk();x.ready();x.init();
    x.reply({renewal:next,generation:3,expires:2000,session});
    assert.equal(x.replies.length,1);assert.equal(x.replies[0].headline,"Remembered sign-in unavailable");
    assert(x.requests.every(r=>!r.path.endsWith("home.json")));
});

test("aggregate init timeout settles once and late renewal cannot save or navigate",()=>{
    const x=browserLab();x.sdk();x.ready();x.init();x.tick(25000);
    assert.equal(x.replies.length,1);assert.equal(x.replies[0].headline,"Remembered sign-in unavailable");
    x.reply({renewal:next,generation:3,expires:2000,session});
    assert.equal(x.value,raw());assert.equal(x.requests.length,0);assert.equal(x.pages.length,0);
    x.init();assert.equal(x.requests.length,0);assert.equal(x.replies.length,2);
});

test("deadline after save suppresses late home and unknown IDs never disclose the page",()=>{
    const x=browserLab();x.sdk();x.ready();x.init();
    x.reply({renewal:next,generation:3,expires:2000,session});x.tick(25000);
    assert.equal(x.replies.length,1);
    x.reply({headline:"Jellyfin libraries",items:[]});
    assert.equal(x.replies.length,1);assert.equal(x.pages.length,0);
    x.request("unknown");assert.equal(x.replies.at(-1),null);assert.equal(x.requests.length,0);
});

test("missing SDK or storage readiness cannot leave init hanging or start late renewal",()=>{
    for(const missing of ["sdk","storage"]){
        const x=browserLab();x.sdk();if(missing==="storage"){x.storageReady=false;x.ready();}
        x.init();x.control("pair");assert.equal(x.requests.length,0);
        x.tick(missing==="sdk"?25000:5000);
        assert.equal(x.replies.length,1);assert.equal(x.replies[0].headline,"Remembered sign-in unavailable");
        x.storageReady=true;x.ready();assert.equal(x.requests.length,0);
    }
});

test("later explicit init refreshes authority while controls still render normally",()=>{
    const x=browserLab();x.sdk();x.ready();x.init();
    x.reply({renewal:next,generation:3,expires:2000,session});x.reply({headline:"Jellyfin libraries",items:[]});
    x.init();assert.equal(x.requests.length,1);assert.equal(x.replies.length,1);
    x.reply({renewal:"d".repeat(43),generation:4,expires:2000,session});x.reply({headline:"Jellyfin libraries",items:[]});
    x.control("home");x.reply({headline:"Jellyfin libraries",items:[]});assert.equal(x.pages.length,2);
    assert.equal(x.replies.length,2);
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
        XMLHttpRequest:XHR, setTimeout:()=>1, clearTimeout:()=>{},
        TVXPluginTools:{onReady:fn=>fn()},
        TVXServices:{storage:{isReady:()=>true,get:()=>null}},
        TVXInteractionPlugin:{setupHandler:h=>{handler=h;}, init:()=>handler.ready(),
            showContent:value=>pages.push(value)}};
    vm.runInNewContext(fs.readFileSync(require.resolve("../src/jellyfin_msx/templates/remember.js"),"utf8"),scope);
    assert.equal(requests.length,0); handler.handleRequest("init",null,p=>pages.push(p));
    assert.equal(requests.length,1); handler.ready(); assert.equal(requests.length,1);
    requests[0].responseText=JSON.stringify({session,page:{headline:"Pair",items:[]}});
    requests[0].onload(); const count=pages.length;
    requests[0].onload(); requests[0].onerror(); assert.equal(pages.length,count);
});

test("RAM-only lifecycle flags follow actual delayed adapter boundaries without values",()=>{
    const vm=require("node:vm"), fs=require("node:fs");
    let sdkReady, handler, initialized=false;
    const attributes={"data-jellyfin-msx-lifecycle":"1"}, exposed=[], requests=[];
    class XHR { open(){} setRequestHeader(){} send(){requests.push(this);} }
    const scope={window:{location:{origin:"https://portal.test"}}, Date:{now:()=>1000000},
        document:{documentElement:{setAttribute:(name,value)=>{
            assert.equal(name,"data-jellyfin-msx-lifecycle");
            assert.match(value,/^\d+$/); attributes[name]=value; exposed.push(value);
        }}}, XMLHttpRequest:XHR, setTimeout:()=>1, clearTimeout:()=>{},
        TVXPluginTools:{onReady:fn=>{sdkReady=fn;}},
        TVXServices:{storage:{isReady:()=>true,get:()=>raw()}},
        TVXInteractionPlugin:{setupHandler:h=>{handler=h;}, init:()=>{initialized=true;},
            showContent:()=>{}}};
    vm.runInNewContext(fs.readFileSync(require.resolve("../src/jellyfin_msx/templates/remember.js"),"utf8"),scope);
    assert.equal(attributes["data-jellyfin-msx-lifecycle"],"3");
    assert.equal(requests.length,0); assert.equal(initialized,false);
    sdkReady();
    assert.equal(attributes["data-jellyfin-msx-lifecycle"],"15");
    assert.equal(initialized,true); assert.equal(requests.length,0);
    handler.ready();
    assert.equal(attributes["data-jellyfin-msx-lifecycle"],"31");
    assert.equal(requests.length,0);
    handler.handleRequest("init",null,()=>{});
    assert.equal(attributes["data-jellyfin-msx-lifecycle"],"63");
    assert.equal(requests.length,1);
    assert(!JSON.stringify(exposed).includes(old));
    handler.ready(); assert.equal(requests.length,1);
});
