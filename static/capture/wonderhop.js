// Each finished daily direction is appended to cielabysses.parties as
//   {day, mode: "daily", sens: "monter" | "plonger" | "passe" | "futur", points, questions}
// day 1 was 2026-10-05 in Montreal. cielabysses.streak is {last: day, count}.
// shortcut: read from the site's bundle (storage-*.js), not yet seen on a finished game; check it on the first real play
var day = daysSince(today("America/Montreal"), "2026-10-05") + 1;
var done = (ls("cielabysses.parties") || []).filter(function (p) { return p.mode === "daily" && p.day === day; });
if (!done.length) return null;
var NAMES = { monter: "⬆️ Up", plonger: "⬇️ Down", passe: "⏪ Past", futur: "⏩ Future" };
var streak = ls("cielabysses.streak");
return {
  num: day,
  streak: streak && streak.last === day && streak.count > 1 ? streak.count : null,
  details: done.map(function (p) { return (NAMES[p.sens] || p.sens) + ": " + p.points + " points"; }),
};
