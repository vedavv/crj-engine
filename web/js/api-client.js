/**
 * CRJ API client — handles file upload and reference data fetching.
 */
const CRJApi = {
    baseUrl: '/api/v1',

    async analyze(blob, options = {}) {
        const formData = new FormData();
        const ext = (blob.type || '').includes('webm') ? '.webm'
                  : (blob.type || '').includes('ogg') ? '.ogg'
                  : (blob.type || '').includes('mp4') ? '.m4a'
                  : '.webm';
        formData.append('file', blob, 'recording' + ext);
        formData.append('reference_sa_hz', options.referenceSaHz || 261.63);
        formData.append('algorithm', options.algorithm || 'pyin');
        formData.append('script', options.script || 'iast');
        formData.append('tolerance_cents', options.toleranceCents || 40);
        formData.append('include_contour', options.includeContour || false);

        const r = await fetch(this.baseUrl + '/analyze', {
            method: 'POST',
            body: formData,
        });
        if (!r.ok) {
            const err = await r.json().catch(() => ({ detail: 'Server error' }));
            throw new Error(err.detail || 'HTTP ' + r.status);
        }
        return r.json();
    },

    async analyzeFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('reference_sa_hz', options.referenceSaHz || 261.63);
        formData.append('algorithm', options.algorithm || 'pyin');
        formData.append('script', options.script || 'iast');
        formData.append('tolerance_cents', options.toleranceCents || 40);
        formData.append('include_contour', options.includeContour || false);

        const r = await fetch(this.baseUrl + '/analyze', {
            method: 'POST',
            body: formData,
        });
        if (!r.ok) {
            const err = await r.json().catch(() => ({ detail: 'Server error' }));
            throw new Error(err.detail || 'HTTP ' + r.status);
        }
        return r.json();
    },

    async getTuningPresets() {
        const r = await fetch(this.baseUrl + '/tuning-presets');
        return r.json();
    },

    async getSwarasthanas() {
        const r = await fetch(this.baseUrl + '/swarasthanas');
        return r.json();
    },

    async getRagas() {
        const r = await fetch(this.baseUrl + '/ragas');
        return r.json();
    },

    async healthCheck() {
        const r = await fetch(this.baseUrl + '/health');
        return r.json();
    },
};
