---
avatar_url: "https://cdn.discordapp.com/avatars/${detail.user.id}/${detail.user.avatar}.png"
guild_logo: "https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.${ext}"
---
import { initAuth, login, logout } from "./discord-auth.js";

document.addEventListener("DOMContentLoaded", async () => {
  await initAuth();
});

window.addEventListener("auth:needed", ({ detail }) => {
  document.getElementById("auth-gate").style.display = "flex";
  if (detail?.error) {
    const el = document.getElementById("auth-error");
    el.style.display = "block";
    el.textContent = detail.error;
  }
});

window.addEventListener("auth:ready", ({ detail }) => {
  window.__auth = detail; // { user, matchedGuilds, token }
  document.getElementById("auth-gate").style.display = "none";
  document.getElementById("auth-user").style.display = "flex";
  document.getElementById("auth-avatar").src = `{{ page.avatar_url }}`;
  document.getElementById("auth-username").textContent = detail.user.global_name;
  for (const guild of detail.matchedGuilds) {
    const el = document.querySelector(`[data-guild-id="${guild.id}"]`);
    if (el) {
      el.style.display = "block";
      const ext = guild.icon?.startsWith("a_") ? "gif" : "png";
      const logo = el.querySelector(".logo");
      if (logo) logo.src = `{{ page.guild_logo }}`;
    }
  }
});

function guildAvatarUrl(guildId) {
  const guild = window.__auth?.matchedGuilds.find(
    g => String(g.id) === String(guildId)
  );
  if (!guild?.icon) return '';
  const ext = guild.icon.startsWith('a_') ? 'gif' : 'png';
  return `{{ page.guild_logo }}`;
}

window.login = login;
window.logout = logout;
window.guildAvatarUrl = guildAvatarUrl;
