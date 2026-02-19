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

    let recorder = null;

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
        processingCard.style.display = isProcessing ? 'block' : 'none';
        resultsCard.style.display = isResults ? 'block' : 'none';

        if (isIdle) {
            progressFill.style.width = '0%';
            processingMsg.textContent = '';
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
        ctx.fillStyle = '#0d1b2a';
        ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = '#4CAF50';
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
        ctx.fillStyle = '#0d1b2a';
        ctx.fillRect(0, 0, waveformCanvas.width, waveformCanvas.height);
    }

    // --- Analysis ---

    async function runAnalysis(blobOrFile, isFile) {
        setState('processing');
        processingMsg.textContent = 'Uploading audio\u2026';
        progressFill.style.width = '20%';

        try {
            processingMsg.textContent = 'Analyzing pitch contour\u2026';
            progressFill.style.width = '40%';

            const opts = getOptions();
            const result = isFile
                ? await CRJApi.analyzeFile(blobOrFile, opts)
                : await CRJApi.analyze(blobOrFile, opts);

            progressFill.style.width = '100%';
            processingMsg.textContent = 'Done!';
            displayResults(result);
            setState('results');
        } catch (err) {
            showError('Analysis failed: ' + err.message);
        }
    }

    function displayResults(result) {
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

        // Summary
        NotationRenderer.renderSummary(
            result,
            document.getElementById('summary')
        );
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
                    recordingStatus.textContent =
                        'Recording: ' + (ms / 1000).toFixed(1) + 's / 30s';
                    recordingStatus.className = 'recording-status';
                    recordingStatus.style.color = '#4CAF50';
                },
                onMaxReached(blob) {
                    recordingStatus.textContent = 'Max duration reached. Processing\u2026';
                    runAnalysis(blob, false);
                },
                onWaveformData: drawWaveform,
            });
            await recorder.start();
            setState('recording');
            recordingStatus.textContent = 'Recording\u2026';
            recordingStatus.style.color = '#4CAF50';
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
    });

    // --- Init ---
    setState('idle');
    clearWaveform();
});
