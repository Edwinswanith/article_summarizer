document.querySelector('form')?.addEventListener('submit', function(e) {
    const btn = document.getElementById('submitBtn');
    btn.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        <span class="ms-2">Processing...</span>
    `;
    btn.disabled = true;
});

// Initialize Popovers with custom template and close functionality
document.addEventListener('DOMContentLoaded', function () {
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');

    popoverTriggerList.forEach(popoverTriggerEl => {
        const popover = new bootstrap.Popover(popoverTriggerEl, {
            html: true,
            sanitize: false, // We are using a safe title, so this is okay.
            title: function () {
                // Fix: Use the `popoverTriggerEl` from the outer scope, as `this` is not the element here.
                const title = popoverTriggerEl.getAttribute('data-bs-title');
                return `${title}<button type="button" class="btn-close popover-close" aria-label="Close"></button>`;
            }
        });

        // Hide other popovers when a new one is shown
        popoverTriggerEl.addEventListener('click', function(e) {
            popoverTriggerList.forEach(el => {
                if (el !== popoverTriggerEl) {
                    bootstrap.Popover.getInstance(el)?.hide();
                }
            });
        });
    });

    // Add a global click listener to handle closing popovers
    document.addEventListener('click', function (e) {
        const target = e.target;

        // If the click is on our custom close button
        if (target.classList.contains('popover-close')) {
            const popoverEl = target.closest('.popover');
            if (popoverEl) {
                const trigger = document.querySelector(`[aria-describedby="${popoverEl.id}"]`);
                if (trigger) {
                    bootstrap.Popover.getInstance(trigger)?.hide();
                }
            }
            return;
        }
        
        // If the click is outside a popover and its trigger
        const isPopoverTrigger = target.closest('[data-bs-toggle="popover"]');
        const inPopover = target.closest('.popover');

        if (!isPopoverTrigger && !inPopover) {
            popoverTriggerList.forEach(el => {
                const popover = bootstrap.Popover.getInstance(el);
                if (popover) {
                    popover.hide();
                }
            });
        }
    });
});


// Audio player time update handler
const audioPlayer = document.getElementById('audioPlayer');
if (audioPlayer) {
    const words = document.querySelectorAll('.word');
    const wordMetas = [];
    let totalChars = 0;

    let currentCharlength = 0;
    words.forEach(word => {
        const wordText = word.textContent || word.innerText;
        word.dataset.startChar = currentCharlength;
        wordMetas.push({
            startChar: currentCharlength,
            endChar: currentCharlength + wordText.length,
        });
        currentCharlength += wordText.length + 1; // for space
    });
    totalChars = currentCharlength > 0 ? currentCharlength - 1 : 0;

    let currentWordIndex = -1;
    audioPlayer.addEventListener('timeupdate', function() {
        if (!audioPlayer.duration) return;

        const progress = audioPlayer.currentTime / audioPlayer.duration;
        const currentCharacter = Math.floor(progress * totalChars);

        let foundWordIndex = -1;
        // Find what word should be highlighted
        for (let i = 0; i < wordMetas.length; i++) {
            if (currentCharacter >= wordMetas[i].startChar && currentCharacter < wordMetas[i].endChar) {
                foundWordIndex = i;
                break;
            }
        }

        if (foundWordIndex !== -1 && foundWordIndex !== currentWordIndex) {
            // Remove highlight from the previous word
            if (currentWordIndex !== -1) {
                words[currentWordIndex].classList.remove('highlight');
            }
            // Add highlight to the current word
            words[foundWordIndex].classList.add('highlight');
            words[foundWordIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
            currentWordIndex = foundWordIndex;
        }
    });

    // Click on a word to jump to the corresponding audio position
    words.forEach(word => {
        word.addEventListener('click', function() {
            const startChar = parseInt(this.dataset.startChar);
            if (!isNaN(startChar) && audioPlayer.duration) {
                const timePosition = (startChar / totalChars) * audioPlayer.duration;
                audioPlayer.currentTime = timePosition;
            }
        });
    });
}