document.addEventListener('DOMContentLoaded', () => {
    try {
        // Elements
        const rawMessage = document.getElementById('rawMessage');
        const charCount = document.getElementById('charCount');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const loadingPipeline = document.getElementById('loadingPipeline');
        const statusText = document.getElementById('statusText');
        const resultsPanel = document.getElementById('resultsPanel');
        const errorBanner = document.getElementById('errorBanner');
        const retryBtn = document.getElementById('retryBtn');
        const escalationBanner = document.getElementById('escalationBanner');
        
        if (!analyzeBtn) {
            alert('CRITICAL ERROR: analyzeBtn not found in DOM.');
            return;
        }

        // Capability Pills Animation
        setTimeout(() => {
            const pills = document.querySelectorAll('.pill');
            pills.forEach((pill, index) => {
                setTimeout(() => {
                    pill.style.transition = 'all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    pill.style.opacity = '1';
                    pill.style.transform = 'scale(1)';
                }, index * 200);
            });
        }, 500);

        // Custom Dropdown Logic
        const customSelects = document.querySelectorAll('.custom-select');

    customSelects.forEach(customSelect => {
        const trigger = customSelect.querySelector('.select-trigger');
        const options = customSelect.querySelectorAll('.custom-option');
        const hiddenInput = customSelect.nextElementSibling;
        const selectedText = customSelect.querySelector('.selected-text');
        const optionsPanel = customSelect.querySelector('.custom-options');

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close others
            customSelects.forEach(select => {
                if (select !== customSelect) select.classList.remove('open');
            });
            customSelect.classList.toggle('open');
        });

        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                options.forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');
                selectedText.textContent = option.textContent;
                hiddenInput.value = option.dataset.value;
                customSelect.classList.remove('open');
            });
        });

        optionsPanel.addEventListener('wheel', (e) => {
            e.stopPropagation();
        }, { passive: true });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', () => {
        customSelects.forEach(select => select.classList.remove('open'));
    });

    // Textarea Auto-expand & Char Count
    rawMessage.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        const count = this.value.length;
        charCount.textContent = `${count} / 2000`;
        
        if (count < 1500) charCount.style.color = 'var(--text-muted)';
        else if (count < 1900) charCount.style.color = 'var(--accent-amber)';
        else charCount.style.color = 'var(--accent-rose)';
    });

    let currentAnalysisResult = null;
    let selectedVersion = null;

    // Retry button
    retryBtn.addEventListener('click', () => analyzeBtn.click());

    // Analyze Button
    analyzeBtn.addEventListener('click', async () => {
        const text = rawMessage.value.trim();
        const recipient = document.getElementById('recipientName').value.trim();
        const platform = document.getElementById('platformSelect') ? document.getElementById('platformSelect').value : 'email';
        const langSelect = document.getElementById('languageSelect');
        const targetLanguage = langSelect ? langSelect.value : 'Auto';

        if (!text || !recipient) {
            alert('Please provide both a message and a recipient name.');
            return;
        }

        // Reset UI
        analyzeBtn.classList.add('hidden');
        loadingPipeline.classList.remove('hidden');
        resultsPanel.classList.add('hidden');
        errorBanner.classList.add('hidden');
        document.getElementById('formatPanel').classList.add('hidden');
        document.getElementById('outcomePanel').classList.add('hidden');
        
        // Reset Pipeline
        for(let i=1; i<=4; i++) {
            document.getElementById(`node-${i}`)?.classList.remove('active');
            if(document.getElementById(`fill-${i}`)) document.getElementById(`fill-${i}`).style.width = '0%';
        }
        
        // Pipeline Animation Sequence
        const statuses = [
            "Reading your message and detecting tone...",
            "Checking history with this contact...",
            "Rewriting in the right language and tone... (This takes 20-40s locally)",
            "Applying final formatting..."
        ];

        let step = 1;
        const interval = setInterval(() => {
            if(step <= 3) {
                document.getElementById(`node-${step}`).classList.add('active');
                if(step > 1) document.getElementById(`fill-${step-1}`).style.width = '100%';
                statusText.textContent = statuses[step-1];
                step++;
            }
        }, 800);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw_text: text,
                    recipient_name: recipient,
                    platform: platform,
                    target_language: targetLanguage
                })
            });

            clearInterval(interval);
            
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to analyze');
            }

            const data = await response.json();
            currentAnalysisResult = data;
            
            // Complete Pipeline UI
            document.getElementById('node-4').classList.add('active');
            document.getElementById('fill-3').style.width = '100%';
            statusText.textContent = "Done!";
            
            setTimeout(() => {
                loadingPipeline.classList.add('hidden');
                analyzeBtn.classList.remove('hidden');
                displayResults(data);
            }, 600);

        } catch (error) {
            clearInterval(interval);
            loadingPipeline.classList.add('hidden');
            analyzeBtn.classList.remove('hidden');
            errorBanner.classList.remove('hidden');
            document.getElementById('errorMsgText').textContent = error.message;
        }
    });

    function displayResults(data) {
        resultsPanel.classList.remove('hidden');
        
        const risk = data.risk_analysis;
        const memory = data.memory_analysis;
        const rewrites = data.rewrites;

        // Context Chips
        const relChip = document.getElementById('chipRelationship');
        const scnChip = document.getElementById('chipScenario');
        const langChip = document.getElementById('chipLanguage');
        
        relChip.textContent = `👤 ${risk.relationship_type.replace('_', ' ')}`;
        scnChip.textContent = `💬 ${risk.scenario}`;
        langChip.textContent = `🌐 Output: ${risk.output_language}`;
        
        // Staggered pop-in for chips
        [relChip, scnChip, langChip].forEach((chip, i) => {
            chip.style.transform = 'scale(0.6)';
            chip.style.opacity = '0';
            setTimeout(() => {
                chip.style.transition = 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
                chip.style.transform = 'scale(1)';
                chip.style.opacity = '1';
                chip.classList.add('active');
            }, 100 + (i * 80));
        });

        // Risk Gauge Animation
        const score = risk.risk_score;
        const gaugeFill = document.getElementById('gaugeFill');
        const scoreVal = document.getElementById('riskScoreVal');
        const circ = 314; // 2 * PI * 50
        
        // Color Interpolation (Emerald -> Amber -> Rose)
        let color = 'var(--accent-emerald)';
        if(score > 30 && score <= 60) color = 'var(--accent-amber)';
        if(score > 60) color = 'var(--accent-rose)';
        
        gaugeFill.style.strokeDashoffset = circ;
        gaugeFill.style.stroke = color;
        scoreVal.style.color = color;
        
        setTimeout(() => {
            gaugeFill.style.strokeDashoffset = circ - (circ * (score / 100));
            
            // Number counter
            let current = 0;
            const updateCount = () => {
                if (current < score) {
                    current += Math.ceil(score / 30);
                    if (current > score) current = score;
                    scoreVal.textContent = current;
                    requestAnimationFrame(updateCount);
                }
            };
            requestAnimationFrame(updateCount);
        }, 300);

        document.getElementById('detectedTone').textContent = `Tone: ${risk.detected_tone}`;

        // Risk Tags
        const tagsContainer = document.getElementById('riskTags');
        tagsContainer.innerHTML = '';
        (risk.risk_reasons || []).forEach((r, i) => {
            const tag = document.createElement('div');
            tag.className = 'risk-tag';
            tag.textContent = r;
            tagsContainer.appendChild(tag);
            
            setTimeout(() => {
                tag.style.transition = 'all 0.3s ease';
                tag.style.transform = 'translateX(0)';
                tag.style.opacity = '1';
            }, 300 + (i * 120));
        });

        // Memory
        let memText = `Past Interactions: ${memory.message_count} messages`;
        if (memory.message_count > 0) {
            memText += ` (Last outcome: ${memory.last_outcome || 'N/A'})`;
            if (memory.repeat_issue_warning) {
                memText += `<br><span style="color:var(--accent-amber)">⚠️ ${memory.repeat_issue_warning}</span>`;
            }
        } else {
            memText = "First time messaging this contact.";
        }
        document.getElementById('memoryStatus').innerHTML = memText;

        // Escalation
        if (risk.escalation_detected) {
            escalationBanner.classList.remove('hidden');
            document.getElementById('escReason').textContent = risk.escalation_reason || "High risk of conflict.";
            document.getElementById('escAction').textContent = risk.recommended_action;
        } else {
            escalationBanner.classList.add('hidden');
        }

        // Rewrite notes
        const notes = document.getElementById('rewriteNotes');
        notes.textContent = `✨ ${rewrites.rewrite_notes || 'Adjusted tone for context.'}`;
        setTimeout(() => { notes.style.opacity = '1'; }, 400);

        // Version Cards
        ['diplomatic', 'direct', 'warm'].forEach((v, i) => {
            const card = document.querySelector(`.card-${v}`);
            const textEl = document.getElementById(`text${v.charAt(0).toUpperCase() + v.slice(1)}`);
            const badge = document.getElementById(`riskBadge${v.charAt(0).toUpperCase() + v.slice(1)}`);
            
            // Reset styles
            card.classList.remove('selected');
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.filter = 'none';
            textEl.textContent = '';
            textEl.classList.remove('typing');
            
            // Risk Badge
            const sAfter = rewrites.risk_score_after[v];
            badge.textContent = sAfter;
            badge.className = 'risk-badge';
            if(sAfter <= 30) badge.classList.add('risk-emerald');
            else if(sAfter <= 60) badge.classList.add('risk-amber');
            else badge.classList.add('risk-rose');

            // Animate card entrance
            setTimeout(() => {
                card.style.transition = 'all 0.4s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
                
                // Start typewriter effect after card appears
                setTimeout(() => typeWriter(textEl, rewrites.versions[v]), 200);
            }, 600 + (i * 100));
        });
    }

    function typeWriter(element, text) {
        element.classList.add('typing');
        let i = 0;
        const speed = 18; // ms per char
        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            } else {
                element.classList.remove('typing');
            }
        }
        type();
    }

    // Card Selection
    document.querySelectorAll('.use-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const card = e.target.closest('.version-card');
            const version = card.dataset.version;
            selectedVersion = version;

            // UI styling for selection
            document.querySelectorAll('.version-card').forEach(c => {
                if (c === card) {
                    c.classList.add('selected');
                    c.style.opacity = '1';
                    c.style.filter = 'none';
                } else {
                    c.classList.remove('selected');
                    c.style.opacity = '0.35';
                    c.style.filter = 'saturate(0.3)';
                }
            });

            // Call Formatter
            const chosenText = currentAnalysisResult.rewrites.versions[version];
            const platform = document.getElementById('platformSelect').value;
            const relType = currentAnalysisResult.risk_analysis.relationship_type;
            const outputLanguage = currentAnalysisResult.risk_analysis.output_language || currentAnalysisResult.rewrites.output_language || 'english';

            document.getElementById('formatPanel').classList.add('hidden');
            
            try {
                const response = await fetch('/format', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        chosen_message: chosenText,
                        platform: platform,
                        relationship_type: relType,
                        output_language: outputLanguage
                    })
                });
                
                const data = await response.json();
                
                // Show Formatted Output
                const formatPanel = document.getElementById('formatPanel');
                let icon = platform === 'email' ? '📧' : platform === 'slack' ? '💬' : '📱';
                document.getElementById('formatPlatform').textContent = `${icon} ${platform.charAt(0).toUpperCase() + platform.slice(1)} Format`;
                document.getElementById('finalMessage').textContent = data.formatted_message || chosenText;
                
                formatPanel.classList.remove('hidden');
                document.getElementById('outcomePanel').classList.remove('hidden');
                
            } catch (err) {
                console.error(err);
            }
        });
    });

    // Copy to Clipboard
    const copyBtn = document.getElementById('copyBtn');
    copyBtn.addEventListener('click', () => {
        const text = document.getElementById('finalMessage').textContent;
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = '✓ Copied';
            copyBtn.classList.add('copied');
            setTimeout(() => {
                copyBtn.textContent = 'Copy to clipboard';
                copyBtn.classList.remove('copied');
            }, 2000);
        });
    });

    // Outcome Logging
    document.querySelectorAll('.outcome-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            // Visual feedback
            document.querySelectorAll('.outcome-btn').forEach(b => {
                b.classList.remove('active');
                b.style.opacity = '0.5';
            });
            const clicked = e.target;
            clicked.classList.add('active');
            clicked.style.opacity = '1';

            const outcome = clicked.dataset.outcome;
            const recipient = document.getElementById('recipientName').value.trim();

            try {
                await fetch('/outcome', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        recipient_name: recipient,
                        message: currentAnalysisResult.sanitized_text, // Use the sanitized original
                        tone: currentAnalysisResult.risk_analysis.detected_tone,
                        relationship_type: currentAnalysisResult.risk_analysis.relationship_type,
                        scenario: currentAnalysisResult.risk_analysis.scenario,
                        detected_language: currentAnalysisResult.risk_analysis.detected_language,
                        output_language: currentAnalysisResult.risk_analysis.output_language,
                        risk_score: currentAnalysisResult.risk_analysis.risk_score,
                        chosen_version: selectedVersion,
                        outcome: outcome
                    })
                });

                // Show toast
                const toast = document.getElementById('toast');
                toast.classList.remove('hidden');
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => toast.classList.add('hidden'), 350);
                }, 3000);

            } catch (err) {
                console.error("Failed to log outcome:", err);
            }
        });
        });
    } catch (e) {
        alert("CRITICAL ERROR ON LOAD: " + e.message);
        console.error(e);
    }
});
