// Initialize AOS
document.addEventListener('DOMContentLoaded', function() {
    AOS.init({
        duration: 800,
        easing: 'ease-in-out',
        once: true
    });
    
    // Initialize Feather Icons
    feather.replace();
    
    // Setup Quiz functionality
    setupQuiz();
});

// Quiz Management
function setupQuiz() {
    const quizModal = document.getElementById('quizModal');
    if (quizModal) {
        const modal = new bootstrap.Modal(quizModal);
    }
}

function startQuiz(subject, difficulty) {
    const entranceFees = {
        'easy': 10,
        'medium': 25,
        'hard': 50
    };
    
    const rewards = {
        'easy': 5,
        'medium': 10,
        'hard': 15
    };
    
    if (confirm(`Start ${difficulty} ${subject} quiz? Entry fee: ${entranceFees[difficulty]} coins`)) {
        loadQuestions(subject, difficulty);
    }
}

let currentQuestions = [];
let currentQuestionIndex = 0;
let score = 0;

async function loadQuestions(subject, difficulty) {
    try {
        showLoadingSpinner();
        
        // Simulate API call to get questions
        // In production, this would be a real API call
        const response = await fetch(`/api/questions?subject=${subject}&difficulty=${difficulty}`);
        const questions = await response.json();
        
        currentQuestions = questions;
        currentQuestionIndex = 0;
        score = 0;
        
        showQuestion();
        hideLoadingSpinner();
        
    } catch (error) {
        console.error('Error loading questions:', error);
        hideLoadingSpinner();
        showError('Failed to load questions. Please try again.');
    }
}

function showQuestion() {
    const questionContainer = document.getElementById('questionContainer');
    const question = currentQuestions[currentQuestionIndex];
    
    if (!question) {
        endQuiz();
        return;
    }
    
    const optionsHtml = ['A', 'B', 'C', 'D'].map(letter => `
        <button class="option-button" onclick="selectAnswer('${letter}')">
            ${letter}. ${question['option_' + letter.toLowerCase()]}
        </button>
    `).join('');
    
    questionContainer.innerHTML = `
        <h4 class="mb-4">${question.question_text}</h4>
        <div class="options-container">
            ${optionsHtml}
        </div>
    `;
}

function selectAnswer(answer) {
    const question = currentQuestions[currentQuestionIndex];
    const isCorrect = answer === question.correct_answer;
    
    // Highlight correct/incorrect answer
    const buttons = document.querySelectorAll('.option-button');
    buttons.forEach(button => {
        button.disabled = true;
        if (button.textContent.startsWith(answer)) {
            button.classList.add(isCorrect ? 'btn-success' : 'btn-danger');
        }
        if (button.textContent.startsWith(question.correct_answer)) {
            button.classList.add('btn-success');
        }
    });
    
    if (isCorrect) {
        score++;
    }
    
    // Show next question after delay
    setTimeout(() => {
        currentQuestionIndex++;
        showQuestion();
    }, 1500);
}

function endQuiz() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('quizModal'));
    modal.hide();
    
    showResult();
}

function showResult() {
    const totalQuestions = currentQuestions.length;
    const percentage = (score / totalQuestions) * 100;
    
    Swal.fire({
        title: 'Quiz Complete!',
        html: `
            <p>You scored ${score} out of ${totalQuestions}</p>
            <p>Percentage: ${percentage.toFixed(1)}%</p>
        `,
        icon: percentage >= 70 ? 'success' : 'info',
        confirmButtonText: 'OK'
    });
}

// UI Helpers
function showLoadingSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    document.body.appendChild(spinner);
}

function hideLoadingSpinner() {
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

function showError(message) {
    Swal.fire({
        title: 'Error',
        text: message,
        icon: 'error',
        confirmButtonText: 'OK'
    });
}

// Shop Functionality
function purchaseItem(itemName, cost) {
    Swal.fire({
        title: 'Confirm Purchase',
        text: `Do you want to purchase ${itemName} for ${cost} coins?`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Yes',
        cancelButtonText: 'No'
    }).then((result) => {
        if (result.isConfirmed) {
            // Send purchase request to server
            fetch('/api/purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    item: itemName,
                    cost: cost
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire('Success', 'Item purchased successfully!', 'success');
                    // Update user's coin balance
                    updateUserCoins(data.newBalance);
                } else {
                    Swal.fire('Error', data.message || 'Purchase failed', 'error');
                }
            })
            .catch(error => {
                console.error('Purchase error:', error);
                Swal.fire('Error', 'Failed to process purchase', 'error');
            });
        }
    });
}

function updateUserCoins(newBalance) {
    const coinsElement = document.querySelector('.nav-link span');
    if (coinsElement) {
        coinsElement.textContent = `🪙 ${newBalance}`;
    }
}
