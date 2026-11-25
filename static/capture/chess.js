// chess.com keeps nothing in storage for the daily puzzle (a reload restarts it), so this reads
// the sidebar. "Next Day" is disabled only on today's puzzle; each wrong move breaks a heart;
// a solve shows the success modal or, once closed, the "Learn more" video card.
var next = document.querySelector('.game-mode-top-section-date-picker button[aria-label="Next Day"]');
if (!next || !next.disabled) return null;
var hearts = document.querySelectorAll(".daily-puzzle-hearts-heart").length;
var left = document.querySelectorAll(".daily-puzzle-hearts-heart.daily-puzzle-hearts-filled").length;
var solved = !!document.querySelector(".daily-puzzle-success-modal-component, .video-prompt-component");
if (!hearts || !(solved || left === 0)) return null;
var mistakes = hearts - left;
return {
  num: daysSince(today(), "2007-05-08") + 1,
  score: mistakes,
  details: [
    solved && left ? (mistakes ? mistakes + " mistakes" : "Perfect") : "Out of hearts",
    "💚".repeat(left) + "💔".repeat(mistakes),
  ],
};
