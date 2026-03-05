/**
 * LyricsSync — Audio-text sync engine with timeupdate-driven highlighting.
 *
 * Provides karaoke-style lyrics highlighting during audio playback,
 * with multilingual script support via MultilingualDisplay.
 */
class LyricsSync {
  /**
   * @param {HTMLAudioElement} audioEl - The audio element to sync with.
   * @param {HTMLElement} container - Container to render lyrics blocks into.
   */
  constructor(audioEl, container) {
    this._audio = audioEl;
    this._container = container;
    this._data = null;
    this._blocks = [];
    this._activeBlockId = null;
    this._boundUpdate = this._onTimeUpdate.bind(this);
    this._audio.addEventListener('timeupdate', this._boundUpdate);
  }

  /**
   * Load lyrics for a track by fetching from the API.
   * @param {string} trackId - e.g. "sama_1_setu"
   * @returns {Promise<boolean>} true if lyrics were found
   */
  async loadTrackLyrics(trackId) {
    this._data = null;
    this._blocks = [];
    this._activeBlockId = null;

    if (!trackId) {
      this._renderEmpty('No track selected.');
      return false;
    }

    try {
      const res = await fetch(`/api/v1/lyrics/${encodeURIComponent(trackId)}`);
      if (!res.ok) {
        if (res.status === 404) {
          this._renderEmpty('No lyrics available for this track.');
          return false;
        }
        throw new Error(res.statusText);
      }
      this._data = await res.json();
      this._blocks = this._data.blocks || [];
      this._render();
      return true;
    } catch (err) {
      console.warn('LyricsSync: Failed to load lyrics:', err);
      this._renderEmpty('No lyrics available for this track.');
      return false;
    }
  }

  /**
   * Set lyrics data directly (without fetching).
   * @param {Object} data - Lyrics JSON data
   */
  setData(data) {
    this._data = data;
    this._blocks = data?.blocks || [];
    this._activeBlockId = null;
    this._render();
  }

  /**
   * Clear lyrics display.
   */
  clear() {
    this._data = null;
    this._blocks = [];
    this._activeBlockId = null;
    this._container.innerHTML = '';
  }

  /**
   * Destroy the instance and remove event listeners.
   */
  destroy() {
    this._audio.removeEventListener('timeupdate', this._boundUpdate);
    this.clear();
  }

  // ── Private ──

  _onTimeUpdate() {
    if (!this._blocks.length) return;

    const currentMs = this._audio.currentTime * 1000;
    let newActiveId = null;

    for (const block of this._blocks) {
      if (currentMs >= block.start_ms && currentMs < block.end_ms) {
        newActiveId = block.id;
        break;
      }
    }

    if (newActiveId !== this._activeBlockId) {
      // Remove old highlight
      if (this._activeBlockId) {
        const oldEl = this._container.querySelector(`[data-block-id="${this._activeBlockId}"]`);
        if (oldEl) oldEl.classList.remove('lyrics-block--active');
      }

      // Add new highlight
      if (newActiveId) {
        const newEl = this._container.querySelector(`[data-block-id="${newActiveId}"]`);
        if (newEl) {
          newEl.classList.add('lyrics-block--active');
          // Auto-scroll into view
          newEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }

      this._activeBlockId = newActiveId;
    }
  }

  _render() {
    this._container.innerHTML = '';

    if (!this._blocks.length) {
      this._renderEmpty('No lyrics available.');
      return;
    }

    const lyricsDiv = document.createElement('div');
    lyricsDiv.className = 'lyrics-container';

    this._blocks.forEach(block => {
      const blockEl = document.createElement('div');
      blockEl.className = 'lyrics-block';
      blockEl.dataset.blockId = block.id;

      // Time label
      const timeEl = document.createElement('div');
      timeEl.className = 'lyrics-block__time';
      timeEl.textContent = this._formatMs(block.start_ms) + ' \u2013 ' + this._formatMs(block.end_ms);
      blockEl.appendChild(timeEl);

      // Text in multiple scripts
      const textEl = document.createElement('div');
      textEl.className = 'lyrics-block__text';
      this._renderBlockText(textEl, block);
      blockEl.appendChild(textEl);

      // Swara labels
      if (block.swaras && block.swaras.length) {
        const swaraEl = document.createElement('div');
        swaraEl.className = 'lyrics-block__swaras';
        swaraEl.textContent = block.swaras.join(' \u2013 ');
        blockEl.appendChild(swaraEl);
      }

      // Click to seek
      blockEl.addEventListener('click', () => {
        this._audio.currentTime = block.start_ms / 1000;
      });

      lyricsDiv.appendChild(blockEl);
    });

    this._container.appendChild(lyricsDiv);
  }

  _renderBlockText(textEl, block) {
    if (!block.text) return;

    const scripts = (typeof MultilingualDisplay !== 'undefined')
      ? MultilingualDisplay.currentScripts
      : ['iast'];

    const fontMap = {
      devanagari: "'Noto Sans Devanagari', 'Vijaya', serif",
      kannada: "'Noto Sans Kannada', serif",
      tamil: "'Noto Sans Tamil', serif",
      telugu: "'Noto Sans Telugu', serif",
      iast: "'Cormorant Garamond', serif",
    };

    scripts.forEach(script => {
      if (!block.text[script]) return;
      const row = document.createElement('span');
      row.className = 'lyrics-block__script-row';
      row.dataset.script = script;
      row.style.fontFamily = fontMap[script] || 'serif';
      row.textContent = block.text[script];
      textEl.appendChild(row);
      textEl.appendChild(document.createElement('br'));
    });
  }

  _renderEmpty(msg) {
    this._container.innerHTML = `<div class="lyrics-empty">${this._escHtml(msg)}</div>`;
  }

  _formatMs(ms) {
    const s = ms / 1000;
    const m = Math.floor(s / 60);
    const sec = (s % 60).toFixed(1);
    return m + ':' + sec.padStart(4, '0');
  }

  _escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }
}
