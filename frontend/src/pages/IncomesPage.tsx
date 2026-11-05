import { Button } from '../components/Button';
import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, TrendingUp } from 'lucide-react';
import api from '../services/api';
import type { Income, PaginatedResponse, IncomeCategory, Account } from '../types';
import { Modal } from '../components/Modal';

export const IncomesPage = () => {
    const [incomes, setIncomes] = useState<Income[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingIncome, setEditingIncome] = useState<Income | null>(null);
    const [incomeToDelete, setIncomeToDelete] = useState<string | null>(null);

    // Options States
    const [categories, setCategories] = useState<IncomeCategory[]>([]);
    const [accounts, setAccounts] = useState<Account[]>([]);

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
        description: '',
        amount: '',
        category: '',
        payment_method: '',
        received_at: monthDates.end,
        competence_date: ''
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
            let query = `/incomes/?page=${p}&size=10`;
            if (sDate) query += `&start_date=${sDate}`;
            if (eDate) query += `&end_date=${eDate}`;

            const response = await api.get<PaginatedResponse<Income>>(query);
            setIncomes(response.data.items);
            setTotalPages(response.data.pages);
            setTotalItems(response.data.total);
        } catch (error) {
            console.error("Failed to fetch incomes", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const [catRes, accRes] = await Promise.all([
                    api.get<PaginatedResponse<IncomeCategory>>('/income-categories/?size=1000'),
                    api.get<PaginatedResponse<Account>>('/accounts/?size=1000')
                ]);
                setCategories(catRes.data.items);
                setAccounts(accRes.data.items);
            } catch (error) {
                console.error("Failed to fetch options", error);
            }
        };
        fetchOptions();
    }, []);

    useEffect(() => {
        fetchData(page);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [page]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload: Record<string, unknown> = {
                description: formData.description,
                amount: parseFloat(formData.amount),
                category: formData.category,
                payment_method: formData.payment_method || null,
                received_at: new Date(formData.received_at + 'T12:00:00Z').toISOString(),
                competence_date: formData.competence_date || null
            };

            if (editingIncome) {
                await api.patch(`/incomes/${editingIncome.id}`, payload);
            } else {
                await api.post('/incomes/', payload);
            }
            setIsModalOpen(false);
            setEditingIncome(null);
            setFormData({ description: '', amount: '', category: '', payment_method: '', received_at: monthDates.end, competence_date: '' });
            fetchData(page);
        } catch (error) {
            console.error("Failed to save income", error);
        }
    };

    const handleEdit = (income: Income) => {
        setEditingIncome(income);
        setFormData({
            description: income.description,
            amount: income.amount.toString(),
            category: income.category,
            payment_method: income.payment_method || '',
            received_at: income.received_at ? income.received_at.split('T')[0] : monthDates.end,
            competence_date: income.competence_date ? income.competence_date.split('T')[0] : ''
        });
        setIsModalOpen(true);
    };

    const handleDelete = async () => {
        if (!incomeToDelete) return;
        try {
            await api.delete(`/incomes/${incomeToDelete}`);
            setIncomeToDelete(null);
            fetchData(page);
        } catch (error) {
            console.error("Failed to delete income", error);
        }
    };

    const handleFilterSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        fetchData(1);
    };

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
    };

    return (
        <div>
            {/* Header */}
            <div className="ui-page-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <TrendingUp size={28} color="var(--success)" />
                        Receitas e Entradas
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                        Controle seus salários, rendimentos, pix recebidos e outras entradas financeiras
                    </p>
                </div>
                <Button variant="success"
                    onClick={() => {
                        setEditingIncome(null);
                        setFormData({ description: '', amount: '', category: '', payment_method: '', received_at: monthDates.end, competence_date: '' });
                        setIsModalOpen(true);
                    }}

                >
                    <Plus size={20} />
                    Nova Receita
                </Button>
            </div>

            {/* Filtros de Data */}
            <form onSubmit={handleFilterSubmit} className="ui-filter-form" style={{
                display: 'flex',
                gap: '1rem',
                alignItems: 'flex-end',
                backgroundColor: 'var(--bg-secondary)',
                padding: '1.25rem 1.5rem',
                borderRadius: '12px',
                marginBottom: '1.5rem',
                flexWrap: 'wrap',
                border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
                <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Data Inicial
                    </label>
                    <input
                        type="date"
                        value={startDate}
                        onChange={e => setStartDate(e.target.value)}
                        style={{ border: '1px solid var(--border-color)', color: 'white' }}
                    />
                </div>
                <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Data Final
                    </label>
                    <input
                        type="date"
                        value={endDate}
                        onChange={e => setEndDate(e.target.value)}
                        style={{ border: '1px solid var(--border-color)', color: 'white' }}
                    />
                </div>
                <Button variant="primary"
                    type="submit"

                >
                    Filtrar
                </Button>
                <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <Button
                        type="button"
                        onClick={() => handleSetPeriod('current')}
                        style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                    >
                        Mês Atual
                    </Button>
                    <Button
                        type="button"
                        onClick={() => handleSetPeriod('90days')}
                        style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                    >
                        Últimos 90 dias
                    </Button>
                    <Button
                        type="button"
                        onClick={() => handleSetPeriod('all')}
                        style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                    >
                        Ver Todos
                    </Button>
                </div>
            </form>

            {/* Table */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '12px',
                overflow: 'hidden',
                border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                            <th style={{ padding: '1rem' }}>Data</th>
                            <th style={{ padding: '1rem' }}>Descrição</th>
                            <th style={{ padding: '1rem' }}>Categoria</th>
                            <th style={{ padding: '1rem' }}>Conta de Destino</th>
                            <th style={{ padding: '1rem' }}>Valor</th>
                            <th style={{ padding: '1rem', textAlign: 'center' }}>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr>
                                <td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                    Carregando receitas...
                                </td>
                            </tr>
                        ) : incomes.length === 0 ? (
                            <tr>
                                <td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                    Nenhuma receita encontrada para o período.
                                </td>
                            </tr>
                        ) : (
                            incomes.map(income => (
                                <tr key={income.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={{ padding: '1rem' }}>
                                        <div>{new Date(income.received_at).toLocaleDateString('pt-BR')}</div>
                                        {income.competence_date && (
                                            <div style={{ fontSize: '0.75rem', color: '#a5b4fc', marginTop: '0.2rem' }}>
                                                Comp: {new Date(income.competence_date + 'T12:00:00').toLocaleDateString('pt-BR')}
                                            </div>
                                        )}
                                    </td>
                                    <td style={{ padding: '1rem', fontWeight: 500 }}>{income.description}</td>
                                    <td style={{ padding: '1rem' }}>
                                        <span style={{
                                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                            padding: '0.25rem 0.5rem',
                                            borderRadius: '4px',
                                            fontSize: '0.85rem'
                                        }}>
                                            {income.category}
                                        </span>
                                    </td>
                                    <td style={{ padding: '1rem', color: 'var(--accent-color)', fontWeight: 500 }}>
                                        {income.payment_method || '-'}
                                    </td>
                                    <td style={{ padding: '1rem', fontWeight: 600, color: 'var(--success)' }}>
                                        {formatCurrency(income.amount)}
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'center' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                                            <Button
                                                onClick={() => handleEdit(income)}
                                                style={{ background: 'transparent', border: 'none', color: 'var(--accent-color)' }}
                                                title="Editar"
                                            >
                                                <Edit2 size={16} />
                                            </Button>
                                            <Button
                                                onClick={() => setIncomeToDelete(income.id)}
                                                style={{ background: 'transparent', border: 'none', color: 'var(--danger)' }}
                                                title="Excluir"
                                            >
                                                <Trash2 size={16} />
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>

                {/* Paginação */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '1rem',
                    color: 'var(--text-secondary)',
                    fontSize: '0.9rem'
                }}>
                    <span>Total: {totalItems} receitas</span>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <Button
                            disabled={page === 1}
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            title="Página anterior"
                            style={{ background: 'transparent', border: '1px solid var(--border-color)', color: page === 1 ? 'var(--text-secondary)' : 'white' }}
                        >
                            <ChevronLeft size={16} />
                        </Button>
                        <span>Página {page} de {totalPages || 1}</span>
                        <Button
                            disabled={page >= totalPages}
                            onClick={() => setPage(p => p + 1)}
                            title="Próxima página"
                            style={{ background: 'transparent', border: '1px solid var(--border-color)', color: page >= totalPages ? 'var(--text-secondary)' : 'white' }}
                        >
                            <ChevronRight size={16} />
                        </Button>
                    </div>
                </div>
            </div>

            {/* Modal de Criação / Edição */}
            <Modal
                isOpen={isModalOpen}
                onClose={() => {
                    setIsModalOpen(false);
                    setEditingIncome(null);
                }}
                title={editingIncome ? "Editar Receita" : "Nova Receita"}
            >
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Descrição</label>
                        <input
                            type="text"
                            required
                            placeholder="Ex: Salário Mensal, Pix de Cliente"
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Valor (R$)</label>
                        <input
                            type="number"
                            step="0.01"
                            required
                            placeholder="0.00"
                            value={formData.amount}
                            onChange={e => setFormData({ ...formData, amount: e.target.value })}
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Categoria</label>
                        <select
                            required
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        >
                            <option value="">Selecione uma categoria</option>
                            {categories.map(c => (
                                <option key={c.id} value={c.key}>{c.display_name}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Conta Bancária de Recebimento</label>
                        <select
                            value={formData.payment_method}
                            onChange={e => setFormData({ ...formData, payment_method: e.target.value })}
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        >
                            <option value="">Não especificado / Outro</option>
                            {accounts.map(a => (
                                <option key={a.id} value={a.key}>{a.name} ({a.bank})</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Data de Recebimento</label>
                        <input
                            type="date"
                            required
                            value={formData.received_at}
                            onChange={e => setFormData({ ...formData, received_at: e.target.value })}
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            Data de Competência (Opcional - mês de planejamento)
                        </label>
                        <input
                            type="date"
                            value={formData.competence_date}
                            onChange={e => setFormData({ ...formData, competence_date: e.target.value })}
                            placeholder="Vazio = data de recebimento"
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                        <Button
                            type="button"
                            onClick={() => {
                                setIsModalOpen(false);
                                setEditingIncome(null);
                            }}

                        >
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            style={{ border: 'none', background: 'var(--success)', color: 'white' }}
                        >
                            Salvar
                        </Button>
                    </div>
                </form>
            </Modal>

            {/* Modal de Exclusão */}
            <Modal
                isOpen={!!incomeToDelete}
                onClose={() => setIncomeToDelete(null)}
                title="Excluir Receita"
            >
                <div>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                        Tem certeza que deseja excluir esta receita? Esta ação não pode ser desfeita.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                        <Button
                            onClick={() => setIncomeToDelete(null)}

                        >
                            Cancelar
                        </Button>
                        <Button
                            onClick={handleDelete}
                            style={{ border: 'none', background: 'var(--danger)', color: 'white' }}
                        >
                            Excluir
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
};
