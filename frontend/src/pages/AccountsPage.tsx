import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, Wallet, CreditCard } from 'lucide-react';
import api from '../services/api';
import type { Account, CreditCard as CreditCardType, PaginatedResponse } from '../types';
import { Modal } from '../components/Modal';

export const AccountsPage = () => {
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [creditCards, setCreditCards] = useState<CreditCardType[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'accounts' | 'cards'>('accounts');

    // Pagination for accounts
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);

    // Account Modal State
    const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
    const [editingAccount, setEditingAccount] = useState<Account | null>(null);
    const [accountToDelete, setAccountToDelete] = useState<string | null>(null);
    const [accountForm, setAccountForm] = useState({
        key: '',
        name: '',
        bank: 'outro',
        owner: 'joao',
        type: 'CHECKING',
    });

    // Card Modal State
    const [isCardModalOpen, setIsCardModalOpen] = useState(false);
    const [editingCard, setEditingCard] = useState<CreditCardType | null>(null);
    const [cardToDelete, setCardToDelete] = useState<string | null>(null);
    const [cardForm, setCardForm] = useState({
        key: '',
        name: '',
        account_id: '',
        closing_day: '2',
        due_day: '10',
        credit_limit: '0',
    });

    const fetchData = async (p: number) => {
        setLoading(true);
        try {
            const [accRes, cardsRes] = await Promise.all([
                api.get<PaginatedResponse<Account>>(`/accounts/?page=${p}&size=20`),
                api.get<PaginatedResponse<CreditCardType>>('/credit-cards/?page=1&size=100'),
            ]);
            setAccounts(accRes.data.items);
            setTotalPages(accRes.data.pages);
            setTotalItems(accRes.data.total);
            setCreditCards(cardsRes.data.items);
        } catch (error) {
            console.error("Failed to fetch accounts and cards", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(page);
    }, [page]);

    // Account Handlers
    const handleAccountSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                key: accountForm.key.trim().toLowerCase(),
                name: accountForm.name.trim(),
                bank: accountForm.bank.trim().toLowerCase(),
                owner: accountForm.owner.trim().toLowerCase(),
                type: accountForm.type,
            };
            if (editingAccount) {
                await api.put(`/accounts/${editingAccount.id}`, payload);
            } else {
                await api.post('/accounts/', payload);
            }
            setIsAccountModalOpen(false);
            setEditingAccount(null);
            fetchData(page);
        } catch (error) {
            console.error("Error saving account", error);
        }
    };

    const confirmAccountDelete = async () => {
        if (!accountToDelete) return;
        try {
            await api.delete(`/accounts/${accountToDelete}`);
            setAccountToDelete(null);
            fetchData(page);
        } catch (error) {
            console.error("Error deleting account", error);
        }
    };

    const openCreateAccount = () => {
        setEditingAccount(null);
        setAccountForm({ key: '', name: '', bank: 'outro', owner: 'joao', type: 'CHECKING' });
        setIsAccountModalOpen(true);
    };

    const openEditAccount = (acc: Account) => {
        setEditingAccount(acc);
        setAccountForm({
            key: acc.key,
            name: acc.name,
            bank: acc.bank,
            owner: acc.owner,
            type: acc.type,
        });
        setIsAccountModalOpen(true);
    };

    // Card Handlers
    const handleCardSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                key: cardForm.key.trim().toLowerCase(),
                name: cardForm.name.trim(),
                account_id: cardForm.account_id,
                closing_day: parseInt(cardForm.closing_day, 10),
                due_day: parseInt(cardForm.due_day, 10),
                credit_limit: parseFloat(cardForm.credit_limit) || 0.0,
            };
            if (editingCard) {
                await api.put(`/credit-cards/${editingCard.id}`, payload);
            } else {
                await api.post('/credit-cards/', payload);
            }
            setIsCardModalOpen(false);
            setEditingCard(null);
            fetchData(page);
        } catch (error) {
            console.error("Error saving credit card", error);
        }
    };

    const confirmCardDelete = async () => {
        if (!cardToDelete) return;
        try {
            await api.delete(`/credit-cards/${cardToDelete}`);
            setCardToDelete(null);
            fetchData(page);
        } catch (error) {
            console.error("Error deleting card", error);
        }
    };

    const openCreateCard = (accountId?: string) => {
        setEditingCard(null);
        setCardForm({
            key: '',
            name: '',
            account_id: accountId || (accounts[0]?.id ?? ''),
            closing_day: '2',
            due_day: '10',
            credit_limit: '0',
        });
        setIsCardModalOpen(true);
    };

    const openEditCard = (card: CreditCardType) => {
        setEditingCard(card);
        setCardForm({
            key: card.key,
            name: card.name,
            account_id: card.account_id,
            closing_day: card.closing_day.toString(),
            due_day: card.due_day.toString(),
            credit_limit: card.credit_limit.toString(),
        });
        setIsCardModalOpen(true);
    };

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
    };

    return (
        <div>
            {/* Page Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Contas e Cartões</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                        Gerencie a hierarquia de contas bancárias e seus cartões de crédito vinculados
                    </p>
                </div>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                        onClick={() => openCreateCard()}
                        style={{
                            backgroundColor: 'var(--bg-tertiary)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            height: '42px',
                            border: '1px solid var(--border-color)',
                            padding: '0 1.25rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: 600,
                            transition: 'all 0.2s',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)')}
                    >
                        <CreditCard size={18} /> Novo Cartão
                    </button>

                    <button
                        onClick={openCreateAccount}
                        style={{
                            backgroundColor: 'var(--accent-color)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            height: '42px',
                            border: 'none',
                            padding: '0 1.25rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: 600,
                            boxShadow: '0 4px 6px rgba(99, 102, 241, 0.2)',
                            transition: 'all 0.2s',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
                        onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
                    >
                        <Plus size={20} /> Nova Conta
                    </button>
                </div>
            </div>

            {/* Stats Summary */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '1.5rem',
                marginBottom: '2rem'
            }}>
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}>
                    <div style={{
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        padding: '1rem',
                        borderRadius: '12px'
                    }}>
                        <Wallet size={24} color="var(--accent-color)" />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, marginBottom: '0.25rem' }}>
                            Total de Contas
                        </p>
                        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>{totalItems}</h2>
                    </div>
                </div>

                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}>
                    <div style={{
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        padding: '1rem',
                        borderRadius: '12px'
                    }}>
                        <CreditCard size={24} color="var(--success)" />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, marginBottom: '0.25rem' }}>
                            Cartões de Crédito Vinculados
                        </p>
                        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>{creditCards.length}</h2>
                    </div>
                </div>
            </div>

            {/* Tab Buttons */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                <button
                    onClick={() => setActiveTab('accounts')}
                    style={{
                        padding: '0.6rem 1.25rem',
                        borderRadius: '8px',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '0.95rem',
                        backgroundColor: activeTab === 'accounts' ? 'var(--accent-color)' : 'var(--bg-secondary)',
                        color: activeTab === 'accounts' ? 'white' : 'var(--text-secondary)',
                        transition: 'all 0.2s',
                    }}
                >
                    Contas Bancárias ({accounts.length})
                </button>
                <button
                    onClick={() => setActiveTab('cards')}
                    style={{
                        padding: '0.6rem 1.25rem',
                        borderRadius: '8px',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '0.95rem',
                        backgroundColor: activeTab === 'cards' ? 'var(--accent-color)' : 'var(--bg-secondary)',
                        color: activeTab === 'cards' ? 'white' : 'var(--text-secondary)',
                        transition: 'all 0.2s',
                    }}
                >
                    Cartões de Crédito ({creditCards.length})
                </button>
            </div>

            {/* Main Table Container */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                overflow: 'hidden',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                display: 'flex',
                flexDirection: 'column',
                maxHeight: 'calc(100vh - 250px)'
            }}>
                {loading ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        Carregando dados...
                    </div>
                ) : activeTab === 'accounts' ? (
                    // Accounts Table
                    <>
                        <div style={{ overflowX: 'auto', overflowY: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{
                                        textAlign: 'left',
                                        borderBottom: '1px solid var(--border-color)',
                                        backgroundColor: 'var(--bg-secondary)',
                                        position: 'sticky',
                                        top: 0,
                                        zIndex: 10
                                    }}>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CHAVE (SLUG)</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>NOME DA CONTA</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>BANCO</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>TITULAR</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>TIPO</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CARTÕES</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>AÇÕES</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {accounts.length === 0 ? (
                                        <tr>
                                            <td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                                Nenhuma conta encontrada. Cadastre uma para começar!
                                            </td>
                                        </tr>
                                    ) : (
                                        accounts.map((acc) => {
                                            const cards = acc.credit_cards || [];
                                            return (
                                                <tr
                                                    key={acc.id}
                                                    style={{
                                                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                                        transition: 'background-color 0.2s'
                                                    }}
                                                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                                                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                                                >
                                                    <td style={{ padding: '1.25rem 1.5rem' }}>
                                                        <span style={{
                                                            fontFamily: 'monospace',
                                                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                                            padding: '0.25rem 0.5rem',
                                                            borderRadius: '4px',
                                                            fontSize: '0.85rem'
                                                        }}>
                                                            {acc.key}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '1.25rem 1.5rem', fontWeight: 600, fontSize: '1rem' }}>
                                                        {acc.name}
                                                    </td>
                                                    <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem', textTransform: 'capitalize' }}>
                                                        {acc.bank}
                                                    </td>
                                                    <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem', textTransform: 'capitalize' }}>
                                                        {acc.owner}
                                                    </td>
                                                    <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.85rem' }}>
                                                        <span style={{
                                                            padding: '0.2rem 0.5rem',
                                                            borderRadius: '4px',
                                                            backgroundColor: 'rgba(99, 102, 241, 0.15)',
                                                            color: 'var(--accent-color)',
                                                            fontWeight: 600
                                                        }}>
                                                            {acc.type}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem' }}>
                                                        {cards.length > 0 ? (
                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                                                                {cards.map(c => (
                                                                    <span
                                                                        key={c.id}
                                                                        style={{
                                                                            fontSize: '0.8rem',
                                                                            backgroundColor: 'rgba(34, 197, 94, 0.15)',
                                                                            color: 'var(--success)',
                                                                            padding: '0.15rem 0.45rem',
                                                                            borderRadius: '4px',
                                                                            fontWeight: 500
                                                                        }}
                                                                    >
                                                                        {c.name}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        ) : (
                                                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Nenhum</span>
                                                        )}
                                                    </td>
                                                    <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                            <button
                                                                onClick={() => openCreateCard(acc.id)}
                                                                title="Adicionar Cartão"
                                                                style={{
                                                                    padding: '0.5rem',
                                                                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                                                    border: '1px solid rgba(99, 102, 241, 0.2)',
                                                                    borderRadius: '8px',
                                                                    cursor: 'pointer',
                                                                    transition: 'all 0.2s',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    justifyContent: 'center'
                                                                }}
                                                            >
                                                                <Plus size={16} color="var(--accent-color)" />
                                                            </button>
                                                            <button
                                                                onClick={() => openEditAccount(acc)}
                                                                title="Editar Conta"
                                                                style={{
                                                                    padding: '0.5rem',
                                                                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                                                    border: '1px solid rgba(245, 158, 11, 0.2)',
                                                                    borderRadius: '8px',
                                                                    cursor: 'pointer',
                                                                    transition: 'all 0.2s',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    justifyContent: 'center'
                                                                }}
                                                            >
                                                                <Edit2 size={16} color="#f59e0b" />
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() => setAccountToDelete(acc.id)}
                                                                title="Excluir Conta"
                                                                style={{
                                                                    padding: '0.5rem',
                                                                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                                                    border: '1px solid rgba(239, 68, 68, 0.2)',
                                                                    borderRadius: '8px',
                                                                    cursor: 'pointer',
                                                                    transition: 'all 0.2s',
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    justifyContent: 'center'
                                                                }}
                                                            >
                                                                <Trash2 size={16} color="#ef4444" />
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {totalPages > 1 && (
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '1.5rem',
                                borderTop: '1px solid rgba(255, 255, 255, 0.05)'
                            }}>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                    Mostrando página {page} de {totalPages}
                                </span>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                        disabled={page === 1}
                                        onClick={() => setPage(page - 1)}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            padding: '0.5rem 1rem',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '8px',
                                            background: 'transparent',
                                            color: 'var(--text-primary)',
                                            cursor: page === 1 ? 'not-allowed' : 'pointer',
                                            opacity: page === 1 ? 0.5 : 1,
                                            fontSize: '0.9rem'
                                        }}
                                    >
                                        <ChevronLeft size={16} /> Anterior
                                    </button>
                                    <button
                                        disabled={page === totalPages}
                                        onClick={() => setPage(page + 1)}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            padding: '0.5rem 1rem',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '8px',
                                            background: 'transparent',
                                            color: 'var(--text-primary)',
                                            cursor: page === totalPages ? 'not-allowed' : 'pointer',
                                            opacity: page === totalPages ? 0.5 : 1,
                                            fontSize: '0.9rem'
                                        }}
                                    >
                                        Próximo <ChevronRight size={16} />
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    // Credit Cards Table
                    <div style={{ overflowX: 'auto', overflowY: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{
                                    textAlign: 'left',
                                    borderBottom: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-secondary)',
                                    position: 'sticky',
                                    top: 0,
                                    zIndex: 10
                                }}>
                                    <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CHAVE (SLUG)</th>
                                    <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>NOME DO CARTÃO</th>
                                    <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CONTA VINCULADA</th>
                                    <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>FECHAMENTO / VENCIMENTO</th>
                                    <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>LIMITE</th>
                                    <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>AÇÕES</th>
                                </tr>
                            </thead>
                            <tbody>
                                {creditCards.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                            Nenhum cartão de crédito cadastrado.
                                        </td>
                                    </tr>
                                ) : (
                                    creditCards.map((card) => {
                                        const parentAcc = accounts.find(a => a.id === card.account_id);
                                        return (
                                            <tr
                                                key={card.id}
                                                style={{
                                                    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                                    transition: 'background-color 0.2s'
                                                }}
                                                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                                                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                                            >
                                                <td style={{ padding: '1.25rem 1.5rem' }}>
                                                    <span style={{
                                                        fontFamily: 'monospace',
                                                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                                        padding: '0.25rem 0.5rem',
                                                        borderRadius: '4px',
                                                        fontSize: '0.85rem'
                                                    }}>
                                                        {card.key}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontWeight: 600, fontSize: '1rem' }}>
                                                    {card.name}
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem' }}>
                                                    <span style={{ color: 'var(--accent-color)', fontWeight: 500 }}>
                                                        {parentAcc ? parentAcc.name : (card.account_name || 'Conta Vinculada')}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem' }}>
                                                    Fecha dia <strong style={{ color: 'var(--text-primary)' }}>{card.closing_day}</strong> / Vence dia <strong style={{ color: 'var(--text-primary)' }}>{card.due_day}</strong>
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem', fontWeight: 600 }}>
                                                    {card.credit_limit > 0 ? formatCurrency(card.credit_limit) : '-'}
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                        <button
                                                            onClick={() => openEditCard(card)}
                                                            title="Editar Cartão"
                                                            style={{
                                                                padding: '0.5rem',
                                                                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                                                border: '1px solid rgba(245, 158, 11, 0.2)',
                                                                borderRadius: '8px',
                                                                cursor: 'pointer',
                                                                transition: 'all 0.2s',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                justifyContent: 'center'
                                                            }}
                                                        >
                                                            <Edit2 size={16} color="#f59e0b" />
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => setCardToDelete(card.id)}
                                                            title="Excluir Cartão"
                                                            style={{
                                                                padding: '0.5rem',
                                                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                                                borderRadius: '8px',
                                                                cursor: 'pointer',
                                                                transition: 'all 0.2s',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                justifyContent: 'center'
                                                            }}
                                                        >
                                                            <Trash2 size={16} color="#ef4444" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Modal de Conta Bancária */}
            <Modal
                isOpen={isAccountModalOpen}
                onClose={() => setIsAccountModalOpen(false)}
                title={editingAccount ? "Editar Conta Bancária" : "Nova Conta Bancária"}
            >
                <form onSubmit={handleAccountSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Chave Identificadora (Slug único)
                        </label>
                        <input
                            required
                            value={accountForm.key}
                            onChange={e => setAccountForm({ ...accountForm, key: e.target.value })}
                            placeholder="ex: itau_joao, nubank_lailla"
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontFamily: 'monospace',
                                fontSize: '1rem'
                            }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Nome de Exibição da Conta
                        </label>
                        <input
                            required
                            value={accountForm.name}
                            onChange={e => setAccountForm({ ...accountForm, name: e.target.value })}
                            placeholder="ex: Itaú (João Lucas), Nubank Principal"
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem'
                            }}
                        />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                Banco / Instituição
                            </label>
                            <input
                                required
                                value={accountForm.bank}
                                onChange={e => setAccountForm({ ...accountForm, bank: e.target.value })}
                                placeholder="ex: itau, nubank, c6"
                                style={{
                                    width: '100%',
                                    padding: '0.9rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'white',
                                    fontSize: '1rem'
                                }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                Titular
                            </label>
                            <input
                                required
                                value={accountForm.owner}
                                onChange={e => setAccountForm({ ...accountForm, owner: e.target.value })}
                                placeholder="ex: joao, lailla"
                                style={{
                                    width: '100%',
                                    padding: '0.9rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'white',
                                    fontSize: '1rem'
                                }}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Tipo de Conta
                        </label>
                        <select
                            value={accountForm.type}
                            onChange={e => setAccountForm({ ...accountForm, type: e.target.value })}
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem'
                            }}
                        >
                            <option value="CHECKING">Conta Corrente (CHECKING)</option>
                            <option value="SAVINGS">Conta Poupança (SAVINGS)</option>
                            <option value="WALLET">Dinheiro Vivo / Carteira (WALLET)</option>
                            <option value="INVESTMENT">Conta de Investimento (INVESTMENT)</option>
                        </select>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setIsAccountModalOpen(false)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                background: 'transparent',
                                color: 'var(--text-secondary)',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: 'var(--accent-color)',
                                color: 'white',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            {editingAccount ? 'Salvar Alterações' : 'Criar Conta'}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Modal de Cartão de Crédito */}
            <Modal
                isOpen={isCardModalOpen}
                onClose={() => setIsCardModalOpen(false)}
                title={editingCard ? "Editar Cartão de Crédito" : "Novo Cartão de Crédito"}
            >
                <form onSubmit={handleCardSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Conta Emissora Vinculada
                        </label>
                        <select
                            required
                            value={cardForm.account_id}
                            onChange={e => setCardForm({ ...cardForm, account_id: e.target.value })}
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem'
                            }}
                        >
                            <option value="">Selecione uma conta...</option>
                            {accounts.map(acc => (
                                <option key={acc.id} value={acc.id}>
                                    {acc.name} ({acc.key})
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Chave Identificadora (Slug único)
                        </label>
                        <input
                            required
                            value={cardForm.key}
                            onChange={e => setCardForm({ ...cardForm, key: e.target.value })}
                            placeholder="ex: itau_card_joao, nubank_card_lailla"
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontFamily: 'monospace',
                                fontSize: '1rem'
                            }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Nome do Cartão
                        </label>
                        <input
                            required
                            value={cardForm.name}
                            onChange={e => setCardForm({ ...cardForm, name: e.target.value })}
                            placeholder="ex: Itaú Mastercard Black, Nubank Gold"
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem'
                            }}
                        />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                Dia de Fechamento da Fatura
                            </label>
                            <input
                                type="number"
                                min={1}
                                max={31}
                                required
                                value={cardForm.closing_day}
                                onChange={e => setCardForm({ ...cardForm, closing_day: e.target.value })}
                                style={{
                                    width: '100%',
                                    padding: '0.9rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'white',
                                    fontSize: '1rem'
                                }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                Dia de Vencimento da Fatura
                            </label>
                            <input
                                type="number"
                                min={1}
                                max={31}
                                required
                                value={cardForm.due_day}
                                onChange={e => setCardForm({ ...cardForm, due_day: e.target.value })}
                                style={{
                                    width: '100%',
                                    padding: '0.9rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'white',
                                    fontSize: '1rem'
                                }}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Limite de Crédito (R$)
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            min={0}
                            value={cardForm.credit_limit}
                            onChange={e => setCardForm({ ...cardForm, credit_limit: e.target.value })}
                            placeholder="0.00"
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem'
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setIsCardModalOpen(false)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                background: 'transparent',
                                color: 'var(--text-secondary)',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: 'var(--accent-color)',
                                color: 'white',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            {editingCard ? 'Salvar Alterações' : 'Criar Cartão'}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Modal de Confirmação para Excluir Conta */}
            <Modal
                isOpen={!!accountToDelete}
                onClose={() => setAccountToDelete(null)}
                title="Excluir Conta Bancária"
            >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                        Tem certeza que deseja excluir esta conta bancária? Todos os cartões de crédito vinculados a ela também serão excluídos automaticamente.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setAccountToDelete(null)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                background: 'transparent',
                                color: 'var(--text-secondary)',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Cancelar
                        </button>
                        <button
                            type="button"
                            onClick={confirmAccountDelete}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: 'var(--danger)',
                                color: 'white',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Excluir Definitivamente
                        </button>
                    </div>
                </div>
            </Modal>

            {/* Modal de Confirmação para Excluir Cartão */}
            <Modal
                isOpen={!!cardToDelete}
                onClose={() => setCardToDelete(null)}
                title="Excluir Cartão de Crédito"
            >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                        Tem certeza que deseja excluir este cartão de crédito?
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setCardToDelete(null)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                background: 'transparent',
                                color: 'var(--text-secondary)',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Cancelar
                        </button>
                        <button
                            type="button"
                            onClick={confirmCardDelete}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                backgroundColor: 'var(--danger)',
                                color: 'white',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Excluir
                        </button>
                    </div>
                </div>
            </Modal>
        </div>
    );
};
