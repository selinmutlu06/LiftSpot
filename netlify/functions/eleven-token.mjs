// Mints a short-lived ElevenLabs WebRTC conversation token so the browser can
// start a voice conversation WITHOUT ever seeing the API key. The key and the
// agent id live only in Netlify env vars, server-side. The browser gets back a
// single throwaway token and nothing else.
//
// Env vars (set locally in .env for `netlify dev`, and in the Netlify
// dashboard for production):
//   ELEVENLABS_API_KEY   — your secret xi-api-key
//   ELEVENLABS_AGENT_ID  — the agent to talk to (not secret, but kept here too)

// Only LiftSpot's own pages get a token. Browsers mark same-site requests with
// Sec-Fetch-Site, and send Origin/Referer otherwise. A script can fake these,
// so this stops casual reuse, not a determined attacker. The real ceiling is
// on the ElevenLabs agent itself: auth on, this site's hostname allowlisted,
// 3 calls at once, 100 a day, 5 minutes each.
const ALLOWED = /^(liftspot\.netlify\.app|[\w-]+--liftspot\.netlify\.app|localhost|127\.0\.0\.1)$/;

function fromOurSite(req) {
  if (req.headers.get('sec-fetch-site') === 'same-origin') return true;
  for (const h of ['origin', 'referer']) {
    const v = req.headers.get(h);
    if (!v) continue;
    try { return ALLOWED.test(new URL(v).hostname); } catch { return false; }
  }
  return false;
}

// Per-visitor limit: 6 tokens per IP per 10 minutes. It lives in memory, so it
// resets when Netlify starts a fresh instance; it slows down a loop, and the
// agent's daily cap catches the rest.
const WINDOW_MS = 10 * 60 * 1000, MAX_PER_WINDOW = 6;
const hits = new Map();

function overLimit(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter(t => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > MAX_PER_WINDOW;
}

export default async (req, context) => {
  if (!fromOurSite(req)) return json({ error: 'Not allowed.' }, 403);
  const ip = context?.ip || req.headers.get('x-nf-client-connection-ip') || 'unknown';
  if (overLimit(ip)) return json({ error: 'Too many voice sessions. Try again in a few minutes.' }, 429);

  const apiKey = process.env.ELEVENLABS_API_KEY;
  const agentId = process.env.ELEVENLABS_AGENT_ID;

  if (!apiKey || !agentId) {
    console.error('Voice token: missing ELEVENLABS_API_KEY or ELEVENLABS_AGENT_ID');
    return json({ error: 'Voice agent is not configured.' }, 500);
  }

  try {
    const url = `https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=${encodeURIComponent(agentId)}`;
    const res = await fetch(url, { headers: { 'xi-api-key': apiKey } });

    if (!res.ok) {
      const detail = await res.text();
      console.error('Voice token: ElevenLabs request failed', res.status, detail);
      return json({ error: 'Could not start the voice agent.' }, 502);
    }

    const data = await res.json();
    if (!data.token) {
      console.error('Voice token: response had no token', data);
      return json({ error: 'Could not start the voice agent.' }, 502);
    }
    return json({ token: data.token }, 200);
  } catch (err) {
    console.error('Voice token: request errored', err);
    return json({ error: 'Could not start the voice agent.' }, 502);
  }
};

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  });
}

// Clean public route: the browser fetches /api/voice-token.
export const config = { path: '/api/voice-token' };
