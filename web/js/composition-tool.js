/**
 * CompositionTool — Bar-based composition editor for Carnatic music.
 *
 * Provides a grid-based editor with swara palette, sahitya input,
 * tala-aware layout, playback preview, save/load, and WAV export.
 */
class CompositionTool {
  /**
   * @param {HTMLElement} container - Main container for the composition editor.
   * @param {Object} [opts]
   * @param {ShrutiDrone} [opts.drone] - Optional ShrutiDrone instance.
   */
  constructor(container, opts = {}) {
    this._container = container;
    this._drone = opts.drone || null;

    // Composition state
    this._id = null;
    this._title = 'Untitled Composition';
    this._raga = '';
    this._talaId = 'triputa_chatusra';
    this._composer = '';
    this._referenceSaHz = 261.63;
    this._tempoBpm = 60;
    this._sections = [{ name: 'Pallavi', lines: [] }];
    this._activeSectionIdx = 0;

    // UI state
    this._selectedCell = null; // { sectionIdx, lineIdx, barIdx, posIdx }
    this._palette = null;
    this._talas = [];
    this._ragas = [];

    // Swara IDs with colors
    this.SWARA_IDS = ['Sa', 'Ri1', 'Ri2', 'Ga2', 'Ga3', 'Ma1', 'Ma2', 'Pa', 'Dha1', 'Dha2', 'Ni2', 'Ni3', '-', ','];
    this.SWARA_COLORS = {
      Sa: '#66bb6a', Ri1: '#42a5f5', Ri2: '#5b9bd5',
      Ga1: '#5b9bd5', Ga2: '#b388ff', Ga3: '#a07de0',
      Ma1: '#e0a840', Ma2: '#d4912a', Pa: '#e05555',
      Dha1: '#4dd0e1', Dha2: '#26c6da',
      Ni1: '#4dd0e1', Ni2: '#ec407a', Ni3: '#e91e63',
    };

    this._boundKeyHandler = this._onKeyDown.bind(this);
  }

  /**
   * Initialize: load talas and ragas from API, render initial UI.
   */
  async init() {
    try {
      const [talasRes, ragasRes] = await Promise.all([
        fetch('/api/v1/talas').then(r => r.json()),
        fetch('/api/v1/ragas').then(r => r.json()),
      ]);
      this._talas = talasRes;
      this._ragas = ragasRes;
    } catch (err) {
      console.warn('CompositionTool: Failed to load reference data:', err);
    }

    this._ensureDefaultLine();
    this.render();
    document.addEventListener('keydown', this._boundKeyHandler);
  }

  /**
   * Destroy the tool and clean up.
   */
  destroy() {
    document.removeEventListener('keydown', this._boundKeyHandler);
    this._closePalette();
    this._container.innerHTML = '';
  }

  /**
   * Load a composition from data (e.g., from API).
   * @param {Object} data
   */
  loadComposition(data) {
    this._id = data.id || null;
    this._title = data.title || 'Untitled';
    this._raga = data.raga || '';
    this._talaId = data.tala_id || 'triputa_chatusra';
    this._composer = data.composer || '';
    this._referenceSaHz = data.reference_sa_hz || 261.63;
    this._sections = (data.sections || []).map(s => ({
      name: s.name,
      lines: (s.lines || []).map(l => ({
        bars: (l.bars || []).map(b => ({
          tala_id: b.tala_id,
          speed: b.speed,
          swaras: (b.swaras || []).map(sw =>
            typeof sw === 'string' ? { swara_id: sw, octave: 'madhya' } : sw
          ),
          saahitya: b.saahitya || [],
        })),
        repeat: l.repeat || 2,
      })),
    }));
    if (!this._sections.length) {
      this._sections = [{ name: 'Pallavi', lines: [] }];
    }
    this._activeSectionIdx = 0;
    this._ensureDefaultLine();
    this.render();
  }

  /**
   * Export composition as JSON data.
   * @returns {Object}
   */
  toJSON() {
    return {
      id: this._id,
      title: this._title,
      raga: this._raga,
      tala_id: this._talaId,
      composer: this._composer,
      reference_sa_hz: this._referenceSaHz,
      sections: this._sections.map(s => ({
        name: s.name,
        lines: s.lines.map(l => ({
          bars: l.bars.map(b => ({
            tala_id: b.tala_id || this._talaId,
            speed: b.speed || 1,
            swaras: b.swaras.map(sw => ({
              swara_id: sw.swara_id || '-',
              octave: sw.octave || 'madhya',
            })),
            saahitya: b.saahitya || [],
          })),
          repeat: l.repeat || 2,
        })),
      })),
    };
  }

  /**
   * Full render of the composition editor.
   */
  render() {
    this._container.innerHTML = '';

    // Metadata panel
    this._renderMetaPanel();

    // Section tabs
    this._renderSectionTabs();

    // Grid editor for active section
    this._renderGrid();

    // Action buttons
    this._renderActions();
  }

  // ── Private: Render sub-sections ──

  _renderMetaPanel() {
    const panel = document.createElement('div');
    panel.className = 'comp-meta-panel';

    // Title
    panel.appendChild(this._field('Title', 'text', this._title, v => { this._title = v; }));

    // Raga dropdown
    const ragaField = this._selectField('Raga', this._ragas.map(r => ({
      value: r.name, label: `${r.name} (#${r.number})`
    })), this._raga, v => { this._raga = v; });
    panel.appendChild(ragaField);

    // Tala dropdown
    const talaField = this._selectField('Tala', this._talas.map(t => ({
      value: t.id, label: `${t.name} (${t.total_aksharas})`
    })), this._talaId, v => {
      this._talaId = v;
      this._ensureDefaultLine();
      this.render();
    });
    panel.appendChild(talaField);

    // Composer
    panel.appendChild(this._field('Composer', 'text', this._composer, v => { this._composer = v; }));

    // Tempo
    const tempoField = document.createElement('div');
    tempoField.className = 'comp-field';
    const tempoLabel = document.createElement('label');
    tempoLabel.textContent = `Tempo (${this._tempoBpm} BPM)`;
    const tempoInput = document.createElement('input');
    tempoInput.type = 'range';
    tempoInput.min = '30';
    tempoInput.max = '180';
    tempoInput.value = String(this._tempoBpm);
    tempoInput.addEventListener('input', (e) => {
      this._tempoBpm = parseInt(e.target.value);
      tempoLabel.textContent = `Tempo (${this._tempoBpm} BPM)`;
    });
    tempoField.appendChild(tempoLabel);
    tempoField.appendChild(tempoInput);
    panel.appendChild(tempoField);

    // Reference Sa
    const saField = this._field('Sa (Hz)', 'number', String(this._referenceSaHz), v => {
      this._referenceSaHz = parseFloat(v) || 261.63;
      if (this._drone) this._drone.setSaHz(this._referenceSaHz);
    });
    panel.appendChild(saField);

    this._container.appendChild(panel);
  }

  _renderSectionTabs() {
    const tabs = document.createElement('div');
    tabs.className = 'comp-sections-tabs';

    this._sections.forEach((sec, i) => {
      const tab = document.createElement('button');
      tab.className = 'comp-section-tab' + (i === this._activeSectionIdx ? ' active' : '');
      tab.textContent = sec.name;
      tab.addEventListener('click', () => {
        this._activeSectionIdx = i;
        this.render();
      });
      tabs.appendChild(tab);
    });

    // Add section button
    const addBtn = document.createElement('button');
    addBtn.className = 'comp-section-tab comp-section-add';
    addBtn.textContent = '+ Section';
    addBtn.addEventListener('click', () => {
      const names = ['Pallavi', 'Anupallavi', 'Charanam', 'Charanam 2', 'Chittaswaram'];
      const existing = this._sections.map(s => s.name);
      const name = names.find(n => !existing.includes(n)) || `Section ${this._sections.length + 1}`;
      this._sections.push({ name, lines: [] });
      this._activeSectionIdx = this._sections.length - 1;
      this._ensureDefaultLine();
      this.render();
    });
    tabs.appendChild(addBtn);

    this._container.appendChild(tabs);
  }

  _renderGrid() {
    const section = this._sections[this._activeSectionIdx];
    if (!section) return;

    const gridWrap = document.createElement('div');
    gridWrap.className = 'comp-grid';

    const tala = this._talas.find(t => t.id === this._talaId);
    const totalAksharas = tala ? tala.total_aksharas : 8;

    section.lines.forEach((line, lineIdx) => {
      line.bars.forEach((bar, barIdx) => {
        const speed = bar.speed || 1;
        const cols = totalAksharas * speed;
        const boundaries = tala ? this._getBoundaries(tala, speed) : [];

        // Ensure swaras/saahitya arrays are the right size
        while (bar.swaras.length < cols) bar.swaras.push({ swara_id: '-', octave: 'madhya' });
        while (bar.saahitya.length < cols) bar.saahitya.push('');

        const row = document.createElement('div');
        row.className = 'comp-bar-row';
        row.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

        // Speed selector for this line
        const speedRow = document.createElement('div');
        speedRow.style.gridColumn = `1 / -1`;
        speedRow.style.display = 'flex';
        speedRow.style.alignItems = 'center';
        speedRow.style.gap = '8px';
        speedRow.style.padding = '4px 8px';
        speedRow.style.background = 'rgba(0,0,0,0.15)';
        speedRow.style.fontSize = '0.6rem';
        speedRow.style.fontFamily = "'Cinzel', serif";
        speedRow.style.color = 'var(--text-muted, #9a8e7e)';
        speedRow.style.letterSpacing = '0.1em';
        speedRow.textContent = `Line ${lineIdx + 1}, Bar ${barIdx + 1} `;

        [1, 2, 3].forEach(sp => {
          const spBtn = document.createElement('button');
          spBtn.style.cssText = 'font-size:0.55rem;padding:2px 6px;border:1px solid rgba(212,168,84,0.15);background:' +
            (sp === speed ? 'rgba(212,168,84,0.1)' : 'transparent') +
            ';color:' + (sp === speed ? 'var(--amber-glow,#d4a854)' : 'var(--text-muted,#9a8e7e)') +
            ';cursor:pointer;border-radius:2px;font-family:Cinzel,serif;letter-spacing:0.05em;';
          spBtn.textContent = sp === 1 ? '1x' : sp === 2 ? '2x' : '3x';
          spBtn.addEventListener('click', () => {
            bar.speed = sp;
            this.render();
          });
          speedRow.appendChild(spBtn);
        });
        row.appendChild(speedRow);

        // Swara cells
        for (let i = 0; i < cols; i++) {
          const cell = document.createElement('div');
          cell.className = 'comp-cell';

          const boundary = boundaries.find(b => i >= b.start && i < b.end);
          if (boundary && i === boundary.start) {
            cell.classList.add('comp-cell--component-start');
          }

          // Swara display
          const swaraDiv = document.createElement('div');
          swaraDiv.className = 'comp-cell__swara';
          const swaraId = bar.swaras[i]?.swara_id || '-';
          const octave = bar.swaras[i]?.octave || 'madhya';

          const script = (typeof MultilingualDisplay !== 'undefined')
            ? MultilingualDisplay.primaryScript
            : 'iast';
          const displayName = (typeof MultilingualDisplay !== 'undefined' && swaraId !== '-' && swaraId !== ',')
            ? MultilingualDisplay.getSwaraName(swaraId, script)
            : swaraId;

          swaraDiv.textContent = displayName;
          if (this.SWARA_COLORS[swaraId]) swaraDiv.style.color = this.SWARA_COLORS[swaraId];
          if (octave === 'mandra') swaraDiv.style.borderBottom = '2px solid currentColor';
          if (octave === 'tara') swaraDiv.style.borderTop = '2px solid currentColor';

          swaraDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            this._selectedCell = { sectionIdx: this._activeSectionIdx, lineIdx, barIdx, posIdx: i };
            this._openPalette(e.clientX, e.clientY);
          });
          cell.appendChild(swaraDiv);

          // Sahitya input
          const sahDiv = document.createElement('div');
          sahDiv.className = 'comp-cell__sahitya';
          const sahInput = document.createElement('input');
          sahInput.value = bar.saahitya[i] || '';
          sahInput.placeholder = '\u00B7';
          sahInput.addEventListener('change', (e) => {
            bar.saahitya[i] = e.target.value;
          });
          sahDiv.appendChild(sahInput);
          cell.appendChild(sahDiv);

          row.appendChild(cell);
        }

        gridWrap.appendChild(row);
      });
    });

    // Add line button
    const addLineBtn = document.createElement('button');
    addLineBtn.className = 'comp-btn';
    addLineBtn.textContent = '+ Add Line';
    addLineBtn.style.marginTop = '8px';
    addLineBtn.addEventListener('click', () => {
      this._addLine();
      this.render();
    });
    gridWrap.appendChild(addLineBtn);

    this._container.appendChild(gridWrap);
  }

  _renderActions() {
    const actions = document.createElement('div');
    actions.className = 'comp-actions';

    const buttons = [
      { label: 'Play Bar', icon: '\u25B6', action: () => this._playBar() },
      { label: 'Play All', icon: '\u25B6\u25B6', action: () => this._playComposition() },
      { label: 'Play + Drone', icon: '\u{1F3B5}', action: () => this._playWithDrone() },
      { label: 'Save', icon: '\u{1F4BE}', primary: true, action: () => this._save() },
      { label: 'Export WAV', icon: '\u{1F4E5}', action: () => this._exportWav() },
      { label: 'Download JSON', icon: '\u{1F4C4}', action: () => this._downloadJson() },
    ];

    buttons.forEach(b => {
      const btn = document.createElement('button');
      btn.className = 'comp-btn' + (b.primary ? ' comp-btn--primary' : '');
      btn.textContent = b.label;
      btn.addEventListener('click', b.action);
      actions.appendChild(btn);
    });

    this._container.appendChild(actions);
  }

  // ── Private: Palette ──

  _openPalette(x, y) {
    this._closePalette();

    const palette = document.createElement('div');
    palette.className = 'swara-palette';
    palette.style.left = Math.min(x, window.innerWidth - 220) + 'px';
    palette.style.top = Math.min(y, window.innerHeight - 300) + 'px';

    // Octave selector
    const octaveRow = document.createElement('div');
    octaveRow.className = 'swara-palette__octave';
    let selectedOctave = 'madhya';

    if (this._selectedCell) {
      const sec = this._sections[this._selectedCell.sectionIdx];
      const bar = sec?.lines[this._selectedCell.lineIdx]?.bars[this._selectedCell.barIdx];
      const note = bar?.swaras[this._selectedCell.posIdx];
      if (note) selectedOctave = note.octave || 'madhya';
    }

    ['mandra', 'madhya', 'tara'].forEach(oct => {
      const btn = document.createElement('button');
      btn.className = 'swara-palette__octave-btn' + (oct === selectedOctave ? ' active' : '');
      btn.textContent = oct === 'mandra' ? 'Lower' : oct === 'madhya' ? 'Middle' : 'Upper';
      btn.addEventListener('click', () => {
        selectedOctave = oct;
        octaveRow.querySelectorAll('.swara-palette__octave-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
      octaveRow.appendChild(btn);
    });
    palette.appendChild(octaveRow);

    // Swara grid
    const grid = document.createElement('div');
    grid.className = 'swara-palette__grid';

    this.SWARA_IDS.forEach(id => {
      const btn = document.createElement('button');
      btn.className = 'swara-palette__btn';

      const script = (typeof MultilingualDisplay !== 'undefined')
        ? MultilingualDisplay.primaryScript
        : 'iast';
      const displayName = (id !== '-' && id !== ',' && typeof MultilingualDisplay !== 'undefined')
        ? MultilingualDisplay.getSwaraName(id, script)
        : id;

      btn.textContent = id === '-' ? 'Rest' : id === ',' ? 'Hold' : displayName;
      if (this.SWARA_COLORS[id]) btn.style.color = this.SWARA_COLORS[id];

      btn.addEventListener('click', () => {
        this._setSwara(id, selectedOctave);
        this._closePalette();
        this.render();
      });
      grid.appendChild(btn);
    });
    palette.appendChild(grid);

    document.body.appendChild(palette);
    this._palette = palette;

    // Close on outside click
    setTimeout(() => {
      const handler = (e) => {
        if (!palette.contains(e.target)) {
          this._closePalette();
          document.removeEventListener('click', handler);
        }
      };
      document.addEventListener('click', handler);
    }, 0);
  }

  _closePalette() {
    if (this._palette) {
      this._palette.remove();
      this._palette = null;
    }
  }

  _setSwara(swaraId, octave) {
    if (!this._selectedCell) return;
    const sec = this._sections[this._selectedCell.sectionIdx];
    const bar = sec?.lines[this._selectedCell.lineIdx]?.bars[this._selectedCell.barIdx];
    if (!bar) return;
    bar.swaras[this._selectedCell.posIdx] = { swara_id: swaraId, octave };
  }

  // ── Private: Actions ──

  async _playBar() {
    const section = this._sections[this._activeSectionIdx];
    if (!section?.lines.length) return;
    const bar = section.lines[0]?.bars[0];
    if (!bar) return;

    try {
      const res = await fetch('/api/v1/synthesize-bar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bar: {
            tala_id: bar.tala_id || this._talaId,
            speed: bar.speed || 1,
            swaras: bar.swaras,
            saahitya: bar.saahitya,
          },
          reference_sa_hz: this._referenceSaHz,
          tempo_bpm: this._tempoBpm,
          tone: 'voice',
        }),
      });
      if (!res.ok) throw new Error('Synthesis failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
      audio.addEventListener('ended', () => URL.revokeObjectURL(url));
    } catch (err) {
      console.error('Play bar failed:', err);
    }
  }

  async _playComposition() {
    try {
      const compData = this.toJSON();
      delete compData.id;
      const res = await fetch('/api/v1/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          composition: compData,
          tempo_bpm: this._tempoBpm,
          tone: 'voice',
          include_tanpura: false,
        }),
      });
      if (!res.ok) throw new Error('Synthesis failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
      audio.addEventListener('ended', () => URL.revokeObjectURL(url));
    } catch (err) {
      console.error('Play composition failed:', err);
    }
  }

  async _playWithDrone() {
    if (this._drone && !this._drone.isPlaying) {
      this._drone.setSaHz(this._referenceSaHz);
      this._drone.start();
    }
    await this._playComposition();
  }

  async _save() {
    const data = this.toJSON();
    delete data.id;

    try {
      const method = this._id ? 'PUT' : 'POST';
      const url = this._id
        ? `/api/v1/compositions/${this._id}`
        : '/api/v1/compositions';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!res.ok) throw new Error('Save failed');
      const result = await res.json();
      this._id = result.id;
      alert(`Composition saved (ID: ${this._id})`);
    } catch (err) {
      console.error('Save failed:', err);
      alert('Save failed: ' + err.message);
    }
  }

  async _exportWav() {
    try {
      const compData = this.toJSON();
      delete compData.id;
      const res = await fetch('/api/v1/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          composition: compData,
          tempo_bpm: this._tempoBpm,
          tone: 'voice',
          include_tanpura: true,
        }),
      });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (this._title || 'composition').replace(/\s+/g, '_') + '.wav';
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export failed: ' + err.message);
    }
  }

  _downloadJson() {
    const data = this.toJSON();
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (this._title || 'composition').replace(/\s+/g, '_') + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ── Private: Helpers ──

  _ensureDefaultLine() {
    const section = this._sections[this._activeSectionIdx];
    if (!section) return;
    if (!section.lines.length) {
      const tala = this._talas.find(t => t.id === this._talaId);
      const cols = tala ? tala.total_aksharas : 8;
      section.lines.push({
        bars: [{
          tala_id: this._talaId,
          speed: 1,
          swaras: Array(cols).fill(null).map(() => ({ swara_id: '-', octave: 'madhya' })),
          saahitya: Array(cols).fill(''),
        }],
        repeat: 2,
      });
    }
  }

  _addLine() {
    const section = this._sections[this._activeSectionIdx];
    if (!section) return;
    const tala = this._talas.find(t => t.id === this._talaId);
    const cols = tala ? tala.total_aksharas : 8;
    section.lines.push({
      bars: [{
        tala_id: this._talaId,
        speed: 1,
        swaras: Array(cols).fill(null).map(() => ({ swara_id: '-', octave: 'madhya' })),
        saahitya: Array(cols).fill(''),
      }],
      repeat: 2,
    });
  }

  _getBoundaries(tala, speed) {
    const boundaries = [];
    let pos = 0;
    (tala.beat_pattern || []).forEach((beats, compIdx) => {
      boundaries.push({
        start: pos * speed,
        end: (pos + beats) * speed,
        component: (tala.components || [])[compIdx] || 'laghu',
      });
      pos += beats;
    });
    return boundaries;
  }

  _field(label, type, value, onChange) {
    const wrap = document.createElement('div');
    wrap.className = 'comp-field';
    const lbl = document.createElement('label');
    lbl.textContent = label;
    const input = document.createElement('input');
    input.type = type;
    input.value = value;
    if (type === 'number') input.step = '0.01';
    input.addEventListener('change', (e) => onChange(e.target.value));
    wrap.appendChild(lbl);
    wrap.appendChild(input);
    return wrap;
  }

  _selectField(label, options, value, onChange) {
    const wrap = document.createElement('div');
    wrap.className = 'comp-field';
    const lbl = document.createElement('label');
    lbl.textContent = label;
    const sel = document.createElement('select');
    options.forEach(o => {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      if (o.value === value) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener('change', (e) => onChange(e.target.value));
    wrap.appendChild(lbl);
    wrap.appendChild(sel);
    return wrap;
  }

  _onKeyDown(e) {
    if (!this._selectedCell) return;
    // Ignore if user is typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

    const keyMap = {
      's': 'Sa', 'r': 'Ri2', 'g': 'Ga3', 'm': 'Ma1', 'p': 'Pa', 'd': 'Dha2', 'n': 'Ni3',
    };

    if (keyMap[e.key]) {
      e.preventDefault();
      this._setSwara(keyMap[e.key], 'madhya');
      // Advance to next cell
      this._advanceCell();
      this.render();
    } else if (e.key === '-') {
      e.preventDefault();
      this._setSwara('-', 'madhya');
      this._advanceCell();
      this.render();
    } else if (e.key === ',') {
      e.preventDefault();
      this._setSwara(',', 'madhya');
      this._advanceCell();
      this.render();
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      this._advanceCell();
      this.render();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      this._retreatCell();
      this.render();
    }
  }

  _advanceCell() {
    if (!this._selectedCell) return;
    const sec = this._sections[this._selectedCell.sectionIdx];
    const bar = sec?.lines[this._selectedCell.lineIdx]?.bars[this._selectedCell.barIdx];
    if (!bar) return;

    if (this._selectedCell.posIdx < bar.swaras.length - 1) {
      this._selectedCell.posIdx++;
    }
  }

  _retreatCell() {
    if (!this._selectedCell) return;
    if (this._selectedCell.posIdx > 0) {
      this._selectedCell.posIdx--;
    }
  }
}
