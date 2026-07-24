(function () {
    'use strict';

    const ui = window.FORMULA_UI || {};
    const formulas = (typeof FORMULAS_DATA !== 'undefined' ? FORMULAS_DATA : window.FORMULAS_DATA) || {};
    const text = (value) => String(value || '').trim();
    const esc = (value) => window.escapeHtml(text(value));
    const isRealPattern = (value) => text(value) && text(value) !== 'Textbook / 原文方';

    function citationLabels(formula) {
        const labels = [];
        if (text(formula.yuanben_article_num) && text(formula.yuanben_article_num) !== '0') {
            labels.push(`${ui.fulingLine} ${text(formula.yuanben_article_num)}`);
        }
        const comparison = text(formula.comparison_article_num) || text(formula.songben_article_num);
        if (comparison && comparison !== '0') {
            const label = formula.comparison_book === '金匮'
                ? (ui.language === 'en' ? 'Jingui line' : '金匮第')
                : ui.songbenLine;
            labels.push(`${label} ${comparison}`);
        }
        return labels;
    }

    function citationLabel(formula) {
        return citationLabels(formula).join(' · ');
    }

    function formulaCitationHtml(formula, key) {
        const label = citationLabel(formula);
        if (!label) return '';
        return `<span role="button" tabindex="0" class="fp-citation fp-citation-link" data-formula-key="${esc(key)}">${esc(label)}</span>`;
    }

    function bindFormulaCitationLinks(root) {
        root.querySelectorAll('.fp-citation-link').forEach((link) => {
            const handler = (event) => {
                if (typeof window.openFormulaReference === 'function') {
                    window.openFormulaReference(event, link.dataset.formulaKey);
                }
            };
            link.addEventListener('click', handler);
            link.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') handler(event);
            });
        });
    }

    function formulaOrder(formula) {
        const number = parseInt(text(formula.formula_number), 10);
        return Number.isFinite(number) ? number : 9999;
    }

    function formulaTitle(formula, key) {
        const names = formula.names || {};
        const baseTitle = ui.language === 'en' ? (names.en || names.zh || key) : (names.zh || names.en || key);
        const textbookNumber = text(formula.formula_number);
        const textbookLabel = textbookNumber && textbookNumber !== '0'
            ? (ui.language === 'en' ? `Formula ${textbookNumber}` : `方${textbookNumber}`)
            : '';
        return `${textbookLabel ? `${textbookLabel} · ` : ''}${baseTitle}`;
    }

    function renderFormula(formula, key) {
        const names = formula.names || {};
        const citation = formulaCitationHtml(formula, key);
        const subtitle = [text(names.zh), text(names.en)].filter(Boolean).join(' · ');
        const source = text(formula.source_text);
        const preparation = text(formula.preparation_text);
        const rows = (formula.composition || []).map((herb) =>
            `<tr><td>${esc(herb.herb)}</td><td>${esc(herb.pinyin)}</td><td>${esc(herb.en)}</td><td>${esc(herb.dosage)}</td><td>${esc(herb.role)}</td></tr>`
        ).join('');
        const composition = source
            ? `<div class="fp-text" style="white-space:pre-wrap">${esc(source)}</div>`
            : `<table class="fp-table"><thead><tr>${ui.tableHeaders.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`;

        return `<div class="fp-formula">
            <div class="fp-title">${esc(names.zh || names.en)} <span class="fp-pinyin">${esc(names.pinyin)}</span></div>
            ${subtitle ? `<div class="fp-en">${esc(subtitle)}</div>` : ''}
            ${citation ? `<div class="fp-citations">${citation}</div>` : ''}
            <div class="fp-section"><div class="fp-section-title">${esc(ui.composition)}</div>${composition}</div>
            ${preparation ? `<div class="fp-section"><div class="fp-section-title">${esc(ui.preparation)}</div><div class="fp-text" style="white-space:pre-wrap">${esc(preparation)}</div></div>` : ''}
            ${text(formula.indications) ? `<div class="fp-section"><div class="fp-section-title">${esc(ui.usage)}</div><div class="fp-text">${esc(formula.indications)}</div></div>` : ''}
            ${text(formula.functions) ? `<div class="fp-section"><div class="fp-section-title">${esc(ui.functions)}</div><div class="fp-text">${esc(formula.functions)}</div></div>` : ''}
            ${isRealPattern(formula.pattern) ? `<div class="fp-section"><div class="fp-section-title">${esc(ui.pattern)}</div><div class="fp-text">${esc(formula.pattern)}</div></div>` : ''}
        </div>`;
    }

    window.openFormulaPopup = function (keys) {
        const overlay = document.getElementById('formulaPopup');
        const body = document.getElementById('formulaPopupBody');
        if (!overlay || !body) return;
        const html = (keys || []).map((key) => [key, formulas[key]]).filter(([, formula]) => formula).map(([key, formula]) => renderFormula(formula, key)).join('');
        body.innerHTML = html || `<div class="loading">${esc(ui.unavailable)}</div>`;
        bindFormulaCitationLinks(body);
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    window.loadFormulas = function () {
        const grid = document.getElementById('formula-grid');
        if (!grid) return;
        const entries = Object.entries(formulas).filter(([, formula]) => text(formula.formula_number)).sort((a, b) => {
            const orderDiff = formulaOrder(a[1]) - formulaOrder(b[1]);
            if (orderDiff) return orderDiff;
            return String(a[0]).localeCompare(String(b[0]));
        });
        grid.innerHTML = entries.map(([key, formula]) => {
            const names = formula.names || {};
            const title = formulaTitle(formula, key);
            const subtitle = [text(names.zh), text(names.en)].filter(Boolean).join(' · ');
            const citation = formulaCitationHtml(formula, key);
            return `<button class="formula-pill" type="button" data-formula-key="${esc(key)}">
                <div class="formula-pill-name">${esc(title)}</div>
                ${subtitle ? `<div class="formula-pill-subtitle">${esc(subtitle)}</div>` : ''}
                ${citation ? `<div class="formula-pill-reference">${citation}</div>` : ''}
            </button>`;
        }).join('') || `<div class="loading">${esc(ui.unavailable)}</div>`;
        bindFormulaCitationLinks(grid);
        grid.querySelectorAll('.formula-pill').forEach((button) => {
            button.addEventListener('click', () => window.openFormulaPopup([button.dataset.formulaKey]));
        });
    };
})();
