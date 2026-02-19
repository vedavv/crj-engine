/**
 * NotationRenderer — renders swara notation, raga candidates,
 * gamaka distribution, summary stats, and pitch contour visualization.
 */
const NotationRenderer = {
    SWARA_COLORS: {
        'Sa':  '#66bb6a', 'Ri1': '#42a5f5', 'Ri2': '#5b9bd5',
        'Ga1': '#5b9bd5', 'Ga2': '#b388ff', 'Ga3': '#a07de0',
        'Ma1': '#e0a840', 'Ma2': '#d4912a', 'Pa':  '#e05555',
        'Dha1': '#4dd0e1', 'Dha2': '#26c6da', 'Dha3': '#26c6da',
        'Ni1': '#4dd0e1', 'Ni2': '#ec407a', 'Ni3': '#e91e63',
    },

    GAMAKA_COLORS: {
        'kampita':    '#dbb978',
        'jaru':       '#66bb6a',
        'sphuritham': '#e0a840',
        'steady':     '#6b7394',
    },

    /* ─── Swara Phrases ─── */
    renderPhrases(phrases, container) {
        container.innerHTML = '';
        phrases.forEach((phrase, i) => {
            const div = document.createElement('div');
            div.className = 'phrase';

            const hdr = document.createElement('div');
            hdr.className = 'phrase-header';
            hdr.textContent = 'Phrase ' + (i + 1) +
                '  [' + (phrase.start_ms / 1000).toFixed(1) + 's \u2013 ' +
                (phrase.end_ms / 1000).toFixed(1) + 's]';
            div.appendChild(hdr);

            const notes = document.createElement('div');
            notes.className = 'phrase-notes';
            phrase.notes.forEach(note => {
                const span = document.createElement('span');
                span.className = 'swara-note';
                span.textContent = note.swara_id;
                span.style.color = this.SWARA_COLORS[note.swara_id] || '#b0a898';
                if (note.octave === 'mandra') span.classList.add('octave-low');
                if (note.octave === 'tara') span.classList.add('octave-high');

                // Tooltip
                const tip = document.createElement('span');
                tip.className = 'swara-tooltip';
                tip.textContent = note.frequency_hz.toFixed(1) + ' Hz | ' +
                    (note.cents_deviation >= 0 ? '+' : '') +
                    note.cents_deviation.toFixed(1) + '\u00A2';
                span.appendChild(tip);

                notes.appendChild(span);
            });
            div.appendChild(notes);
            container.appendChild(div);
        });
    },

    /* ─── Raga Candidates (ranked styling) ─── */
    renderRagas(candidates, container) {
        container.innerHTML = '';
        if (!candidates.length) {
            container.innerHTML = '<p style="color:var(--text-muted)">No raga candidates identified.</p>';
            return;
        }
        candidates.forEach((c, i) => {
            const pct = (c.confidence * 100).toFixed(0);
            const rankClass = i === 0 ? 'raga-rank--1'
                            : i === 1 ? 'raga-rank--2'
                            : i === 2 ? 'raga-rank--3'
                            : 'raga-rank--default';

            const div = document.createElement('div');
            div.className = 'raga-candidate';
            div.innerHTML =
                '<span class="raga-rank ' + rankClass + '">' + (i + 1) + '</span>' +
                '<div><span class="raga-name">' + this._esc(c.raga_name) + '</span>' +
                ' <span class="raga-number">Melakarta ' + c.raga_number + '</span></div>' +
                '<div class="confidence-bar"><div class="confidence-fill" style="width:0%"' +
                ' data-target-width="' + pct + '%"></div></div>' +
                '<span class="confidence-pct">' + pct + '%</span>' +
                '<div class="raga-scale">\u2191 ' + c.arohana.join(' ') +
                '  |  \u2193 ' + c.avarohana.join(' ') + '</div>';
            container.appendChild(div);
        });

        // Animate confidence bars after brief delay
        requestAnimationFrame(() => {
            setTimeout(() => {
                container.querySelectorAll('.confidence-fill').forEach(bar => {
                    bar.style.width = bar.dataset.targetWidth;
                });
            }, 100);
        });
    },

    /* ─── Gamaka Distribution ─── */
    renderGamakas(gamakas, container) {
        container.innerHTML = '';
        const counts = {};
        gamakas.forEach(g => { counts[g.gamaka_type] = (counts[g.gamaka_type] || 0) + 1; });

        const row = document.createElement('div');
        row.className = 'gamaka-row';
        Object.entries(counts).forEach(([type, count]) => {
            const item = document.createElement('div');
            item.className = 'gamaka-item';
            const color = this.GAMAKA_COLORS[type] || '#6b7394';
            item.innerHTML =
                '<span class="gamaka-dot" style="background:' + color +
                '; box-shadow: 0 0 8px ' + color + '"></span>' +
                '<div class="gamaka-info">' +
                '<span class="gamaka-name">' + type.charAt(0).toUpperCase() + type.slice(1) + '</span>' +
                '<span class="gamaka-count">' + count + ' segment' + (count !== 1 ? 's' : '') + '</span>' +
                '</div>';
            row.appendChild(item);
        });
        container.appendChild(row);
    },

    /* ─── Summary Stats ─── */
    renderSummary(result, container) {
        container.innerHTML =
            '<div class="summary-grid">' +
            this._summaryItem('Duration', result.duration_s.toFixed(1) + 's') +
            this._summaryItem('Reference Sa', result.reference_sa_hz + ' Hz') +
            this._summaryItem('Algorithm', result.algorithm.toUpperCase()) +
            this._summaryItem('Swaras', result.unique_swaras.join(', ')) +
            '</div>';
    },

    /* ─── Pitch Contour Visualization ─── */
    renderContour(contour, referenceSaHz, canvas) {
        if (!contour || !contour.length) {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#0d1624';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#786e60';
            ctx.font = '14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No contour data (enable "include contour" to see this)',
                canvas.width / 2, canvas.height / 2);
            return;
        }

        const ctx = canvas.getContext('2d');
        const W = canvas.width;
        const H = canvas.height;
        const padding = { top: 20, bottom: 30, left: 55, right: 15 };
        const plotW = W - padding.left - padding.right;
        const plotH = H - padding.top - padding.bottom;

        // Clear
        ctx.fillStyle = '#0d1624';
        ctx.fillRect(0, 0, W, H);

        // Get voiced frames
        const voiced = contour.filter(f => f.frequency_hz > 0 && f.confidence > 0.2);
        if (!voiced.length) return;

        const freqs = voiced.map(f => f.frequency_hz);
        const fMin = Math.min(...freqs) * 0.9;
        const fMax = Math.max(...freqs) * 1.1;
        const tMin = contour[0].timestamp_ms;
        const tMax = contour[contour.length - 1].timestamp_ms;

        const xScale = (ms) => padding.left + ((ms - tMin) / (tMax - tMin)) * plotW;
        const yScale = (hz) => padding.top + plotH - ((hz - fMin) / (fMax - fMin)) * plotH;

        // Reference Sa line
        if (referenceSaHz >= fMin && referenceSaHz <= fMax) {
            const saY = yScale(referenceSaHz);
            ctx.strokeStyle = 'rgba(197, 160, 89, 0.25)';
            ctx.setLineDash([6, 4]);
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(padding.left, saY);
            ctx.lineTo(W - padding.right, saY);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.fillStyle = 'rgba(197, 160, 89, 0.5)';
            ctx.font = '10px JetBrains Mono, monospace';
            ctx.textAlign = 'left';
            ctx.fillText('Sa ' + referenceSaHz + ' Hz', padding.left + 4, saY - 4);
        }

        // Octave lines (Pa, upper Sa)
        [referenceSaHz * 1.5, referenceSaHz * 2].forEach(hz => {
            if (hz >= fMin && hz <= fMax) {
                const y = yScale(hz);
                ctx.strokeStyle = 'rgba(197, 160, 89, 0.1)';
                ctx.setLineDash([3, 5]);
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(W - padding.right, y);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        });

        // Pitch contour line
        ctx.strokeStyle = '#5cc8d4';
        ctx.lineWidth = 2;
        ctx.lineJoin = 'round';
        ctx.beginPath();
        let started = false;
        for (const f of contour) {
            if (f.frequency_hz <= 0 || f.confidence < 0.2) {
                started = false;
                continue;
            }
            const x = xScale(f.timestamp_ms);
            const y = yScale(f.frequency_hz);
            if (!started) {
                ctx.moveTo(x, y);
                started = true;
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();

        // Confidence shading
        ctx.fillStyle = 'rgba(92, 200, 212, 0.08)';
        ctx.beginPath();
        started = false;
        let lastX = 0;
        for (const f of contour) {
            if (f.frequency_hz <= 0 || f.confidence < 0.2) {
                if (started) {
                    ctx.lineTo(lastX, padding.top + plotH);
                    ctx.fill();
                    ctx.beginPath();
                    started = false;
                }
                continue;
            }
            const x = xScale(f.timestamp_ms);
            const y = yScale(f.frequency_hz);
            if (!started) {
                ctx.moveTo(x, padding.top + plotH);
                ctx.lineTo(x, y);
                started = true;
            } else {
                ctx.lineTo(x, y);
            }
            lastX = x;
        }
        if (started) {
            ctx.lineTo(lastX, padding.top + plotH);
            ctx.fill();
        }

        // Time axis
        ctx.fillStyle = '#786e60';
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        const nTicks = 6;
        for (let i = 0; i <= nTicks; i++) {
            const t = tMin + (tMax - tMin) * (i / nTicks);
            const x = xScale(t);
            ctx.fillText((t / 1000).toFixed(1) + 's', x, H - 6);
            ctx.strokeStyle = 'rgba(197, 160, 89, 0.06)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, padding.top);
            ctx.lineTo(x, padding.top + plotH);
            ctx.stroke();
        }

        // Frequency axis
        ctx.textAlign = 'right';
        const nYTicks = 4;
        for (let i = 0; i <= nYTicks; i++) {
            const hz = fMin + (fMax - fMin) * (i / nYTicks);
            const y = yScale(hz);
            ctx.fillStyle = '#786e60';
            ctx.fillText(hz.toFixed(0) + ' Hz', padding.left - 6, y + 3);
        }
    },

    /* ─── Private ─── */
    _summaryItem(label, value) {
        return '<div class="summary-item">' +
            '<span class="summary-label">' + label + '</span>' +
            '<span class="summary-value">' + this._esc(String(value)) + '</span></div>';
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    },
};
