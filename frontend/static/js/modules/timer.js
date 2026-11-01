/**
 * Pomodoro & Focus Timer Module
 */

class PomodoroTimer {
    constructor(options = {}) {
        this.durations = {
            pomodoro: 25 * 60,
            short_break: 5 * 60,
            long_break: 15 * 60,
            custom: 45 * 60
        };

        this.currentMode = 'pomodoro';
        this.totalSeconds = this.durations[this.currentMode];
        this.remainingSeconds = this.totalSeconds;
        this.timerInterval = null;
        this.isRunning = false;

        // Callbacks
        this.onTick = options.onTick || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onStateChange = options.onStateChange || (() => {});
    }

    setMode(mode, customMinutes = null) {
        this.pause();
        this.currentMode = mode;
        if (mode === 'custom' && customMinutes) {
            this.durations.custom = customMinutes * 60;
        }
        this.totalSeconds = this.durations[this.currentMode] || (25 * 60);
        this.remainingSeconds = this.totalSeconds;
        this.onTick(this.getFormattedTime(), this.getProgressPercentage());
        this.onStateChange(this.isRunning, this.currentMode);
    }

    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.onStateChange(this.isRunning, this.currentMode);

        this.timerInterval = setInterval(() => {
            if (this.remainingSeconds > 0) {
                this.remainingSeconds--;
                this.onTick(this.getFormattedTime(), this.getProgressPercentage());
            } else {
                this.complete();
            }
        }, 1000);
    }

    pause() {
        if (!this.isRunning) return;
        this.isRunning = false;
        clearInterval(this.timerInterval);
        this.timerInterval = null;
        this.onStateChange(this.isRunning, this.currentMode);
    }

    toggle() {
        if (this.isRunning) {
            this.pause();
        } else {
            this.start();
        }
    }

    reset() {
        this.pause();
        this.remainingSeconds = this.totalSeconds;
        this.onTick(this.getFormattedTime(), this.getProgressPercentage());
    }

    complete() {
        this.pause();
        if (window.playChimeSound) {
            window.playChimeSound();
        }
        
        const completedMinutes = Math.round(this.totalSeconds / 60);
        this.onComplete(this.currentMode, completedMinutes);
        this.reset();
    }

    getFormattedTime() {
        const mins = Math.floor(this.remainingSeconds / 60);
        const secs = this.remainingSeconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    getProgressPercentage() {
        if (this.totalSeconds === 0) return 100;
        return ((this.totalSeconds - this.remainingSeconds) / this.totalSeconds) * 100;
    }
}

window.PomodoroTimer = PomodoroTimer;
