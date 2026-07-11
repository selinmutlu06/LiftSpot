/* Voice agent: a calm, patient, two-way spoken conversation powered by
   ElevenLabs Agents. The API key never reaches the browser — we fetch a
   short-lived WebRTC token from our Netlify function, then connect with it.
   Pressing "Ask aloud" opens the cab overlay (see .voice-overlay in app.css). */

// Zero-build: pull the official SDK straight from an ESM CDN, the same way the
// rest of the app loads Supabase / MapLibre. Pinned so it can't drift on us.
import { Conversation } from 'https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.13.0/+esm';
import { trapFocus } from './focus.js';
import { sb, BUILDINGS, loadBuildings, topMatches, verified, storiesVerified, rated } from './data.js';

const TOKEN_ENDPOINT = '/api/voice-token';

/* ── the agent's eyes on the catalogue ──
   The ElevenLabs agent calls find_buildings(...) (a client tool declared on the
   agent) whenever it needs real building data. We answer from the same data the
   UI shows, and bake the honesty rules straight into the field names so the
   model can't quietly turn an estimate into a fact:
     elevators_estimate  — ALWAYS an estimate, never a hard count
     floors_confirmed    — true only when OSM building:levels backs it
     verified            — existence/location independently confirmed
     rating              — null when there are no real reviews yet  */
async function findBuildings({ query, limit }) {
  if (!BUILDINGS.length) { try { await loadBuildings(); } catch { /* offline */ } }

  const n = Math.min(Math.max(parseInt(limit, 10) || 5, 1), 8);
  const ranked = query ? topMatches(query, BUILDINGS.length) : [];
  const shown = ranked.slice(0, n);

  // One round-trip for the reviews of every building we're returning.
  const reviewsBy = {};
  if (shown.length) {
    const { data } = await sb
      .from('reviews')
      .select('building_id, who, stars, body, created_at')
      .in('building_id', shown.map(b => b.id))
      .order('created_at', { ascending: false });
    (data || []).forEach(r => { (reviewsBy[r.building_id] ||= []).push(r); });
  }

  const buildings = shown.map(b => {
    const reviews = reviewsBy[b.id] || [];
    return {
      name: b.name,
      type: b.type,
      town: b.town,
      address: b.addr,
      floors: b.stories,                      // null → no source has the count; say "unknown"
      floors_confirmed: storiesVerified(b),   // false → it's an estimate, say "about"
      elevators_estimate: b.elevators,        // null until the community reports one
      verified: verified(b),                  // false → not independently confirmed yet
      rating: rated(b) ? Number(b.rating) : null,  // null → "no reviews yet"
      review_count: reviews.length,
      reviews: reviews.slice(0, 3).map(r => ({ stars: r.stars, comment: r.body, by: r.who })),
    };
  });

  return JSON.stringify({
    total_matches: ranked.length,
    returned: buildings.length,
    buildings,
    reminder: ranked.length === 0
      ? 'No building in the LiftSpot directory matched this query. Do not invent one.'
      : 'A null floors or elevators_estimate means nobody has the number — say it is unknown, never guess one. Non-null elevators_estimate is a community estimate (say "about"). floors are an estimate unless floors_confirmed is true. If verified is false, the building is not independently confirmed. rating is null when there are no real reviews.',
  });
}

let conversation = null;   // active session, or null when idle
let starting = false;      // guard against double-clicks mid-connect

export function initVoice(els, { toast } = {}) {
  const { btn, status, overlay, cab, statusText, caption, endBtn, closeBtn } = els;
  if (!btn) return;

  const labelEl = btn.querySelector('.v-label');
  const setBtnLabel = text => { if (labelEl) labelEl.textContent = text; };
  const announce = msg => { if (status) status.textContent = msg; };       // screen-reader live region
  const showStatus = msg => { if (statusText) statusText.textContent = msg; }; // visible text in the cab

  let lastFocus = null;
  if (cab) trapFocus(cab);

  // s: 'idle' | 'connecting' | 'listening' | 'speaking'
  const setState = s => {
    btn.dataset.vstate = s;
    if (cab) cab.dataset.vstate = s;
    const active = s !== 'idle';
    btn.classList.toggle('on', active);
    btn.setAttribute('aria-pressed', String(active));
    if (s === 'idle') {
      setBtnLabel('Ask aloud');
      btn.setAttribute('aria-label', 'Start talking to the elevator guide');
    } else if (s === 'connecting') {
      setBtnLabel('Connecting…');
      btn.setAttribute('aria-label', 'Connecting to the elevator guide');
      showStatus('Connecting. Please wait.');
    } else if (s === 'speaking') {
      setBtnLabel('Stop');
      btn.setAttribute('aria-label', 'Stop talking to the elevator guide');
      showStatus('The guide is talking.');
    } else { // listening
      setBtnLabel('Stop');
      btn.setAttribute('aria-label', 'Stop talking to the elevator guide');
      showStatus('Your turn. Take your time.');
    }
  };

  const openOverlay = () => {
    if (!overlay) return;
    lastFocus = document.activeElement;
    if (caption) caption.textContent = '';
    overlay.classList.add('show');
    overlay.setAttribute('aria-hidden', 'false');
    // Move focus into the dialog so a keyboard / screen-reader user lands here.
    requestAnimationFrame(() => endBtn?.focus());
  };

  const closeOverlay = () => {
    if (!overlay) return;
    overlay.classList.remove('show');
    overlay.setAttribute('aria-hidden', 'true');
    // Return focus to where the user was (the Ask aloud button).
    (lastFocus instanceof HTMLElement ? lastFocus : btn).focus();
  };

  const renderCaption = (text, source) => {
    if (!caption || !text) return;
    const who = source === 'user' ? 'You' : 'Guide';
    caption.innerHTML = `<span class="vc-who">${who}</span>${escapeHtml(text)}`;
  };

  async function start() {
    if (conversation || starting) return;
    starting = true;
    setState('connecting');
    openOverlay();
    announce('Connecting. Please wait.');
    try {
      // Ask for the mic first, so a denial fails fast with a clear message.
      await navigator.mediaDevices.getUserMedia({ audio: true });

      const res = await fetch(TOKEN_ENDPOINT);
      if (!res.ok) throw new Error(`token request failed (${res.status})`);
      const { token } = await res.json();
      if (!token) throw new Error('no token returned');

      conversation = await Conversation.startSession({
        conversationToken: token,
        connectionType: 'webrtc',
        // Client tools the agent can call. find_buildings gives it LiftSpot's
        // real catalogue (Step 2). App-control tools (open a building, filter
        // the map) can join this map later.
        clientTools: { find_buildings: findBuildings },
        onConnect: () => { setState('listening'); announce('Connected. Take your time. You can talk now.'); },
        onDisconnect: () => { conversation = null; setState('idle'); announce('The conversation has ended.'); closeOverlay(); },
        onModeChange: ({ mode }) => {
          if (!conversation) return;
          if (mode === 'speaking') { setState('speaking'); announce('The guide is talking.'); }
          else { setState('listening'); announce('Your turn. Take your time.'); }
        },
        onMessage: ({ message, source }) => {
          renderCaption(message, source);
          // Let screen readers hear the user's own words echoed back, calmly.
          if (source === 'user') announce(`You said: ${message}`);
        },
        onError: err => {
          console.error('Voice agent error', err);
          announce('Something went wrong with the voice agent.');
          showStatus('Something went wrong. You can close this and try again.');
          toast?.('Voice agent error. Please try again.', { error: true });
        },
      });
    } catch (err) {
      console.error('Could not start voice agent', err);
      conversation = null;
      setState('idle');
      const denied = err && (err.name === 'NotAllowedError' || err.name === 'SecurityError');
      const msg = denied
        ? 'The microphone is off. Allow the microphone, then try again.'
        : 'Could not start the voice agent. Please try again.';
      announce(msg);
      toast?.(msg, { error: true });
      closeOverlay();
    } finally {
      starting = false;
    }
  }

  async function stop() {
    announce('Ending the conversation.');
    const c = conversation;
    conversation = null;
    setState('idle');
    closeOverlay();
    if (c) {
      try { await c.endSession(); }
      catch (err) { console.error('Error ending voice session', err); }
    }
  }

  const toggle = () => { (conversation || starting) ? stop() : start(); };

  btn.addEventListener('click', toggle);
  endBtn?.addEventListener('click', stop);
  closeBtn?.addEventListener('click', stop);
  overlay?.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.stopPropagation(); stop(); }
  });

  setState('idle');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
