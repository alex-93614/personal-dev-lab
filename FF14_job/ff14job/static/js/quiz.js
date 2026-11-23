// 診断フォーム: 1 問ずつ表示するステッパー（JS 無効時は全問を縦に並べて表示）
(() => {
  const form = document.getElementById('quiz');
  if (!form) return;

  const cards = [...form.querySelectorAll('.q-card')];
  const total = cards.length;
  const bar = document.getElementById('progress-bar');
  const count = document.getElementById('progress-count');
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  const submitBtn = document.getElementById('btn-submit');
  const STORE_KEY = 'ff14job-answers';
  const ADVANCE_MS = 260;

  form.classList.add('stepper');

  const answered = (card) => !!card.querySelector('input:checked');
  const firstUnanswered = () => cards.findIndex((c) => !answered(c));

  // サーバー側で回答が埋め込まれていない場合は、途中までの回答を復元する
  const prefilled = !!form.querySelector('input:checked');
  if (!prefilled) {
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || '{}');
      for (const [name, value] of Object.entries(saved)) {
        const el = form.querySelector(`input[name="${CSS.escape(name)}"][value="${CSS.escape(String(value))}"]`);
        if (el) el.checked = true;
      }
    } catch { /* 破損データは無視 */ }
  }

  const save = () => {
    const data = {};
    new FormData(form).forEach((v, k) => { data[k] = v; });
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch { /* ignore */ }
  };

  let idx = 0;
  let timer = null;

  function render(dir = 1) {
    cards.forEach((c, j) => {
      const on = j === idx;
      c.classList.toggle('active', on);
      c.classList.toggle('from-left', on && dir < 0);
    });
    const done = cards.filter(answered).length;
    bar.style.width = `${(done / total) * 100}%`;
    count.textContent = `${idx + 1} / ${total}`;
    const last = idx === total - 1;
    prevBtn.disabled = idx === 0;
    nextBtn.hidden = last;
    nextBtn.disabled = !answered(cards[idx]);
    submitBtn.hidden = !last;
    submitBtn.disabled = firstUnanswered() !== -1;
  }

  function go(i, dir = 1) {
    clearTimeout(timer);
    const next = Math.max(0, Math.min(total - 1, i));
    if (next === idx && cards[idx].classList.contains('active')) { render(dir); return; }
    idx = next;
    render(dir);
  }

  form.addEventListener('change', (e) => {
    if (e.target.type !== 'radio') return;
    save();
    const i = cards.indexOf(e.target.closest('.q-card'));
    render(1);
    clearTimeout(timer);
    if (i === idx && i < total - 1) {
      timer = setTimeout(() => go(i + 1, 1), ADVANCE_MS);
    }
  });

  prevBtn.addEventListener('click', () => go(idx - 1, -1));
  nextBtn.addEventListener('click', () => go(idx + 1, 1));

  form.addEventListener('submit', (e) => {
    const u = firstUnanswered();
    if (u !== -1) {
      e.preventDefault();
      go(u, 1);
      return;
    }
    try { sessionStorage.removeItem(STORE_KEY); } catch { /* ignore */ }
    submitBtn.disabled = true;
    submitBtn.textContent = '診断中…';
  });

  document.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const inputs = cards[idx].querySelectorAll('input[type="radio"]');
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= inputs.length) {
      e.preventDefault();
      inputs[n - 1].checked = true;
      inputs[n - 1].dispatchEvent(new Event('change', { bubbles: true }));
    } else if (e.key === 'ArrowLeft' || e.key === 'Backspace') {
      e.preventDefault();
      go(idx - 1, -1);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      if (answered(cards[idx])) go(idx + 1, 1);
    } else if (e.key === 'Enter' && idx === total - 1 && firstUnanswered() === -1) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  const u = firstUnanswered();
  idx = prefilled ? 0 : (u === -1 ? total - 1 : u);
  render(1);
})();
