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

  const area = document.getElementById('now-playing');
  const audio = area.querySelector('[data-audio]');
  const guildAvatar = area.querySelector('[data-guild-avatar]');
  const gotoBtn = area.querySelector('[data-goto]');

  if (record.source_type === 'attachment') {
    // acquire stable cached blob first
    const blobUrl = await acquireBlob(record);
    if (!blobUrl) return; // failed to acquire

    audio.src = blobUrl;
    audio.hidden = false;
    document.querySelector('iframe')?.remove();
  } else {
    audio.hidden = true;
    // iframe handling later
  }

  guildAvatar.src = guildAvatarUrl(record.guild_id);
  area.querySelector('[data-art]').src = record.cover || '';
  area.querySelector('[data-label]').textContent = record.label;
  gotoBtn.onclick = () => {
    document.querySelector(`[data-message-id="${record.message_id}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  area.hidden = false;
  audio.play();
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
