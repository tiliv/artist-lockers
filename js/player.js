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
  const key = record.message.id; // stable, no query params

  // check OPFS first
  try {
    const root = await navigator.storage.getDirectory();
    const file = await root.getFileHandle(key);
    const blob = await (await file.getFile()).arrayBuffer();
    return URL.createObjectURL(new Blob([blob], {
      type: record.attachment.content_type,
    }));
  } catch {
    // not cached, fetch live
  }

  // fetch from CDN (may be expired — handle that separately)
  try {
    const res = await fetch(record.url);
    if (!res.ok) throw new Error(`fetch failed: ${res.status}`);
    const buffer = await res.arrayBuffer();

    // persist to OPFS
    try {
      const root = await navigator.storage.getDirectory();
      const file = await root.getFileHandle(key, { create: true });
      const writable = await file.createWritable();
      await writable.write(buffer);
      await writable.close();
    } catch (e) {
      console.warn('OPFS write failed:', e);
    }

    return URL.createObjectURL(
      new Blob([buffer], { type: record.attachment.content_type })
    );
  } catch (e) {
    console.error('acquireBlob failed:', e);
    return null;
  }
}
