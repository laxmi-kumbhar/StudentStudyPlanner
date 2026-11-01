/**
 * Global Student Study Planner JavaScript Core
 */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initModals();
});

// Toast notification helper
window.showToast = function(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconSvg = type === 'success' 
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

    toast.innerHTML = `${iconSvg} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
};

// Modal helpers
window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
};

window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
};

function initModals() {
    // Close modal on background click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
        }
    });
}

// Sidebar toggle for mobile responsive view
function initSidebar() {
    const toggleBtn = document.querySelector('.mobile-nav-toggle');
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    const closeBtn = document.getElementById('sidebarCloseBtn');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            if (sidebar.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeSidebar);
    }

    // Auto-close sidebar on mobile when navigating
    document.querySelectorAll('.sidebar .nav-item, .sidebar a').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 1024) {
                closeSidebar();
            }
        });
    });

    window.closeMobileSidebar = closeSidebar;
}

// Web Audio API Chime Synth (High fidelity sound without external mp3)
window.playChimeSound = function() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        
        const ctx = new AudioContext();
        const frequencies = [523.25, 659.25, 783.99, 1046.50]; // C Major chord
        
        frequencies.forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.1);
            
            gain.gain.setValueAtTime(0.15, ctx.currentTime + idx * 0.1);
            gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + idx * 0.1 + 1.2);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start(ctx.currentTime + idx * 0.1);
            osc.stop(ctx.currentTime + idx * 0.1 + 1.2);
        });
    } catch (e) {
        console.log("Audio not allowed or supported:", e);
    }
};

/* ================= STUDYFLOW AI ASSISTANT CONTROLLER ================= */
let aiChatHistory = [];

document.addEventListener('DOMContentLoaded', () => {
    initAiChat();
    initAiConfig();
    initAmbientAudio();
    initFlashcards();
});

function initAiConfig() {
    const toggleBtn = document.getElementById('aiConfigToggleBtn');
    const drawer = document.getElementById('aiConfigDrawer');
    const providerSelect = document.getElementById('aiProviderSelect');
    const apiKeyRow = document.getElementById('aiApiKeyRow');
    const apiKeyInput = document.getElementById('aiApiKeyInput');
    const keyHint = document.getElementById('aiKeyHint');
    const saveKeyBtn = document.getElementById('aiSaveKeyBtn');
    const activeBadge = document.getElementById('aiActiveProviderBadge');

    if (!toggleBtn || !drawer || !providerSelect) return;

    // Toggle drawer visibility
    toggleBtn.addEventListener('click', () => {
        const isHidden = drawer.style.display === 'none' || !drawer.style.display;
        drawer.style.display = isHidden ? 'block' : 'none';
        toggleBtn.style.color = isHidden ? '#a855f7' : '';
    });

    // Hints per provider
    const hints = {
        builtin: "Ready to use! Built-in offline ChatGPT assistant requires no key.",
        gemini: 'Get a free Google Gemini key in 30 seconds at <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener">Google AI Studio</a>',
        groq: 'Get a free, ultra-fast Groq key at <a href="https://console.groq.com/keys" target="_blank" rel="noopener">Groq Console</a>',
        openai: 'Get an OpenAI API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">OpenAI Platform</a>'
    };

    function updateDrawerUI(selected) {
        if (selected === 'builtin') {
            apiKeyRow.style.display = 'none';
        } else {
            apiKeyRow.style.display = 'block';
            apiKeyInput.placeholder = selected === 'gemini' ? 'AIzaSy...' : 'sk-... or gsk_...';
        }
        if (keyHint) {
            keyHint.innerHTML = hints[selected] || '';
        }
    }

    providerSelect.addEventListener('change', () => {
        updateDrawerUI(providerSelect.value);
    });

    // Load active config on startup
    fetch('/api/ai/config')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.config) {
                const cfg = data.config;
                providerSelect.value = cfg.active_provider || 'builtin';
                updateDrawerUI(providerSelect.value);
                if (activeBadge) {
                    activeBadge.textContent = `Active: ${cfg.active_display}`;
                }
            }
        })
        .catch(err => console.log('Could not load AI config:', err));

    // Save key
    if (saveKeyBtn) {
        saveKeyBtn.addEventListener('click', async () => {
            const provider = providerSelect.value;
            const apiKey = apiKeyInput.value.trim();

            if (provider !== 'builtin' && !apiKey) {
                if (window.showToast) window.showToast("Please enter an API key", "warning");
                return;
            }

            saveKeyBtn.disabled = true;
            saveKeyBtn.textContent = 'Saving...';

            try {
                const res = await fetch('/api/ai/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider: provider, api_key: apiKey })
                });
                const result = await res.json();
                if (result.success) {
                    if (window.showToast) window.showToast(`AI Engine updated to ${provider.toUpperCase()}`, "success");
                    if (activeBadge && result.config) {
                        activeBadge.textContent = `Active: ${result.config.active_display}`;
                    }
                    apiKeyInput.value = '';
                    drawer.style.display = 'none';
                    if (toggleBtn) toggleBtn.style.color = '';
                } else {
                    if (window.showToast) window.showToast(result.error || "Failed to save key", "error");
                }
            } catch (err) {
                if (window.showToast) window.showToast("Connection error while saving key", "error");
            } finally {
                saveKeyBtn.disabled = false;
                saveKeyBtn.textContent = 'Save Key';
            }
        });
    }
}

function initAiChat() {
    const form = document.getElementById('aiChatForm');
    const input = document.getElementById('aiPromptInput');
    const messages = document.getElementById('aiChatMessages');
    const clearBtn = document.getElementById('aiClearChatBtn');
    const quickChips = document.querySelectorAll('.ai-prompt-chip');

    if (!form || !input || !messages) return;

    // Auto-resize textarea as user types
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    // Enter to submit, Shift+Enter for new line
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    });

    // Quick prompt chips
    quickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const prompt = chip.dataset.prompt || chip.textContent.trim();
            input.value = prompt;
            submitAiQuery(prompt);
        });
    });

    // Clear chat button
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            aiChatHistory = [];
            messages.innerHTML = `
                <div class="ai-message ai-message-bot">
                    <div class="ai-msg-avatar">🤖</div>
                    <div class="ai-msg-content">
                        <p>Chat cleared! 👋 How can I help with your studies, programming, projects, or career plans?</p>
                    </div>
                </div>
            `;
            if (window.showToast) window.showToast("Conversation reset", "success");
        });
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prompt = input.value.trim();
        if (!prompt) return;
        await submitAiQuery(prompt);
    });

    async function submitAiQuery(promptText) {
        // Append user message
        const userMsg = document.createElement('div');
        userMsg.className = 'ai-message ai-message-user';
        userMsg.innerHTML = `<div class="ai-msg-content">${escapeHtmlText(promptText)}</div>`;
        messages.appendChild(userMsg);

        // Snapshot history to send
        const historyToSend = [...aiChatHistory];
        aiChatHistory.push({ role: 'user', content: promptText });

        // Reset input
        input.value = '';
        input.style.height = 'auto';
        messages.scrollTop = messages.scrollHeight;

        // Show typing indicator
        const typingMsg = document.createElement('div');
        typingMsg.className = 'ai-message ai-message-bot ai-typing-msg';
        typingMsg.innerHTML = `
            <div class="ai-msg-avatar">🤖</div>
            <div class="ai-msg-content">
                <div class="ai-typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        messages.appendChild(typingMsg);
        messages.scrollTop = messages.scrollHeight;

        const sendBtn = document.getElementById('aiSendBtn');
        if (sendBtn) sendBtn.disabled = true;

        try {
            let res;
            if (typeof api !== 'undefined' && api.post) {
                res = await api.post('/api/ai/ask', { prompt: promptText, history: historyToSend });
            } else {
                const response = await fetch('/api/ai/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: promptText, history: historyToSend })
                });
                res = await response.json();
            }

            // Remove typing indicator
            typingMsg.remove();

            if (res && res.success && res.answer) {
                // Update history
                aiChatHistory.push({ role: 'assistant', content: res.answer });
                if (aiChatHistory.length > 14) {
                    aiChatHistory = aiChatHistory.slice(-14);
                }

                const botMsg = document.createElement('div');
                botMsg.className = 'ai-message ai-message-bot';
                botMsg.innerHTML = `
                    <div class="ai-msg-avatar">🤖</div>
                    <div class="ai-msg-content">${formatAiMarkdown(res.answer)}</div>
                `;
                messages.appendChild(botMsg);
                if (window.playChimeSound) window.playChimeSound();
            } else {
                const errMsg = document.createElement('div');
                errMsg.className = 'ai-message ai-message-bot';
                errMsg.innerHTML = `
                    <div class="ai-msg-avatar">⚠️</div>
                    <div class="ai-msg-content" style="border-left: 3px solid #f43f5e;">
                        <p>${res && res.error ? escapeHtmlText(res.error) : "Sorry, I couldn't process your request right now. Please try again."}</p>
                    </div>
                `;
                messages.appendChild(errMsg);
            }
        } catch (err) {
            console.error("AI chat request failed:", err);
            typingMsg.remove();
            const errMsg = document.createElement('div');
            errMsg.className = 'ai-message ai-message-bot';
            errMsg.innerHTML = `
                <div class="ai-msg-avatar">⚠️</div>
                <div class="ai-msg-content" style="border-left: 3px solid #f43f5e;">
                    <p>Connection error. Please ensure the server is running and try again.</p>
                </div>
            `;
            messages.appendChild(errMsg);
        } finally {
            if (sendBtn) sendBtn.disabled = false;
            messages.scrollTop = messages.scrollHeight;
            input.focus();
        }
    }
}

// Global copy button handler
window.copyAiCode = function(btn) {
    const codeBlock = btn.closest('.ai-code-block');
    if (!codeBlock) return;
    const codeEl = codeBlock.querySelector('code');
    if (!codeEl) return;
    const text = codeEl.innerText || codeEl.textContent;

    navigator.clipboard.writeText(text).then(() => {
        const orig = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        btn.style.color = '#34d399';
        btn.style.borderColor = '#10b981';
        setTimeout(() => {
            btn.innerHTML = orig;
            btn.style.color = '';
            btn.style.borderColor = '';
        }, 2000);
    }).catch(() => {
        if (window.showToast) window.showToast("Could not copy to clipboard", "warning");
    });
};

function escapeHtmlText(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatAiMarkdown(text) {
    if (!text) return '';

    const codeBlocks = [];
    const tableBlocks = [];

    // 1. Isolate and preserve fenced code blocks: ```lang ... ```
    let processed = text.replace(/```([a-zA-Z0-9_\-\+]*)\r?\n?([\s\S]*?)```/g, (match, lang, code) => {
        const cleanLang = (lang || 'code').toUpperCase();
        const placeholder = `@@AI_CODE_BLOCK_${codeBlocks.length}@@`;
        const escapedCode = escapeHtmlText(code.trim());
        codeBlocks.push(
            `\n<div class="ai-code-block">` +
                `<div class="ai-code-header">` +
                    `<span class="ai-code-lang">${cleanLang}</span>` +
                    `<button type="button" class="ai-code-copy-btn" onclick="copyAiCode(this)">📋 Copy Code</button>` +
                `</div>` +
                `<pre><code>${escapedCode}</code></pre>` +
            `</div>\n`
        );
        return placeholder;
    });

    // 2. Isolate and preserve markdown tables
    processed = processed.replace(/(?:^|\n)(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)/g, function(match, tableBlock) {
        const placeholder = `\n@@AI_TABLE_BLOCK_${tableBlocks.length}@@\n`;
        const lines = tableBlock.trim().split(/\r?\n/);
        if (lines.length < 2) return match;
        
        const headerCells = lines[0].split('|').slice(1, -1);
        const thead = `<thead><tr>${headerCells.map(c => `<th>${escapeHtmlText(c.trim())}</th>`).join('')}</tr></thead>`;
        
        const bodyRows = lines.slice(2).map(row => {
            const cells = row.split('|').slice(1, -1);
            return `<tr>${cells.map(c => `<td>${escapeHtmlText(c.trim())}</td>`).join('')}</tr>`;
        }).join('');
        
        tableBlocks.push(
            `\n<div class="ai-table-responsive">` +
                `<table class="ai-table">${thead}<tbody>${bodyRows}</tbody></table>` +
            `</div>\n`
        );
        return placeholder;
    });

    // 3. Escape HTML for remaining narrative text
    let html = escapeHtmlText(processed);

    // 4. Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 5. Horizontal rule
    html = html.replace(/^\s*---\s*$/gim, '<hr class="ai-divider">');

    // 6. Headings
    html = html.replace(/^#### (.*$)/gim, '<h5 style="color:#f8fafc; margin:8px 0 4px; font-weight:700;">$1</h5>');
    html = html.replace(/^### (.*$)/gim, '<h4 style="color:#f8fafc; margin:10px 0 4px; font-weight:700;">$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3 style="color:#f8fafc; margin:12px 0 6px; font-weight:700;">$1</h3>');

    // 7. Bold & italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 8. Blockquotes
    html = html.replace(/^&gt; (.*$)/gim, '<blockquote>$1</blockquote>');

    // 9. Numbered lists
    html = html.replace(/^(\d+)\.\s+(.*$)/gim, '<li data-num="$1">$2</li>');
    html = html.replace(/(<li data-num="[0-9]+">.*?<\/li>)/gim, '<ol>$1</ol>');
    html = html.replace(/<\/ol>\s*<ol>/gim, '');

    // 10. Bullet lists
    html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\s*<ul>/gim, '');

    // 11. Paragraph splits
    const paras = html.split(/\n{2,}/);
    html = paras.map(p => {
        p = p.trim();
        if (!p) return '';
        if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<blockquote') || p.startsWith('<hr') || p.includes('@@AI_CODE_BLOCK_') || p.includes('@@AI_TABLE_BLOCK_')) {
            return p;
        }
        return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).filter(Boolean).join('');

    // 12. Reinsert preserved code blocks and tables
    codeBlocks.forEach((block, idx) => {
        html = html.replace(`@@AI_CODE_BLOCK_${idx}@@`, block);
    });
    tableBlocks.forEach((tbl, idx) => {
        html = html.replace(`@@AI_TABLE_BLOCK_${idx}@@`, tbl);
    });

    return html;
}

/* ================= FOCUS ROOM AMBIENT SOUND SYNTHESIZER ================= */
let ambientAudioCtx = null;
let currentAmbientNodes = [];
let ambientMasterGain = null;
let currentActiveSound = 'none';

function initAmbientAudio() {
    const trackBtns = document.querySelectorAll('.ambient-track-btn');
    const volSlider = document.getElementById('ambientVolumeSlider');
    if (!trackBtns.length) return;

    if (volSlider) {
        volSlider.addEventListener('input', (e) => {
            const vol = parseFloat(e.target.value) / 100;
            if (ambientMasterGain && ambientAudioCtx) {
                ambientMasterGain.gain.setValueAtTime(vol, ambientAudioCtx.currentTime);
            }
        });
    }

    trackBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const soundType = btn.dataset.sound;
            playAmbientSound(soundType, trackBtns);
        });
    });
}

function stopAmbientSound() {
    if (currentAmbientNodes.length) {
        currentAmbientNodes.forEach(node => {
            try { 
                if (typeof node.stop === 'function') node.stop();
                if (typeof node.disconnect === 'function') node.disconnect();
            } catch (e) {}
        });
        currentAmbientNodes = [];
    }
    currentActiveSound = 'none';
}

function playAmbientSound(type, trackBtns) {
    stopAmbientSound();

    trackBtns.forEach(b => {
        b.classList.remove('active-play');
        if (b.dataset.sound === 'none') b.classList.add('active-stop');
    });

    if (type === 'none') {
        const offBtn = Array.from(trackBtns).find(b => b.dataset.sound === 'none');
        if (offBtn) offBtn.classList.add('active-stop');
        return;
    }

    const clickedBtn = Array.from(trackBtns).find(b => b.dataset.sound === type);
    if (clickedBtn) {
        clickedBtn.classList.add('active-play');
        const offBtn = Array.from(trackBtns).find(b => b.dataset.sound === 'none');
        if (offBtn) offBtn.classList.remove('active-stop');
    }

    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    if (!ambientAudioCtx) ambientAudioCtx = new AudioContext();
    if (ambientAudioCtx.state === 'suspended') ambientAudioCtx.resume();

    const volSlider = document.getElementById('ambientVolumeSlider');
    const vol = volSlider ? parseFloat(volSlider.value) / 100 : 0.4;
    ambientMasterGain = ambientAudioCtx.createGain();
    ambientMasterGain.gain.setValueAtTime(vol, ambientAudioCtx.currentTime);
    ambientMasterGain.connect(ambientAudioCtx.destination);

    currentActiveSound = type;

    if (type === 'rain' || type === 'ocean' || type === 'whitenoise') {
        const bufferSize = ambientAudioCtx.sampleRate * 3;
        const noiseBuffer = ambientAudioCtx.createBuffer(1, bufferSize, ambientAudioCtx.sampleRate);
        const output = noiseBuffer.getChannelData(0);
        let lastOut = 0.0;
        for (let i = 0; i < bufferSize; i++) {
            const white = Math.random() * 2 - 1;
            if (type === 'whitenoise') {
                output[i] = (lastOut + (0.02 * white)) / 1.02;
                lastOut = output[i];
            } else {
                output[i] = white * 0.4;
            }
        }

        const whiteNoiseSource = ambientAudioCtx.createBufferSource();
        whiteNoiseSource.buffer = noiseBuffer;
        whiteNoiseSource.loop = true;

        if (type === 'rain') {
            const filter = ambientAudioCtx.createBiquadFilter();
            filter.type = 'lowpass';
            filter.frequency.setValueAtTime(1100, ambientAudioCtx.currentTime);
            whiteNoiseSource.connect(filter);
            filter.connect(ambientMasterGain);
        } else if (type === 'ocean') {
            const filter = ambientAudioCtx.createBiquadFilter();
            filter.type = 'bandpass';
            filter.frequency.setValueAtTime(500, ambientAudioCtx.currentTime);

            const waveGain = ambientAudioCtx.createGain();
            const lfo = ambientAudioCtx.createOscillator();
            lfo.frequency.setValueAtTime(0.12, ambientAudioCtx.currentTime);
            const lfoGain = ambientAudioCtx.createGain();
            lfoGain.gain.setValueAtTime(0.35, ambientAudioCtx.currentTime);

            lfo.connect(lfoGain);
            lfoGain.connect(waveGain.gain);

            whiteNoiseSource.connect(filter);
            filter.connect(waveGain);
            waveGain.connect(ambientMasterGain);

            lfo.start();
            currentAmbientNodes.push(lfo);
        } else {
            whiteNoiseSource.connect(ambientMasterGain);
        }

        whiteNoiseSource.start();
        currentAmbientNodes.push(whiteNoiseSource);
    } else if (type === 'lofi') {
        const notes = [130.81, 164.81, 196.00, 246.94];
        notes.forEach(freq => {
            const osc = ambientAudioCtx.createOscillator();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(freq, ambientAudioCtx.currentTime);

            const lpf = ambientAudioCtx.createBiquadFilter();
            lpf.type = 'lowpass';
            lpf.frequency.setValueAtTime(450, ambientAudioCtx.currentTime);

            const oscGain = ambientAudioCtx.createGain();
            oscGain.gain.setValueAtTime(0.08, ambientAudioCtx.currentTime);

            osc.connect(lpf);
            lpf.connect(oscGain);
            oscGain.connect(ambientMasterGain);

            osc.start();
            currentAmbientNodes.push(osc);
        });
    }
}

/* ================= AI FLASHCARDS CONTROLLER ================= */
let activeFlashcardsDeck = [];
let currentCardIndex = 0;

window.openFlashcardsModal = function() {
    const modal = document.getElementById('flashcardsModal');
    if (!modal) return;
    modal.classList.add('active');
    if (!activeFlashcardsDeck.length) {
        loadFlashcardDeck();
    }
};

window.toggleFlashcardFlip = function() {
    const card = document.getElementById('activeFlashcard');
    if (card) {
        card.classList.toggle('flipped');
    }
};

window.navigateFlashcard = function(dir) {
    if (!activeFlashcardsDeck.length) return;
    const newIdx = currentCardIndex + dir;
    if (newIdx >= 0 && newIdx < activeFlashcardsDeck.length) {
        currentCardIndex = newIdx;
        renderCurrentCard();
    }
};

window.markCardMastered = function() {
    const btn = document.getElementById('btnMarkMastered');
    if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '🌟 Mastered!';
        btn.style.background = '#10b981';
        btn.style.color = '#ffffff';
        if (window.playChimeSound) window.playChimeSound();
        setTimeout(() => {
            btn.innerHTML = orig;
            btn.style.background = '';
            btn.style.color = '';
            navigateFlashcard(1);
        }, 700);
    }
};

function renderCurrentCard() {
    const cardEl = document.getElementById('activeFlashcard');
    if (cardEl) cardEl.classList.remove('flipped');

    if (!activeFlashcardsDeck.length) return;
    const card = activeFlashcardsDeck[currentCardIndex];

    const qEl = document.getElementById('fcQuestionText');
    const aEl = document.getElementById('fcAnswerText');
    const tagEl = document.getElementById('fcTagBadge');
    const diffEl = document.getElementById('fcDifficultyBadge');
    const counterEl = document.getElementById('fcCounterText');
    const progressEl = document.getElementById('fcProgressBar');

    if (qEl) qEl.textContent = card.front;
    if (aEl) aEl.textContent = card.back;
    if (tagEl) tagEl.textContent = card.tag || 'Core Concept';
    if (diffEl) diffEl.textContent = card.difficulty || 'Fundamental';
    if (counterEl) counterEl.textContent = `Card ${currentCardIndex + 1} of ${activeFlashcardsDeck.length}`;
    if (progressEl) {
        const pct = ((currentCardIndex + 1) / activeFlashcardsDeck.length) * 100;
        progressEl.style.width = `${pct}%`;
    }

    const prevBtn = document.getElementById('btnPrevCard');
    const nextBtn = document.getElementById('btnNextCard');
    if (prevBtn) prevBtn.disabled = currentCardIndex === 0;
    if (nextBtn) nextBtn.disabled = currentCardIndex === activeFlashcardsDeck.length - 1;
}

function loadFlashcardDeck(topic = '', subjectId = null) {
    const qEl = document.getElementById('fcQuestionText');
    if (qEl) qEl.innerHTML = '<div style="color:#818cf8;">✨ Generating AI Flashcard Deck...</div>';

    fetch('/api/ai/flashcards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, subject_id: subjectId })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success && data.cards && data.cards.length) {
            activeFlashcardsDeck = data.cards;
            currentCardIndex = 0;
            renderCurrentCard();
        } else {
            if (qEl) qEl.textContent = 'Could not load flashcards. Please try again.';
        }
    })
    .catch(err => {
        console.error('Flashcards error:', err);
        if (qEl) qEl.textContent = 'Network error loading cards.';
    });
}

function initFlashcards() {
    const genBtn = document.getElementById('btnGenerateFlashcards');
    const subjSelect = document.getElementById('flashcardSubjectSelect');
    const customInput = document.getElementById('flashcardCustomTopic');

    if (genBtn) {
        genBtn.addEventListener('click', () => {
            const custom = customInput ? customInput.value.trim() : '';
            const subjId = subjSelect ? subjSelect.value : null;
            loadFlashcardDeck(custom, subjId ? parseInt(subjId) : null);
        });
    }

    // Keyboard shortcuts
    window.addEventListener('keydown', (e) => {
        const modal = document.getElementById('flashcardsModal');
        if (modal && modal.classList.contains('active')) {
            if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                toggleFlashcardFlip();
            } else if (e.code === 'ArrowRight') {
                navigateFlashcard(1);
            } else if (e.code === 'ArrowLeft') {
                navigateFlashcard(-1);
            }
        }
    });
}

/* ================= PRINT TIMETABLE EXPORTER ================= */
window.printTimetableSchedule = function() {
    if (typeof switchView === 'function') {
        switchView('calendar');
    }
    const ttTab = document.getElementById('timetableTab');
    const exTab = document.getElementById('examsTab');
    if (ttTab) ttTab.style.display = 'block';
    if (exTab) exTab.style.display = 'none';

    setTimeout(() => {
        window.print();
    }, 200);
};

