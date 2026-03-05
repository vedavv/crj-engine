/**
 * ShrutiDrone — Web Audio API tanpura drone generator + Sa display.
 *
 * Generates a 4-string tanpura drone (Pa, Sa', Sa', Sa) using harmonic-rich
 * PeriodicWave oscillators with subtle amplitude LFO for breathing effect.
 */
class ShrutiDrone {
  /**
   * @param {Object} opts
   * @param {number} [opts.referenceSaHz=261.63] - Sa frequency in Hz.
   * @param {number} [opts.volume=0.3] - Default volume (0-1).
   */
  constructor(opts = {}) {
    this.referenceSaHz = opts.referenceSaHz || 261.63;
    this.volume = opts.volume || 0.3;
    this._ctx = null;
    this._masterGain = null;
    this._oscillators = [];
    this._lfo = null;
    this._lfoGain = null;
    this._isPlaying = false;
    this._listeners = [];
  }

  /** Whether the drone is currently playing. */
  get isPlaying() { return this._isPlaying; }

  /**
   * Get the Western note name for the current Sa.
   * @returns {{ name: string, octave: number, hz: number }}
   */
  getWesternNote() {
    const hz = this.referenceSaHz;
    const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const a4 = 440;
    const semitones = 12 * Math.log2(hz / a4);
    const midiNote = Math.round(69 + semitones);
    const noteIdx = ((midiNote % 12) + 12) % 12;
    const octave = Math.floor(midiNote / 12) - 1;
    return { name: noteNames[noteIdx], octave, hz };
  }

  /**
   * Format Sa display string: "Sa = C4 (261.63 Hz)"
   * @returns {string}
   */
  getSaDisplayString() {
    const w = this.getWesternNote();
    return `Sa = ${w.name}${w.octave} (${this.referenceSaHz.toFixed(2)} Hz)`;
  }

  /**
   * Set Sa frequency. If drone is playing, frequencies update live.
   * @param {number} hz
   */
  setSaHz(hz) {
    this.referenceSaHz = hz;
    if (this._isPlaying) {
      this._updateFrequencies();
    }
    this._notifyListeners();
  }

  /**
   * Toggle drone on/off.
   */
  toggle() {
    if (this._isPlaying) {
      this.stop();
    } else {
      this.start();
    }
  }

  /**
   * Start the tanpura drone.
   */
  start() {
    if (this._isPlaying) return;

    if (!this._ctx) {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this._ctx.state === 'suspended') {
      this._ctx.resume();
    }

    const ctx = this._ctx;

    // Master gain
    this._masterGain = ctx.createGain();
    this._masterGain.gain.value = this.volume;
    this._masterGain.connect(ctx.destination);

    // LFO for breathing effect (~0.15 Hz)
    this._lfo = ctx.createOscillator();
    this._lfo.frequency.value = 0.15;
    this._lfoGain = ctx.createGain();
    this._lfoGain.gain.value = 0.08; // Subtle modulation depth
    this._lfo.connect(this._lfoGain);
    this._lfoGain.connect(this._masterGain.gain);
    this._lfo.start();

    // 4 tanpura strings: Pa, Sa(upper), Sa(upper), Sa(lower)
    const paHz = this.referenceSaHz * Math.pow(2, 700 / 1200);
    const saUpper = this.referenceSaHz * 2;
    const saLower = this.referenceSaHz;

    const strings = [
      { freq: paHz, amp: 0.25 },
      { freq: saUpper, amp: 0.28 },
      { freq: saUpper, amp: 0.28 },
      { freq: saLower, amp: 0.20 },
    ];

    // Build a harmonic-rich PeriodicWave (jivari buzz simulation)
    const numHarmonics = 16;
    const real = new Float32Array(numHarmonics + 1);
    const imag = new Float32Array(numHarmonics + 1);
    real[0] = 0;
    imag[0] = 0;
    for (let h = 1; h <= numHarmonics; h++) {
      real[h] = 0;
      imag[h] = 1.0 / Math.pow(h, 1.2); // Tanpura-like harmonic decay
    }
    const tanpuraWave = ctx.createPeriodicWave(real, imag, { disableNormalization: false });

    this._oscillators = strings.map((s, i) => {
      const osc = ctx.createOscillator();
      osc.setPeriodicWave(tanpuraWave);
      osc.frequency.value = s.freq;
      // Slight detuning for warmth between same-pitch strings
      if (i === 2) osc.detune.value = 3; // 3 cents sharp

      const gain = ctx.createGain();
      gain.gain.value = s.amp;
      osc.connect(gain);
      gain.connect(this._masterGain);
      osc.start();

      return { osc, gain, baseFreq: s.freq, baseAmp: s.amp };
    });

    this._isPlaying = true;
    this._notifyListeners();
  }

  /**
   * Stop the tanpura drone.
   */
  stop() {
    if (!this._isPlaying) return;

    // Fade out to avoid click
    if (this._masterGain) {
      const now = this._ctx.currentTime;
      this._masterGain.gain.setValueAtTime(this._masterGain.gain.value, now);
      this._masterGain.gain.linearRampToValueAtTime(0, now + 0.3);
    }

    setTimeout(() => {
      this._oscillators.forEach(o => {
        try { o.osc.stop(); } catch {}
      });
      this._oscillators = [];
      if (this._lfo) {
        try { this._lfo.stop(); } catch {}
        this._lfo = null;
        this._lfoGain = null;
      }
      this._masterGain = null;
    }, 350);

    this._isPlaying = false;
    this._notifyListeners();
  }

  /**
   * Set volume (0-1).
   * @param {number} vol
   */
  setVolume(vol) {
    this.volume = Math.max(0, Math.min(1, vol));
    if (this._masterGain) {
      this._masterGain.gain.setValueAtTime(this.volume, this._ctx.currentTime);
    }
  }

  /**
   * Register a listener for state changes.
   * @param {function} fn - Called with { isPlaying, saHz, saDisplay }
   */
  onChange(fn) {
    this._listeners.push(fn);
  }

  // ── Private ──

  _updateFrequencies() {
    if (!this._oscillators.length || !this._ctx) return;
    const paHz = this.referenceSaHz * Math.pow(2, 700 / 1200);
    const saUpper = this.referenceSaHz * 2;
    const saLower = this.referenceSaHz;
    const freqs = [paHz, saUpper, saUpper, saLower];
    const now = this._ctx.currentTime;
    this._oscillators.forEach((o, i) => {
      o.osc.frequency.setValueAtTime(freqs[i], now);
    });
  }

  _notifyListeners() {
    const state = {
      isPlaying: this._isPlaying,
      saHz: this.referenceSaHz,
      saDisplay: this.getSaDisplayString(),
    };
    this._listeners.forEach(fn => {
      try { fn(state); } catch (e) { console.error('ShrutiDrone listener error:', e); }
    });
  }

  /**
   * Render drone controls into a container element.
   * @param {HTMLElement} container
   */
  renderControls(container) {
    container.innerHTML = '';
    container.className = 'shruti-controls';

    // Sa display
    const saDisplay = document.createElement('span');
    saDisplay.className = 'shruti-sa-display';
    saDisplay.textContent = this.getSaDisplayString();
    container.appendChild(saDisplay);

    // Toggle button
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'shruti-toggle' + (this._isPlaying ? ' active' : '');
    toggleBtn.innerHTML = this._isPlaying
      ? '<svg viewBox="0 0 24 24" width="16" height="16"><rect x="6" y="4" width="4" height="16" fill="currentColor"/><rect x="14" y="4" width="4" height="16" fill="currentColor"/></svg> Drone'
      : '<svg viewBox="0 0 24 24" width="16" height="16"><polygon points="8,5 19,12 8,19" fill="currentColor"/></svg> Drone';
    toggleBtn.title = this._isPlaying ? 'Stop tanpura drone' : 'Start tanpura drone';
    toggleBtn.addEventListener('click', () => {
      this.toggle();
      this.renderControls(container);
    });
    container.appendChild(toggleBtn);

    // Volume slider
    const volWrap = document.createElement('div');
    volWrap.className = 'shruti-vol-wrap';
    const volLabel = document.createElement('span');
    volLabel.className = 'shruti-vol-label';
    volLabel.textContent = 'Vol';
    const volSlider = document.createElement('input');
    volSlider.type = 'range';
    volSlider.className = 'shruti-vol-slider';
    volSlider.min = '0';
    volSlider.max = '100';
    volSlider.value = String(Math.round(this.volume * 100));
    volSlider.addEventListener('input', (e) => {
      this.setVolume(parseInt(e.target.value) / 100);
    });
    volWrap.appendChild(volLabel);
    volWrap.appendChild(volSlider);
    container.appendChild(volWrap);

    // Sa preset selector
    const saWrap = document.createElement('div');
    saWrap.className = 'shruti-sa-wrap';
    const saLabel = document.createElement('span');
    saLabel.className = 'shruti-sa-label';
    saLabel.textContent = 'Sa';
    const saSelect = document.createElement('select');
    saSelect.className = 'shruti-sa-select';

    // Common Sa presets
    const presets = [
      { label: 'C4 (261.63 Hz)', hz: 261.63 },
      { label: 'A3 (220.00 Hz)', hz: 220.00 },
      { label: 'D#4 (311.13 Hz)', hz: 311.13 },
      { label: 'Bb3 (233.08 Hz)', hz: 233.08 },
      { label: 'D4 (293.66 Hz)', hz: 293.66 },
      { label: 'E4 (329.63 Hz)', hz: 329.63 },
    ];
    presets.forEach(p => {
      const opt = document.createElement('option');
      opt.value = String(p.hz);
      opt.textContent = p.label;
      if (Math.abs(p.hz - this.referenceSaHz) < 0.1) opt.selected = true;
      saSelect.appendChild(opt);
    });
    // Custom option
    const customOpt = document.createElement('option');
    customOpt.value = 'custom';
    customOpt.textContent = 'Custom...';
    if (!presets.some(p => Math.abs(p.hz - this.referenceSaHz) < 0.1)) {
      customOpt.selected = true;
      customOpt.textContent = `Custom (${this.referenceSaHz} Hz)`;
    }
    saSelect.appendChild(customOpt);

    saSelect.addEventListener('change', (e) => {
      if (e.target.value === 'custom') {
        const hz = prompt('Enter Sa frequency in Hz:', String(this.referenceSaHz));
        if (hz && !isNaN(parseFloat(hz))) {
          this.setSaHz(parseFloat(hz));
          this.renderControls(container);
        }
      } else {
        this.setSaHz(parseFloat(e.target.value));
        saDisplay.textContent = this.getSaDisplayString();
      }
    });

    saWrap.appendChild(saLabel);
    saWrap.appendChild(saSelect);
    container.appendChild(saWrap);

    // Listen for state changes to update display
    this.onChange((state) => {
      saDisplay.textContent = state.saDisplay;
      toggleBtn.className = 'shruti-toggle' + (state.isPlaying ? ' active' : '');
    });
  }
}
