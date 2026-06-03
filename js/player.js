---
---

document.addEventListener('click', (event) => {
  const item = event.target.closest('[data-message-id]');
  if (!item) return;
  event.preventDefault();
  try { openPlayer(item); } catch (_) {}
});

window.openPlayer = async function openPlayer(source) {
  const record = source instanceof Element
    ? JSON.parse(source.dataset.player)
    : source;

  const nowPlaying = document.getElementById('now-playing');
  const audio = document.getElementById('np-audio');

  if (record.source_type === 'attachment') {
    // acquire stable cached blob first
    const blobUrl = await acquireBlob(record);
    if (!blobUrl) return; // failed to acquire

    audio.src = blobUrl;
    audio.hidden = false;
    document.querySelector('iframe#np-embed')?.remove();
  } else {
    audio.hidden = true;
    // iframe handling later
  }

  // stamp guild avatar
  const guildAvatar = document.getElementById('np-guild-avatar');
  guildAvatar.src = guildAvatarUrl(record.guild_id);

  document.getElementById('np-art').src = record.cover || '';
  document.getElementById('np-label').textContent = record.label;

  // wire goto button to scroll the li into view
  const gotoBtn = document.getElementById('np-goto');
  gotoBtn.onclick = () => {
    document.querySelector(`li[data-message-id="${record.message_id}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  nowPlaying.hidden = false;
  audio.play();

  return false;
}

async function acquireBlob(record) {
  const key = record.message_id;

  // check local
  try {
    const root = await navigator.storage.getDirectory();
    const file = await root.getFileHandle(key);
    const buffer = await (await file.getFile()).arrayBuffer();
    return URL.createObjectURL(new Blob([buffer], {
      type: record.content_type,
    }));
  } catch {
    // not cached
  }

  // check decentralized
  if (record.cid) {
    try {
      const res = await fetch(`https://{{ site.pinata_gateway }}/ipfs/${record.cid}`);
      if (!res.ok) throw new Error(`IPFS fetch failed: ${res.status}`);
      const buffer = await res.arrayBuffer();
      await writeToOPFS(key, buffer);
      return URL.createObjectURL(
        new Blob([buffer], { type: record.content_type })
      );
    } catch (e) {
      console.warn('IPFS fetch failed, falling back to CDN:', e);
    }
  }

  // use discord CDN. this is will not work after the cdn url's expiration
  return record.cdn;
}

async function writeToOPFS(key, buffer) {
  try {
    const root = await navigator.storage.getDirectory();
    const file = await root.getFileHandle(key, { create: true });
    const writable = await file.createWritable();
    await writable.write(buffer);
    await writable.close();
  } catch (e) {
    console.warn('OPFS write failed:', e);
  }
}
