import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let vite;
let Button;
let Modal;
let getInstallmentAmounts;
let isInstallmentInProgress;
let Dashboard;
let InstallmentsPage;

before(async () => {
    vite = await createServer({
        configFile: new URL('../vite.config.ts', import.meta.url).pathname,
        server: { middlewareMode: true, hmr: false },
        appType: 'custom',
    });

    ({ Button } = await vite.ssrLoadModule('/src/components/Button.tsx'));
    ({ Modal } = await vite.ssrLoadModule('/src/components/Modal.tsx'));
    ({ getInstallmentAmounts, isInstallmentInProgress } = await vite.ssrLoadModule('/src/utils/installments.ts'));
    ({ Dashboard } = await vite.ssrLoadModule('/src/pages/Dashboard.tsx'));
    ({ InstallmentsPage } = await vite.ssrLoadModule('/src/pages/InstallmentsPage.tsx'));
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

test('installment amounts split total purchase into paid and remaining values', () => {
    const installment = {
        installment_id: 'installment-1',
        category: 'tecnologia',
        item_bought: 'Monitor',
        amount: 100,
        total_installments: 10,
        passed_installments: 2,
    };

    assert.deepEqual(getInstallmentAmounts(installment), {
        totalAmount: 1000,
        paidAmount: 200,
        remainingAmount: 800,
        isCompleted: false,
    });
    assert.equal(isInstallmentInProgress(installment), true);
});

test('caps paid value at the total for completed or over-counted installments', () => {
    const installment = {
        installment_id: 'installment-2',
        category: 'casa',
        item_bought: 'Cadeira',
        amount: 75.5,
        total_installments: 4,
        passed_installments: 8,
    };

    assert.deepEqual(getInstallmentAmounts(installment), {
        totalAmount: 302,
        paidAmount: 302,
        remainingAmount: 0,
        isCompleted: true,
    });
    assert.equal(isInstallmentInProgress(installment), false);
});

test('excludes invalid zero-installment summaries from the in-progress list', () => {
    const installment = {
        installment_id: 'installment-3',
        category: 'casa',
        item_bought: 'Mesa',
        amount: 120,
        total_installments: 0,
        passed_installments: 0,
    };

    assert.deepEqual(getInstallmentAmounts(installment), {
        totalAmount: 0,
        paidAmount: 0,
        remainingAmount: 0,
        isCompleted: false,
    });
    assert.equal(isInstallmentInProgress(installment), false);
});

test('dashboard renders without crashing in its initial loading state', () => {
    const markup = renderToStaticMarkup(React.createElement(Dashboard));

    assert.match(markup, /Carregando painel/);
});

test('installments page renders its loading state without crashing', () => {
    const markup = renderToStaticMarkup(React.createElement(InstallmentsPage));

    assert.match(markup, /animate-spin/);
});
