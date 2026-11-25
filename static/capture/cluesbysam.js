// The daily puzzle (at "/"; older ones are under /s/play) keeps state-<New York date>:
//   {imperfections: [{index, type: "error" | "hint" | "second-hint"}], completeTime: ms, 0 until solved}
if (location.pathname !== "/") return null;
var d = today("America/New_York"), st = ls("state-" + d);
if (!st || !(st.completeTime > 0)) return null;
var imp = st.imperfections || [];
var count = function (t) { return imp.filter(function (m) { return m.type === t; }).length; };
return {
  num: daysSince(d, "2025-04-28") + 1,
  details: [
    (imp.length ? imp.length + " imperfections" : "Perfect") + " in " + clock(Math.ceil(st.completeTime / 1000)),
    "❌ " + count("error") + " mistakes · 💡 " + (count("hint") + count("second-hint")) + " hints",
  ],
};
