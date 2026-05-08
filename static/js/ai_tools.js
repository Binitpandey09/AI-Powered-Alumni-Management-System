/* ============================================================
   AlumniAI — AI Career Tools JS
   Handles all 4 tools: Resume Score, Resume Builder,
   AI Mock Interview, Skill Gap Analyzer
   ============================================================ */

'use strict';

let _currentUsageId   = null;
let _interviewState   = {
    questions:     [],
    currentIdx:    0,
    answers:       [],
    jobRole:       '',
    timerInterval: null,
    timeLeft:      0,
};


// ══════════════════════════════════════════════════════════════
// SHARED: Payment gate
// ══════════════════════════════════════════════════════════════

function initToolPage(toolType) {
    // Placeholder — reserved for future lazy init
}

async function handleToolAccess(toolType, price) {
    const btn = document.querySelector('#payment-gate button');
    if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }

    const initRes = await apiPost('/api/payments/ai-tools/init/', { tool_type: toolType });
    if (!initRes.ok) {
        if (btn) { btn.disabled = false; btn.textContent = btn._origText || 'Get Started'; }
        showToast(initRes.data?.error || 'Could not start. Please try again.', 'error');
        return;
    }

    const data = initRes.data;

    if (data.is_free) {
        // No payment needed — verify immediately
        const verRes = await apiPost('/api/payments/ai-tools/verify/', {
            tool_type: toolType,
            is_free:   true,
        });
        if (!verRes.ok) {
            if (btn) { btn.disabled = false; }
            showToast(verRes.data?.error || 'Could not unlock tool.', 'error');
            return;
        }
        _currentUsageId = verRes.data.usage_id;
        _showToolSection();
    } else {
        // Open Razorpay
        if (typeof Razorpay === 'undefined') {
            showToast('Payment gateway not loaded. Please refresh.', 'error');
            if (btn) { btn.disabled = false; }
            return;
        }
        const rzp = new Razorpay({
            key:         data.razorpay_key_id,
            amount:      parseFloat(data.amount) * 100,
            currency:    data.currency || 'INR',
            name:        'AlumniAI',
            description: data.description,
            order_id:    data.razorpay_order_id,
            prefill:     { name: data.student_name, email: data.student_email },
            handler: async function (response) {
                const vRes = await apiPost('/api/payments/ai-tools/verify/', {
                    tool_type:           toolType,
                    is_free:             false,
                    razorpay_order_id:   response.razorpay_order_id,
                    razorpay_payment_id: response.razorpay_payment_id,
                    razorpay_signature:  response.razorpay_signature,
                });
                if (!vRes.ok) { showToast('Payment verification failed.', 'error'); return; }
                _currentUsageId = vRes.data.usage_id;
                _showToolSection();
            },
            modal: {
                ondismiss: () => { if (btn) { btn.disabled = false; } }
            },
        });
        rzp.open();
    }
}

function _showToolSection() {
    const gate  = document.getElementById('payment-gate');
    const iface = document.getElementById('tool-interface');
    if (gate)  gate.style.display  = 'none';
    if (iface) { iface.style.display = 'block'; iface.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}

function _showLoading(msg) {
    const ls = document.getElementById('loading-state');
    const lt = document.getElementById('loading-text');
    const ti = document.getElementById('tool-interface');
    if (ls) ls.style.display = 'block';
    if (lt && msg) lt.textContent = msg;
    if (ti) ti.style.display = 'none';
}

function _hideLoading() {
    const ls = document.getElementById('loading-state');
    if (ls) ls.style.display = 'none';
}

function _set(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}


// ══════════════════════════════════════════════════════════════
// TOOL 1 — Resume Score Checker
// ══════════════════════════════════════════════════════════════

async function runResumeCheck() {
    if (!_currentUsageId) { showToast('Please unlock the tool first.', 'error'); return; }

    const jobRole = (document.getElementById('job-role-input')?.value || '').trim();
    _showLoading('Analyzing your resume with AI…');

    const res = await apiPost('/api/ai/resume-score/', {
        usage_id: _currentUsageId,
        job_role: jobRole || null,
    });

    _hideLoading();

    if (!res.ok) {
        showToast(res.data?.error || 'Analysis failed. Please try again.', 'error');
        document.getElementById('tool-interface').style.display = 'block';
        return;
    }

    _renderResumeScore(res.data.result);
}

function _renderResumeScore(d) {
    const rs = document.getElementById('result-section');
    if (rs) rs.style.display = 'block';

    // Score ring
    const ring = document.getElementById('score-ring');
    const txt  = document.getElementById('score-text');
    if (ring) ring.setAttribute('stroke-dasharray', `${d.overall_score}, 100`);
    if (txt)  txt.textContent = d.overall_score;

    // Grade + ATS + summary
    const grade = document.getElementById('grade-badge');
    const ats   = document.getElementById('ats-score-text');
    const summ  = document.getElementById('summary-text');
    if (grade) { grade.textContent = d.grade; grade.style.color = _gradeColor(d.grade); grade.style.background = _gradeColor(d.grade) + '22'; }
    if (ats)   ats.textContent  = `ATS Score: ${d.ats_score}/100`;
    if (summ)  summ.textContent = d.summary;

    // Section bars
    const barsEl = document.getElementById('section-bars');
    const maxes  = { contact_info: 10, education: 20, skills: 20, experience: 25, projects: 15, formatting: 10 };
    if (barsEl && d.section_scores) {
        barsEl.innerHTML = Object.entries(d.section_scores).map(([key, val]) => {
            const max   = maxes[key] || 10;
            const pct   = Math.round((val / max) * 100);
            const color = pct >= 70 ? '#10B981' : pct >= 40 ? '#F59E0B' : '#EF4444';
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            return `<div>
              <div style="display:flex;justify-content:space-between;font-size:13px;color:#334155;margin-bottom:4px;">
                <span>${label}</span><span style="font-weight:600;">${val}/${max}</span>
              </div>
              <div style="background:#F1F5F9;border-radius:99px;height:8px;">
                <div style="background:${color};height:8px;border-radius:99px;width:${pct}%;transition:width .6s ease;"></div>
              </div>
            </div>`;
        }).join('');
    }

    // Strengths / weaknesses
    const sl = document.getElementById('strengths-list');
    const wl = document.getElementById('weaknesses-list');
    if (sl) sl.innerHTML = (d.strengths || []).map(s => `<li style="display:flex;gap:8px;"><span style="color:#10B981;flex-shrink:0;">✓</span>${s}</li>`).join('');
    if (wl) wl.innerHTML = (d.weaknesses || []).map(w => `<li style="display:flex;gap:8px;"><span style="color:#EF4444;flex-shrink:0;">✗</span>${w}</li>`).join('');

    // Improvements table
    const tbl = document.getElementById('improvements-table');
    if (tbl) {
        tbl.innerHTML = (d.improvements || []).map(i => `
          <tr style="border-bottom:1px solid #F1F5F9;">
            <td style="padding:10px 8px;font-weight:600;color:#334155;white-space:nowrap;">${i.section}</td>
            <td style="padding:10px 8px;color:#64748B;">${i.issue}</td>
            <td style="padding:10px 8px;color:#0F172A;">${i.suggestion}</td>
          </tr>`).join('');
    }

    // ATS keywords
    const fk = document.getElementById('found-keywords');
    const mk = document.getElementById('missing-keywords');
    if (fk) fk.innerHTML = (d.ats_keywords_found || []).map(k =>
        `<span style="background:#DCFCE7;color:#166534;font-size:12px;font-weight:600;padding:4px 10px;border-radius:20px;">${k}</span>`).join('');
    if (mk) mk.innerHTML = (d.ats_keywords_missing || []).map(k =>
        `<span style="background:#FEE2E2;color:#991B1B;font-size:12px;font-weight:600;padding:4px 10px;border-radius:20px;">${k}</span>`).join('');

    rs?.scrollIntoView({ behavior: 'smooth' });
}


// ══════════════════════════════════════════════════════════════
// TOOL 2 — Skill Gap Analyzer
// ══════════════════════════════════════════════════════════════

async function runSkillGapAnalysis() {
    if (!_currentUsageId) { showToast('Please unlock the tool first.', 'error'); return; }

    const targetRole = (document.getElementById('target-role-input')?.value || '').trim();
    if (!targetRole) {
        showToast('Please enter a target role.', 'error');
        document.getElementById('target-role-input')?.focus();
        return;
    }

    _showLoading('Analyzing your skill gap…');

    const res = await apiPost('/api/ai/skill-gap/', {
        usage_id:    _currentUsageId,
        target_role: targetRole,
    });

    _hideLoading();

    if (!res.ok) {
        showToast(res.data?.error || 'Analysis failed. Please try again.', 'error');
        document.getElementById('tool-interface').style.display = 'block';
        return;
    }

    _renderSkillGap(res.data.result);
}

function _renderSkillGap(d) {
    const rs = document.getElementById('result-section');
    if (rs) rs.style.display = 'block';

    // Readiness ring — template id: readiness-score-ring
    const ring = document.getElementById('readiness-score-ring');
    if (ring) ring.setAttribute('stroke-dasharray', `${d.readiness_score}, 100`);
    _set('readiness-score-text', d.readiness_score + '%');

    // Level + role + weeks — template ids: readiness-level-text, readiness-role, readiness-weeks
    _set('readiness-level-text', d.readiness_level);
    _set('readiness-role',       d.target_role);
    _set('readiness-weeks',      `${d.total_weeks_to_ready} weeks to job-ready`);

    // Matching skills — template id: matching-skills-container
    const cs = document.getElementById('matching-skills-container');
    if (cs) cs.innerHTML = (d.current_skills_relevant || []).map(s =>
        `<span style="background:#DCFCE7;color:#166534;font-size:12px;font-weight:600;padding:4px 10px;border-radius:20px;border:1px solid #BBF7D0;">${s}</span>`
    ).join('');

    // Skills to learn — template id: missing-skills-list
    const stl   = document.getElementById('missing-skills-list');
    const count = document.getElementById('missing-skills-count');
    const list  = d.skills_to_learn || [];
    if (count) count.textContent = `${list.length} skills`;
    if (stl) {
        const colors = { Critical: '#EF4444', High: '#F59E0B', Medium: '#2563EB', 'Nice to Have': '#64748B' };
        stl.innerHTML = list.map(s => `
          <div style="border-bottom:1px solid #F1F5F9;">
            <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 20px;cursor:pointer;"
                 onclick="var n=this.nextElementSibling;n.style.display=n.style.display==='none'?'block':'none'">
              <div style="display:flex;align-items:center;gap:10px;">
                <span style="background:${colors[s.priority]||'#475569'}22;color:${colors[s.priority]||'#475569'};font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">${s.priority}</span>
                <span style="font-weight:600;font-size:14px;color:#0F172A;">${s.skill}</span>
              </div>
              <span style="font-size:12px;color:#64748B;">${s.estimated_weeks}w ▾</span>
            </div>
            <div style="display:none;padding:0 20px 14px;">
              <p style="font-size:13px;color:#475569;margin:0 0 8px;">${s.why_needed}</p>
              ${s.free_resources?.length ? `<div style="font-size:12px;font-weight:600;color:#334155;margin-bottom:4px;">Free resources:</div>
              <ul style="margin:0;padding-left:16px;font-size:12px;color:#2563EB;">${s.free_resources.map(r=>`<li>${r}</li>`).join('')}</ul>` : ''}
            </div>
          </div>`).join('');
    }

    // Roadmap — template id: roadmap-timeline
    const rm = document.getElementById('roadmap-timeline');
    if (rm) {
        const weeks = d.learning_roadmap || [];
        rm.innerHTML = weeks.map((w, i) => `
          <div style="display:flex;gap:16px;margin-bottom:20px;position:relative;z-index:1;">
            <div style="flex-shrink:0;width:30px;height:30px;border-radius:50%;background:#0D9488;color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">W${w.week}</div>
            <div style="padding-top:4px;">
              <div style="font-weight:600;font-size:14px;color:#0F172A;margin-bottom:2px;">${w.focus}</div>
              <div style="font-size:12px;color:#64748B;margin-bottom:4px;">${(w.skills||[]).join(' · ')}</div>
              <div style="font-size:12px;color:#0D9488;font-weight:500;">${w.milestone}</div>
            </div>
          </div>`).join('');
    }

    const total = document.getElementById('roadmap-total');
    if (total) total.textContent = `Total: ${d.total_weeks_to_ready} weeks to become job-ready`;

    // Market insight — template id: market-insight-text (matches ✓)
    _set('market-insight-text', d.job_market_insight || '');

    rs?.scrollIntoView({ behavior: 'smooth' });
}


// ══════════════════════════════════════════════════════════════
// TOOL 3 — AI Mock Interview
// ══════════════════════════════════════════════════════════════

async function startInterview() {
    if (!_currentUsageId) { showToast('Please unlock the tool first.', 'error'); return; }

    // Template uses id="interview-role" (not job-role-input)
    const jobRole = (document.getElementById('interview-role')?.value || '').trim();
    if (!jobRole) { showToast('Please enter a target role.', 'error'); document.getElementById('interview-role')?.focus(); return; }

    // Template uses radio buttons name="num_questions"
    const numQEl = document.querySelector('input[name="num_questions"]:checked');
    const numQ   = parseInt(numQEl?.value || '5');

    _interviewState.jobRole = jobRole;
    _showLoading('Generating your personalised interview questions…');

    const res = await apiPost('/api/ai/interview/', {
        usage_id:      _currentUsageId,
        action:        'start',
        job_role:      jobRole,
        num_questions: numQ,
    });

    _hideLoading();

    if (!res.ok) {
        showToast(res.data?.error || 'Could not start interview. Please try again.', 'error');
        document.getElementById('tool-interface').style.display = 'block';
        return;
    }

    _currentUsageId            = res.data.usage_id || _currentUsageId;
    _interviewState.questions  = res.data.result?.questions || [];
    _interviewState.currentIdx = 0;
    _interviewState.answers    = [];

    document.getElementById('tool-interface').style.display = 'none';
    _showQuestion();
}

function _showQuestion() {
    const q     = _interviewState.questions[_interviewState.currentIdx];
    const total = _interviewState.questions.length;
    if (!q) return;

    // Progress — template id: progress-text
    _set('progress-text', `Question ${_interviewState.currentIdx + 1} of ${total}`);

    // Progress bar — template id: progress-bar-container (fill with dots)
    const pb = document.getElementById('progress-bar-container');
    if (pb) {
        pb.innerHTML = _interviewState.questions.map((_, i) =>
            `<div style="flex:1;height:6px;border-radius:3px;background:${i < _interviewState.currentIdx ? '#7C3AED' : i === _interviewState.currentIdx ? '#7C3AED' : '#E2E8F0'};"></div>`
        ).join('');
    }

    // Question badges — template ids: question-type-badge, question-diff-badge
    _set('question-type-badge', q.type?.charAt(0).toUpperCase() + q.type?.slice(1) || 'Technical');
    _set('question-diff-badge', q.difficulty?.charAt(0).toUpperCase() + q.difficulty?.slice(1) || 'Medium');
    _set('question-number-badge', String(_interviewState.currentIdx + 1));

    // Question text + hint — template ids: question-text, question-hint ✓
    _set('question-text', q.question);
    _set('question-hint', `💡 ${q.hint}`);

    // Clear answer input
    const ansinp = document.getElementById('answer-input');
    if (ansinp) { ansinp.value = ''; ansinp.focus(); }

    // Show in-progress section, hide feedback
    const ip = document.getElementById('interview-in-progress');
    const fb = document.getElementById('answer-feedback');
    if (ip) ip.style.display = 'block';
    if (fb) fb.style.display = 'none';

    _startTimer(q.time_limit_seconds || 180);
}

function _startTimer(seconds) {
    clearInterval(_interviewState.timerInterval);
    _interviewState.timeLeft = seconds;
    _updateTimer();
    _interviewState.timerInterval = setInterval(() => {
        _interviewState.timeLeft--;
        _updateTimer();
        if (_interviewState.timeLeft <= 0) { clearInterval(_interviewState.timerInterval); submitAnswer(); }
    }, 1000);
}

function _updateTimer() {
    const el = document.getElementById('timer-display');
    if (!el) return;
    const m = Math.floor(_interviewState.timeLeft / 60);
    const s = _interviewState.timeLeft % 60;
    el.textContent = `${m}:${s.toString().padStart(2, '0')}`;
    el.style.color  = _interviewState.timeLeft < 30 ? '#EF4444' : '#0F172A';
}

async function submitAnswer() {
    clearInterval(_interviewState.timerInterval);
    const q      = _interviewState.questions[_interviewState.currentIdx];
    const answer = (document.getElementById('answer-input')?.value || '').trim();

    const btn = document.getElementById('submit-answer-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Evaluating…'; }

    const res = await apiPost('/api/ai/interview/', {
        usage_id:    _currentUsageId,
        action:      'submit_answer',
        question_id: q.id,
        answer:      answer || '(No answer provided)',
    });

    if (btn) { btn.disabled = false; btn.textContent = 'Submit Answer'; }

    const fb = res.ok ? res.data.result : { score: 0, feedback: 'Evaluation failed.', strengths: [], improvements: [], ideal_answer_points: [] };

    _interviewState.answers.push({
        question:      q.question,
        question_type: q.type,
        answer:        answer,
        score:         fb.score,
        feedback:      fb.feedback,
    });

    _showAnswerFeedback(fb);
}

function _showAnswerFeedback(fb) {
    const ip = document.getElementById('interview-in-progress');
    const af = document.getElementById('answer-feedback');
    if (ip) ip.style.display = 'none';
    if (!af) return;
    af.style.display = 'block';

    // Score — template id: feedback-score
    const scoreEl = document.getElementById('feedback-score');
    const color   = fb.score >= 8 ? '#10B981' : fb.score >= 6 ? '#2563EB' : fb.score >= 4 ? '#F59E0B' : '#EF4444';
    if (scoreEl) scoreEl.innerHTML = `<span style="font-size:36px;font-weight:800;color:${color};">${fb.score}</span><span style="font-size:16px;color:#94A3B8;">/10</span>`;

    // Feedback — template id: feedback-overall
    _set('feedback-overall', fb.feedback);

    // Strengths — template id: feedback-strengths
    const strEl = document.getElementById('feedback-strengths');
    if (strEl) strEl.innerHTML = (fb.strengths || []).map(s => `<li>${s}</li>`).join('');

    // Improvements — template id: feedback-improve
    const impEl = document.getElementById('feedback-improve');
    if (impEl) impEl.innerHTML = (fb.improvements || []).map(i => `<li>${i}</li>`).join('');

    // Next button
    const isLast = _interviewState.currentIdx >= _interviewState.questions.length - 1;
    const nextBtn = document.getElementById('next-question-btn');
    if (nextBtn) {
        nextBtn.textContent = isLast ? 'Finish & Get Report' : 'Next Question →';
        nextBtn.onclick     = isLast ? _finishInterview : () => { _interviewState.currentIdx++; _showQuestion(); };
    }

    af.scrollIntoView({ behavior: 'smooth' });
}

async function _finishInterview() {
    _showLoading('Generating your interview report…');
    const af = document.getElementById('answer-feedback');
    if (af) af.style.display = 'none';

    const res = await apiPost('/api/ai/interview/', {
        usage_id: _currentUsageId,
        action:   'finish',
    });

    _hideLoading();

    if (!res.ok) { showToast('Report generation failed. Please try again.', 'error'); return; }
    _renderInterviewReport(res.data.result);
}

function _renderInterviewReport(d) {
    const rpt = document.getElementById('interview-report');
    if (!rpt) return;
    rpt.style.display = 'block';

    // Score ring — template id: report-score-ring, report-score-text
    const ring = document.getElementById('report-score-ring');
    if (ring) ring.setAttribute('stroke-dasharray', `${d.overall_score}, 100`);
    _set('report-score-text', String(d.overall_score));

    // Grade + Hire — template ids: report-grade, report-hire
    const grade = document.getElementById('report-grade');
    const hire  = document.getElementById('report-hire');
    if (grade) { grade.textContent = `Grade: ${d.grade}`; grade.style.color = _gradeColor(d.grade); grade.style.background = _gradeColor(d.grade) + '22'; }
    if (hire)  {
        hire.textContent = d.hiring_recommendation;
        const hireColors = { 'Strong Hire': '#166534', 'Hire': '#1D4ED8', 'Maybe': '#92400E', 'No Hire': '#991B1B' };
        hire.style.color      = hireColors[d.hiring_recommendation] || '#166534';
        hire.style.background = hireColors[d.hiring_recommendation]?.replace(/[^,]+\)/, '0.1)') || '#DCFCE7';
    }

    // Performance by type — template ids: report-tech-score, report-beh-score, report-hr-score
    const pt = d.performance_by_type || {};
    _set('report-tech-score', `${pt.technical || 0}/100`);
    _set('report-beh-score',  `${pt.behavioral || 0}/100`);
    _set('report-hr-score',   `${pt.hr || 0}/100`);

    // Strengths — template id: report-strengths ✓
    const strEl = document.getElementById('report-strengths');
    if (strEl) strEl.innerHTML = (d.top_strengths || []).map(s => `<li>${s}</li>`).join('');

    // Improvements — template id: report-improve
    const impEl = document.getElementById('report-improve');
    if (impEl) impEl.innerHTML = (d.areas_to_improve || []).map(i => `<li>${i}</li>`).join('');

    // QA list summary — template id: report-qa-list
    const qa = document.getElementById('report-qa-list');
    if (qa) {
        qa.innerHTML = `<h3 style="font-size:14px;font-weight:700;margin:20px 0 12px;">Detailed Feedback</h3>
          <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 12px;">${d.detailed_feedback || ''}</p>
          ${d.next_steps?.length ? `<h4 style="font-size:13px;font-weight:700;margin:12px 0 8px;">Next Steps:</h4>
          <ol style="margin:0;padding-left:18px;font-size:13px;color:#334155;line-height:1.8;">${d.next_steps.map(s=>`<li>${s}</li>`).join('')}</ol>` : ''}`;
    }

    rpt.scrollIntoView({ behavior: 'smooth' });
}


// ══════════════════════════════════════════════════════════════
// TOOL 4 — Resume Builder
// ══════════════════════════════════════════════════════════════

async function runResumeBuilder() {
    if (!_currentUsageId) { showToast('Please unlock the tool first.', 'error'); return; }

    // Template uses id="resume-target-role" (not target-role-input)
    const targetRole = (document.getElementById('resume-target-role')?.value || '').trim();
    _showLoading('Building your professional resume…');

    const res = await apiPost('/api/ai/resume-build/', {
        usage_id:    _currentUsageId,
        target_role: targetRole || null,
    });

    _hideLoading();

    if (!res.ok) {
        showToast(res.data?.error || 'Resume build failed. Please try again.', 'error');
        document.getElementById('tool-interface').style.display = 'block';
        return;
    }

    _renderBuiltResume(res.data.result);
}

function _renderBuiltResume(d) {
    const rs = document.getElementById('result-section');
    if (rs) rs.style.display = 'block';

    const preview = document.getElementById('resume-preview-card');
    if (preview) {
        const s = d.resume_sections;
        const h = s.header || {};

        preview.innerHTML = `
        <div style="font-family:'Times New Roman',serif;max-width:700px;margin:0 auto;padding:24px;font-size:11pt;line-height:1.55;color:#0f172a;">
          <div style="text-align:center;border-bottom:2px solid #0f172a;padding-bottom:10px;margin-bottom:14px;">
            <h1 style="font-size:20pt;font-weight:700;margin:0 0 4px;">${h.name || ''}</h1>
            <div style="font-size:10pt;color:#334155;">${[h.phone,h.email,h.location,h.github].filter(Boolean).join(' | ')}</div>
          </div>
          ${s.summary ? `<div style="margin-bottom:12px;"><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Professional Summary</h2><p style="margin:0;font-size:10pt;">${s.summary}</p></div>` : ''}
          ${(s.education||[]).length ? `<div style="margin-bottom:12px;"><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Education</h2>${(s.education||[]).map(e=>`<div style="display:flex;justify-content:space-between;"><div><strong>${e.degree}</strong>, ${e.institution} — ${e.grade}</div><div style="font-size:10pt;">${e.year}</div></div>`).join('')}</div>` : ''}
          ${s.skills ? `<div style="margin-bottom:12px;"><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Technical Skills</h2>
            ${s.skills.technical?.length ? `<div style="margin-bottom:3px;"><strong>Languages/Frameworks:</strong> ${s.skills.technical.join(', ')}</div>` : ''}
            ${s.skills.tools?.length ? `<div style="margin-bottom:3px;"><strong>Tools/Platforms:</strong> ${s.skills.tools.join(', ')}</div>` : ''}
            ${s.skills.soft?.length ? `<div><strong>Soft Skills:</strong> ${s.skills.soft.join(', ')}</div>` : ''}
          </div>` : ''}
          ${(s.experience||[]).filter(e=>e.company).length ? `<div style="margin-bottom:12px;"><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Experience</h2>${(s.experience||[]).map(e=>`<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;"><strong>${e.title}</strong><span style="font-size:10pt;">${e.duration}</span></div><div style="color:#475569;font-size:10pt;margin-bottom:3px;">${e.company}</div><ul style="margin:0;padding-left:18px;font-size:10pt;">${(e.bullets||[]).map(b=>`<li>${b}</li>`).join('')}</ul></div>`).join('')}</div>` : ''}
          ${(s.projects||[]).length ? `<div style="margin-bottom:12px;"><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Projects</h2>${(s.projects||[]).map(p=>`<div style="margin-bottom:8px;"><div><strong>${p.name}</strong> — <em style="font-size:10pt;">${(p.tech_stack||[]).join(', ')}</em></div><ul style="margin:2px 0 0;padding-left:18px;font-size:10pt;">${(p.bullets||[]).map(b=>`<li>${b}</li>`).join('')}</ul></div>`).join('')}</div>` : ''}
          ${(s.certifications||[]).length ? `<div style="margin-bottom:12px;"><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Certifications</h2>${(s.certifications||[]).map(c=>`<div style="font-size:10pt;">${c.name} — ${c.issuer} (${c.year})</div>`).join('')}</div>` : ''}
          ${(s.achievements||[]).length ? `<div><h2 style="font-size:11pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #94a3b8;margin:0 0 6px;">Achievements</h2><ul style="margin:0;padding-left:18px;font-size:10pt;">${(s.achievements||[]).map(a=>`<li>${a}</li>`).join('')}</ul></div>` : ''}
        </div>`;
    }

    // ATS tips — template id: resume-ats-tips
    const tips = document.getElementById('resume-ats-tips');
    if (tips) tips.innerHTML = (d.ats_optimization_tips || []).map(t => `<li style="padding:3px 0;">${t}</li>`).join('');

    rs?.scrollIntoView({ behavior: 'smooth' });
}

function copyResumeText() {
    const preview = document.getElementById('resume-preview-card');
    if (!preview) return;
    navigator.clipboard?.writeText(preview.innerText).then(() => showToast('Resume text copied!', 'success'));
}


// ══════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════

function _gradeColor(grade) {
    return { A: '#16A34A', B: '#2563EB', C: '#D97706', D: '#EF4444', F: '#7F1D1D' }[grade] || '#475569';
}
