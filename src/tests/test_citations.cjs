// Exercise the actual template handlers with a minimal DOM, without a server or LLM.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

for (const template of ['chat.html', 'chat_en.html']) {
    test(`${template}: each answer and reference list retains its own evidence`, () => {
        const html = fs.readFileSync(path.join(__dirname, '../templates', template), 'utf8');
        const names = ['addMessage', 'addSources', 'processBotMessage', 'showCitationPopup'];
        const handlers = names.map(name => {
            const start = html.indexOf(`        function ${name}(`);
            const end = html.indexOf('\n        function ', start + 1);
            assert.ok(start >= 0 && end > start);
            return html.slice(start, end);
        }).join('\n');
        const stateDeclaration = html.match(/        const messageSources = .*;/)?.[0];
        assert.ok(stateDeclaration);
        const context = vm.createContext({assert});
        vm.runInContext(`
            ${stateDeclaration}
            const FORMULA_NAME_MAP = {};
            const elements = {};
            const messagesEl = {children: [], appendChild(node) { this.children.push(node); }};
            const document = {
                body: {style: {}},
                createElement() { return {innerHTML: '', classList: {add() {}}}; },
                getElementById(id) { return elements[id]; }
            };
            elements.citationPopup = {classList: {add() {}}};
            elements.citationPopupBody = {innerHTML: ''};
            const escapeHtml = text => String(text);
            const renderMarkdown = text => text;
            const scrollToBottom = () => {};
            ${handlers}
            const first = [{title: 'First source', content: 'First evidence'}];
            const second = [{title: 'Second source', content: 'Second evidence'}];
            const firstAnswer = addMessage('First answer [1]', 'bot', first);
            addSources(first);
            const firstReferences = messagesEl.children.at(-1);
            addMessage('Second answer [1]', 'bot', second);
            addSources(second);
            const click = owner => ({preventDefault() {}, currentTarget: {closest() { return owner; }}});
            showCitationPopup(click(firstAnswer), 1);
            assert.match(elements.citationPopupBody.innerHTML, /First evidence/);
            assert.doesNotMatch(elements.citationPopupBody.innerHTML, /Second evidence/);
            showCitationPopup(click(firstReferences), 1);
            assert.match(elements.citationPopupBody.innerHTML, /First evidence/);
            showCitationPopup(click(messagesEl.children.at(-1)), 1);
            assert.match(elements.citationPopupBody.innerHTML, /Second evidence/);
            const hidden = [{title: 'Lecture', hide_in_popup: true}];
            const lecture = addMessage('Lecture [1]', 'bot', hidden);
            assert.doesNotMatch(lecture.innerHTML, /showCitationPopup/);
            elements.citationPopupBody.innerHTML = '';
            showCitationPopup(click(lecture), 1);
            assert.equal(elements.citationPopupBody.innerHTML, '');
            const empty = addMessage('Missing [99]', 'bot');
            assert.doesNotMatch(empty.innerHTML, /showCitationPopup/);
        `, context);
    });
}
