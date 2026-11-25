// Puzzles are dated UTC+3. Anonymous runs write gauntle:anon:lastPlayedDate/Time/Details at the
// end; logged-in runs only show up in the last POST /api/run/complete-game, which answers
// {done: true, results: {totalTimeMs, breakdown}} for a request with runId "<date>-<uuid>".
// breakdown: {gameOrder: [id, ...], games: {id: {flawless, failed, skipped}}}
var day = new Date(Date.now() + 3 * 36e5).toISOString().slice(0, 10), run = null;
if (res) {
  var m = /^(\d{4}-\d{2}-\d{2})-/.exec((res.req && res.req.runId) || "");
  if (/\/api\/run\/complete-game(\?|$)/.test(res.url) && res.json && res.json.done && m && m[1] === day) {
    run = { ms: res.json.results.totalTimeMs, d: res.json.results };
  }
} else if (ls("gauntle:anon:lastPlayedDate") === day) {
  run = { ms: Number(ls("gauntle:anon:lastPlayedTime")), d: ls("gauntle:anon:lastPlayedDetails") };
}
if (!run || !(run.ms > 0) || !run.d || !run.d.breakdown) return null;
var g = run.d.breakdown.games || {}, order = run.d.breakdown.gameOrder || [];
return {
  num: daysSince(day, "2026-05-13") + 1,
  score: Math.round(run.ms / 10) / 100,  // total seconds
  secs: Math.round(run.ms / 1000),
  details: [
    clock(run.ms / 1000) + " total, " + order.filter(function (id) { return (g[id] || {}).flawless; }).length + "/" + order.length + " flawless",
    order.map(function (id) { var x = g[id] || {}; return x.failed || x.skipped ? "🟥" : x.flawless ? "🟩" : "🟨"; }).join(""),
  ],
};
