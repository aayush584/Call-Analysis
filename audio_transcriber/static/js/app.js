// ============== STATE ==============
let currentJobId = null;
let pollingInterval = null;
let resultData = null;
let allExpanded = false;
let questionsData = { questions: [], categories: {} };
let confirmCallback = null;

// ============== DOM ELEMENTS ==============
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const filePreview = document.getElementById('filePreview');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const audioPlayer = document.getElementById('audioPlayer');
const removeFileBtn = document.getElementById('removeFile');
const processBtn = document.getElementById('processBtn');
const uploadSection = document.getElementById('uploadSection');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');
const progressMessage = document.getElementById('progressMessage');
const transcriptAudioContainer = document.getElementById('transcriptAudioContainer');
const transcriptAudioPlayer = document.getElementById('transcriptAudioPlayer');
const transcriptAudioFilename = document.getElementById('transcriptAudioFilename');
const transcriptAudioDownloadBtn = document.getElementById('transcriptAudioDownloadBtn');

// ============== INITIALIZATION ==============
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadQuestions();
});

function resolveAudioUrl(result = resultData) {
    if (!result) return currentJobId ? `/audio/${currentJobId}` : null;
    if (result.audio_url) return result.audio_url;
    if (result.job_id) return `/audio/${result.job_id}`;
    if (currentJobId) return `/audio/${currentJobId}`;
    return null;
}

function setupEventListeners() {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    dropZone.addEventListener('click', () => fileInput.click());
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    removeFileBtn.addEventListener('click', resetUpload);
    processBtn.addEventListener('click', startProcessing);
    if (transcriptAudioDownloadBtn) {
        transcriptAudioDownloadBtn.addEventListener('click', downloadOriginalAudio);
    }
}

// ============== QUESTIONS MANAGEMENT ==============
async function loadQuestions() {
    try {
        const response = await fetch('/api/questions');
        questionsData = await response.json();
        updateEnabledCount();
        renderQuestionsList();
        renderCategoriesList();
        populateCategoryDropdowns();
    } catch (error) {
        console.error('Error loading questions:', error);
    }
}

function updateEnabledCount() {
    const enabledCount = questionsData.questions.filter(q => q.enabled !== false).length;
    document.getElementById('enabledCount').textContent = enabledCount;
    document.getElementById('questionCount').textContent = `${questionsData.questions.length} questions (${enabledCount} enabled)`;
}

function openQuestionsModal() {
    document.getElementById('questionsModal').classList.remove('hidden');
    loadQuestions();
}

function closeQuestionsModal() {
    document.getElementById('questionsModal').classList.add('hidden');
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

function filterQuestions() {
    const search = document.getElementById('questionSearch').value.toLowerCase();
    const category = document.getElementById('categoryFilter').value;
    
    document.querySelectorAll('.question-item').forEach(item => {
        const text = item.dataset.question.toLowerCase();
        const cat = item.dataset.category;
        
        const matchesSearch = text.includes(search);
        const matchesCategory = !category || cat === category;
        
        item.style.display = matchesSearch && matchesCategory ? 'flex' : 'none';
    });
}

function populateCategoryDropdowns() {
    const categories = Object.keys(questionsData.categories);
    
    // Category filter
    const filterSelect = document.getElementById('categoryFilter');
    filterSelect.innerHTML = '<option value="">All Categories</option>' + 
        categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
    
    // Question form category
    const formSelect = document.getElementById('questionCategory');
    formSelect.innerHTML = categories.map(cat => `<option value="${cat}">${cat}</option>`).join('') +
        '<option value="__new__">+ New Category</option>';
}

function renderQuestionsList() {
    const list = document.getElementById('questionsList');
    
    if (questionsData.questions.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-clipboard-list"></i>
                <p>No questions configured. Add your first question!</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = questionsData.questions.map(q => {
        const catInfo = questionsData.categories[q.category] || {};
        const isEnabled = q.enabled !== false;
        
        return `
            <div class="question-item ${isEnabled ? '' : 'disabled'}" 
                 data-id="${q.id}" 
                 data-question="${q.question}" 
                 data-category="${q.category}">
                <label class="question-toggle">
                    <input type="checkbox" ${isEnabled ? 'checked' : ''} 
                           onchange="toggleQuestion('${q.id}')">
                    <span class="toggle-slider"></span>
                </label>
                <div class="question-info">
                    <div class="question-title">
                        ${q.question}
                        <span class="badge" style="background: ${catInfo.color || '#6366f1'}20; color: ${catInfo.color || '#6366f1'}">
                            ${q.category}
                        </span>
                    </div>
                    <div class="question-meta">
                        <span><i class="fas fa-fingerprint"></i> ${q.id}</span>
                        <span><i class="fas fa-weight-hanging"></i> Weight: ${q.weight || 3}</span>
                    </div>
                </div>
                <div class="question-actions">
                    <button class="btn btn-icon" onclick="editQuestion('${q.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-icon" onclick="deleteQuestion('${q.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderCategoriesList() {
    const list = document.getElementById('categoriesList');
    const categories = Object.entries(questionsData.categories);
    
    list.innerHTML = categories.map(([name, info]) => {
        const count = questionsData.questions.filter(q => q.category === name).length;
        return `
            <div class="category-item">
                <div class="category-icon" style="background: ${info.color || '#6366f1'}20; color: ${info.color || '#6366f1'}">
                    <i class="fas ${info.icon || 'fa-folder'}"></i>
                </div>
                <div class="category-info">
                    <div class="category-name">${name}</div>
                    <div class="category-desc">${info.description || ''}</div>
                    <div class="category-count">${count} questions</div>
                </div>
                <div class="question-actions">
                    <button class="btn btn-icon" onclick="deleteCategory('${name}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// ============== QUESTION CRUD ==============
function openAddQuestionForm() {
    document.getElementById('questionForm').classList.remove('hidden');
    document.getElementById('formTitle').textContent = 'Add New Question';
    document.getElementById('editQuestionId').value = '';
    document.getElementById('questionId').value = '';
    document.getElementById('questionId').disabled = false;
    document.getElementById('questionText').value = '';
    document.getElementById('questionCategory').value = Object.keys(questionsData.categories)[0] || '';
    document.getElementById('questionWeight').value = 3;
    document.getElementById('questionDescription').value = '';
}

function editQuestion(id) {
    const q = questionsData.questions.find(q => q.id === id);
    if (!q) return;
    
    document.getElementById('questionForm').classList.remove('hidden');
    document.getElementById('formTitle').textContent = 'Edit Question';
    document.getElementById('editQuestionId').value = id;
    document.getElementById('questionId').value = q.id;
    document.getElementById('questionId').disabled = true;
    document.getElementById('questionText').value = q.question;
    document.getElementById('questionCategory').value = q.category;
    document.getElementById('questionWeight').value = q.weight || 3;
    document.getElementById('questionDescription').value = q.description || '';
}

function cancelQuestionForm() {
    document.getElementById('questionForm').classList.add('hidden');
}

async function saveQuestion() {
    const editId = document.getElementById('editQuestionId').value;
    const id = document.getElementById('questionId').value.trim();
    const question = document.getElementById('questionText').value.trim();
    const category = document.getElementById('questionCategory').value;
    const weight = parseInt(document.getElementById('questionWeight').value) || 3;
    const description = document.getElementById('questionDescription').value.trim();
    
    if (!id || !question) {
        showToast('Please fill in required fields', 'error');
        return;
    }
    
    const data = { id, question, category, weight, description, enabled: true };
    
    try {
        let response;
        if (editId) {
            // Update existing
            response = await fetch(`/api/questions/${editId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, category, weight, description })
            });
        } else {
            // Add new
            response = await fetch('/api/questions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save');
        }
        
        showToast(editId ? 'Question updated!' : 'Question added!', 'success');
        cancelQuestionForm();
        loadQuestions();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function toggleQuestion(id) {
    try {
        const response = await fetch(`/api/questions/${id}/toggle`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to toggle');
        loadQuestions();
    } catch (error) {
        showToast('Failed to toggle question', 'error');
    }
}

function deleteQuestion(id) {
    showConfirm(
        'Delete Question',
        'Are you sure you want to delete this question? This action cannot be undone.',
        async () => {
            try {
                const response = await fetch(`/api/questions/${id}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete');
                showToast('Question deleted!', 'success');
                loadQuestions();
            } catch (error) {
                showToast('Failed to delete question', 'error');
            }
        }
    );
}

// ============== CATEGORY CRUD ==============
function openAddCategoryForm() {
    document.getElementById('categoryForm').classList.remove('hidden');
    document.getElementById('categoryName').value = '';
    document.getElementById('categoryDescription').value = '';
    document.getElementById('categoryIcon').value = 'fa-question';
    document.getElementById('categoryColor').value = '#6366f1';
}

function cancelCategoryForm() {
    document.getElementById('categoryForm').classList.add('hidden');
}

async function saveCategory() {
    const name = document.getElementById('categoryName').value.trim();
    const description = document.getElementById('categoryDescription').value.trim();
    const icon = document.getElementById('categoryIcon').value.trim();
    const color = document.getElementById('categoryColor').value;
    
    if (!name) {
        showToast('Please enter a category name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, icon, color })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save');
        }
        
        showToast('Category added!', 'success');
        cancelCategoryForm();
        loadQuestions();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function deleteCategory(name) {
    showConfirm(
        'Delete Category',
        `Are you sure you want to delete "${name}"? Questions in this category will be moved to "General".`,
        async () => {
            try {
                const response = await fetch(`/api/categories/${encodeURIComponent(name)}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete');
                showToast('Category deleted!', 'success');
                loadQuestions();
            } catch (error) {
                showToast('Failed to delete category', 'error');
            }
        }
    );
}

// ============== IMPORT/EXPORT ==============
function exportQuestions() {
    const json = JSON.stringify(questionsData, null, 2);
    downloadFile(json, 'questions_config.json', 'application/json');
    showToast('Questions exported!', 'success');
}

async function importQuestions(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        const text = await file.text();
        const data = JSON.parse(text);
        
        if (!data.questions || !Array.isArray(data.questions)) {
            throw new Error('Invalid format: missing questions array');
        }
        
        showConfirm(
            'Import Questions',
            `This will replace all existing questions with ${data.questions.length} imported questions. Continue?`,
            async () => {
                // Save imported data
                for (const q of data.questions) {
                    if (!q.id || !q.question) continue;
                    await fetch('/api/questions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ...q, enabled: q.enabled !== false })
                    }).catch(() => {});
                }
                
                showToast('Questions imported!', 'success');
                loadQuestions();
            }
        );
    } catch (error) {
        showToast('Invalid JSON file', 'error');
    }
    
    event.target.value = '';
}

function resetToDefaults() {
    showConfirm(
        'Reset to Defaults',
        'This will delete all custom questions and restore the default set. Continue?',
        async () => {
            try {
                const response = await fetch('/api/questions/reset', { method: 'POST' });
                if (!response.ok) throw new Error('Failed to reset');
                showToast('Questions reset to defaults!', 'success');
                loadQuestions();
            } catch (error) {
                showToast('Failed to reset questions', 'error');
            }
        }
    );
}

// ============== CONFIRM DIALOG ==============
function showConfirm(title, message, callback) {
    confirmCallback = callback;
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmModal').classList.remove('hidden');
}

function closeConfirmModal() {
    document.getElementById('confirmModal').classList.add('hidden');
    confirmCallback = null;
}

function confirmAction() {
    if (confirmCallback) {
        confirmCallback();
    }
    closeConfirmModal();
}

// ============== FILE HANDLING ==============
function handleFile(file) {
    const allowedExtensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(ext)) {
        showToast('Invalid file type. Please upload an audio file.', 'error');
        return;
    }

    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    
    const url = URL.createObjectURL(file);
    audioPlayer.src = url;
    
    dropZone.classList.add('hidden');
    filePreview.classList.remove('hidden');
    
    fileInput.file = file;
}

function resetUpload() {
    dropZone.classList.remove('hidden');
    filePreview.classList.add('hidden');
    fileInput.value = '';
    fileInput.file = null;
    audioPlayer.src = '';
}

// ============== PROCESSING ==============
async function startProcessing() {
    const file = fileInput.file;
    if (!file) {
        showToast('Please select a file first', 'error');
        return;
    }

    uploadSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    
    updateProgress(5, 'Uploading file...');
    setStepActive(1);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const uploadData = await uploadResponse.json();
        currentJobId = uploadData.job_id;

        setStepCompleted(1);
        updateProgress(10, 'Starting processing...');

        const processResponse = await fetch(`/process/${currentJobId}`, {
            method: 'POST'
        });

        if (!processResponse.ok) {
            throw new Error('Failed to start processing');
        }

        startPolling();

    } catch (error) {
        console.error('Error:', error);
        showToast('Error: ' + error.message, 'error');
        resetApp();
    }
}

function startPolling() {
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${currentJobId}`);
            const data = await response.json();

            updateProgress(data.progress, data.message);
            updateSteps(data.progress);

            if (data.status === 'completed') {
                stopPolling();
                resultData = data.result || {};
                resultData.job_id = resultData.job_id || data.job_id || currentJobId;
                resultData.audio_url = resolveAudioUrl(resultData);
                showResults(resultData);
            } else if (data.status === 'failed') {
                stopPolling();
                showToast('Processing failed: ' + data.message, 'error');
                resetApp();
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function updateProgress(percent, message) {
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;
    progressMessage.textContent = message;
}

function updateSteps(progress) {
    if (progress >= 10) setStepCompleted(1);
    if (progress >= 15) setStepActive(2);
    if (progress >= 30) { setStepCompleted(2); setStepActive(3); }
    if (progress >= 65) { setStepCompleted(3); setStepActive(4); }
    if (progress >= 75) { setStepCompleted(4); setStepActive(5); }
    if (progress >= 100) setStepCompleted(5);
}

function setStepActive(step) {
    document.getElementById(`step${step}`).classList.add('active');
}

function setStepCompleted(step) {
    const stepEl = document.getElementById(`step${step}`);
    stepEl.classList.remove('active');
    stepEl.classList.add('completed');
}

function resetSteps() {
    for (let i = 1; i <= 5; i++) {
        const step = document.getElementById(`step${i}`);
        step.classList.remove('active', 'completed');
    }
}

// ============== RESULTS DISPLAY ==============
function showResults(result) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    const audioUrl = resolveAudioUrl(result);
    updateTranscriptAudio(audioUrl, result.filename);

    if (result.evaluation) {
        displayScoreOverview(result.evaluation.scores);
        displayEvaluationCategories(result.evaluation.by_category);
    }

    document.getElementById('summaryContent').textContent = result.summary;

    const speakerStats = document.getElementById('speakerStats');
    speakerStats.innerHTML = result.speaker_stats.map((stat, index) => `
        <div class="speaker-stat-item">
            <div class="speaker-name">
                <div class="speaker-avatar speaker-${index % 3}">${stat.speaker.replace('SPEAKER_', 'S')}</div>
                <span>${stat.speaker}</span>
            </div>
            <div class="speaker-stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${stat.segments}</div>
                    <div class="stat-label">Segments</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${formatDuration(stat.duration)}</div>
                    <div class="stat-label">Duration</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stat.words}</div>
                    <div class="stat-label">Words</div>
                </div>
            </div>
        </div>
    `).join('');

    const transcriptContent = document.getElementById('transcriptContent');
    transcriptContent.innerHTML = result.transcript.map((segment) => {
        const speakerIndex = parseInt(segment.speaker.replace('SPEAKER_', '')) || 0;
        return `
            <div class="transcript-segment">
                <span class="segment-time">${formatTime(segment.start)} - ${formatTime(segment.end)}</span>
                <span class="segment-speaker speaker-${speakerIndex % 3}">${segment.speaker}</span>
                <span class="segment-text">${segment.text || '<em>No speech detected</em>'}</span>
            </div>
        `;
    }).join('');

    showToast('Processing complete!', 'success');
}

function updateTranscriptAudio(audioUrl, filename) {
    if (!transcriptAudioContainer) return;

    if (audioUrl && transcriptAudioPlayer) {
        transcriptAudioContainer.classList.remove('hidden');
        transcriptAudioPlayer.src = `${audioUrl}?v=${Date.now()}`;
        transcriptAudioPlayer.load();
        if (transcriptAudioFilename) {
            transcriptAudioFilename.textContent = filename || 'Processed audio';
        }
        if (transcriptAudioDownloadBtn) {
            transcriptAudioDownloadBtn.disabled = false;
        }
    } else {
        transcriptAudioContainer.classList.add('hidden');
        if (transcriptAudioPlayer) {
            transcriptAudioPlayer.pause();
            transcriptAudioPlayer.removeAttribute('src');
        }
        if (transcriptAudioFilename) {
            transcriptAudioFilename.textContent = '';
        }
        if (transcriptAudioDownloadBtn) {
            transcriptAudioDownloadBtn.disabled = true;
        }
    }
}

function displayScoreOverview(scores) {
    const scoreColor = getScoreColor(scores.overall_score);
    
    document.getElementById('scoreOverview').innerHTML = `
        <div class="score-circle" style="--score-color: ${scoreColor}; --score-percent: ${scores.overall_score}%">
            <span class="score-value">${scores.overall_score}%</span>
            <span class="score-grade" style="color: ${scoreColor}">Grade ${scores.grade}</span>
        </div>
        <div class="score-details">
            <div class="score-stat">
                <span class="score-stat-label">Questions Evaluated</span>
                <span class="score-stat-value">${scores.applicable_questions} / ${resultData.evaluation.total_questions}</span>
            </div>
            <div class="score-stat">
                <span class="score-stat-label">Passed</span>
                <span class="score-stat-value">
                    <span class="status-badge yes">${scores.status_counts.YES} YES</span>
                </span>
            </div>
            <div class="score-stat">
                <span class="score-stat-label">Partial</span>
                <span class="score-stat-value">
                    <span class="status-badge partial">${scores.status_counts.PARTIAL} PARTIAL</span>
                </span>
            </div>
            <div class="score-stat">
                <span class="score-stat-label">Failed</span>
                <span class="score-stat-value">
                    <span class="status-badge no">${scores.status_counts.NO} NO</span>
                </span>
            </div>
            <div class="score-stat">
                <span class="score-stat-label">Average Confidence</span>
                <span class="score-stat-value">${scores.average_confidence}%</span>
            </div>
        </div>
    `;
}

function displayEvaluationCategories(categories) {
    const container = document.getElementById('evaluationCategories');
    
    container.innerHTML = Object.entries(categories).map(([catName, catData]) => {
        const scoreColor = catData.score !== null ? getScoreColor(catData.score) : '#64748b';
        const iconColor = catData.info.color || '#6366f1';
        
        return `
            <div class="eval-category" id="cat-${catName.replace(/\s+/g, '-')}">
                <div class="eval-category-header" onclick="toggleCategory('${catName.replace(/\s+/g, '-')}')">
                    <div class="eval-category-info">
                        <div class="eval-category-icon" style="background: ${iconColor}20; color: ${iconColor}">
                            <i class="fas ${catData.info.icon || 'fa-question'}"></i>
                        </div>
                        <div>
                            <div class="eval-category-name">${catName}</div>
                            <div class="eval-category-desc">${catData.info.description || ''}</div>
                        </div>
                    </div>
                    <div class="eval-category-stats">
                        <div class="eval-category-progress">
                            <div class="eval-category-progress-fill" style="width: ${catData.score || 0}%; background: ${scoreColor}"></div>
                        </div>
                        <span class="eval-category-score" style="color: ${scoreColor}">${catData.score !== null ? catData.score + '%' : 'N/A'}</span>
                        <span class="eval-category-toggle"><i class="fas fa-chevron-down"></i></span>
                    </div>
                </div>
                <div class="eval-category-questions">
                    ${catData.questions.map(q => renderQuestion(q)).join('')}
                </div>
            </div>
        `;
    }).join('');
}

function renderQuestion(q) {
    const status = (q.status || 'N/A').toUpperCase();
    const statusClass = status.toLowerCase().replace('/', '');
    const statusIcon = getStatusIcon(status);
    
    return `
        <div class="eval-question">
            <div class="eval-question-status ${statusClass}">
                <i class="fas ${statusIcon}"></i>
            </div>
            <div class="eval-question-content">
                <div class="eval-question-text">${q.question || q.question_id}</div>
                <div class="eval-question-meta">
                    <span><i class="fas fa-tag"></i> ${status}</span>
                    <span><i class="fas fa-percentage"></i> ${q.confidence || 0}% confidence</span>
                </div>
                ${q.evidence ? `<div class="eval-question-evidence">"${q.evidence}"</div>` : ''}
                ${q.reasoning ? `<div class="eval-question-reasoning">${q.reasoning}</div>` : ''}
            </div>
        </div>
    `;
}

function getStatusIcon(status) {
    switch (status) {
        case 'YES': return 'fa-check';
        case 'NO': return 'fa-times';
        case 'PARTIAL': return 'fa-minus';
        default: return 'fa-question';
    }
}

function getScoreColor(score) {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
}

function toggleCategory(catId) {
    const cat = document.getElementById(`cat-${catId}`);
    cat.classList.toggle('expanded');
}

function toggleAllCategories() {
    allExpanded = !allExpanded;
    document.querySelectorAll('.eval-category').forEach(cat => {
        if (allExpanded) {
            cat.classList.add('expanded');
        } else {
            cat.classList.remove('expanded');
        }
    });
}

// ============== UTILITY FUNCTIONS ==============
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    navigator.clipboard.writeText(element.innerText).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'error');
    });
}

function downloadTranscript() {
    if (!resultData) return;
    downloadFile(resultData.formatted_transcript, 'transcript.txt', 'text/plain');
}

function downloadAll() {
    if (!resultData) return;
    
    let report = `CALL QUALITY REPORT\n${'='.repeat(60)}\n\n`;
    
    if (resultData.evaluation) {
        const scores = resultData.evaluation.scores;
        report += `QUALITY SCORE: ${scores.overall_score}% (Grade ${scores.grade})\n`;
        report += `Confidence: ${scores.average_confidence}%\n`;
        report += `Results: ${scores.status_counts.YES} Passed | ${scores.status_counts.PARTIAL} Partial | ${scores.status_counts.NO} Failed\n\n`;
        
        report += `${'='.repeat(60)}\nDETAILED EVALUATION\n${'='.repeat(60)}\n\n`;
        
        for (const [catName, catData] of Object.entries(resultData.evaluation.by_category)) {
            report += `\n${catName} (${catData.score || 'N/A'}%)\n${'-'.repeat(40)}\n`;
            for (const q of catData.questions) {
                report += `\n[${q.status}] ${q.question}\n`;
                report += `    Confidence: ${q.confidence}%\n`;
                if (q.evidence) report += `    Evidence: "${q.evidence}"\n`;
                if (q.reasoning) report += `    Reasoning: ${q.reasoning}\n`;
            }
        }
    }
    
    report += `\n\n${'='.repeat(60)}\nCALL SUMMARY\n${'='.repeat(60)}\n\n`;
    report += resultData.summary;
    
    report += `\n\n${'='.repeat(60)}\nFULL TRANSCRIPT\n${'='.repeat(60)}\n\n`;
    report += resultData.formatted_transcript;
    
    downloadFile(report, 'call_quality_report.txt', 'text/plain');
    
    const jsonReport = JSON.stringify(resultData, null, 2);
    downloadFile(jsonReport, 'call_data.json', 'application/json');
    
    showToast('Report downloaded!', 'success');
}

function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function downloadOriginalAudio() {
    const audioUrl = resolveAudioUrl();
    if (!audioUrl) {
        showToast('Audio not available yet', 'error');
        return;
    }
    const link = document.createElement('a');
    link.href = `${audioUrl}?download=1`;
    link.download = resultData?.filename || 'audio-file';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Audio download started', 'success');
}

function resetApp() {
    stopPolling();
    currentJobId = null;
    resultData = null;
    allExpanded = false;
    
    resultsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    
    resetUpload();
    resetSteps();
    updateProgress(0, '');
    updateTranscriptAudio(null);
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    toast.style.background = type === 'error' ? '#ef4444' : '#10b981';
    toast.querySelector('i').className = type === 'error' ? 'fas fa-exclamation-circle' : 'fas fa-check-circle';
    toastMessage.textContent = message;
    
    toast.classList.remove('hidden');
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.classList.add('hidden'), 300);
    }, 3000);
}