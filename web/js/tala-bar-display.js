/**
 * TalaBarDisplay — Swara-Sahitya tala bar grid visualization.
 *
 * Renders a CSS Grid where columns = total_aksharas x speed,
 * with component boundaries, swara/sahitya rows, and beat markers.
 * Syncs highlighting to audio playback via timeupdate.
 */
class TalaBarDisplay {
  /**
   * @param {HTMLElement} container - Container to render the tala bar grid.
   * @param {HTMLAudioElement} [audioEl] - Optional audio element for playback sync.
   */
  constructor(container, audioEl) {
    this._container = container;
    this._audio = audioEl || null;
    this._tala = null;
    this._bars = [];
    this._speed = 1;
    this._activeCol = -1;
    this._barStartMs = 0;
    this._barEndMs = 0;

    if (this._audio) {
      this._boundUpdate = this._onTimeUpdate.bind(this);
      this._audio.addEventListener('timeupdate', this._boundUpdate);
    }
  }

  // ── Beat marker symbols ──
  static BEAT_SYMBOLS = {
    laghu_start: '\u{1F44F}', // Clap (simplified as |)
    laghu_count: '\u00B7',    // Middle dot for finger counts
    drutam_clap: '\u25CB',    // Circle (clap)
    drutam_wave: '\u25CB',    // Circle (wave)
    anudrutam:   '\u2022',    // Bullet
  };

  /**
   * Set the tala definition.
   * @param {Object} tala - Tala object with id, components, beat_pattern, total_aksharas
   */
  setTala(tala) {
    this._tala = tala;
  }

  /**
   * Render bars from composition bar data.
   * @param {Array} bars - Array of bar objects { swaras, saahitya, speed }
   * @param {Object} [opts] - Options
   * @param {number} [opts.barStartMs] - Start time of first bar in ms
   * @param {number} [opts.barEndMs] - End time of last bar in ms
   */
  renderBars(bars, opts = {}) {
    this._bars = bars || [];
    this._barStartMs = opts.barStartMs || 0;
    this._barEndMs = opts.barEndMs || 0;
    this._render();
  }

  /**
   * Render an empty grid for the current tala (for composition editing).
   * @param {number} [numCycles=1] - Number of tala cycles to show
   * @param {number} [speed=1] - Speed multiplier
   */
  renderEmpty(numCycles = 1, speed = 1) {
    if (!this._tala) {
      this._container.innerHTML = '<div class="tala-empty">Select a tala to display grid.</div>';
      return;
    }

    this._speed = speed;
    const cols = this._tala.total_aksharas * speed;
    this._bars = [];

    for (let c = 0; c < numCycles; c++) {
      const bar = {
        swaras: Array(cols).fill({ swara_id: '-', octave: 'madhya' }),
        saahitya: Array(cols).fill(''),
        speed,
      };
      this._bars.push(bar);
    }

    this._render();
  }

  /**
   * Clear the display.
   */
  clear() {
    this._container.innerHTML = '';
    this._bars = [];
  }

  /**
   * Destroy and remove event listeners.
   */
  destroy() {
    if (this._audio && this._boundUpdate) {
      this._audio.removeEventListener('timeupdate', this._boundUpdate);
    }
    this.clear();
  }

  // ── Private ──

  _onTimeUpdate() {
    if (!this._bars.length || !this._barEndMs) return;

    const currentMs = this._audio.currentTime * 1000;
    if (currentMs < this._barStartMs || currentMs > this._barEndMs) {
      if (this._activeCol >= 0) {
        this._clearHighlight();
        this._activeCol = -1;
      }
      return;
    }

    const totalPositions = this._bars.reduce((sum, b) => {
      const swaras = Array.isArray(b.swaras) ? b.swaras : [];
      return sum + swaras.length;
    }, 0);

    if (!totalPositions) return;

    const elapsed = currentMs - this._barStartMs;
    const totalDuration = this._barEndMs - this._barStartMs;
    const positionIdx = Math.floor((elapsed / totalDuration) * totalPositions);

    if (positionIdx !== this._activeCol && positionIdx >= 0 && positionIdx < totalPositions) {
      this._clearHighlight();
      this._activeCol = positionIdx;

      // Find the cell and highlight it
      const cells = this._container.querySelectorAll('.tala-bar-cell');
      if (cells[positionIdx]) {
        cells[positionIdx].classList.add('tala-bar-cell--active');
      }
    }
  }

  _clearHighlight() {
    this._container.querySelectorAll('.tala-bar-cell--active').forEach(el => {
      el.classList.remove('tala-bar-cell--active');
    });
  }

  _render() {
    this._container.innerHTML = '';

    if (!this._tala || !this._bars.length) {
      this._container.innerHTML = '<div class="tala-empty">No tala data to display.</div>';
      return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'tala-bar-container';

    this._bars.forEach((bar, cycleIdx) => {
      const cycleEl = document.createElement('div');
      cycleEl.className = 'tala-cycle-row';

      // Cycle label
      const labelEl = document.createElement('div');
      labelEl.className = 'tala-cycle-label';
      labelEl.textContent = `Cycle ${cycleIdx + 1}`;
      cycleEl.appendChild(labelEl);

      // Build the grid
      const swaras = Array.isArray(bar.swaras) ? bar.swaras : [];
      const sahitya = Array.isArray(bar.saahitya) ? bar.saahitya : [];
      const cols = swaras.length || this._tala.total_aksharas;

      const grid = document.createElement('div');
      grid.className = 'tala-bar-grid';
      grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

      // Determine component boundaries
      const boundaries = this._getComponentBoundaries(cols, bar.speed || 1);

      // Row 1: Component labels
      this._renderLabelRow(grid, cols, boundaries, bar.speed || 1);

      // Row 2: Beat markers
      this._renderBeatRow(grid, cols, boundaries, bar.speed || 1);

      // Row 3: Swaras
      this._renderSwaraRow(grid, swaras, boundaries);

      // Row 4: Sahitya
      this._renderSahityaRow(grid, sahitya, boundaries);

      cycleEl.appendChild(grid);
      wrapper.appendChild(cycleEl);
    });

    this._container.appendChild(wrapper);
  }

  _getComponentBoundaries(cols, speed) {
    if (!this._tala) return [];
    const boundaries = [];
    let pos = 0;
    this._tala.beat_pattern.forEach((beats, compIdx) => {
      boundaries.push({
        start: pos * speed,
        end: (pos + beats) * speed,
        component: this._tala.components[compIdx] || 'laghu',
        beats: beats,
      });
      pos += beats;
    });
    return boundaries;
  }

  _renderLabelRow(grid, cols, boundaries, speed) {
    for (let i = 0; i < cols; i++) {
      const cell = document.createElement('div');
      cell.className = 'tala-bar-cell tala-bar-row--label';

      const boundary = boundaries.find(b => i >= b.start && i < b.end);
      if (boundary && i === boundary.start) {
        const abbr = boundary.component === 'laghu' ? 'L'
          : boundary.component === 'drutam' ? 'D'
          : boundary.component === 'anudrutam' ? 'A' : '';
        cell.textContent = abbr;
        cell.classList.add('tala-bar-cell--component-start');
      }

      grid.appendChild(cell);
    }
  }

  _renderBeatRow(grid, cols, boundaries, speed) {
    for (let i = 0; i < cols; i++) {
      const cell = document.createElement('div');
      cell.className = 'tala-bar-cell tala-bar-row--beat';

      const boundary = boundaries.find(b => i >= b.start && i < b.end);
      if (boundary) {
        if (i === boundary.start) {
          cell.classList.add('tala-bar-cell--component-start');
        }
        // Beat marker at akshara positions (every `speed` columns)
        if ((i - boundary.start) % speed === 0) {
          const aksharaInComp = (i - boundary.start) / speed;
          const marker = document.createElement('span');
          marker.className = 'tala-beat-marker';

          if (boundary.component === 'laghu') {
            marker.textContent = aksharaInComp === 0 ? '|' : '\u00B7';
          } else if (boundary.component === 'drutam') {
            marker.textContent = aksharaInComp === 0 ? 'O' : '\u25CB';
          } else {
            marker.textContent = '\u2022';
          }
          cell.appendChild(marker);
        }
      }

      grid.appendChild(cell);
    }
  }

  _renderSwaraRow(grid, swaras, boundaries) {
    const script = (typeof MultilingualDisplay !== 'undefined')
      ? MultilingualDisplay.primaryScript
      : 'iast';

    swaras.forEach((note, i) => {
      const cell = document.createElement('div');
      cell.className = 'tala-bar-cell tala-bar-row--swara';

      const boundary = boundaries.find(b => i >= b.start && i < b.end);
      if (boundary && i === boundary.start) {
        cell.classList.add('tala-bar-cell--component-start');
      }

      const swaraId = typeof note === 'string' ? note : (note.swara_id || '-');

      if (swaraId !== '-' && swaraId !== ',') {
        const name = (typeof MultilingualDisplay !== 'undefined')
          ? MultilingualDisplay.getSwaraName(swaraId, script)
          : swaraId;
        cell.textContent = name;

        // Swara color
        const colors = {
          Sa: '#66bb6a', Ri1: '#42a5f5', Ri2: '#5b9bd5',
          Ga1: '#5b9bd5', Ga2: '#b388ff', Ga3: '#a07de0',
          Ma1: '#e0a840', Ma2: '#d4912a', Pa: '#e05555',
          Dha1: '#4dd0e1', Dha2: '#26c6da',
          Ni1: '#4dd0e1', Ni2: '#ec407a', Ni3: '#e91e63',
        };
        if (colors[swaraId]) cell.style.color = colors[swaraId];

        // Octave indicator
        const octave = typeof note === 'object' ? note.octave : 'madhya';
        if (octave === 'mandra') cell.style.borderBottom = '2px solid currentColor';
        if (octave === 'tara') cell.style.borderTop = '2px solid currentColor';
      } else {
        cell.textContent = swaraId === ',' ? '\u2014' : '\u00B7';
        cell.style.color = 'var(--text-muted, #9a8e7e)';
      }

      grid.appendChild(cell);
    });
  }

  _renderSahityaRow(grid, sahitya, boundaries) {
    const cols = sahitya.length || (this._tala ? this._tala.total_aksharas : 0);

    for (let i = 0; i < cols; i++) {
      const cell = document.createElement('div');
      cell.className = 'tala-bar-cell tala-bar-row--sahitya';

      const boundary = boundaries.find(b => i >= b.start && i < b.end);
      if (boundary && i === boundary.start) {
        cell.classList.add('tala-bar-cell--component-start');
      }

      const text = sahitya[i];
      if (typeof text === 'string') {
        cell.textContent = text;
      } else if (text && text.text) {
        cell.textContent = text.text;
      }

      grid.appendChild(cell);
    }
  }
}
