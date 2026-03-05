/**
 * MultilingualDisplay — Script switching manager for CRJ SoundScape.
 *
 * Singleton that manages which scripts (IAST, Devanagari, Kannada, Tamil, Telugu)
 * are currently active, caches swarasthana data, and notifies registered listeners
 * when the script selection changes.
 */
const MultilingualDisplay = (() => {
  // ── Private state ──
  let _currentScripts = ['iast'];
  let _swarasthanas = null;
  const _listeners = [];

  // Script metadata
  const SCRIPTS = {
    iast:       { label: 'IAST',  short: 'IAST', fontFamily: "'Cormorant Garamond', serif" },
    devanagari: { label: 'देव',   short: 'देव',  fontFamily: "'Noto Sans Devanagari', 'Vijaya', serif" },
    kannada:    { label: 'ಕನ',    short: 'ಕನ',   fontFamily: "'Noto Sans Kannada', serif" },
    tamil:      { label: 'தமி',   short: 'தமி',  fontFamily: "'Noto Sans Tamil', serif" },
    telugu:     { label: 'తెలు',  short: 'తెలు', fontFamily: "'Noto Sans Telugu', serif" },
  };

  const ALL_SCRIPT_IDS = Object.keys(SCRIPTS);

  // ── Swarasthana cache ──
  async function _loadSwarasthanas() {
    if (_swarasthanas) return _swarasthanas;
    try {
      const res = await fetch('/api/v1/swarasthanas');
      if (!res.ok) throw new Error(res.statusText);
      _swarasthanas = await res.json();
    } catch {
      // Fallback: minimal built-in data
      _swarasthanas = [
        { id: 'Sa', names: { iast: 'Sa', devanagari: 'स', kannada: 'ಸ', tamil: 'ச', telugu: 'స' } },
        { id: 'Ri1', names: { iast: 'Ri₁', devanagari: 'रि₁', kannada: 'ರಿ₁', tamil: 'ரி₁', telugu: 'రి₁' } },
        { id: 'Ri2', names: { iast: 'Ri₂', devanagari: 'रि₂', kannada: 'ರಿ₂', tamil: 'ரி₂', telugu: 'రి₂' } },
        { id: 'Ga2', names: { iast: 'Ga₂', devanagari: 'ग₂', kannada: 'ಗ₂', tamil: 'க₂', telugu: 'గ₂' } },
        { id: 'Ga3', names: { iast: 'Ga₃', devanagari: 'ग₃', kannada: 'ಗ₃', tamil: 'க₃', telugu: 'గ₃' } },
        { id: 'Ma1', names: { iast: 'Ma₁', devanagari: 'म₁', kannada: 'ಮ₁', tamil: 'ம₁', telugu: 'మ₁' } },
        { id: 'Ma2', names: { iast: 'Ma₂', devanagari: 'म₂', kannada: 'ಮ₂', tamil: 'ம₂', telugu: 'మ₂' } },
        { id: 'Pa', names: { iast: 'Pa', devanagari: 'प', kannada: 'ಪ', tamil: 'ப', telugu: 'ప' } },
        { id: 'Dha1', names: { iast: 'Dha₁', devanagari: 'ध₁', kannada: 'ಧ₁', tamil: 'த₁', telugu: 'ధ₁' } },
        { id: 'Dha2', names: { iast: 'Dha₂', devanagari: 'ध₂', kannada: 'ಧ₂', tamil: 'த₂', telugu: 'ధ₂' } },
        { id: 'Ni2', names: { iast: 'Ni₂', devanagari: 'नि₂', kannada: 'ನಿ₂', tamil: 'நி₂', telugu: 'ని₂' } },
        { id: 'Ni3', names: { iast: 'Ni₃', devanagari: 'नि₃', kannada: 'ನಿ₃', tamil: 'நி₃', telugu: 'ని₃' } },
      ];
    }
    return _swarasthanas;
  }

  // ── Public API ──
  return {
    SCRIPTS,
    ALL_SCRIPT_IDS,

    /** Get currently active scripts. */
    get currentScripts() { return [..._currentScripts]; },

    /** Get the primary (first) active script. */
    get primaryScript() { return _currentScripts[0] || 'iast'; },

    /**
     * Initialize: load swarasthanas and set up.
     * Call once on page load.
     */
    async init() {
      await _loadSwarasthanas();
    },

    /**
     * Set active scripts and notify all listeners.
     * @param {string[]} scripts - Array of script ids.
     */
    setScripts(scripts) {
      if (!scripts.length) scripts = ['iast'];
      _currentScripts = scripts.filter(s => ALL_SCRIPT_IDS.includes(s));
      if (!_currentScripts.length) _currentScripts = ['iast'];
      _listeners.forEach(fn => {
        try { fn(_currentScripts); } catch (e) { console.error('MultilingualDisplay listener error:', e); }
      });
    },

    /**
     * Toggle "all" mode: if all scripts are on, switch to just IAST; else turn all on.
     */
    toggleAll() {
      if (_currentScripts.length === ALL_SCRIPT_IDS.length) {
        this.setScripts(['iast']);
      } else {
        this.setScripts([...ALL_SCRIPT_IDS]);
      }
    },

    /**
     * Toggle a single script.
     * @param {string} scriptId
     */
    toggleScript(scriptId) {
      if (_currentScripts.includes(scriptId)) {
        if (_currentScripts.length === 1) return; // Keep at least one
        this.setScripts(_currentScripts.filter(s => s !== scriptId));
      } else {
        this.setScripts([..._currentScripts, scriptId]);
      }
    },

    /**
     * Register a callback fired when scripts change.
     * @param {function} fn - Called with (scripts: string[])
     */
    onChange(fn) {
      _listeners.push(fn);
    },

    /**
     * Get swara name in a given script.
     * @param {string} swaraId - e.g. "Sa", "Ri2"
     * @param {string} script  - e.g. "devanagari"
     * @returns {string}
     */
    getSwaraName(swaraId, script) {
      if (!_swarasthanas) return swaraId;
      // Handle rest and sustain
      if (swaraId === '-' || swaraId === ',') return swaraId;
      const sw = _swarasthanas.find(s => s.id === swaraId);
      if (!sw) return swaraId;
      return (sw.names && sw.names[script]) || swaraId;
    },

    /**
     * Get swara full name in a given script.
     * @param {string} swaraId
     * @param {string} script
     * @returns {string}
     */
    getSwaraFullName(swaraId, script) {
      if (!_swarasthanas) return swaraId;
      if (swaraId === '-' || swaraId === ',') return swaraId;
      const sw = _swarasthanas.find(s => s.id === swaraId);
      if (!sw) return swaraId;
      return (sw.full_names && sw.full_names[script]) || this.getSwaraName(swaraId, script);
    },

    /**
     * Get font family for a script.
     * @param {string} script
     * @returns {string}
     */
    getFontFamily(script) {
      return SCRIPTS[script]?.fontFamily || "'Inter', sans-serif";
    },

    /**
     * Get all loaded swarasthana data.
     * @returns {Array|null}
     */
    getSwarasthanas() {
      return _swarasthanas;
    },

    /**
     * Render script selector pill buttons into a container.
     * @param {HTMLElement} container
     */
    renderSelector(container) {
      container.innerHTML = '';
      container.className = 'script-selector';

      ALL_SCRIPT_IDS.forEach(id => {
        const btn = document.createElement('button');
        btn.className = 'script-pill' + (_currentScripts.includes(id) ? ' active' : '');
        btn.textContent = SCRIPTS[id].short;
        btn.dataset.script = id;
        btn.title = id.charAt(0).toUpperCase() + id.slice(1);
        btn.addEventListener('click', () => {
          this.toggleScript(id);
          this.renderSelector(container);
        });
        container.appendChild(btn);
      });

      // "All" button
      const allBtn = document.createElement('button');
      allBtn.className = 'script-pill script-pill--all' +
        (_currentScripts.length === ALL_SCRIPT_IDS.length ? ' active' : '');
      allBtn.textContent = 'All';
      allBtn.title = 'Toggle all scripts';
      allBtn.addEventListener('click', () => {
        this.toggleAll();
        this.renderSelector(container);
      });
      container.appendChild(allBtn);
    },
  };
})();
