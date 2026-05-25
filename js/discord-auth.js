---
---
/**
 * Discord OAuth2 public client + PKCE auth flow.
 */
const AUTH = {
  CLIENT_ID: "{{ site.oauth_client_id }}",
  REDIRECT_URI: window.location.origin + window.location.pathname,
  SCOPES: "identify guilds",
  KNOWN_GUILDS: new Set([
    {%- for guild in site.data -%}
      "{{ guild[0] }}"{% unless forloop.last %},{% endunless %}
    {%- endfor -%}
  ]),
};

const STORAGE = {
  STATE:    "discord_oauth_state",
  VERIFIER: "discord_oauth_verifier",
  TOKEN:    "discord_oauth_token",
  USER:     "discord_oauth_user",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function randomBytes() {
  const arr = new Uint8Array(16);
  crypto.getRandomValues(arr);
  return Array.from(arr, b => b.toString(16).padStart(2, "0")).join("");
}

async function generatePKCE() {
  const verifier = randomBytes() + randomBytes(); // 64 chars, within 43–128
  const data = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const challenge = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
  return { verifier, challenge };
}

function clearAuth() {
  Object.values(STORAGE).forEach(k => sessionStorage.removeItem(k));
}

function cleanUrl() {
  history.replaceState(null, "", window.location.pathname);
}

function getStoredToken() {
  return sessionStorage.getItem(STORAGE.TOKEN);
}

function getStoredUser() {
  const raw = sessionStorage.getItem(STORAGE.USER);
  return raw ? JSON.parse(raw) : null;
}

// ── Discord API ───────────────────────────────────────────────────────────────

async function exchangeCode(code) {
  const verifier = sessionStorage.getItem(STORAGE.VERIFIER);
  if (!verifier) throw new Error("Missing code_verifier");
  const res = await fetch("https://discord.com/api/oauth2/token", {
    method: "POST",
    body: new URLSearchParams({
      client_id: AUTH.CLIENT_ID,
      grant_type: "authorization_code",
      code,
      redirect_uri: AUTH.REDIRECT_URI,
      code_verifier: verifier,
    }),
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  if (!res.ok) throw new Error(`Token exchange failed: ${res.status}`);
  return res.json();
}

async function fetchUser(token) {
  const res = await fetch("https://discord.com/api/v10/users/@me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`User fetch failed: ${res.status}`);
  return res.json();
}

async function fetchGuilds(token) {
  const res = await fetch("https://discord.com/api/v10/users/@me/guilds", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Guilds fetch failed: ${res.status}`);
  return res.json();
}

// ── Auth Flow ─────────────────────────────────────────────────────────────────

async function redirectToDiscord() {
  const state = randomBytes();
  const { verifier, challenge } = await generatePKCE();
  sessionStorage.setItem(STORAGE.STATE, state);
  sessionStorage.setItem(STORAGE.VERIFIER, verifier);
  const url = new URL("https://discord.com/oauth2/authorize");
  url.searchParams.set("client_id", AUTH.CLIENT_ID);
  url.searchParams.set("redirect_uri", AUTH.REDIRECT_URI);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", AUTH.SCOPES);
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  window.location.href = url.toString();
}

async function handleCallback(code, returnedState) {
  const expectedState = sessionStorage.getItem(STORAGE.STATE);
  if (!expectedState || returnedState !== expectedState) {
    throw new Error("State mismatch — possible CSRF");
  }
  sessionStorage.removeItem(STORAGE.STATE);

  const { access_token } = await exchangeCode(code);
  sessionStorage.removeItem(STORAGE.VERIFIER);

  const [user, guilds] = await Promise.all([
    fetchUser(access_token),
    fetchGuilds(access_token),
  ]);

  const matchedGuilds = guilds.filter(g => AUTH.KNOWN_GUILDS.has(String(g.id)));
  if (matchedGuilds.length === 0) {
    throw new Error("Not a member of any supported server");
  }

  sessionStorage.setItem(STORAGE.TOKEN, access_token);
  sessionStorage.setItem(STORAGE.USER, JSON.stringify({ user, matchedGuilds }));

  return { user, matchedGuilds, token: access_token };
}

// ── Entry Point ───────────────────────────────────────────────────────────────

export async function initAuth() {
  const params = new URLSearchParams(window.location.search);
  const code  = params.get("code");
  const state = params.get("state");
  const error = params.get("error");

  if (error) {
    cleanUrl();
    clearAuth();
    window.dispatchEvent(new CustomEvent("auth:needed", { detail: { error } }));
    return null;
  }

  if (code && state) {
    cleanUrl();
    try {
      const result = await handleCallback(code, state);
      window.dispatchEvent(new CustomEvent("auth:ready", { detail: result }));
      return result;
    } catch (err) {
      console.error("Auth failed:", err.message);
      clearAuth();
      window.dispatchEvent(new CustomEvent("auth:needed", { detail: { error: err.message } }));
      return null;
    }
  }

  const token = getStoredToken();
  const stored = getStoredUser();
  if (token && stored) {
    window.dispatchEvent(new CustomEvent("auth:ready", { detail: { ...stored, token } }));
    return { ...stored, token };
  }

  window.dispatchEvent(new CustomEvent("auth:needed"));
  return null;
}

export { redirectToDiscord as login, clearAuth as logout };
