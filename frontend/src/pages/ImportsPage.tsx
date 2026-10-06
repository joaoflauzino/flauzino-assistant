import React, { useEffect, useState } from 'react';
import {
    FileUp,
    Check,
    X,
    Sparkles,
    AlertTriangle,
    Link as LinkIcon,
    ChevronLeft,
    ChevronRight,
    CheckCircle2,
} from 'lucide-react';
import api from '../services/api';
import { showToast } from '../components/Toast';
import type {
    Account,
    CreditCard,
    BulkActionResult,
    Category,
    CommitResult,
    ImportBatch,
    ImportSummary,
    IncomeCategory,
    PaginatedResponse,
    StagedTransaction,
} from '../types';

export const ImportsPage: React.FC = () => {
    // Master data
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [creditCards, setCreditCards] = useState<CreditCard[]>([]);
    const [expenseCategories, setExpenseCategories] = useState<Category[]>([]);
    const [incomeCategories, setIncomeCategories] = useState<IncomeCategory[]>([]);

    // Batches & summary
    const [batches, setBatches] = useState<ImportBatch[]>([]);
    const [selectedBatchId, setSelectedBatchId] = useState<string>('');
    const [summary, setSummary] = useState<ImportSummary>({ pending: 0, approved: 0 });

    // Upload form
    const [uploadTargetKey, setUploadTargetKey] = useState<string>('');
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [lastUploadBatch, setLastUploadBatch] = useState<ImportBatch | null>(null);

    // Staging transactions table
    const [transactions, setTransactions] = useState<StagedTransaction[]>([]);
    const [loadingTx, setLoadingTx] = useState(false);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);

    // Filters
    const [statusFilter, setStatusFilter] = useState<string>('PENDING');
    const [kindFilter, setKindFilter] = useState<string>('');
    const [onlyDuplicates, setOnlyDuplicates] = useState(false);
    const [onlyUnclassified, setOnlyUnclassified] = useState(false);

    // Selection & Bulk actions
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [bulkCategory, setBulkCategory] = useState<string>('');
    const [rememberRule, setRememberRule] = useState<boolean>(true);
    const [isCommitting, setIsCommitting] = useState(false);
    const [isReclassifying, setIsReclassifying] = useState(false);

    // Initial load
    useEffect(() => {
        fetchMasterData();
        fetchBatchesAndSummary();
    }, []);

    // When filters or page change, reload transactions
    useEffect(() => {
        fetchTransactions();
    }, [page, selectedBatchId, statusFilter, kindFilter, onlyDuplicates, onlyUnclassified]);

    const fetchMasterData = async () => {
        try {
            const [accRes, cardRes, expRes, incRes] = await Promise.all([
                api.get<PaginatedResponse<Account>>('/accounts/?size=100'),
                api.get<PaginatedResponse<CreditCard>>('/credit-cards/?size=100'),
                api.get<PaginatedResponse<Category>>('/categories/?size=200'),
                api.get<PaginatedResponse<IncomeCategory>>('/income-categories/?size=200'),
            ]);
            setAccounts(accRes.data.items);
            setCreditCards(cardRes.data.items);

            if (!uploadTargetKey) {
                const c6Card = cardRes.data.items.find(c => c.key.toLowerCase().includes('c6') || c.name.toLowerCase().includes('c6'));
                if (c6Card) {
                    setUploadTargetKey(`card:${c6Card.id}`);
                } else if (accRes.data.items.length > 0) {
                    setUploadTargetKey(`account:${accRes.data.items[0].id}`);
                }
            }
            setExpenseCategories(expRes.data.items);
            setIncomeCategories(incRes.data.items);
        } catch (e) {
            console.error('Failed to load master data', e);
        }
    };

    const fetchBatchesAndSummary = async () => {
        try {
            const [batchesRes, summaryRes] = await Promise.all([
                api.get<ImportBatch[]>('/imports/'),
                api.get<ImportSummary>('/imports/summary'),
            ]);
            setBatches(batchesRes.data);
            setSummary(summaryRes.data);
        } catch (e) {
            console.error('Failed to load batches or summary', e);
        }
    };

    const fetchTransactions = async () => {
        setLoadingTx(true);
        try {
            const params = new URLSearchParams();
            params.set('page', String(page));
            params.set('size', '30');
            if (selectedBatchId) params.set('batch_id', selectedBatchId);
            if (statusFilter && statusFilter !== 'ALL') params.set('status', statusFilter);
            if (kindFilter) params.set('kind', kindFilter);
            if (onlyDuplicates) params.set('only_duplicates', 'true');
            if (onlyUnclassified) params.set('only_unclassified', 'true');

            const res = await api.get<PaginatedResponse<StagedTransaction>>(`/imports/transactions?${params.toString()}`);
            setTransactions(res.data.items);
            setTotalPages(res.data.pages);
            setTotalItems(res.data.total);
            setSelectedIds([]);
        } catch (e) {
            console.error('Failed to load transactions', e);
        } finally {
            setLoadingTx(false);
        }
    };

    // Upload handler
    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!uploadFile) {
            showToast('Selecione um arquivo de extrato ou fatura (.csv)', 'error');
            return;
        }
        if (!uploadTargetKey) {
            showToast('Selecione a conta ou cartão correspondente', 'error');
            return;
        }

        setIsUploading(true);
        try {
            const [targetType, targetId] = uploadTargetKey.split(':');
            const formData = new FormData();
            formData.append('file', uploadFile);
            if (targetType === 'card') {
                formData.append('credit_card_id', targetId);
            } else {
                formData.append('account_id', targetId);
            }

            const res = await api.post<ImportBatch>('/imports/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setLastUploadBatch(res.data);
            setSelectedBatchId(res.data.id);
            setUploadFile(null);
            // Reset input element
            const input = document.getElementById('statement-file-input') as HTMLInputElement;
            if (input) input.value = '';

            showToast(`Extrato importado com sucesso! ${res.data.new_rows} novas transações adicionadas à fila.`, 'success');
            await fetchBatchesAndSummary();
            setPage(1);
            setStatusFilter('PENDING');
        } catch (e) {
            console.error('Upload failed', e);
        } finally {
            setIsUploading(false);
        }
    };

    // Single item field update (PATCH)
    const handleUpdateField = async (
        txId: string,
        fields: { kind?: string; category?: string; status?: string; remember?: boolean; location?: string | null }
    ) => {
        try {
            const payload = { ...fields, remember: fields.remember ?? rememberRule };
            const res = await api.patch<StagedTransaction>(`/imports/transactions/${txId}`, payload);
            setTransactions(prev => prev.map(t => (t.id === txId ? res.data : t)));
            fetchBatchesAndSummary();
        } catch (e) {
            console.error('Failed to update transaction', e);
        }
    };

    // Single item approve
    const handleApprove = async (tx: StagedTransaction) => {
        if ((tx.kind === 'EXPENSE' || tx.kind === 'INCOME') && !tx.category) {
            showToast(`Selecione uma categoria para aprovar este item (${tx.kind}).`, 'error');
            return;
        }
        await handleUpdateField(tx.id, { status: 'APPROVED' });
        showToast('Transação aprovada!', 'success');
    };

    // Single item ignore
    const handleIgnore = async (txId: string) => {
        await handleUpdateField(txId, { status: 'IGNORED' });
        showToast('Transação ignorada.', 'success');
    };

    // Link duplicate
    const handleLinkDuplicate = async (txId: string) => {
        try {
            const res = await api.post<StagedTransaction>(`/imports/transactions/${txId}/link`);
            setTransactions(prev => prev.map(t => (t.id === txId ? res.data : t)));
            showToast('Transação vinculada ao lançamento existente!', 'success');
            fetchBatchesAndSummary();
        } catch (e) {
            console.error('Failed to link transaction', e);
        }
    };

    // Bulk actions
    const handleBulkAction = async (action: 'approve' | 'ignore' | 'reopen' | 'set_category') => {
        if (selectedIds.length === 0) return;
        if (action === 'set_category' && !bulkCategory) {
            showToast('Selecione uma categoria para aplicar em massa.', 'error');
            return;
        }

        try {
            const res = await api.post<BulkActionResult>('/imports/transactions/bulk', {
                ids: selectedIds,
                action,
                category: action === 'set_category' ? bulkCategory : undefined,
                remember: rememberRule,
            });

            showToast(
                `Ação concluída: ${res.data.updated} atualizados, ${res.data.skipped} pulados.`,
                res.data.updated > 0 ? 'success' : 'info'
            );
            if (res.data.errors && res.data.errors.length > 0) {
                showToast(`${res.data.errors.length} erros ao processar o lote.`, 'error');
            }

            setSelectedIds([]);
            fetchTransactions();
            fetchBatchesAndSummary();
        } catch (e) {
            console.error('Bulk action failed', e);
        }
    };

    // Commit approved
    const handleCommitApproved = async () => {
        const targetBatch = batches.find(b => b.id === selectedBatchId);
        const msg = selectedBatchId
            ? `Efetivar todas as transações aprovadas do lote "${targetBatch?.filename || 'selecionado'}" no sistema financeiro?`
            : 'Efetivar TODAS as transações aprovadas de todos os lotes no sistema financeiro?';

        if (!window.confirm(msg)) return;

        setIsCommitting(true);
        try {
            const res = await api.post<CommitResult>('/imports/commit', {
                batch_id: selectedBatchId || undefined,
            });

            showToast(
                `Importação concluída! ${res.data.committed_spents} despesas e ${res.data.committed_incomes} receitas geradas (${res.data.processed_without_record} transferências/faturas arquivadas). Dica: use os filtros 'Últimos 90 dias' ou 'Ver Todos' em Gastos/Receitas para visualizar registros de meses anteriores.`,
                'success'
            );

            if (res.data.failed.length > 0) {
                showToast(`${res.data.failed.length} itens falharam ao ser gravados.`, 'error');
            }

            fetchTransactions();
            fetchBatchesAndSummary();
        } catch (e) {
            console.error('Commit failed', e);
        } finally {
            setIsCommitting(false);
        }
    };

    // Reclassify with AI
    const handleReclassify = async () => {
        if (!selectedBatchId) return;
        setIsReclassifying(true);
        try {
            const res = await api.post<{ classified: number; ai_used: boolean }>(
                `/imports/${selectedBatchId}/classify`
            );
            if (res.data.ai_used) {
                showToast(`IA classificou ${res.data.classified} transações com sucesso!`, 'success');
            } else {
                showToast('Serviço de IA indisponível no momento.', 'info');
            }
            fetchTransactions();
            fetchBatchesAndSummary();
        } catch (e) {
            console.error('Reclassify failed', e);
        } finally {
            setIsReclassifying(false);
        }
    };

    // Selection helpers
    const handleToggleSelectAll = () => {
        if (selectedIds.length === transactions.length) {
            setSelectedIds([]);
        } else {
            setSelectedIds(transactions.map(t => t.id));
        }
    };

    const handleToggleSelect = (id: string) => {
        setSelectedIds(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const formatCurrency = (val: number, direction: 'IN' | 'OUT') => {
        const formatted = new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL',
        }).format(val);
        return direction === 'IN' ? `+${formatted}` : `-${formatted}`;
    };

    const formatDate = (iso: string) => {
        try {
            const d = new Date(iso);
            return d.toLocaleDateString('pt-BR');
        } catch {
            return iso;
        }
    };

    return (
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '2rem',
                flexWrap: 'wrap',
                gap: '1rem',
            }}>
                <div>
                    <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-primary)' }}>
                        Importação de Extratos
                    </h1>
                    <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                        Suba o extrato do banco, valide e ajuste as categorias antes de oficializar os lançamentos.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <div style={{
                        padding: '0.5rem 1rem',
                        backgroundColor: 'var(--bg-secondary)',
                        borderRadius: '8px',
                        border: '1px solid var(--border-color)',
                        display: 'flex',
                        gap: '1.5rem',
                        fontSize: '0.9rem',
                    }}>
                        <div>
                            <span style={{ color: 'var(--text-secondary)' }}>Pendentes: </span>
                            <strong style={{ color: 'var(--warning)' }}>{summary.pending}</strong>
                        </div>
                        <div>
                            <span style={{ color: 'var(--text-secondary)' }}>Aprovadas: </span>
                            <strong style={{ color: 'var(--success)' }}>{summary.approved}</strong>
                        </div>
                    </div>
                    <button
                        onClick={handleCommitApproved}
                        disabled={isCommitting || summary.approved === 0}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            backgroundColor: summary.approved > 0 ? 'var(--success)' : 'var(--bg-tertiary)',
                            color: 'white',
                            border: 'none',
                            padding: '0.75rem 1.25rem',
                            borderRadius: '8px',
                            fontWeight: 600,
                            cursor: summary.approved > 0 ? 'pointer' : 'not-allowed',
                            transition: 'all 0.2s',
                        }}
                    >
                        <CheckCircle2 size={18} />
                        {isCommitting ? 'Efetivando...' : `Importar Aprovadas (${summary.approved})`}
                    </button>
                </div>
            </div>

            {/* Section 1: Upload Card */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                padding: '1.5rem',
                borderRadius: '12px',
                border: '1px solid var(--border-color)',
                marginBottom: '2rem',
            }}>
                <h3 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileUp size={20} color="var(--accent-color)" />
                    Novo Upload de Extrato
                </h3>
                <form onSubmit={handleUpload} style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
                    <div style={{ flex: '1 1 280px' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Destino (Conta ou Cartão)
                        </label>
                        <select
                            value={uploadTargetKey}
                            onChange={e => setUploadTargetKey(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.65rem 0.75rem',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-primary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                            }}
                            required
                        >
                            <optgroup label="💳 Cartões de Crédito (Fatura)">
                                {creditCards.map(c => (
                                    <option key={`card:${c.id}`} value={`card:${c.id}`}>
                                        💳 {c.name}
                                    </option>
                                ))}
                            </optgroup>
                            <optgroup label="🏦 Contas Bancárias (Extrato)">
                                {accounts.map(acc => (
                                    <option key={`account:${acc.id}`} value={`account:${acc.id}`}>
                                        🏦 {acc.name} ({acc.bank.toUpperCase()})
                                    </option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    <div style={{ flex: '2 1 300px' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Arquivo do Extrato (.CSV do C6 Bank)
                        </label>
                        <input
                            id="statement-file-input"
                            type="file"
                            accept=".csv"
                            onChange={e => setUploadFile(e.target.files?.[0] || null)}
                            style={{
                                width: '100%',
                                padding: '0.5rem',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-primary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                            }}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isUploading}
                        style={{
                            padding: '0.65rem 1.5rem',
                            backgroundColor: 'var(--accent-color)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                        }}
                    >
                        <FileUp size={18} />
                        {isUploading ? 'Processando e classificando...' : 'Enviar Extrato'}
                    </button>
                </form>

                {/* Banner de resumo do último upload */}
                {lastUploadBatch && (
                    <div style={{
                        marginTop: '1.25rem',
                        padding: '1rem',
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '1rem',
                    }}>
                        <div>
                            <strong>Extrato processado: </strong>
                            <span>{lastUploadBatch.filename}</span>
                            <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                                ({lastUploadBatch.total_rows} linhas no total)
                            </span>
                            <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                                <span style={{ color: 'var(--success)' }}>
                                    ✓ {lastUploadBatch.new_rows} novas transações para revisão
                                </span>
                                {lastUploadBatch.duplicate_rows > 0 && (
                                    <span style={{ color: 'var(--text-secondary)' }}>
                                        • {lastUploadBatch.duplicate_rows} já existiam (descartadas)
                                    </span>
                                )}
                                {lastUploadBatch.possible_duplicates > 0 && (
                                    <span style={{ color: 'var(--warning)' }}>
                                        ⚠ {lastUploadBatch.possible_duplicates} possíveis duplicatas com lançamentos manuais
                                    </span>
                                )}
                            </div>
                        </div>
                        <div>
                            {lastUploadBatch.ai_used ? (
                                <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    padding: '0.25rem 0.6rem',
                                    borderRadius: '12px',
                                    fontSize: '0.75rem',
                                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                                    color: '#a5b4fc',
                                    border: '1px solid #6366f1',
                                }}>
                                    <Sparkles size={12} />
                                    IA aplicada nas categorias
                                </span>
                            ) : (
                                <span style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--text-secondary)',
                                }}>
                                    Classificado por regras determinísticas
                                </span>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Section 2: Filter bar */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                padding: '1.25rem',
                borderRadius: '12px',
                border: '1px solid var(--border-color)',
                marginBottom: '1.5rem',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '1rem',
                alignItems: 'center',
                justifyContent: 'space-between',
            }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
                    {/* Batch selector */}
                    <div>
                        <select
                            value={selectedBatchId}
                            onChange={e => { setSelectedBatchId(e.target.value); setPage(1); }}
                            style={{
                                padding: '0.5rem 0.75rem',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-primary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                                fontSize: '0.9rem',
                            }}
                        >
                            <option value="">Todos os lotes de extrato</option>
                            {batches.map(b => (
                                <option key={b.id} value={b.id}>
                                    {b.filename} - {b.credit_card_name ? `💳 ${b.credit_card_name}` : (b.account_name ? `🏦 ${b.account_name}` : 'Lote')} ({formatDate(b.created_at)})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Status tabs */}
                    <div style={{ display: 'flex', backgroundColor: 'var(--bg-primary)', borderRadius: '6px', padding: '2px', border: '1px solid var(--border-color)' }}>
                        {[
                            { key: 'PENDING', label: 'Pendentes' },
                            { key: 'APPROVED', label: 'Aprovadas' },
                            { key: 'COMMITTED', label: 'Efetivadas' },
                            { key: 'IGNORED', label: 'Ignoradas' },
                            { key: 'ALL', label: 'Todas' },
                        ].map(st => (
                            <button
                                key={st.key}
                                onClick={() => { setStatusFilter(st.key); setPage(1); }}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    border: 'none',
                                    borderRadius: '4px',
                                    fontSize: '0.8rem',
                                    fontWeight: 500,
                                    backgroundColor: statusFilter === st.key ? 'var(--accent-color)' : 'transparent',
                                    color: statusFilter === st.key ? 'white' : 'var(--text-secondary)',
                                }}
                            >
                                {st.label}
                            </button>
                        ))}
                    </div>

                    {/* Kind filter */}
                    <select
                        value={kindFilter}
                        onChange={e => { setKindFilter(e.target.value); setPage(1); }}
                        style={{
                            padding: '0.5rem 0.75rem',
                            backgroundColor: 'var(--bg-primary)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                        }}
                    >
                        <option value="">Todos os tipos</option>
                        <option value="EXPENSE">Despesa (EXPENSE)</option>
                        <option value="INCOME">Receita (INCOME)</option>
                        <option value="TRANSFER">Transferência (TRANSFER)</option>
                        <option value="INVOICE_PAYMENT">Pagto Fatura (INVOICE_PAYMENT)</option>
                        <option value="REFUND">Estorno (REFUND)</option>
                    </select>
                </div>

                <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'center' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={onlyDuplicates}
                            onChange={e => { setOnlyDuplicates(e.target.checked); setPage(1); }}
                        />
                        Só duplicatas suspeitas
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={onlyUnclassified}
                            onChange={e => { setOnlyUnclassified(e.target.checked); setPage(1); }}
                        />
                        Só sem categoria
                    </label>

                    {selectedBatchId && (
                        <button
                            onClick={handleReclassify}
                            disabled={isReclassifying}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.75rem',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-secondary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                                fontSize: '0.8rem',
                            }}
                        >
                            <Sparkles size={14} color="var(--accent-color)" />
                            {isReclassifying ? 'Classificando...' : 'Reclassificar com IA'}
                        </button>
                    )}
                </div>
            </div>

            {/* Section 3: Bulk Actions bar */}
            {selectedIds.length > 0 && (
                <div style={{
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    border: '1px solid var(--accent-color)',
                    padding: '0.75rem 1.25rem',
                    borderRadius: '8px',
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '1rem',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--accent-color)' }}>
                            {selectedIds.length} item(ns) selecionado(s)
                        </span>

                        <button
                            onClick={() => handleBulkAction('approve')}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.8rem',
                                backgroundColor: 'var(--success)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                                fontWeight: 600,
                            }}
                        >
                            <Check size={16} />
                            Aprovar selecionados
                        </button>

                        <button
                            onClick={() => handleBulkAction('ignore')}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.8rem',
                                backgroundColor: 'var(--bg-tertiary)',
                                color: 'var(--text-primary)',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                            }}
                        >
                            <X size={16} />
                            Ignorar selecionados
                        </button>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <select
                            value={bulkCategory}
                            onChange={e => setBulkCategory(e.target.value)}
                            style={{
                                padding: '0.4rem 0.6rem',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-primary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                            }}
                        >
                            <option value="">Selecione categoria em massa...</option>
                            <optgroup label="Despesas">
                                {expenseCategories.map(c => (
                                    <option key={c.key} value={c.key}>{c.display_name}</option>
                                ))}
                            </optgroup>
                            <optgroup label="Receitas">
                                {incomeCategories.map(ic => (
                                    <option key={ic.key} value={ic.key}>{ic.display_name}</option>
                                ))}
                            </optgroup>
                        </select>
                        <button
                            onClick={() => handleBulkAction('set_category')}
                            style={{
                                padding: '0.4rem 0.8rem',
                                backgroundColor: 'var(--accent-color)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                                fontWeight: 500,
                            }}
                        >
                            Aplicar Categoria
                        </button>
                    </div>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        <input
                            type="checkbox"
                            checked={rememberRule}
                            onChange={e => setRememberRule(e.target.checked)}
                        />
                        Lembrar regra de comerciante
                    </label>
                </div>
            )}

            {/* Section 4: Table */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '12px',
                border: '1px solid var(--border-color)',
                overflowX: 'auto',
            }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', backgroundColor: 'rgba(0,0,0,0.1)' }}>
                            <th style={{ padding: '0.75rem 1rem', width: '30px' }}>
                                <input
                                    type="checkbox"
                                    checked={transactions.length > 0 && selectedIds.length === transactions.length}
                                    onChange={handleToggleSelectAll}
                                />
                            </th>
                            <th style={{ padding: '0.75rem 1rem', width: '90px' }}>Data</th>
                            <th style={{ padding: '0.75rem 1rem', minWidth: '220px' }}>Descrição / Comerciante</th>
                            <th style={{ padding: '0.75rem 1rem', width: '110px' }}>Valor</th>
                            <th style={{ padding: '0.75rem 1rem', width: '150px' }}>Tipo (Kind)</th>
                            <th style={{ padding: '0.75rem 1rem', width: '180px' }}>Categoria</th>
                            <th style={{ padding: '0.75rem 1rem', width: '130px' }}>Local</th>
                            <th style={{ padding: '0.75rem 1rem', width: '130px' }}>Origem Sugestão</th>
                            <th style={{ padding: '0.75rem 1rem', width: '130px', textAlign: 'center' }}>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loadingTx ? (
                            <tr>
                                <td colSpan={9} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                    Carregando transações...
                                </td>
                            </tr>
                        ) : transactions.length === 0 ? (
                            <tr>
                                <td colSpan={9} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                    Nenhuma transação encontrada para os filtros selecionados.
                                </td>
                            </tr>
                        ) : (
                            transactions.map(tx => {
                                const isSelected = selectedIds.includes(tx.id);
                                const isIncome = tx.direction === 'IN';
                                const isNeutral = ['TRANSFER', 'INVOICE_PAYMENT', 'REFUND'].includes(tx.kind);

                                return (
                                    <React.Fragment key={tx.id}>
                                        <tr style={{
                                            borderBottom: tx.possible_duplicate ? 'none' : '1px solid var(--border-color)',
                                            backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.05)' : 'transparent',
                                            opacity: tx.status === 'IGNORED' ? 0.5 : 1,
                                        }}>
                                            <td style={{ padding: '0.75rem 1rem' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => handleToggleSelect(tx.id)}
                                                />
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                                                {formatDate(tx.occurred_at)}
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                                        {tx.merchant || tx.raw_title}
                                                    </span>
                                                    {tx.current_installment && tx.total_installments && (
                                                        <span style={{
                                                            fontSize: '0.72rem',
                                                            padding: '0.15rem 0.5rem',
                                                            borderRadius: '4px',
                                                            backgroundColor: 'rgba(99, 102, 241, 0.15)',
                                                            color: 'var(--accent-color)',
                                                            fontWeight: 600,
                                                        }}>
                                                            Parcela {tx.current_installment}/{tx.total_installments}
                                                        </span>
                                                    )}
                                                    {tx.card_last_digits && (
                                                        <span style={{
                                                            fontSize: '0.72rem',
                                                            padding: '0.15rem 0.45rem',
                                                            borderRadius: '4px',
                                                            backgroundColor: 'var(--bg-tertiary)',
                                                            color: 'var(--text-secondary)',
                                                            fontWeight: 500,
                                                        }}>
                                                            Final {tx.card_last_digits}
                                                        </span>
                                                    )}
                                                </div>
                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                    {tx.raw_title} {tx.raw_description ? `• ${tx.raw_description}` : ''}
                                                </div>
                                            </td>
                                            <td style={{
                                                padding: '0.75rem 1rem',
                                                fontWeight: 600,
                                                whiteSpace: 'nowrap',
                                                color: isIncome ? 'var(--success)' : 'var(--danger)',
                                            }}>
                                                {formatCurrency(tx.amount, tx.direction)}
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem' }}>
                                                <select
                                                    value={tx.kind}
                                                    disabled={tx.status === 'COMMITTED'}
                                                    onChange={e => handleUpdateField(tx.id, { kind: e.target.value })}
                                                    style={{
                                                        padding: '0.35rem 0.5rem',
                                                        backgroundColor: 'var(--bg-primary)',
                                                        color: 'var(--text-primary)',
                                                        border: '1px solid var(--border-color)',
                                                        borderRadius: '4px',
                                                        fontSize: '0.8rem',
                                                        width: '100%',
                                                    }}
                                                >
                                                    <option value="EXPENSE">Despesa</option>
                                                    <option value="INCOME">Receita</option>
                                                    <option value="TRANSFER">Transferência</option>
                                                    <option value="INVOICE_PAYMENT">Pgto Fatura</option>
                                                    <option value="REFUND">Estorno</option>
                                                </select>
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem' }}>
                                                {isNeutral ? (
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                                                        Sem categoria (não gera lançamento)
                                                    </span>
                                                ) : (
                                                    <select
                                                        value={tx.category || ''}
                                                        disabled={tx.status === 'COMMITTED'}
                                                        onChange={e => handleUpdateField(tx.id, { category: e.target.value })}
                                                        style={{
                                                            padding: '0.35rem 0.5rem',
                                                            backgroundColor: 'var(--bg-primary)',
                                                            color: tx.category ? 'var(--text-primary)' : 'var(--warning)',
                                                            border: `1px solid ${tx.category ? 'var(--border-color)' : 'var(--warning)'}`,
                                                            borderRadius: '4px',
                                                            fontSize: '0.8rem',
                                                            width: '100%',
                                                        }}
                                                    >
                                                        <option value="">Selecione categoria...</option>
                                                        {tx.kind === 'EXPENSE'
                                                            ? expenseCategories.map(c => (
                                                                <option key={c.key} value={c.key}>
                                                                    {c.display_name}
                                                                </option>
                                                            ))
                                                            : incomeCategories.map(ic => (
                                                                <option key={ic.key} value={ic.key}>
                                                                    {ic.display_name}
                                                                </option>
                                                            ))}
                                                    </select>
                                                )}
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem' }}>
                                                {tx.kind === 'EXPENSE' ? (
                                                    <input
                                                        type="text"
                                                        placeholder="Opcional..."
                                                        value={tx.location || ''}
                                                        disabled={tx.status === 'COMMITTED'}
                                                        onChange={e => {
                                                            const val = e.target.value;
                                                            setTransactions(prev => prev.map(t => (t.id === tx.id ? { ...t, location: val } : t)));
                                                        }}
                                                        onBlur={e => handleUpdateField(tx.id, { location: e.target.value || null })}
                                                        style={{
                                                            padding: '0.35rem 0.5rem',
                                                            backgroundColor: 'var(--bg-primary)',
                                                            color: 'var(--text-primary)',
                                                            border: '1px solid var(--border-color)',
                                                            borderRadius: '4px',
                                                            fontSize: '0.8rem',
                                                            width: '100%',
                                                        }}
                                                    />
                                                ) : (
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>-</span>
                                                )}
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem' }}>
                                                {tx.suggestion_source ? (
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                        <span style={{
                                                            fontSize: '0.7rem',
                                                            padding: '2px 6px',
                                                            borderRadius: '10px',
                                                            backgroundColor:
                                                                tx.suggestion_source === 'LLM'
                                                                    ? 'rgba(99, 102, 241, 0.2)'
                                                                    : tx.suggestion_source === 'MEMORY'
                                                                        ? 'rgba(34, 197, 94, 0.2)'
                                                                        : 'rgba(245, 158, 11, 0.2)',
                                                            color:
                                                                tx.suggestion_source === 'LLM'
                                                                    ? '#a5b4fc'
                                                                    : tx.suggestion_source === 'MEMORY'
                                                                        ? '#86efac'
                                                                        : '#fde047',
                                                            border: '1px solid currentColor',
                                                        }}>
                                                            {tx.suggestion_source === 'LLM' && '✦ IA'}
                                                            {tx.suggestion_source === 'MEMORY' && '★ Memória'}
                                                            {tx.suggestion_source === 'RULE' && '● Regra'}
                                                        </span>
                                                        {tx.confidence && (
                                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                                {Math.round(tx.confidence * 100)}%
                                                            </span>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>-</span>
                                                )}
                                            </td>
                                            <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                                                <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                                                    {tx.status === 'PENDING' && (
                                                        <>
                                                            <button
                                                                onClick={() => handleApprove(tx)}
                                                                title="Aprovar transação"
                                                                style={{
                                                                    padding: '0.35rem 0.5rem',
                                                                    backgroundColor: 'rgba(34, 197, 94, 0.15)',
                                                                    border: '1px solid var(--success)',
                                                                    color: 'var(--success)',
                                                                    borderRadius: '4px',
                                                                }}
                                                            >
                                                                <Check size={14} />
                                                            </button>
                                                            <button
                                                                onClick={() => handleIgnore(tx.id)}
                                                                title="Ignorar transação"
                                                                style={{
                                                                    padding: '0.35rem 0.5rem',
                                                                    backgroundColor: 'transparent',
                                                                    border: '1px solid var(--border-color)',
                                                                    color: 'var(--text-secondary)',
                                                                    borderRadius: '4px',
                                                                }}
                                                            >
                                                                <X size={14} />
                                                            </button>
                                                        </>
                                                    )}
                                                    {tx.status === 'APPROVED' && (
                                                        <span style={{
                                                            fontSize: '0.75rem',
                                                            color: 'var(--success)',
                                                            fontWeight: 600,
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.25rem',
                                                        }}>
                                                            <CheckCircle2 size={14} /> Aprovada
                                                        </span>
                                                    )}
                                                    {tx.status === 'COMMITTED' && (
                                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                            Efetivada
                                                        </span>
                                                    )}
                                                    {tx.status === 'IGNORED' && (
                                                        <button
                                                            onClick={() => handleUpdateField(tx.id, { status: 'PENDING' })}
                                                            title="Restaurar para pendente"
                                                            style={{
                                                                padding: '0.25rem 0.5rem',
                                                                backgroundColor: 'transparent',
                                                                border: '1px solid var(--border-color)',
                                                                color: 'var(--text-secondary)',
                                                                borderRadius: '4px',
                                                                fontSize: '0.75rem',
                                                            }}
                                                        >
                                                            Restaurar
                                                        </button>
                                                    )}
                                                    {tx.status === 'LINKED' && (
                                                        <span style={{ fontSize: '0.75rem', color: '#a5b4fc', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                                                            <LinkIcon size={12} /> Vinculada
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Sub-row de possível duplicata */}
                                        {tx.possible_duplicate && tx.status === 'PENDING' && (
                                            <tr style={{
                                                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                                                borderBottom: '1px solid var(--border-color)',
                                            }}>
                                                <td></td>
                                                <td colSpan={7} style={{ padding: '0.5rem 1rem' }}>
                                                    <div style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'space-between',
                                                        fontSize: '0.82rem',
                                                    }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--warning)' }}>
                                                            <AlertTriangle size={15} />
                                                            <span>
                                                                Possível duplicata com lançamento manual:{' '}
                                                                <strong>"{tx.possible_duplicate.label}"</strong> de R$ {tx.possible_duplicate.amount.toFixed(2)} em {tx.possible_duplicate.date}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                            <button
                                                                onClick={() => handleLinkDuplicate(tx.id)}
                                                                style={{
                                                                    padding: '0.25rem 0.6rem',
                                                                    backgroundColor: 'var(--bg-primary)',
                                                                    border: '1px solid var(--warning)',
                                                                    color: 'var(--warning)',
                                                                    borderRadius: '4px',
                                                                    fontSize: '0.75rem',
                                                                    cursor: 'pointer',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: '0.25rem',
                                                                }}
                                                            >
                                                                <LinkIcon size={12} /> É o mesmo (vincular)
                                                            </button>
                                                            <button
                                                                onClick={() => handleApprove(tx)}
                                                                style={{
                                                                    padding: '0.25rem 0.6rem',
                                                                    backgroundColor: 'transparent',
                                                                    border: '1px solid var(--border-color)',
                                                                    color: 'var(--text-secondary)',
                                                                    borderRadius: '4px',
                                                                    fontSize: '0.75rem',
                                                                    cursor: 'pointer',
                                                                }}
                                                            >
                                                                Criar mesmo assim
                                                            </button>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>

            {/* Section 5: Pagination */}
            {totalPages > 1 && (
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginTop: '1.5rem',
                    color: 'var(--text-secondary)',
                    fontSize: '0.9rem',
                }}>
                    <div>
                        Total de <strong>{totalItems}</strong> transações (Página {page} de {totalPages})
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            style={{
                                padding: '0.4rem 0.8rem',
                                backgroundColor: 'var(--bg-secondary)',
                                border: '1px solid var(--border-color)',
                                color: page === 1 ? 'var(--border-color)' : 'var(--text-primary)',
                                borderRadius: '6px',
                                display: 'flex',
                                alignItems: 'center',
                            }}
                        >
                            <ChevronLeft size={16} /> Anterior
                        </button>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            style={{
                                padding: '0.4rem 0.8rem',
                                backgroundColor: 'var(--bg-secondary)',
                                border: '1px solid var(--border-color)',
                                color: page === totalPages ? 'var(--border-color)' : 'var(--text-primary)',
                                borderRadius: '6px',
                                display: 'flex',
                                alignItems: 'center',
                            }}
                        >
                            Próxima <ChevronRight size={16} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};
