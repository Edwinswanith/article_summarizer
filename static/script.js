document.addEventListener('DOMContentLoaded', function () {
    // Render markdown content
    function renderMarkdownContent() {
        const markdownElements = document.querySelectorAll('.markdown-content');
        markdownElements.forEach(element => {
            let markdownText = element.dataset.markdown;
            if (markdownText) {
                // Clean up unwanted characters and normalize the text
                markdownText = markdownText
                    .replace(/\\n/g, '\n')  // Convert escaped newlines to actual newlines
                    .replace(/\n{3,}/g, '\n\n')  // Replace 3+ consecutive newlines with just 2
                    .replace(/^\s+|\s+$/g, '')  // Trim whitespace from start and end
                    .replace(/\n\s*\n\s*\n/g, '\n\n');  // Clean up multiple empty lines with whitespace
                
                if (window.marked) {
                    element.innerHTML = marked.parse(markdownText);
                    // After rendering markdown, wrap words for audio highlighting
                    wrapWordsForHighlighting(element);
                } else {
                    // Fallback if marked.js is not available
                    element.textContent = markdownText;
                    wrapWordsForHighlighting(element);
                }
            }
        });
    }

    // Function to wrap words in spans for audio highlighting
    function wrapWordsForHighlighting(container) {
        const walker = document.createTreeWalker(
            container,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function(node) {
                    // Skip text nodes that are inside code blocks or other special elements
                    const parent = node.parentElement;
                    if (parent && (parent.tagName === 'CODE' || parent.tagName === 'PRE')) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );

        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }

        textNodes.forEach(textNode => {
            const text = textNode.textContent;
            if (text.trim()) {
                // Split text into words and wrap each in a span
                const words = text.split(/(\s+)/);
                const fragment = document.createDocumentFragment();
                
                words.forEach(word => {
                    if (word.trim()) {
                        // Create span for actual words
                        const span = document.createElement('span');
                        span.className = 'word';
                        span.textContent = word;
                        fragment.appendChild(span);
                    } else if (word) {
                        // Keep whitespace as text nodes
                        fragment.appendChild(document.createTextNode(word));
                    }
                });
                
                textNode.parentNode.replaceChild(fragment, textNode);
            }
        });
    }

    // Initialize markdown rendering
    renderMarkdownContent();

    // Submit button spinner
    document.querySelector('form')?.addEventListener('submit', function (e) {
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

        sourceCloseBtn?.addEventListener('click', function () {
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
        audioPlayer.addEventListener('timeupdate', function () {
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
            word.addEventListener('click', function () {
                if (audioPlayer.duration && totalChars > 0) {
                    const timePosition = (wordMetas[index].start / totalChars) * audioPlayer.duration;
                    audioPlayer.currentTime = timePosition;
                }
            });
        });
    }

    // Get references data from the hidden input field
    const referencesDataElement = document.getElementById('references-data');
    let references = {};
    if (referencesDataElement && referencesDataElement.value) {
        try {
            references = JSON.parse(referencesDataElement.value);
        } catch (e) {
            console.error('Error parsing references data:', e);
        }
    }

    // Handle click on inline citations using event delegation
    document.querySelector('.summary-content')?.addEventListener('click', function (e) {
        let target = e.target;
        // Traverse up the DOM tree to find the nearest parent with the 'citation-hover' class
        while (target && !target.classList.contains('citation-hover') && target !== this) {
            target = target.parentNode;
        }

        if (target && target.classList.contains('citation-hover')) {
            e.preventDefault(); // Prevent default link behavior if any
            const refIdsString = target.dataset.refId; // e.g., "1", "3-5", "1,2"
            const refIds = [];

            // Parse the refIdsString to handle ranges and commas
            refIdsString.split(',').forEach(part => {
                part = part.trim();
                if (part.includes('-')) {
                    const [start, end] = part.split('-').map(Number);
                    for (let i = start; i <= end; i++) {
                        refIds.push(i);
                    }
                } else {
                    refIds.push(Number(part));
                }
            });

            let modalContent = '';
            if (Object.keys(references).length === 0) {
                modalContent = '<p>Reference details not loaded.</p>';
            } else {
                refIds.forEach(id => {
                    const ref = references[id];
                    if (ref && ref.full_text) {
                        modalContent += `<p><strong>[${id}]</strong> ${ref.full_text}</p>`;
                    } else {
                        modalContent += `<p><strong>[${id}]</strong> Details not found.</p>`;
                    }
                });
            }

            // Populate and show the Bootstrap modal
            const referenceModal = new bootstrap.Modal(document.getElementById('referenceModal'));
            document.getElementById('referenceModalBody').innerHTML = modalContent;
            referenceModal.show();
        }
    });
});