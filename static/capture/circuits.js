// Puzzmo keeps results on its server; the completion screen POSTs
// api.puzzmo.com/graphql?useCompletionDataV2Query, answering
//   {data: {gamePlay: {pointsAwarded, elapsedTimeSecs, completedAt, boardState,
//     puzzle: {mostRecentDaily: {daily: {dateKey, isToday, seriesNumber}}}}}}
// boardState is "/"-separated; per box (";"), section 3 has the words submitted (","; the last is
// right) and section 5 a time per Bolt used.
if (!res || !/api\.puzzmo\.com\/graphql\?useCompletionDataV2Query/.test(res.url)) return null;
var gp = res.json && res.json.data && res.json.data.gamePlay;
var daily = gp && gp.puzzle && gp.puzzle.mostRecentDaily && gp.puzzle.mostRecentDaily.daily;
if (!gp || !gp.completedAt || !daily || daily.isToday !== true) return null;
var parts = (gp.boardState || "").split("/");
var perBox = function (s) { return (parts[s] || "").split(";").map(function (x) { return x ? x.split(",") : []; }); };
var wrong = perBox(3).reduce(function (n, w) { return n + Math.max(w.length - 1, 0); }, 0);
var bolts = perBox(5).reduce(function (n, b) { return n + b.length; }, 0);
return {
  num: daily.seriesNumber || daysSince(daily.dateKey, "2023-10-16") + 1,
  details: [
    gp.pointsAwarded.toLocaleString("en-US") + " points in " + clock(gp.elapsedTimeSecs),
    "❌ " + wrong + " wrong · ⚡ " + bolts + " bolts",
  ],
};
