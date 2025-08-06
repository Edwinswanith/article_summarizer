document.addEventListener('DOMContentLoaded', function () {
    // Submit button spinner
    document.querySelector('form')?.addEventListener('submit', function(e) {
        const btn = document.getElementById('submitBtn');
        btn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            <span class="ms-2">Processing...</span>
        `;
        btn.disabled = true;
    });

    // Source panel logic
    const sourceBadges = document.querySelectorAll('.source-badge');
    const resultsContainer = document.querySelector('.results-container');
    const sourceContainer = document.getElementById('sourceContainer');
    const sourceTitle = document.getElementById('sourceTitle');
    const sourceText = document.getElementById('sourceText');
    const sourceCloseBtn = document.getElementById('sourceCloseBtn');

    if (resultsContainer && sourceContainer) {
        sourceBadges.forEach(badge => {
            badge.addEventListener('click', function () {
                const page = this.dataset.pageNumber;
                const text = this.dataset.sourceText;
                const isCurrentlyVisible = resultsContainer.classList.contains('source-visible');

                if (isCurrentlyVisible && sourceTitle.textContent.includes(`Page ${page}`)) {
                    resultsContainer.classList.remove('source-visible');
                } else {
                    sourceTitle.textContent = `Source (Page ${page})`;
                    if (window.marked) {
                        sourceText.innerHTML = marked.parse(text);
                    } else {
                        sourceText.textContent = text;
                    }
                    resultsContainer.classList.add('source-visible');
                }
            });
        });

        sourceCloseBtn?.addEventListener('click', function() {
            resultsContainer.classList.remove('source-visible');
        });
    }

    // Audio player time update handler
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        const words = document.querySelectorAll('.word');
        let totalChars = 0;
        const wordMetas = Array.from(words).map(word => {
            const wordText = word.textContent || word.innerText;
            const start = totalChars;
            totalChars += wordText.length + 1; // +1 for space
            return { el: word, start, end: totalChars - 1 };
        });

        let currentWordIndex = -1;
        audioPlayer.addEventListener('timeupdate', function() {
            if (!audioPlayer.duration || totalChars === 0) return;

            const progress = audioPlayer.currentTime / audioPlayer.duration;
            const currentChar = Math.floor(progress * totalChars);

            let foundWordIndex = -1;
            for (let i = 0; i < wordMetas.length; i++) {
                if (currentChar >= wordMetas[i].start && currentChar < wordMetas[i].end) {
                    foundWordIndex = i;
                    break;
                }
            }

            if (foundWordIndex !== -1 && foundWordIndex !== currentWordIndex) {
                if (currentWordIndex !== -1) {
                    wordMetas[currentWordIndex].el.classList.remove('highlight');
                }
                wordMetas[foundWordIndex].el.classList.add('highlight');
                wordMetas[foundWordIndex].el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
                currentWordIndex = foundWordIndex;
            }
        });

        words.forEach((word, index) => {
            word.addEventListener('click', function() {
                if (audioPlayer.duration && totalChars > 0) {
                    const timePosition = (wordMetas[index].start / totalChars) * audioPlayer.duration;
                    audioPlayer.currentTime = timePosition;
                }
            });
        });
    }
});