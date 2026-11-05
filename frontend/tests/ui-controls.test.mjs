import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let vite;
let Button;
let Modal;

before(async () => {
    vite = await createServer({
        configFile: new URL('../vite.config.ts', import.meta.url).pathname,
        server: { middlewareMode: true },
        appType: 'custom',
    });

    ({ Button } = await vite.ssrLoadModule('/src/components/Button.tsx'));
    ({ Modal } = await vite.ssrLoadModule('/src/components/Modal.tsx'));
});

after(async () => {
    await vite?.close();
});

test('Button shares variant styles and removes repeated inline dimensions', () => {
    const markup = renderToStaticMarkup(
        React.createElement(
            Button,
            {
                type: 'submit',
                variant: 'success',
                title: 'Salvar receita',
                style: {
                    padding: '2rem',
                    borderRadius: '2px',
                    backgroundColor: 'var(--success)',
                    color: 'white',
                },
            },
            'Salvar',
        ),
    );

    assert.match(markup, /class="ui-button ui-button--success"/);
    assert.match(markup, /type="submit"/);
    assert.match(markup, /aria-label="Salvar receita"/);
    assert.match(markup, /background-color:var\(--success\)/);
    assert.doesNotMatch(markup, /padding:|border-radius:/);
});

test('Modal renders shared responsive structure only while open', () => {
    const closedMarkup = renderToStaticMarkup(
        React.createElement(Modal, {
            isOpen: false,
            onClose: () => {},
            title: 'Nova receita',
            children: React.createElement('p', null, 'Conteúdo'),
        }),
    );
    const openMarkup = renderToStaticMarkup(
        React.createElement(Modal, {
            isOpen: true,
            onClose: () => {},
            title: 'Nova receita',
            children: React.createElement('p', null, 'Conteúdo'),
        }),
    );

    assert.equal(closedMarkup, '');
    assert.match(openMarkup, /class="modal-dialog"/);
    assert.match(openMarkup, /aria-label="Fechar"/);
    assert.match(openMarkup, /Conteúdo/);
});
