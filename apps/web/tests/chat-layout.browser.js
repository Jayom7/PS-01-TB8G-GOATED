// Evaluate this function in the rendered Ask page at desktop and mobile widths.
// DOM-only regression checks: no auth, network or application-state access.
export default function verifyChatLayout() {
  const checks = [];
  function check(name, pass) {
    if (!pass) throw new Error(`Chat layout regression: ${name}`);
    checks.push(name);
  }
  const questions = [...document.querySelectorAll('.question-bubble')];
  check('user messages exist', questions.length > 0);
  for (const question of questions) {
    const parent = question.closest('.conversation-turn') ?? question.parentElement;
    const bounds = question.getBoundingClientRect();
    check('user aligned right', Math.abs(bounds.right - parent.getBoundingClientRect().right) <= 6);
  }
  for (const answer of document.querySelectorAll('.answer-block, .preview-response')) {
    check('assistant aligned left', Math.abs(answer.getBoundingClientRect().left - answer.parentElement.getBoundingClientRect().left) <= 2);
  }
  for (const turn of document.querySelectorAll('.conversation-turn')) {
    check('one user message per completed turn', turn.querySelectorAll('.question-bubble').length === 1);
  }
  check('no page horizontal overflow', document.documentElement.scrollWidth <= innerWidth + 1);
  const composer = document.querySelector('textarea');
  check('composer usable', !!composer && composer.clientHeight >= 40 && !composer.disabled);
  const error = document.querySelector('.request-error');
  if (error) {
    check('failure has retry action', !!error.querySelector('button'));
    check('failure retains composer question', !!composer.value.trim());
    check('failure omits raw diagnostics', !/gemini|stack trace|768 minutes|46080/i.test(error.textContent));
  }
  const sources = document.querySelector('.retry-source-list');
  if (sources && sources.getBoundingClientRect().height > 0) {
    check('source list keyboard focusable', sources.tabIndex === 0);
    check('source list has bounded height', sources.clientHeight <= 240);
    check('source titles wrap without clipping', sources.scrollWidth <= sources.clientWidth + 1);
    check('source list scrollable', getComputedStyle(sources).overflowY === 'auto');
  }
  return {viewport: {width: innerWidth, height: innerHeight}, checks};
}
