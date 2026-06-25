// Mints a short-lived ElevenLabs WebRTC conversation token so the browser can
// start a voice conversation WITHOUT ever seeing the API key. The key and the
// agent id live only in Netlify env vars, server-side. The browser gets back a
// single throwaway token and nothing else.
//
// Env vars (set locally in .env for `netlify dev`, and in the Netlify
// dashboard for production):
//   ELEVENLABS_API_KEY   — your secret xi-api-key
//   ELEVENLABS_AGENT_ID  — the agent to talk to (not secret, but kept here too)

export default async () => {
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
