// NYT rewrites games-state-wordleV2/<user> after every guess:
//   {states: [{printDate, data: {currentRowIndex, status: "IN_PROGRESS" | "WIN" | ..., isPlayingArchive}}]}
// Tile colours are only on the board, as data-state on each tile once it has flipped.
var key = Object.keys(localStorage).find(function (k) { return k.indexOf("games-state-wordleV2/") === 0; });
var st = ((ls(key) || {}).states || []).find(function (s) { return s.data && !s.data.isPlayingArchive && s.printDate === today(); });
if (!st) return null;
var won = st.data.status === "WIN", n = st.data.currentRowIndex;
if (!won && (st.data.status === "IN_PROGRESS" || n < 6)) return null;
var E = { correct: "🟩", present: "🟨", absent: "⬜" };
var rows = Array.from(document.querySelectorAll('[role="group"][aria-label^="Row "]'))
  .map(function (r) { return Array.from(r.querySelectorAll("[data-state]")).map(function (t) { return E[t.dataset.state]; }); })
  .filter(function (t) { return t.length === 5 && t.every(Boolean); })
  .map(function (t) { return t.join(""); });
if (rows.length !== n) return null;  // the last row is still flipping
return { num: daysSince(st.printDate, "2021-06-19"), details: [(won ? n : "X") + "/6"].concat(rows) };
