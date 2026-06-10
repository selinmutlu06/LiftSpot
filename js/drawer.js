/* Drawer: building detail, door-reveal open, notes, reviews, live rating recalc. */

import { sb, BUILDINGS, state, stars } from './data.js';

let els = null;
let hooks = null;
let lastFocus = null;

export function initDrawer(domEls, callbacks) {
  els = domEls;       // { drawer, scrim, title, type, addr, dataStrip, body, closeBtn }
  hooks = callbacks;  // { onClose(), toast(msg, opts) }

  els.closeBtn.addEventListener('click', () => showDrawer(false));
  els.scrim.addEventListener('click', () => showDrawer(false));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && els.drawer.classList.contains('open')) showDrawer(false);
  });
}

export function showDrawer(open) {
  els.drawer.classList.toggle('open', open);
  els.drawer.setAttribute('aria-hidden', String(!open));
  els.scrim.classList.toggle('show', open);
  if (!open) {
    state.activeId = null;
    hooks.onClose();
    lastFocus?.focus?.();
    lastFocus = null;
  }
}

export async function openBuilding(id) {
  const b = BUILDINGS.find(x => x.id === id);
  if (!b) return;
  lastFocus = document.activeElement;
  state.activeId = id;

  els.title.textContent = b.name;
  els.type.textContent = `${b.type} · ${b.town}`;
  els.addr.textContent = b.addr;
  renderDataStrip(b);

  const savedNote = localStorage.getItem(`liftspot_note_${id}`) || '';
  els.body.innerHTML = `
    <div class="sec">
      <div class="rating-block">
        <span class="big led led-rating">${fmtRating(b.rating)}</span>
        <span class="of">/ 5</span>
        <span class="stars" aria-hidden="true">${stars(b.rating)}</span>
        <span class="rcount" id="rvCount"></span>
      </div>
      <button class="cta" id="rateCta" aria-expanded="false" aria-controls="rform">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l2.9 6.26L21.5 9.27l-4.75 4.38L17.8 20.5 12 17.27 6.2 20.5l1.05-6.85L2.5 9.27l6.6-1.01z"/></svg>
        Rate this elevator
      </button>
      <div class="rform" id="rform">
        <div class="starpick" id="picker" role="radiogroup" aria-label="Star rating">
          ${[1, 2, 3, 4, 5].map(n => `<button type="button" data-n="${n}" role="radio" aria-checked="false" aria-label="${n} star${n > 1 ? 's' : ''}">★</button>`).join('')}
        </div>
        <p class="form-error" id="formError">Pick a star rating first.</p>
        <div class="field">
          <label for="rvText">Your review</label>
          <textarea id="rvText" placeholder="What are the elevators like here?" style="min-height:80px"></textarea>
        </div>
        <button class="btn" id="postReview">Post review</button>
      </div>
    </div>

    <div class="sec">
      <h4>Reviews</h4>
      <div id="rvList"><div class="empty">Loading…</div></div>
    </div>

    <div class="sec">
      <h4>My private notes</h4>
      <div class="field">
        <label for="noteBox">Saved to this device only</label>
        <textarea class="note-area" id="noteBox" placeholder="e.g. Otis Gen2, glass back, north entrance…" style="min-height:80px">${esc(savedNote)}</textarea>
      </div>
      <button class="btn" id="saveNote">Save note</button>
      <div class="savednote" id="noteSaved">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>
        Saved to this device
      </div>
    </div>`;

  showDrawer(true);
  els.closeBtn.focus();
  wireForm(b);
  await refreshReviews(id);
}

function renderDataStrip(b) {
  const d = b._dCached;
  els.dataStrip.innerHTML = `
    <div class="cell"><span class="v led led-lit">${b.stories}</span><span class="k">stories</span></div>
    <div class="cell"><span class="v led led-lit">${b.elevators}</span><span class="k">elevators</span></div>
    ${d != null ? `<div class="cell"><span class="v led led-lit">${d.toFixed(1)}</span><span class="k">mi away</span></div>` : ''}`;
}

function wireForm(b) {
  const id = b.id;
  const cta = document.getElementById('rateCta');
  const rform = document.getElementById('rform');
  const formError = document.getElementById('formError');

  cta.addEventListener('click', () => {
    const open = rform.classList.toggle('open');
    cta.setAttribute('aria-expanded', String(open));
    if (open) rform.querySelector('[data-n="1"]').focus();
  });

  let pick = 0;
  const picker = document.getElementById('picker');
  const starBtns = [...picker.querySelectorAll('button')];
  const updatePicker = val => {
    pick = val;
    formError.classList.remove('show');
    starBtns.forEach(x => {
      x.classList.toggle('on', +x.dataset.n <= pick);
      x.setAttribute('aria-checked', String(+x.dataset.n === pick));
    });
  };
  starBtns.forEach(s => {
    s.addEventListener('click', () => updatePicker(+s.dataset.n));
    s.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { e.preventDefault(); updatePicker(Math.min(5, pick + 1)); starBtns[pick - 1].focus(); }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { e.preventDefault(); updatePicker(Math.max(1, pick - 1)); starBtns[pick - 1].focus(); }
    });
  });

  document.getElementById('saveNote').addEventListener('click', () => {
    localStorage.setItem(`liftspot_note_${id}`, document.getElementById('noteBox').value);
    document.getElementById('noteSaved').classList.add('show');
    hooks.toast('Note saved.');
  });

  document.getElementById('postReview').addEventListener('click', async () => {
    const t = document.getElementById('rvText').value.trim();
    if (!pick) {
      formError.classList.add('show');
      starBtns[0].focus();
      return;
    }
    const btn = document.getElementById('postReview');
    btn.disabled = true;
    btn.textContent = 'Posting…';
    const { error } = await sb.from('reviews').insert({ building_id: id, who: 'You', stars: pick, body: t || '(no comment)' });
    if (error) {
      btn.disabled = false;
      btn.textContent = 'Post review';
      hooks.toast('Couldn’t post the review. Check your connection and try again.', { error: true });
      return;
    }
    hooks.toast('Review posted.');
    await refreshReviews(id);
    updatePicker(0);
    starBtns.forEach(x => x.classList.remove('on'));
  });
}

async function refreshReviews(id) {
  const { data: reviews, error } = await sb.from('reviews').select('*').eq('building_id', id).order('created_at', { ascending: false });
  const rvList = document.getElementById('rvList');
  if (error) {
    if (rvList) rvList.innerHTML = '<div class="empty">Couldn’t load reviews. Close and reopen to retry.</div>';
    return;
  }
  const b = BUILDINGS.find(x => x.id === id);
  b.reviews = reviews || [];
  if (b.reviews.length) {
    const newRating = +(b.reviews.reduce((s, r) => s + r.stars, 0) / b.reviews.length).toFixed(1);
    if (newRating !== b.rating) {
      b.rating = newRating;
      await sb.from('buildings').update({ rating: newRating }).eq('id', id);
      hooks.onRatingChange?.();
    }
  }
  if (rvList) rvList.innerHTML = renderReviews(b);
  const rvCount = document.getElementById('rvCount');
  if (rvCount) rvCount.textContent = b.reviews.length ? `${b.reviews.length} review${b.reviews.length > 1 ? 's' : ''}` : 'No reviews yet';
  const big = els.body.querySelector('.rating-block .big');
  if (big) big.textContent = fmtRating(b.rating);
  const starsEl = els.body.querySelector('.rating-block .stars');
  if (starsEl) starsEl.textContent = stars(b.rating);
  renderDataStrip(b);
  const rvText = document.getElementById('rvText');
  const btn = document.getElementById('postReview');
  if (rvText) rvText.value = '';
  if (btn) { btn.disabled = false; btn.textContent = 'Post review'; }
}

function renderReviews(b) {
  if (!b.reviews?.length) return '<div class="empty">No reviews yet — be the first.</div>';
  return b.reviews.map(r => `
    <div class="review">
      <div class="rhead">
        <span class="who">${esc(r.who)}</span>
        <span class="rstars" aria-label="${r.stars} stars">${stars(r.stars)}</span>
      </div>
      <p>${esc(r.body || '')}</p>
    </div>`).join('');
}

const fmtRating = r => Number(r).toFixed(1);

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
