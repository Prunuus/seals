// The game runs in a same-origin iframe (/games-embed/bracket-city/); both frames get this
// script, so only the game's frame reports. bracketPuzzle_<New York date> is rewritten every move:
//   {isComplete, puzzleDate, wrongGuesses, peekedClues: [], megaPeekedClues: [], totalKeystrokes, minimumKeystrokes}
// Score as the game computes it: 100 (or keystroke efficiency in "classic" hard mode),
// minus 2 per wrong guess (not in classic), 5 per peek and 15 per reveal.
if (location.pathname.indexOf("/games-embed/") !== 0) return null;
var d = today("America/New_York"), st = ls("bracketPuzzle_" + d);
if (!st || st.isComplete !== true || st.puzzleDate !== d) return null;
var classic = ls("bracketCityInputMode") === "classic";
var peeks = (st.peekedClues || []).length, reveals = (st.megaPeekedClues || []).length;
var eff = st.totalKeystrokes > 0 ? st.minimumKeystrokes / st.totalKeystrokes * 100 : 100;
var score = Math.min(100, Math.max(0, (classic ? eff : 100 - 2 * (st.wrongGuesses || 0)) - 5 * peeks - 15 * reveals));
return {
  num: daysSince(d, "2025-04-08") + 1,
  details: [
    Math.round(score * 10) / 10 + " points" + (classic ? " (hard mode)" : ""),
    "❌ " + (st.wrongGuesses || 0) + " wrong · 👀 " + peeks + " peeks · 🛟 " + reveals + " reveals",
  ],
};
