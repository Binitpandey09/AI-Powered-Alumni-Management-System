// ════════════════════════════════════════════
//  RATING MODAL SYSTEM
// ════════════════════════════════════════════

let _ratingBookingId = null;
let _ratingType = null; // 'student_to_host' or 'host_to_student'
let _ratingCallback = null; // called after successful submission

const STAR_LABELS = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];

function openRatingModal(bookingId, ratingType, sessionTitle, hostName, callback) {
    _ratingBookingId = bookingId;
    _ratingType = ratingType;
    _ratingCallback = callback || null;

    // Set title and session info
    document.getElementById('rating-modal-title').textContent =
        ratingType === 'student_to_host' ? 'Rate Your Session' : 'Rate This Student';
    document.getElementById('rating-modal-subtitle').textContent =
        ratingType === 'student_to_host'
            ? 'Your review helps other students find great mentors'
            : 'Your feedback helps students improve';
    document.getElementById('rating-session-name').textContent = sessionTitle || 'Session';
    document.getElementById('rating-session-host').textContent =
        ratingType === 'student_to_host' ? `Hosted by ${hostName}` : `Student: ${hostName}`;

    // Show/hide correct sections
    document.getElementById('student-ratings-section').style.display =
        ratingType === 'student_to_host' ? 'block' : 'none';
    document.getElementById('host-ratings-section').style.display =
        ratingType === 'host_to_student' ? 'block' : 'none';

    // Reset all inputs
    resetRatingModal();

    // Render stars
    renderMainStars();
    document.querySelectorAll('.mini-stars').forEach(container => {
        renderMiniStars(container);
    });

    // Show modal
    const modal = document.getElementById('rating-modal');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeRatingModal() {
    document.getElementById('rating-modal').style.display = 'none';
    document.body.style.overflow = '';
}

function resetRatingModal() {
    document.getElementById('overall-rating-value').value = '';
    document.getElementById('overall-star-label').textContent = '';
    document.getElementById('communication-rating-value').value = '';
    document.getElementById('value-rating-value').value = '';
    document.getElementById('professionalism-rating-value').value = '';
    document.getElementById('preparation-rating-value').value = '';
    document.getElementById('engagement-rating-value').value = '';
    document.getElementById('punctuality-rating-value').value = '';
    document.getElementById('would-recommend-value').value = '';
    document.getElementById('review-text-input').value = '';
    document.getElementById('review-char-count').textContent = '0/300';
    if (document.getElementById('feedback-text-input')) {
        document.getElementById('feedback-text-input').value = '';
    }
    document.getElementById('rating-error').style.display = 'none';

    // Reset recommend buttons
    ['recommend-yes', 'recommend-no'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.style.background = 'white';
            btn.style.borderColor = '#E2E8F0';
            btn.style.color = '#374151';
            btn.style.fontWeight = '400';
        }
    });

    // Reset submit button
    const submitBtn = document.getElementById('submit-rating-btn');
    if (submitBtn) {
        submitBtn.textContent = 'Submit Rating ★';
        submitBtn.disabled = false;
        submitBtn.style.background = '#7C3AED';
    }
}

function renderMainStars() {
    const container = document.getElementById('overall-stars');
    if (!container) return;
    container.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement('span');
        star.dataset.value = i;
        star.style.cssText = 'font-size:36px; cursor:pointer; color:#E2E8F0; transition:color .1s, transform .1s; user-select:none;';
        star.textContent = '★';
        star.addEventListener('mouseenter', () => highlightMainStars(i));
        star.addEventListener('mouseleave', () => highlightMainStars(parseInt(document.getElementById('overall-rating-value').value) || 0));
        star.addEventListener('click', () => {
            document.getElementById('overall-rating-value').value = i;
            document.getElementById('overall-star-label').textContent = STAR_LABELS[i];
            highlightMainStars(i);
        });
        container.appendChild(star);
    }
}

function highlightMainStars(count) {
    document.querySelectorAll('#overall-stars span').forEach((star, idx) => {
        const active = idx < count;
        star.style.color = active ? '#F59E0B' : '#E2E8F0';
        star.style.transform = active ? 'scale(1.1)' : 'scale(1)';
    });
}

function renderMiniStars(container) {
    const targetId = container.dataset.target;
    container.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement('span');
        star.dataset.value = i;
        star.style.cssText = 'font-size:22px; cursor:pointer; color:#E2E8F0; transition:color .1s; user-select:none;';
        star.textContent = '★';
        star.addEventListener('mouseenter', () => highlightMiniStars(container, i));
        star.addEventListener('mouseleave', () => {
            const current = parseInt(document.getElementById(targetId)?.value) || 0;
            highlightMiniStars(container, current);
        });
        star.addEventListener('click', () => {
            if (document.getElementById(targetId)) {
                document.getElementById(targetId).value = i;
            }
            highlightMiniStars(container, i);
        });
        container.appendChild(star);
    }
}

function highlightMiniStars(container, count) {
    container.querySelectorAll('span').forEach((star, idx) => {
        star.style.color = idx < count ? '#F59E0B' : '#E2E8F0';
    });
}

function setRecommend(val) {
    document.getElementById('would-recommend-value').value = val ? 'true' : 'false';
    const yesBtn = document.getElementById('recommend-yes');
    const noBtn = document.getElementById('recommend-no');
    if (val) {
        yesBtn.style.cssText += 'background:#F0FDF4;border-color:#86EFAC;color:#166534;font-weight:500;';
        noBtn.style.cssText += 'background:white;border-color:#E2E8F0;color:#374151;font-weight:400;';
    } else {
        noBtn.style.cssText += 'background:#FEF2F2;border-color:#FECACA;color:#991B1B;font-weight:500;';
        yesBtn.style.cssText += 'background:white;border-color:#E2E8F0;color:#374151;font-weight:400;';
    }
}

async function submitRating() {
    const overall = document.getElementById('overall-rating-value').value;
    if (!overall) {
        const errEl = document.getElementById('rating-error');
        errEl.textContent = 'Please select an overall star rating before submitting.';
        errEl.style.display = 'block';
        return;
    }

    const btn = document.getElementById('submit-rating-btn');
    btn.textContent = 'Submitting...';
    btn.disabled = true;
    btn.style.background = '#6D28D9';

    const payload = {
        booking_id: _ratingBookingId,
        overall_rating: parseInt(overall),
    };

    if (_ratingType === 'student_to_host') {
        const comm = document.getElementById('communication-rating-value').value;
        const val = document.getElementById('value-rating-value').value;
        const prof = document.getElementById('professionalism-rating-value').value;
        const rec = document.getElementById('would-recommend-value').value;
        if (comm) payload.communication_rating = parseInt(comm);
        if (val) payload.value_rating = parseInt(val);
        if (prof) payload.professionalism_rating = parseInt(prof);
        if (rec !== '') payload.would_recommend = rec === 'true';
        payload.review_text = document.getElementById('review-text-input').value.trim();
    } else {
        const prep = document.getElementById('preparation-rating-value').value;
        const eng = document.getElementById('engagement-rating-value').value;
        const punc = document.getElementById('punctuality-rating-value').value;
        if (prep) payload.preparation_rating = parseInt(prep);
        if (eng) payload.engagement_rating = parseInt(eng);
        if (punc) payload.punctuality_rating = parseInt(punc);
        payload.feedback_text = document.getElementById('feedback-text-input')?.value.trim() || '';
    }

    const result = await apiPost('/api/ratings/session/', payload);

    if (result.ok) {
        closeRatingModal();
        showToast('Rating submitted! Thank you for your feedback. ★', 'success');
        if (_ratingCallback) _ratingCallback(result.data);
    } else {
        const errEl = document.getElementById('rating-error');
        errEl.textContent = result.data?.error || 'Submission failed. Please try again.';
        errEl.style.display = 'block';
        btn.textContent = 'Submit Rating ★';
        btn.disabled = false;
        btn.style.background = '#7C3AED';
    }
}

// Close modal when clicking backdrop
document.getElementById('rating-modal')?.addEventListener('click', function(e) {
    if (e.target === this) closeRatingModal();
});

let _refApplicationId = null;
let _refRatingCallback = null;

function openReferralRatingModal(applicationId, jobTitle, alumniName, callback) {
    _refApplicationId = applicationId;
    _refRatingCallback = callback || null;
    document.getElementById('ref-rating-job').textContent = jobTitle;
    document.getElementById('ref-rating-alumni').textContent = `Posted by ${alumniName}`;
    document.getElementById('ref-overall-value').value = '';
    document.getElementById('ref-process-value').value = '';
    document.getElementById('ref-comm-value').value = '';
    document.getElementById('ref-review-text').value = '';
    document.getElementById('ref-rating-error').style.display = 'none';

    // Render stars
    const mainStars = document.getElementById('ref-overall-stars');
    mainStars.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
        const s = document.createElement('span');
        s.style.cssText = 'font-size:32px;cursor:pointer;color:#E2E8F0;transition:color .1s;user-select:none;';
        s.textContent = '★';
        s.dataset.val = i;
        s.addEventListener('click', () => {
            document.getElementById('ref-overall-value').value = i;
            mainStars.querySelectorAll('span').forEach((el, idx) => {
                el.style.color = idx < i ? '#F59E0B' : '#E2E8F0';
            });
        });
        mainStars.appendChild(s);
    }
    document.querySelectorAll('.ref-mini-stars').forEach(c => renderMiniStars(c));

    document.getElementById('referral-rating-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeReferralRatingModal() {
    document.getElementById('referral-rating-modal').style.display = 'none';
    document.body.style.overflow = '';
}

async function submitReferralRating() {
    const overall = document.getElementById('ref-overall-value').value;
    if (!overall) {
        document.getElementById('ref-rating-error').textContent = 'Please select an overall star rating.';
        document.getElementById('ref-rating-error').style.display = 'block';
        return;
    }
    const btn = document.getElementById('submit-ref-rating-btn');
    btn.textContent = 'Submitting...'; btn.disabled = true;
    const result = await apiPost('/api/ratings/referral/', {
        application_id: _refApplicationId,
        overall_rating: parseInt(overall),
        process_rating: parseInt(document.getElementById('ref-process-value').value) || undefined,
        communication_rating: parseInt(document.getElementById('ref-comm-value').value) || undefined,
        review_text: document.getElementById('ref-review-text').value.trim(),
    });
    btn.textContent = 'Submit Rating ★'; btn.disabled = false;
    if (result.ok) {
        closeReferralRatingModal();
        showToast('Referral rated successfully! ★', 'success');
        if (_refRatingCallback) _refRatingCallback(result.data);
    } else {
        document.getElementById('ref-rating-error').textContent = result.data?.error || 'Submission failed.';
        document.getElementById('ref-rating-error').style.display = 'block';
    }
}
