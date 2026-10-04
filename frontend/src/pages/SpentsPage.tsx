import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, Wallet } from 'lucide-react';
import api from '../services/api';
import type { Spent, PaginatedResponse, Category, Account, CreditCard as CreditCardType } from '../types';
import { Modal } from '../components/Modal';

export const SpentsPage = () => {
    const [spents, setSpents] = useState<Spent[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingSpent, setEditingSpent] = useState<Spent | null>(null);
    const [spentToDelete, setSpentToDelete] = useState<string | null>(null);

    // Options States
    const [categories, setCategories] = useState<Category[]>([]);
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [creditCards, setCreditCards] = useState<CreditCardType[]>([]);

    // Helper to get the first and last day de current month
    const getCurrentMonthDates = () => {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        const formatDate = (date: Date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };

        return {
            start: formatDate(firstDay),
            end: formatDate(today)
        };
    };

    const monthDates = getCurrentMonthDates();
    const [startDate, setStartDate] = useState(monthDates.start);
    const [endDate, setEndDate] = useState(monthDates.end);

    // Form State
    const [formData, setFormData] = useState({
        category: '',
        amount: '',
        item_bought: '',
        payment_method: '',
        location: '',
        created_at: monthDates.end,
        is_installment: false,
        current_installment: 1,
        total_installments: 2
    });

    const handleSetPeriod = (type: 'current' | '90days' | 'all') => {
        let s = '';
        let e = '';
        const now = new Date();
        const formatDate = (date: Date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        if (type === 'current') {
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
            s = formatDate(firstDay);
            e = formatDate(now);
        } else if (type === '90days') {
            const past = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
            s = formatDate(past);
            e = formatDate(now);
        } else if (type === 'all') {
            s = '';
            e = '';
        }
        setStartDate(s);
        setEndDate(e);
        setPage(1);
        fetchData(1, s, e);
    };

    const fetchData = async (p: number, sDate = startDate, eDate = endDate) => {
        setLoading(true);
        try {
            let query = `/spents/?page=${p}&size=10`;
            if (sDate) query += `&start_date=${sDate}`;
            if (eDate) query += `&end_date=${eDate}`;

            const response = await api.get<PaginatedResponse<Spent>>(query);
            setSpents(response.data.items);
            setTotalPages(response.data.pages);
            setTotalItems(response.data.total);
        } catch (error) {
            console.error("Failed to fetch spents", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const [catRes, accRes, cardsRes] = await Promise.all([
                    api.get<PaginatedResponse<Category>>('/categories/?size=1000'),
                    api.get<PaginatedResponse<Account>>('/accounts/?size=1000'),
                    api.get<PaginatedResponse<CreditCardType>>('/credit-cards/?size=1000'),
                ]);
                setCategories(catRes.data.items);
                setAccounts(accRes.data.items);
                setCreditCards(cardsRes.data.items);
            } catch (error) {
                console.error("Failed to fetch options", error);
            }
        };
        fetchOptions();
    }, []);

    useEffect(() => {
        fetchData(page);
    }, [page]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload: any = {
                ...formData,
                amount: parseFloat(formData.amount),
                created_at: new Date(formData.created_at + 'T12:00:00Z').toISOString()
            };

            if (formData.is_installment) {
                payload.is_installment = true;
                payload.current_installment = parseInt(formData.current_installment.toString());
                payload.total_installments = parseInt(formData.total_installments.toString());
            } else {
                payload.is_installment = false;
                payload.current_installment = null;
                payload.total_installments = null;
            }

            if (editingSpent) {
                await api.put(`/spents/${editingSpent.id}`, payload);
            } else {
                await api.post('/spents/', payload);
            }
            setIsModalOpen(false);
            setEditingSpent(null);
            setFormData({
                category: '',
                amount: '',
                item_bought: '',
                payment_method: '',
                location: '',
                created_at: monthDates.end,
                is_installment: false,
                current_installment: 1,
                total_installments: 2
            });
            fetchData(page);
        } catch (error) {
            console.error("Error saving spent", error);
        }
    };

    const handleDelete = (id: string) => {
        setSpentToDelete(id);
    };

    const confirmDelete = async () => {
        if (!spentToDelete) return;
        try {
            await api.delete(`/spents/${spentToDelete}`);
            setSpentToDelete(null);
            fetchData(page);
        } catch (error) {
            console.error("Error deleting spent", error);
        }
    };

    const openEdit = (spent: Spent) => {
        setEditingSpent(spent);
        setFormData({
            category: spent.category,
            amount: spent.amount.toString(),
            item_bought: spent.item_bought,
            payment_method: spent.payment_method,
            location: spent.location || '',
            created_at: spent.created_at.split('T')[0],
            is_installment: spent.is_installment || false,
            current_installment: spent.current_installment || 1,
            total_installments: spent.total_installments || 2
        });
        setIsModalOpen(true);
    };

    const openCreate = () => {
        setEditingSpent(null);
        setFormData({
            category: '',
            amount: '',
            item_bought: '',
            payment_method: '',
            location: '',
            created_at: monthDates.end,
            is_installment: false,
            current_installment: 1,
            total_installments: 2
        });
        setIsModalOpen(true);
    };

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Gastos</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Acompanhe e filtre os lançamentos financeiros da família</p>
                </div>
            </div>

            {/* Top Bar: Dates & Total Spent */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: 'var(--bg-secondary)',
                padding: '1.25rem 1.5rem',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                marginBottom: '2rem',
                gap: '1rem',
                flexWrap: 'wrap'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>De:</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            style={{
                                backgroundColor: 'var(--bg-primary)',
                                border: '1px solid var(--border-color)',
                                color: 'white',
                                padding: '0.4rem 0.6rem',
                                borderRadius: '6px',
                                fontSize: '0.85rem'
                            }}
                        />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Até:</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            style={{
                                backgroundColor: 'var(--bg-primary)',
                                border: '1px solid var(--border-color)',
                                color: 'white',
                                padding: '0.4rem 0.6rem',
                                borderRadius: '6px',
                                fontSize: '0.85rem'
                            }}
                        />
                    </div>
                    <button
                        onClick={() => fetchData(1)}
                        style={{
                            backgroundColor: 'var(--accent-color)',
                            color: 'white',
                            border: 'none',
                            padding: '0.45rem 1rem',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: 600
                        }}
                    >
                        Filtrar
                    </button>
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                        <button
                            type="button"
                            onClick={() => handleSetPeriod('current')}
                            style={{ padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
                        >
                            Mês Atual
                        </button>
                        <button
                            type="button"
                            onClick={() => handleSetPeriod('90days')}
                            style={{ padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
                        >
                            Últimos 90 dias
                        </button>
                        <button
                            type="button"
                            onClick={() => handleSetPeriod('all')}
                            style={{ padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
                        >
                            Ver Todos
                        </button>
                    </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        padding: '0.75rem',
                        borderRadius: '10px'
                    }}>
                        <Wallet size={20} color="var(--accent-color)" />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: 0 }}>Total de Registros</p>
                        <h3 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>{totalItems}</h3>
                    </div>
                </div>
            </div>

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
                        Carregando gastos...
                    </div>
                ) : (
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
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>ITEM</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>VALOR</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CATEGORIA</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>FORMA PGTO</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>LOCAL</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>PARCELAS</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>DATA</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>AÇÕES</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {spents.length === 0 ? (
                                        <tr>
                                            <td colSpan={8} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                                Nenhum gasto encontrado para os filtros selecionados.
                                            </td>
                                        </tr>
                                    ) : (
                                        spents.map((s) => (
                                            <tr key={s.id} style={{
                                                borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                                transition: 'background-color 0.2s'
                                            }}
                                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)'}
                                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                            >
                                                <td style={{ padding: '1.25rem 1.5rem', fontWeight: 600 }}>{s.item_bought}</td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontWeight: 600, color: 'var(--text-primary)' }}>{formatCurrency(s.amount)}</td>
                                                <td style={{ padding: '1.25rem 1.5rem' }}>
                                                    <span style={{
                                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                                        padding: '0.25rem 0.5rem',
                                                        borderRadius: '4px',
                                                        fontSize: '0.85rem'
                                                    }}>
                                                        {s.category}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontSize: '0.9rem', color: 'var(--accent-color)', fontWeight: 500 }}>
                                                    {s.payment_method}
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>{s.location}</td>
                                                <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>
                                                    {s.total_installments ? `${s.current_installment}/${s.total_installments}` : '-'}
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>{new Date(s.created_at).toLocaleDateString()}</td>
                                                <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                        <button
                                                            type="button"
                                                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); openEdit(s); }}
                                                            style={{
                                                                padding: '0.5rem',
                                                                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                                                border: '1px solid rgba(245, 158, 11, 0.2)',
                                                                borderRadius: '8px',
                                                                cursor: 'pointer',
                                                                transition: 'all 0.2s',
                                                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                                                            }}
                                                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(245, 158, 11, 0.2)'}
                                                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(245, 158, 11, 0.1)'}
                                                        >
                                                            <Edit2 size={16} color="#f59e0b" />
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(s.id); }}
                                                            style={{
                                                                padding: '0.5rem',
                                                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                                                borderRadius: '8px',
                                                                cursor: 'pointer',
                                                                transition: 'all 0.2s',
                                                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                                                            }}
                                                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.2)'}
                                                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'}
                                                        >
                                                            <Trash2 size={16} color="#ef4444" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
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
                )}
            </div>

            {/* Bottom Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button
                    onClick={openCreate}
                    style={{
                        backgroundColor: 'var(--accent-color)',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        height: '48px',
                        border: 'none',
                        padding: '0 2rem',
                        borderRadius: '12px',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                        transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                >
                    <Plus size={22} /> Novo Gasto
                </button>
            </div>

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingSpent ? "Editar Gasto" : "Novo Gasto"}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Categoria</label>
                        <select
                            required
                            className="form-input"
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem',
                                appearance: 'none'
                            }}
                        >
                            <option value="" disabled>Selecione uma categoria...</option>
                            {categories.map(c => (
                                <option key={c.id} value={c.key}>{c.display_name}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Item Comprado</label>
                        <input
                            required
                            className="form-input"
                            value={formData.item_bought}
                            onChange={e => setFormData({ ...formData, item_bought: e.target.value })}
                            placeholder="e.g. Almoço"
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
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Valor</label>
                        <input
                            type="number"
                            step="0.01"
                            required
                            className="form-input"
                            value={formData.amount}
                            onChange={e => setFormData({ ...formData, amount: e.target.value })}
                            placeholder="0.00"
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem',
                                fontWeight: 600
                            }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Forma de Pagamento</label>
                        <select
                            required
                            value={formData.payment_method}
                            onChange={e => setFormData({ ...formData, payment_method: e.target.value })}
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '1rem',
                                appearance: 'none'
                            }}
                        >
                            <option value="" disabled>Selecione...</option>
                            {creditCards.length > 0 && (
                                <optgroup label="Cartões de Crédito">
                                    {creditCards.map(cc => (
                                        <option key={cc.id} value={cc.key}>{cc.name}</option>
                                    ))}
                                </optgroup>
                            )}
                            {accounts.length > 0 && (
                                <optgroup label="Contas (Débito / Pix / Dinheiro)">
                                    {accounts.map(acc => (
                                        <option key={acc.id} value={acc.key}>{acc.name} ({acc.bank})</option>
                                    ))}
                                </optgroup>
                            )}
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Localização</label>
                        <input
                            required
                            value={formData.location}
                            onChange={e => setFormData({ ...formData, location: e.target.value })}
                            placeholder="e.g. Restaurante do Zé"
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
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Data do Gasto</label>
                        <input
                            type="date"
                            required
                            value={formData.created_at}
                            onChange={e => setFormData({ ...formData, created_at: e.target.value })}
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

                    <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1rem',
                        padding: '1rem',
                        backgroundColor: 'rgba(255, 255, 255, 0.02)',
                        borderRadius: '8px',
                        border: '1px solid var(--border-color)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                                type="checkbox"
                                id="is_installment"
                                checked={formData.is_installment}
                                onChange={e => setFormData({ ...formData, is_installment: e.target.checked })}
                                style={{ width: '1.2rem', height: '1.2rem', accentColor: 'var(--accent-color)' }}
                            />
                            <label htmlFor="is_installment" style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 500, cursor: 'pointer' }}>
                                É uma compra parcelada?
                            </label>
                        </div>

                        {formData.is_installment && (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '0.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Parcela Atual</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={formData.current_installment}
                                        onChange={e => setFormData({ ...formData, current_installment: parseInt(e.target.value) || 1 })}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            borderRadius: '6px',
                                            border: '1px solid var(--border-color)',
                                            backgroundColor: 'var(--bg-primary)',
                                            color: 'white',
                                            fontSize: '0.9rem'
                                        }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total de Parcelas</label>
                                    <input
                                        type="number"
                                        min="2"
                                        value={formData.total_installments}
                                        onChange={e => setFormData({ ...formData, total_installments: parseInt(e.target.value) || 2 })}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            borderRadius: '6px',
                                            border: '1px solid var(--border-color)',
                                            backgroundColor: 'var(--bg-primary)',
                                            color: 'white',
                                            fontSize: '0.9rem'
                                        }}
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setIsModalOpen(false)}
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
                            {editingSpent ? 'Salvar Alterações' : 'Criar Gasto'}
                        </button>
                    </div>
                </form>
            </Modal>

            <Modal isOpen={!!spentToDelete} onClose={() => setSpentToDelete(null)} title="Excluir Gasto">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                        Tem certeza que deseja excluir este gasto? Essa ação não pode ser desfeita.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setSpentToDelete(null)}
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
                            onClick={confirmDelete}
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
