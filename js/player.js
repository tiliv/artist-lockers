---
---
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
  guildAvatar.src = guildAvatarUrl(record.guild.id); // from auth detail

  document.getElementById('np-art').src = record.embed?.thumbnail_url || '';
  document.getElementById('np-label').textContent = record.label;

  // wire goto button to scroll the li into view
  const gotoBtn = document.getElementById('np-goto');
  gotoBtn.onclick = () => {
    document.querySelector(`li[data-player*="${record.message.id}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  nowPlaying.hidden = false;
  audio.play();

  return false;
}

async function acquireBlob(record) {
  const key = record.message.id;

  // check OPFS first
  try {
    const root = await navigator.storage.getDirectory();
    const file = await root.getFileHandle(key);
    const buffer = await (await file.getFile()).arrayBuffer();
    return URL.createObjectURL(new Blob([buffer], {
      type: record.attachment.content_type,
    }));
  } catch {
    // not cached
  }

  // try IPFS if we have a CID
  if (record.ipfs_cid) {
    try {
      const res = await fetch(`https://{{ site.pinata_gateway }}/ipfs/${record.ipfs_cid}`);
      if (!res.ok) throw new Error(`IPFS fetch failed: ${res.status}`);
      const buffer = await res.arrayBuffer();
      await writeToOPFS(key, buffer);
      return URL.createObjectURL(
        new Blob([buffer], { type: record.attachment.content_type })
      );
    } catch (e) {
      console.warn('IPFS fetch failed, falling back to CDN:', e);
    }
  }

  // fall back to CDN direct src, no blob acquisition possible
  return record.url;
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
