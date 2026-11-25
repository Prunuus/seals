// Finishing all 7 rounds writes the day into krillion:stats:v1 (prefixed when signed in):
//   {history: {"<New York date>": {dayNumber, score, tiers: ["rare", ..., "miss"]}}, currentStreak}
// Nothing is written there mid-dive.
var stats = ls(Object.keys(localStorage).find(function (k) { return /krillion:stats:v1$/.test(k); }));
var day = stats && stats.history && stats.history[today("America/New_York")];
if (!day) return null;
var EMOJI = { plankton: "🫧", tooclever: "🤡", schooler: "🐟", rare: "🦑", deepcut: "🏮", krillion: "🌟", miss: "⬛" };
return {
  num: day.dayNumber,
  score: day.score,
  streak: stats.currentStreak > 1 ? stats.currentStreak : null,
  details: [day.score + " points", day.tiers.map(function (t) { return EMOJI[t] || "⬛"; }).join("")],
};
