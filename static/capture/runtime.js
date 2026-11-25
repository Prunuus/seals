// Injected at the top of every proxied game page (see proxy.py), inside a function that also
// defines the game's result(res) from static/capture/<game>.js. result() returns null until the
// day's game is finished, then {num, details: [lines], streak?}. It's called after storage writes,
// DOM changes and every second with no argument, and with res = {url, req, json} after each
// fetch/XHR response. Each new result is posted to /__dgb/result, where the bot picks it up.
// Games that time themselves put it in r.secs; the rest get the solve timer below.
if (window.__dgb) return;
window.__dgb = true;

var realFetch = window.fetch.bind(window);
var lastSent = null, pending = null;

// Storage values, JSON-parsed when they're JSON.
function ls(key) {
  try {
    var v = localStorage.getItem(key);
    try { return JSON.parse(v); } catch (e) { return v; }
  } catch (e) { return null; }
}
// YYYY-MM-DD in a time zone (the player's own when tz is undefined).
function today(tz) { return new Intl.DateTimeFormat("en-CA", { timeZone: tz }).format(new Date()); }
function daysSince(day, first) { return Math.round((Date.parse(day) - Date.parse(first)) / 864e5); }
function clock(secs) { secs = Math.round(secs); return Math.floor(secs / 60) + ":" + String(secs % 60).padStart(2, "0"); }

function check(res) {
  var r;
  try { r = result(res); } catch (e) { return; }  // half-written state; the next check retries
  if (!r) return;
  if (r.secs == null) r.secs = timerSecs();
  var body = JSON.stringify(r);
  if (body === lastSent) return;
  lastSent = body;
  realFetch("/__dgb/result", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true,
  }).catch(function () { lastSent = null; });
}

// Debounced, so a burst of mutations or writes checks once.
function soon() { if (!pending) pending = setTimeout(function () { pending = null; check(); }, 250); }

function parse(text) { try { return JSON.parse(text); } catch (e) { return null; } }
function onResponse(url, reqBody, text) {
  try { url = new URL(url, location.href).href; } catch (e) { url = String(url); }
  check({ url: url, req: typeof reqBody === "string" ? parse(reqBody) : null, json: parse(text) });
  soon();
}

window.fetch = function (input, init) {
  var p = realFetch(input, init);
  var url = typeof input === "string" || input instanceof URL ? input : input.url;
  p.then(function (r) {
    r.clone().text().then(function (t) { onResponse(url, init && init.body, t); }, function () {});
  }, function () {});
  return p;
};

var open = XMLHttpRequest.prototype.open, send = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function (method, url) { this.__dgbUrl = url; return open.apply(this, arguments); };
XMLHttpRequest.prototype.send = function (body) {
  var xhr = this;
  xhr.addEventListener("loadend", function () {
    var text = null;
    try { text = xhr.responseType === "json" ? JSON.stringify(xhr.response) : xhr.responseText; } catch (e) {}
    onResponse(xhr.__dgbUrl, body, text);
  });
  return send.apply(this, arguments);
};

var setItem = Storage.prototype.setItem;
Storage.prototype.setItem = function () { setItem.apply(this, arguments); soon(); };

// Solve timer: starts at the first load of this game's page on a day and stops when its result
// first appears, kept in the game's localStorage so reloads and reopening don't change it. Only
// counts if the player clicked or typed, so a game already finished elsewhere gets no time.
// shortcut: days follow the player's local date, so a game started just before midnight restarts its timer
var TIMER = "__dgb_timer";
function saveTimer(t) { try { setItem.call(localStorage, TIMER, JSON.stringify(t)); } catch (e) {} }
function timer() {
  var t = ls(TIMER);
  if (!t || t.day !== today()) { t = { day: today(), start: Date.now(), played: false, end: null }; saveTimer(t); }
  return t;
}
function timerSecs() {
  var t = timer();
  if (!t.played) return null;
  if (!t.end) { t.end = Date.now(); saveTimer(t); }
  return Math.round((t.end - t.start) / 1000);
}
timer();
["pointerdown", "keydown"].forEach(function (name) {
  window.addEventListener(name, function (e) {
    var t = timer();
    if (e.isTrusted && !t.played) { t.played = true; saveTimer(t); }
  }, true);
});
new MutationObserver(soon).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true });
setInterval(soon, 1000);
