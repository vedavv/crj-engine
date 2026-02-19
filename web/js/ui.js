/**
 * SoundScape UI controller — state machine for record/upload/analyze workflow.
 *
 * States: idle -> recording -> processing -> results
 *         idle -> processing -> results (file upload)
 *         results -> idle (new analysis)
 */
document.addEventListener('DOMContentLoaded', async () => {
    // DOM refs
    const btnRecord = document.getElementById('btn-record');
    const btnStop = document.getElementById('btn-stop');
    const fileInput = document.getElementById('file-input');
    const recordingStatus = document.getElementById('recording-status');
    const waveformCanvas = document.getElementById('waveform');
    const processingCard = document.getElementById('processing-card');
    const resultsCard = document.getElementById('results-card');
    const progressFill = document.getElementById('progress-fill');
    const processingMsg = document.getElementById('processing-msg');
    const btnNew = document.getElementById('btn-new');
    const saPreset = document.getElementById('sa-preset');
    const saCustom = document.getElementById('sa-custom');
    const inputCard = document.getElementById('input-card');
    const recordIndicator = document.getElementById('record-indicator');
    const recordTimer = document.getElementById('record-timer');
    const contourCanvas = document.getElementById('pitch-contour');

    let recorder = null;
    let lastResult = null;   // store for contour re-rendering

    // --- Load tuning presets ---
    try {
        const presets = await CRJApi.getTuningPresets();
        presets.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.reference_sa_hz;
            opt.textContent = p.description.split(',')[0] + ' (' + p.reference_sa_hz + ' Hz)';
            saPreset.appendChild(opt);
        });
        const custom = document.createElement('option');
        custom.value = 'custom';
        custom.textContent = 'Custom Hz\u2026';
        saPreset.appendChild(custom);
    } catch (e) {
        console.warn('Could not load presets:', e);
    }

    saPreset.addEventListener('change', () => {
        saCustom.style.display = saPreset.value === 'custom' ? 'block' : 'none';
    });

    // --- Tab switching ---
    const tabs = document.getElementById('results-tabs');
    if (tabs) {
        tabs.addEventListener('click', (e) => {
            const btn = e.target.closest('.tab-btn');
            if (!btn) return;
            const tabId = btn.dataset.tab;

            tabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            const panel = document.getElementById(tabId);
            if (panel) panel.classList.add('active');
        });
    }

    // --- Helpers ---

    function getOptions() {
        let saHz = parseFloat(saPreset.value);
        if (saPreset.value === 'custom') {
            saHz = parseFloat(saCustom.value) || 261.63;
        }
        return {
            referenceSaHz: saHz,
            algorithm: document.getElementById('algorithm').value,
            script: document.getElementById('script').value,
            includeContour: true,   // always request contour for visualization
        };
    }

    function setState(s) {
        const isIdle = s === 'idle';
        const isRecording = s === 'recording';
        const isProcessing = s === 'processing';
        const isResults = s === 'results';

        btnRecord.disabled = !isIdle;
        btnStop.disabled = !isRecording;
        fileInput.disabled = !isIdle;
        inputCard.style.opacity = isIdle || isRecording ? '1' : '0.5';
        inputCard.style.pointerEvents = isIdle || isRecording ? 'auto' : 'none';

        // Processing card with smooth show/hide
        processingCard.style.display = isProcessing ? 'block' : 'none';

        // Results card
        resultsCard.style.display = isResults ? 'block' : 'none';
        if (isResults) {
            resultsCard.classList.add('fade-in');
        }

        // Recording button state
        if (isRecording) {
            btnRecord.classList.add('recording');
            recordIndicator.classList.add('active');
        } else {
            btnRecord.classList.remove('recording');
            recordIndicator.classList.remove('active');
        }

        if (isIdle) {
            progressFill.style.width = '0%';
            processingMsg.textContent = '';
            recordTimer.textContent = '0.0 s';

            // Reset to summary tab
            const firstTab = tabs && tabs.querySelector('.tab-btn');
            if (firstTab) firstTab.click();
        }
    }

    function showError(msg) {
        recordingStatus.textContent = msg;
        recordingStatus.className = 'recording-status error-msg';
        setState('idle');
    }

    function clearError() {
        recordingStatus.textContent = '';
        recordingStatus.className = 'recording-status';
    }

    function drawWaveform(data) {
        const ctx = waveformCanvas.getContext('2d');
        const w = waveformCanvas.width;
        const h = waveformCanvas.height;
        ctx.fillStyle = '#0d1624';
        ctx.fillRect(0, 0, w, h);

        // Gradient waveform
        const grad = ctx.createLinearGradient(0, 0, w, 0);
        grad.addColorStop(0, '#5cc8d4');
        grad.addColorStop(0.5, '#c5a059');
        grad.addColorStop(1, '#5cc8d4');
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        const slice = w / data.length;
        let x = 0;
        for (let i = 0; i < data.length; i++) {
            const y = (data[i] / 128.0) * (h / 2);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
            x += slice;
        }
        ctx.stroke();
    }

    function clearWaveform() {
        const ctx = waveformCanvas.getContext('2d');
        ctx.fillStyle = '#0d1624';
        ctx.fillRect(0, 0, waveformCanvas.width, waveformCanvas.height);

        // Draw center line
        ctx.strokeStyle = 'rgba(197, 160, 89, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, waveformCanvas.height / 2);
        ctx.lineTo(waveformCanvas.width, waveformCanvas.height / 2);
        ctx.stroke();
    }

    // --- Analysis ---

    async function runAnalysis(blobOrFile, isFile) {
        setState('processing');
        processingMsg.textContent = 'Uploading audio\u2026';
        progressFill.style.width = '20%';

        try {
            processingMsg.textContent = 'Detecting pitch contour\u2026';
            progressFill.style.width = '40%';

            const opts = getOptions();
            const result = isFile
                ? await CRJApi.analyzeFile(blobOrFile, opts)
                : await CRJApi.analyze(blobOrFile, opts);

            processingMsg.textContent = 'Rendering results\u2026';
            progressFill.style.width = '80%';

            // Small pause so user sees progress
            await new Promise(r => setTimeout(r, 200));

            progressFill.style.width = '100%';
            processingMsg.textContent = 'Complete!';

            lastResult = result;
            displayResults(result, opts.referenceSaHz);

            // Brief delay before showing results
            await new Promise(r => setTimeout(r, 300));
            setState('results');
        } catch (err) {
            showError('Analysis failed: ' + err.message);
        }
    }

    function displayResults(result, referenceSaHz) {
        // Summary
        NotationRenderer.renderSummary(
            result,
            document.getElementById('summary')
        );

        // Compact notation
        const compactEl = document.getElementById('notation-compact');
        compactEl.innerHTML = '<pre class="notation-pre">' +
            escapeHtml(result.notation_compact) + '</pre>';

        // Structured phrases
        NotationRenderer.renderPhrases(
            result.phrases,
            document.getElementById('notation-phrases')
        );

        // Full rendered notation in chosen script
        const fullEl = document.getElementById('notation-full');
        fullEl.innerHTML = '<pre class="notation-pre">' +
            escapeHtml(result.notation_requested) + '</pre>';

        // Ragas
        NotationRenderer.renderRagas(
            result.raga_candidates,
            document.getElementById('raga-results')
        );

        // Gamakas
        NotationRenderer.renderGamakas(
            result.gamakas,
            document.getElementById('gamaka-results')
        );

        // Pitch contour
        if (result.pitch_contour && contourCanvas) {
            NotationRenderer.renderContour(
                result.pitch_contour,
                referenceSaHz || result.reference_sa_hz,
                contourCanvas
            );
        } else if (contourCanvas) {
            NotationRenderer.renderContour(null, 0, contourCanvas);
        }
    }

    function escapeHtml(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    // --- Event handlers ---

    btnRecord.addEventListener('click', async () => {
        clearError();
        try {
            recorder = new AudioRecorder({
                maxDurationMs: 30000,
                onDurationUpdate(ms) {
                    recordTimer.textContent = (ms / 1000).toFixed(1) + ' s';
                },
                onMaxReached(blob) {
                    recordingStatus.textContent = 'Max duration reached.';
                    runAnalysis(blob, false);
                },
                onWaveformData: drawWaveform,
            });
            await recorder.start();
            setState('recording');
        } catch (err) {
            showError('Microphone error: ' + err.message);
        }
    });

    btnStop.addEventListener('click', async () => {
        if (!recorder) return;
        const blob = await recorder.stop();
        recorder = null;
        if (blob && blob.size > 0) {
            runAnalysis(blob, false);
        } else {
            showError('No audio recorded.');
        }
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        clearError();

        if (file.size > 10 * 1024 * 1024) {
            showError('File too large (max 10 MB).');
            fileInput.value = '';
            return;
        }

        runAnalysis(file, true);
        fileInput.value = '';
    });

    btnNew.addEventListener('click', () => {
        setState('idle');
        clearError();
        clearWaveform();
        lastResult = null;
    });

    // --- Init ---
    setState('idle');
    clearWaveform();
});
