// NYT rewrites games-state-connections/<user> after every guess:
//   {states: [{printDate, data: {puzzleComplete, puzzleWon, mistakes, isPlayingArchive,
//     guesses: [{cards: [{level: 0-3}, ...]}]}}]}   level: 0 yellow, 1 green, 2 blue, 3 purple
var key = Object.keys(localStorage).find(function (k) { return k.indexOf("games-state-connections/") === 0; });
var st = ((ls(key) || {}).states || []).find(function (s) { return s.data && !s.data.isPlayingArchive && s.printDate === today(); });
if (!st || !st.data.puzzleComplete) return null;
var C = ["🟨", "🟩", "🟦", "🟪"];
return {
  num: daysSince(st.printDate, "2023-06-11"),
  details: [(st.data.puzzleWon ? "Solved" : "Failed") + " with " + st.data.mistakes + " mistakes"].concat(
    st.data.guesses.map(function (g) { return g.cards.map(function (c) { return C[c.level] || "⬜"; }).join(""); })),
};
