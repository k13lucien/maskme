/* ============================================
   CONFIG — Centralized Application Configuration
   ============================================ */
const CONFIG = {
    THEME_STORAGE_KEY: 'maskme-theme',
    SCROLL_THRESHOLD: 40,
    COPY_SUCCESS_COLOR: '#2E7D32',
    COPY_SUCCESS_DURATION_LONG: 1800,
    COPY_SUCCESS_DURATION_SHORT: 1500,
    REVEAL_OBSERVER_MARGIN: '0px 0px -50px 0px',
    REVEAL_OBSERVER_THRESHOLD: 0.08,
    PANEL_DATA: {
        engine: {
            title: 'MaskMe Engine',
            subtitle: 'Python library · Full programmatic control',
            code: `<span class="comment"># 1. Import MaskMe</span>
<span class="key">from</span> maskme <span class="key">import</span> MaskMe

<span class="comment"># 2. Prepare sensitive data</span>
<span class="key">data</span> = {
    <span class="str">"patient"</span>: {
        <span class="str">"id"</span>: <span class="str">"PAT-2026-0045"</span>,
        <span class="str">"full_name"</span>: <span class="str">"Lucien Kiemde"</span>,
        <span class="str">"birth_date"</span>: <span class="str">"1998-05-12"</span>,
        <span class="str">"address"</span>: <span class="str">"01 BP 548, Ouagadougou"</span>
    },
    <span class="str">"medical_history"</span>: [<span class="str">"Asthma"</span>, <span class="str">"Allergies"</span>],
    <span class="str">"diagnosis"</span>: <span class="str">"Acute Respiratory Distress"</span>,
    <span class="str">"prescription"</span>: <span class="str">"Salbutamol 100mcg - 2 puffs every 4h"</span>
}

<span class="comment"># 3. Define anonymization rules</span>
<span class="key">rules</span> = {
    <span class="str">"patient.id"</span>: <span class="str">"hash"</span>,
    <span class="str">"patient.full_name"</span>: <span class="str">"redact"</span>,
    <span class="str">"patient.birth_date"</span>: <span class="str">"generalize"</span>,
    <span class="str">"patient.address"</span>: <span class="str">"redact"</span>,
    <span class="str">"diagnosis"</span>: <span class="str">"keep"</span>,
    <span class="str">"prescription"</span>: <span class="str">"keep"</span>
}

<span class="comment"># 4. Apply anonymization</span>
<span class="key">engine</span> = MaskMe(rules)
<span class="key">result</span> = engine.mask(data)

<span class="comment"># 5. Collect output</span>
<span class="key">print</span>(result)`
        },
        cli: {
            title: 'MaskMe CLI',
            subtitle: 'Command line · Bulk file processing',
            code: `<span class="comment"># Process a CSV file</span>
maskme --input data.csv \
       --rules rules.json \
       --format csv \
       --output clean.csv

<span class="comment"># Streaming with pipes</span>
cat data.jsonl | maskme \
       --rules rules.json \
       --format jsonl \
       > clean.jsonl

<span class="comment"># Validate utility</span>
maskme validate \
       --original data.csv \
       --masked clean.csv \
       --column salary`
        }
    }
};

/* ============================================
   HELPER: Show copy success feedback (DRY)
   ============================================ */
function showCopySuccess(displayElement, duration) {
    const btn = displayElement.nextElementSibling || displayElement;
    const original = displayElement.textContent;
    displayElement.textContent = 'Copied.';
    btn.style.borderColor = CONFIG.COPY_SUCCESS_COLOR;
    setTimeout(() => {
        displayElement.textContent = original;
        btn.style.borderColor = '';
    }, duration);
}

/* ============================================
   THEME TOGGLE
   ============================================ */
const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;
const savedTheme = localStorage.getItem(CONFIG.THEME_STORAGE_KEY);
if (savedTheme) {
    html.setAttribute('data-theme', savedTheme);
}
themeToggle.addEventListener('click', () => {
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem(CONFIG.THEME_STORAGE_KEY, next);
});

/* ============================================
   NAVBAR SCROLL EFFECT (optimized)
   ============================================ */
const navbar = document.getElementById('navbar');
let ticking = false;
let isScrolled = false;
window.addEventListener('scroll', () => {
    if (!ticking) {
        requestAnimationFrame(() => {
            const shouldBeScrolled = window.scrollY > CONFIG.SCROLL_THRESHOLD;
            if (shouldBeScrolled !== isScrolled) {
                navbar.classList.toggle('scrolled', shouldBeScrolled);
                isScrolled = shouldBeScrolled;
            }
            ticking = false;
        });
        ticking = true;
    }
});

/* ============================================
   SCROLL REVEAL (optimized: unobserve after visible)
   ============================================ */
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, { 
    rootMargin: CONFIG.REVEAL_OBSERVER_MARGIN, 
    threshold: CONFIG.REVEAL_OBSERVER_THRESHOLD 
});
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

/* ============================================
   COPY INSTALL COMMAND
   ============================================ */
function copyInstall() {
    navigator.clipboard.writeText('pip install maskme')
        .then(() => {
            const display = document.getElementById('installText');
            showCopySuccess(display, CONFIG.COPY_SUCCESS_DURATION_LONG);
        })
        .catch(err => console.error('Copy failed:', err));
}

/* ============================================
   COPY CITATION (with error handling)
   ============================================ */
function copyCitation(id) {
    const el = document.getElementById(id);
    if (!el) {
        console.warn(`Citation element with id "${id}" not found`);
        return;
    }
    const text = el.textContent.trim();
    navigator.clipboard.writeText(text)
        .then(() => {
            const btn = el.nextElementSibling;
            if (btn) showCopySuccess(btn, CONFIG.COPY_SUCCESS_DURATION_SHORT);
        })
        .catch(err => console.error('Copy failed:', err));
}

/* ============================================
   GET STARTED PANEL TOGGLE (with null checks)
   ============================================ */
const engineCardLeft = document.querySelector('.get-started-panel-left .engine-card');
const cliCardLeft = document.querySelector('.get-started-panel-left .cli-card');
const expandedPanel = document.getElementById('expandedPanel');

function displayInExpandedPanel(side) {
    if (!expandedPanel) {
        console.warn('Expanded panel element not found');
        return;
    }
    if (!CONFIG.PANEL_DATA[side]) {
        console.warn(`Panel data for "${side}" not found`);
        return;
    }
    
    const data = CONFIG.PANEL_DATA[side];
    const header = expandedPanel.querySelector('.get-started-card-header');
    const body = expandedPanel.querySelector('.get-started-card-body pre code');
    
    if (!header || !body) {
        console.warn('Panel header or body element not found');
        return;
    }
    
    header.innerHTML = `
        <h3>${data.title}</h3>
        <p class="card-subtitle">${data.subtitle}</p>
    `;
    body.innerHTML = data.code;
    
    expandedPanel.classList.remove('engine-card', 'cli-card');
    expandedPanel.classList.add(side === 'engine' ? 'engine-card' : 'cli-card');
}

if (engineCardLeft) engineCardLeft.addEventListener('click', () => displayInExpandedPanel('engine'));
if (cliCardLeft) cliCardLeft.addEventListener('click', () => displayInExpandedPanel('cli'));
