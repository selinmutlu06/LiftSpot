/* Drawer: building detail, door-reveal open, notes, reviews, live rating recalc. */

import { sb, BUILDINGS, state, stars, rated, verified, storiesVerified } from './data.js';
import { trapFocus } from './focus.js';

let els = null;
let hooks = null;
let lastFocus = null;

export function initDrawer(domEls, callbacks) {
  els = domEls;       // { drawer, scrim, title, type, addr, dataStrip, body, closeBtn }
  hooks = callbacks;  // { onClose(), toast(msg, opts) }

  els.closeBtn.addEventListener('click', () => showDrawer(false));
  els.scrim.addEventListener('click', () => showDrawer(false));
  trapFocus(els.drawer);
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
  els.type.innerHTML = `<span>${esc(b.type)}</span><span class="town">${esc(b.town)}</span>`
    + (verified(b) ? '' : `<span class="badge-unverified" title="This building hasn’t been confirmed against OpenStreetMap. Details are unverified estimates.">Unverified</span>`);
  els.addr.textContent = b.addr;
  renderDataStrip(b);

  const savedNote = localStorage.getItem(`liftspot_note_${id}`) || '';
  els.body.innerHTML = `
    <div class="sec">
      <div class="rating-block${rated(b) ? '' : ' unrated'}">
        ${rated(b) ? `
        <span class="big led led-rating">${fmtRating(b.rating)}</span>
        <span class="of">/ 5</span>
        <span class="stars" aria-hidden="true">${stars(b.rating)}</span>` : `
        <span class="stars empty" aria-hidden="true">${stars(0)}</span>`}
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
        <div class="field" style="margin-bottom:8px">
          <label for="rvName">Name (shown with your review)</label>
          <input class="text-input" id="rvName" maxlength="40" placeholder="Anonymous"
            value="${esc(localStorage.getItem('liftspot_reviewer_name') || '')}" />
        </div>
        <div class="field">
          <label for="rvText">Your review</label>
          <textarea id="rvText" placeholder="What are the elevators like here?" style="min-height:80px"></textarea>
        </div>
        <button class="btn" id="postReview">Post review</button>
      </div>
    </div>

    ${b.yt_checked != null && b.yt_videos === 0 ? `
    <div class="sec">
      <h3>Filmed these elevators?</h3>
      <p class="sec-hint">Paste your YouTube link to claim this building. Your video shows up here after a quick review.</p>
      <div class="field">
        <label for="subUrl">YouTube link</label>
        <input class="text-input" id="subUrl" inputmode="url" placeholder="https://www.youtube.com/watch?v=…" />
      </div>
      <p class="form-error" id="subError">That doesn’t look like a YouTube video link.</p>
      <button class="btn" id="subSend">Submit video</button>
      <div class="savednote" id="subPending"></div>
    </div>` : ''}

    <div class="sec">
      <h3>The elevators inside</h3>
      <div id="repList"><div class="empty">Loading…</div></div>
      <button class="btn" id="repCta" aria-expanded="false" aria-controls="repform" style="margin-top:var(--s3)">Report what's inside</button>
      <div class="rform" id="repform">
        <p class="sec-hint">Ridden these? Count, brand, drive type, whatever you know. It shows up after a quick review, labeled as reported, not as official specs.</p>
        <div class="field" style="margin-bottom:8px">
          <label for="repCount">How many elevators</label>
          <input class="text-input" id="repCount" type="number" min="1" max="100" inputmode="numeric" placeholder="e.g. 2" />
        </div>
        <div class="field" style="margin-bottom:8px">
          <label for="repBrand">Brand</label>
          <input class="text-input" id="repBrand" maxlength="40" list="brandList" placeholder="e.g. Otis" />
          <datalist id="brandList">
            <option>Otis</option><option>Schindler</option><option>ThyssenKrupp</option>
            <option>TK Elevator</option><option>KONE</option><option>Dover</option>
            <option>Fujitec</option><option>Mitsubishi</option><option>Montgomery</option>
            <option>Westinghouse</option><option>Armor</option><option>Burlington</option>
          </datalist>
        </div>
        <div class="field" style="margin-bottom:8px">
          <label for="repKind">Drive type</label>
          <select class="text-input" id="repKind">
            <option value="">Not sure</option>
            <option value="hydraulic">Hydraulic</option>
            <option value="traction">Traction</option>
          </select>
        </div>
        <div class="field" style="margin-bottom:8px">
          <label for="repNotes">Notes</label>
          <textarea id="repNotes" maxlength="500" placeholder="e.g. glass back, rebuilt 2019, freight in the rear" style="min-height:60px"></textarea>
        </div>
        <div class="field" style="margin-bottom:8px">
          <label for="repName">Name (shown with your report)</label>
          <input class="text-input" id="repName" maxlength="40" placeholder="Anonymous"
            value="${esc(localStorage.getItem('liftspot_reviewer_name') || '')}" />
        </div>
        <p class="form-error" id="repError">Give at least a count, a brand, or a drive type.</p>
        <button class="btn" id="repSend">Send report</button>
      </div>
    </div>

    <div class="sec">
      <h3>Reviews</h3>
      <div id="rvList"><div class="empty">Loading…</div></div>
    </div>

    <div class="sec">
      <h3>My private notes</h3>
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
  wireSubmitVideo(b);
  wireReports(b);
  await refreshReviews(id);
}

/* Community elevator reports (migrations/015): the only source of elevator
   counts that exists. Approved reports render here with their provenance;
   new ones go in pending and touch nothing until reviewed. */
async function refreshReports(id) {
  const list = document.getElementById('repList');
  if (!list) return;
  const { data, error } = await sb.from('elevator_reports').select('*')
    .eq('building_id', id).order('created_at', { ascending: false });
  if (error) {
    list.innerHTML = '<div class="empty">Nobody has reported these elevators yet.</div>';
    return;
  }
  const approved = data.filter(r => r.status === 'approved');
  const pending = data.filter(r => r.status === 'pending').length;
  const bits = approved.map(r => {
    const what = [
      r.elevators != null ? `${r.elevators} elevator${r.elevators === 1 ? '' : 's'}` : null,
      r.brand, r.kind,
    ].filter(Boolean).join(' · ');
    const when = new Date(r.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    return `<div class="review">
      <div class="rhead"><span class="who">${esc(r.who)}</span><span class="rstars">${when}</span></div>
      <p><b>${esc(what)}</b></p>${r.notes ? `<p>${esc(r.notes)}</p>` : ''}
    </div>`;
  });
  if (pending) bits.push(`<div class="empty">${pending} report${pending === 1 ? '' : 's'} waiting for review</div>`);
  if (!bits.length) bits.push('<div class="empty">Nobody has reported these elevators yet. Ridden them? You’re the source.</div>');
  list.innerHTML = bits.join('');
}

function wireReports(b) {
  const cta = document.getElementById('repCta');
  if (!cta) return;
  refreshReports(b.id);
  const form = document.getElementById('repform');
  const err = document.getElementById('repError');
  cta.addEventListener('click', () => {
    const open = form.classList.toggle('open');
    cta.setAttribute('aria-expanded', String(open));
    if (open) document.getElementById('repCount').focus();
  });
  document.getElementById('repSend').addEventListener('click', async () => {
    const n = parseInt(document.getElementById('repCount').value, 10);
    const brand = document.getElementById('repBrand').value.trim().slice(0, 40);
    const kind = document.getElementById('repKind').value;
    const notes = document.getElementById('repNotes').value.trim().slice(0, 500);
    const who = document.getElementById('repName').value.trim().slice(0, 40);
    if (!(n >= 1 && n <= 100) && !brand && !kind) {
      err.classList.add('show');
      return;
    }
    err.classList.remove('show');
    if (who) localStorage.setItem('liftspot_reviewer_name', who);
    const btn = document.getElementById('repSend');
    btn.disabled = true;
    btn.textContent = 'Sending…';
    const { error } = await sb.from('elevator_reports').insert({
      building_id: b.id,
      elevators: n >= 1 && n <= 100 ? n : null,
      brand: brand || null,
      kind: kind || null,
      notes: notes || null,
      who: who || 'Anonymous',
    });
    btn.disabled = false;
    btn.textContent = 'Send report';
    if (error) {
      hooks.toast('Couldn’t send the report. Check your connection and try again.', { error: true });
      return;
    }
    form.classList.remove('open');
    cta.setAttribute('aria-expanded', 'false');
    hooks.toast('Report sent. It shows up once it’s reviewed.');
    refreshReports(b.id);
  });
}

/* "Filmed these elevators?" — visitors paste a YouTube link on an unfilmed
   building. Rows land in the submissions table as pending (migrations/014) and
   only appear on the site once approved, so the honesty rules hold: an
   unreviewed link is a claim, not a fact. */
const YT_URL_RE = /^https:\/\/((www|m)\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]{6,}/i;

function wireSubmitVideo(b) {
  const send = document.getElementById('subSend');
  if (!send) return;
  const input = document.getElementById('subUrl');
  const err = document.getElementById('subError');
  const pending = document.getElementById('subPending');

  const showPending = n => {
    if (!n) return;
    pending.innerHTML = `
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>
      ${n} video${n === 1 ? '' : 's'} submitted, waiting for review`;
    pending.classList.add('show');
  };
  // Best effort: if the table doesn't exist yet or the count fails, the
  // section still works — the count line just stays hidden.
  sb.from('submissions').select('id', { count: 'exact', head: true })
    .eq('building_id', b.id).eq('status', 'pending')
    .then(({ count, error }) => { if (!error) showPending(count); });

  input.addEventListener('input', () => err.classList.remove('show'));
  send.addEventListener('click', async () => {
    const url = input.value.trim();
    if (!YT_URL_RE.test(url)) {
      err.classList.add('show');
      input.focus();
      return;
    }
    send.disabled = true;
    send.textContent = 'Submitting…';
    const { error } = await sb.from('submissions').insert({ building_id: b.id, url });
    send.disabled = false;
    send.textContent = 'Submit video';
    if (error) {
      if (error.code === '23505') hooks.toast('That video was already submitted for this building.');
      else hooks.toast('Couldn’t submit the video. Check your connection and try again.', { error: true });
      return;
    }
    input.value = '';
    hooks.toast('Video submitted. It shows up once it’s reviewed.');
    const { count, error: cErr } = await sb.from('submissions').select('id', { count: 'exact', head: true })
      .eq('building_id', b.id).eq('status', 'pending');
    if (!cErr) showPending(count);
  });
}

function renderDataStrip(b) {
  const d = b._dCached;
  // Stories are a fact only when a name-matched OSM building polygon carries
  // building:levels; an unnamed polygon's tag shows as "· est"; NULL means no
  // source has the number, so we show "?" — never an invented count. Elevator
  // counts have no public source anywhere: NULL until the community reports one.
  const sv = storiesVerified(b);
  const stories = b.stories == null
    ? `<div class="cell est"><span class="v led">?</span><span class="k">stories · unknown</span></div>`
    : `<div class="cell${sv ? '' : ' est'}"><span class="v led led-lit">${b.stories}</span><span class="k">stories${sv ? '' : ' · est'}</span></div>`;
  // Since the purge (migrations/008) every elevator count was NULL; the only
  // way one exists now is an approved community report (migrations/015), so a
  // non-null count is labeled "reported" — a rider said so, not an estimate.
  const elevators = b.elevators == null
    ? `<div class="cell est"><span class="v led">?</span><span class="k">elevators · unreported</span></div>`
    : `<div class="cell"><span class="v led led-lit">${b.elevators}</span><span class="k">elevators · reported</span></div>`;
  els.dataStrip.innerHTML = `${stories}${elevators}` +
    (d != null ? `<div class="cell"><span class="v led led-lit">${d.toFixed(1)}</span><span class="k">mi away</span></div>` : '') +
    footageRow(b);
}

// Coverage status: YouTube (migrations/010) + Reddit (migrations/012). We
// searched, so we can only say what we FOUND as of the check date — "none
// found", never "never filmed". NULL = ambiguous near-misses — no claim.
function footageRow(b) {
  if (b.yt_checked == null) return '';
  const when = new Date(b.yt_checked + 'T00:00').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const rows = [];
  if (b.yt_videos > 0) {
    rows.push(`<div class="footage"><a href="${b.yt_url}" target="_blank" rel="noopener">
      Watch elevator footage</a> · ${b.yt_videos} video${b.yt_videos === 1 ? '' : 's'} on YouTube as of ${when}</div>`);
  }
  if (b.reddit_posts > 0) {
    rows.push(`<div class="footage"><a href="${b.reddit_url}" target="_blank" rel="noopener">
      Discussed on Reddit</a> · ${b.reddit_posts} post${b.reddit_posts === 1 ? '' : 's'} as of ${when}</div>`);
  }
  if (rows.length) return rows.join('');
  if (b.yt_videos === 0) {
    const sources = b.reddit_posts === 0 ? 'YouTube videos or Reddit posts' : 'YouTube videos';
    return `<div class="footage none"><span class="pill-first">Be the first</span>
      No ${sources} about these elevators found as of ${when}. Film yours and claim it.</div>`;
  }
  return '';
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
    const name = document.getElementById('rvName').value.trim().slice(0, 40);
    if (name) localStorage.setItem('liftspot_reviewer_name', name);
    const btn = document.getElementById('postReview');
    btn.disabled = true;
    btn.textContent = 'Posting…';
    const { error } = await sb.from('reviews').insert({ building_id: id, who: name || 'Anonymous', stars: pick, body: t || '(no comment)' });
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
  const block = els.body.querySelector('.rating-block');
  if (block) {
    block.classList.toggle('unrated', !rated(b));
    block.innerHTML = `${rated(b) ? `
        <span class="big led led-rating">${fmtRating(b.rating)}</span>
        <span class="of">/ 5</span>
        <span class="stars" aria-hidden="true">${stars(b.rating)}</span>` : `
        <span class="stars empty" aria-hidden="true">${stars(0)}</span>`}
        <span class="rcount" id="rvCount"></span>`;
  }
  const rvCount = document.getElementById('rvCount');
  if (rvCount) rvCount.textContent = b.reviews.length ? `${b.reviews.length} review${b.reviews.length > 1 ? 's' : ''}` : 'No reviews yet';
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
