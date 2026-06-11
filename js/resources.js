/* Resources: the elevator community directory. All links verified live (June 2026).
   Fandom/ElevatorWorld block automated checks but are stable, well-known sites. */

const GROUPS = [
  {
    title: 'Communities',
    items: [
      { name: 'Elevatorpedia', url: 'https://elevation.fandom.com/wiki/Elevator_Wiki', desc: 'The elevator wiki — brands, fixtures, history, everything' },
      { name: 'Elevator Community Wiki', url: 'https://elevatorcommunity.fandom.com/wiki/Elevator_Community_Wiki', desc: 'The filmers’ own wiki — people, meetups, culture' },
      { name: 'r/Elevators', url: 'https://www.reddit.com/r/Elevators/', desc: 'Reddit’s elevator community' },
      { name: 'Dat Elevator Community', url: 'https://discord.com/invite/dat-elevator-community-395073624454987776', desc: 'Discord server, 1,500+ enthusiasts, weekly events' },
      { name: 'VatorTrader', url: 'https://www.vatortrader.com', desc: 'Forum run by elevator technicians — deep technical answers' },
    ],
  },
  {
    title: 'Watch',
    items: [
      { name: 'DieselDucy / elevaTOURS', url: 'https://www.youtube.com/@DieselDucy', desc: 'The original elevator filmer — 7,000+ videos since 1993' },
      { name: 'The Elevator Channel', url: 'https://www.youtube.com/@TheElevatorChannel', desc: 'Jacob Bachta’s tours and restorations' },
    ],
  },
  {
    title: 'Learn',
    items: [
      { name: 'Elevator World', url: 'https://elevatorworld.com', desc: 'The industry magazine, publishing since 1953' },
      { name: 'The Elevator Museum', url: 'https://en.wikipedia.org/wiki/The_Elevator_Museum', desc: 'Amesbury, MA — a day trip with real historic cabs' },
      { name: 'Elevator U', url: 'https://www.elevatoru.org', desc: 'Education nonprofit for vertical transportation' },
      { name: 'NAEC', url: 'https://www.naec.org', desc: 'National Association of Elevator Contractors' },
      { name: 'NEII', url: 'https://neii.org', desc: 'National Elevator Industry — codes and safety standards' },
    ],
  },
];

import { trapFocus } from './focus.js';

let els = null;
let lastFocus = null;

export function initResources({ btn, modal, scrim, closeBtn, body }) {
  els = { btn, modal, scrim, closeBtn, body };
  trapFocus(modal);

  body.innerHTML = GROUPS.map(g => `
    <div class="res-group">
      <h3>${g.title}</h3>
      ${g.items.map(i => `
        <a class="res-row" href="${i.url}" target="_blank" rel="noreferrer">
          <span class="res-main">
            <span class="res-name">${i.name}</span>
            <span class="res-desc">${i.desc}</span>
          </span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
        </a>`).join('')}
    </div>`).join('');

  btn.addEventListener('click', () => show(true));
  closeBtn.addEventListener('click', () => show(false));
  scrim.addEventListener('click', () => show(false));
  // Capture phase so Escape closes the modal without also closing a drawer behind it
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && els.modal.classList.contains('open')) {
      e.stopPropagation();
      show(false);
    }
  }, true);
}

function show(open) {
  if (open) lastFocus = document.activeElement;
  els.modal.classList.toggle('open', open);
  els.modal.setAttribute('aria-hidden', String(!open));
  els.scrim.classList.toggle('show', open);
  els.btn.setAttribute('aria-expanded', String(open));
  if (open) els.closeBtn.focus();
  else { lastFocus?.focus?.(); lastFocus = null; }
}
