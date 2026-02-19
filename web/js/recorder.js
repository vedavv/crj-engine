/**
 * AudioRecorder — wraps MediaRecorder API for microphone capture.
 *
 * Produces a Blob (WebM Opus) suitable for upload to the analysis API.
 * Provides real-time waveform data via onWaveformData callback.
 */
class AudioRecorder {
    constructor(options = {}) {
        this.maxDurationMs = options.maxDurationMs || 30000;
        this.mimeType = this._selectMimeType();
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.analyserNode = null;
        this.audioCtx = null;
        this.startTime = null;
        this.timerInterval = null;
        this.onDurationUpdate = options.onDurationUpdate || (() => {});
        this.onMaxReached = options.onMaxReached || (() => {});
        this.onWaveformData = options.onWaveformData || (() => {});
    }

    _selectMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
        ];
        for (const t of types) {
            if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) {
                return t;
            }
        }
        return '';
    }

    async start() {
        this.stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            }
        });

        // Analyser for waveform
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source = this.audioCtx.createMediaStreamSource(this.stream);
        this.analyserNode = this.audioCtx.createAnalyser();
        this.analyserNode.fftSize = 2048;
        source.connect(this.analyserNode);

        this.audioChunks = [];
        const opts = this.mimeType ? { mimeType: this.mimeType } : {};
        this.mediaRecorder = new MediaRecorder(this.stream, opts);

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.audioChunks.push(e.data);
        };

        this.mediaRecorder.start(250);
        this.startTime = Date.now();

        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            this.onDurationUpdate(elapsed);
            if (elapsed >= this.maxDurationMs) {
                this.stop().then(blob => {
                    if (blob) this.onMaxReached(blob);
                });
            }
        }, 100);

        this._drawLoop();
    }

    _drawLoop() {
        if (!this.analyserNode || !this.mediaRecorder ||
            this.mediaRecorder.state !== 'recording') return;
        const data = new Uint8Array(this.analyserNode.frequencyBinCount);
        this.analyserNode.getByteTimeDomainData(data);
        this.onWaveformData(data);
        requestAnimationFrame(() => this._drawLoop());
    }

    async stop() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }

        return new Promise((resolve) => {
            if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
                this._cleanup();
                resolve(null);
                return;
            }
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.audioChunks, {
                    type: this.mimeType || 'audio/webm'
                });
                this._cleanup();
                resolve(blob);
            };
            this.mediaRecorder.stop();
        });
    }

    _cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
        if (this.audioCtx) {
            this.audioCtx.close().catch(() => {});
            this.audioCtx = null;
        }
    }
}
