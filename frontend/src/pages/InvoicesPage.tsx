import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Edit2, CheckCircle, RotateCcw } from 'lucide-react';
import api from '../services/api';
import type { Invoice, PaymentMethod } from '../types';
import { Modal } from '../components/Modal';

export const InvoicesPage = () => {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [paymentMethods, setPaymentMethods] = useState<Record<string, PaymentMethod>>({});
    const [loading, setLoading] = useState(true);
    const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
    
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
    const [newClosingDate, setNewClosingDate] = useState('');
    const [newDueDate, setNewDueDate] = useState('');
    const [newStatus, setNewStatus] = useState('OPEN');
    const [payingKey, setPayingKey] = useState<string | null>(null);
    const [reopeningKey, setReopeningKey] = useState<string | null>(null);

    const referenceMonth = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}`;
    const displayMonth = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' }).format(currentMonth);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [invoicesRes, pmRes] = await Promise.all([
                api.get<Invoice[]>(`/invoices/${referenceMonth}`),
                api.get('/payment-methods/?page=1&size=100')
            ]);
            setInvoices(invoicesRes.data);
            
            const pmMap: Record<string, PaymentMethod> = {};
            pmRes.data.items.forEach((pm: PaymentMethod) => {
                pmMap[pm.key] = pm;
            });
            setPaymentMethods(pmMap);
        } catch (error) {
            console.error("Failed to fetch invoices", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [referenceMonth]);

    const handleUpdateDates = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingInvoice) return;
        
        try {
            await api.put(`/invoices/${editingInvoice.payment_method_key}/${referenceMonth}`, {
                closing_date: newClosingDate || null,
                due_date: newDueDate || null,
                status: newStatus || null
            });
            setIsModalOpen(false);
            setEditingInvoice(null);
            fetchData();
        } catch (error) {
            console.error("Error updating invoice dates", error);
        }
    };

    const handlePayInvoice = async (paymentMethodKey: string) => {
        setPayingKey(paymentMethodKey);
        try {
            await api.post(`/invoices/${paymentMethodKey}/${referenceMonth}/pay`);
            await fetchData();
        } catch (error) {
            console.error("Error marking invoice as paid", error);
        } finally {
            setPayingKey(null);
        }
    };

    const handleReopenInvoice = async (paymentMethodKey: string) => {
        setReopeningKey(paymentMethodKey);
        try {
            await api.post(`/invoices/${paymentMethodKey}/${referenceMonth}/reopen`);
            await fetchData();
        } catch (error) {
            console.error("Error reopening invoice", error);
        } finally {
            setReopeningKey(null);
        }
    };

    const openEdit = (invoice: Invoice) => {
        setEditingInvoice(invoice);
        setNewClosingDate(invoice.real_closing_date);
        setNewDueDate(invoice.real_due_date);
        setNewStatus(invoice.status || 'OPEN');
        setIsModalOpen(true);
    };

    const prevMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
    };
    const nextMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
    };

    const renderStatusBadge = (status: string) => {
        const s = status ? status.toUpperCase() : 'OPEN';
        if (s === 'PAID') {
            return (
                <span style={{
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#10b981',
                    padding: '0.3rem 0.75rem',
                    borderRadius: '16px',
                    fontWeight: 600,
                    fontSize: '0.85rem'
                }}>
                    Paga
                </span>
            );
        }
        if (s === 'CLOSED') {
            return (
                <span style={{
                    backgroundColor: 'rgba(245, 158, 11, 0.15)',
                    color: '#f59e0b',
                    padding: '0.3rem 0.75rem',
                    borderRadius: '16px',
                    fontWeight: 600,
                    fontSize: '0.85rem'
                }}>
                    Fechada
                </span>
            );
        }
        return (
            <span style={{
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                color: '#3b82f6',
                padding: '0.3rem 0.75rem',
                borderRadius: '16px',
                fontWeight: 600,
                fontSize: '0.85rem'
            }}>
                Em Aberto
            </span>
        );
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Faturas</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Acompanhe o fechamento, vencimento e status das faturas de cartão de crédito</p>
                </div>
                
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '0.5rem',
                    borderRadius: '12px',
                    border: '1px solid var(--border-color)'
                }}>
                    <button onClick={prevMonth} style={{ padding: '0.5rem', background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}>
                        <ChevronLeft size={20} />
                    </button>
                    <span style={{ fontWeight: 600, minWidth: '120px', textAlign: 'center', textTransform: 'capitalize' }}>
                        {displayMonth}
                    </span>
                    <button onClick={nextMonth} style={{ padding: '0.5rem', background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}>
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                overflow: 'hidden',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
            }}>
                {loading ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        Carregando faturas...
                    </div>
                ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-color)', backgroundColor: 'rgba(255, 255, 255, 0.02)' }}>
                                <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CARTÃO</th>
                                <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>STATUS</th>
                                <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>DATA DE FECHAMENTO REAL</th>
                                <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>VENCIMENTO REAL</th>
                                <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>AÇÕES</th>
                            </tr>
                        </thead>
                        <tbody>
                            {invoices.length === 0 ? (
                                <tr>
                                    <td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                        Nenhuma fatura de cartão de crédito encontrada.
                                    </td>
                                </tr>
                            ) : (
                                invoices.map((inv) => {
                                    const pm = paymentMethods[inv.payment_method_key];
                                    const isPaid = inv.status?.toUpperCase() === 'PAID';
                                    const isPaying = payingKey === inv.payment_method_key;
                                    const isReopening = reopeningKey === inv.payment_method_key;

                                    return (
                                        <tr key={inv.payment_method_key} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                                            <td style={{ padding: '1.25rem 1.5rem', fontWeight: 500 }}>
                                                {pm?.display_name || inv.payment_method_key}
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem' }}>
                                                {renderStatusBadge(inv.status)}
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem' }}>
                                                <span style={{ 
                                                    backgroundColor: 'rgba(99, 102, 241, 0.1)', 
                                                    color: 'var(--accent-color)', 
                                                    padding: '0.25rem 0.75rem', 
                                                    borderRadius: '16px',
                                                    fontWeight: 600,
                                                    fontSize: '0.9rem'
                                                }}>
                                                    {inv.real_closing_date}
                                                </span>
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                                                {inv.real_due_date}
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                                                    {isPaid ? (
                                                        <button
                                                            onClick={() => handleReopenInvoice(inv.payment_method_key)}
                                                            disabled={isReopening}
                                                            title="Desfazer Pagamento (Reabrir Fatura)"
                                                            style={{
                                                                padding: '0.5rem 0.75rem',
                                                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                                                borderRadius: '8px',
                                                                cursor: isReopening ? 'not-allowed' : 'pointer',
                                                                color: '#ef4444',
                                                                fontWeight: 600,
                                                                fontSize: '0.85rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '0.35rem',
                                                                transition: 'all 0.2s',
                                                                opacity: isReopening ? 0.6 : 1
                                                            }}
                                                        >
                                                            <RotateCcw size={15} color="#ef4444" />
                                                            {isReopening ? 'Reabrindo...' : 'Desfazer'}
                                                        </button>
                                                    ) : (
                                                        <button
                                                            onClick={() => handlePayInvoice(inv.payment_method_key)}
                                                            disabled={isPaying}
                                                            title="Marcar como Paga"
                                                            style={{
                                                                padding: '0.5rem 0.75rem',
                                                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                                                border: '1px solid rgba(16, 185, 129, 0.2)',
                                                                borderRadius: '8px',
                                                                cursor: isPaying ? 'not-allowed' : 'pointer',
                                                                color: '#10b981',
                                                                fontWeight: 600,
                                                                fontSize: '0.85rem',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '0.35rem',
                                                                transition: 'all 0.2s',
                                                                opacity: isPaying ? 0.6 : 1
                                                            }}
                                                        >
                                                            <CheckCircle size={15} color="#10b981" />
                                                            {isPaying ? 'Salvando...' : 'Pagar Fatura'}
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => openEdit(inv)}
                                                        title="Editar Datas e Status da Fatura"
                                                        style={{
                                                            padding: '0.5rem',
                                                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                                            border: '1px solid rgba(245, 158, 11, 0.2)',
                                                            borderRadius: '8px',
                                                            cursor: 'pointer',
                                                            transition: 'all 0.2s',
                                                        }}
                                                    >
                                                        <Edit2 size={16} color="#f59e0b" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                )}
            </div>

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Editar Fatura">
                <form onSubmit={handleUpdateDates} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
                        Ajuste as datas reais e status da fatura de <strong>{paymentMethods[editingInvoice?.payment_method_key || '']?.display_name || editingInvoice?.payment_method_key}</strong> ({referenceMonth}).
                    </p>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                Data de Fechamento Real
                            </label>
                            <input
                                type="date"
                                required
                                value={newClosingDate}
                                onChange={e => setNewClosingDate(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.9rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'white'
                                }}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                                Data de Vencimento Real
                            </label>
                            <input
                                type="date"
                                required
                                value={newDueDate}
                                onChange={e => setNewDueDate(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.9rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'white'
                                }}
                            />
                        </div>
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            Status da Fatura
                        </label>
                        <select
                            value={newStatus}
                            onChange={e => setNewStatus(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.9rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'white',
                                fontSize: '0.95rem'
                            }}
                        >
                            <option value="OPEN">Em Aberto (OPEN)</option>
                            <option value="CLOSED">Fechada (CLOSED)</option>
                            <option value="PAID">Paga (PAID)</option>
                        </select>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <button
                            type="button"
                            onClick={() => setIsModalOpen(false)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                backgroundColor: 'transparent',
                                color: 'var(--text-secondary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '8px',
                                cursor: 'pointer'
                            }}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            style={{
                                padding: '0.75rem 1.5rem',
                                backgroundColor: 'var(--accent-color)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600
                            }}
                        >
                            Salvar Alterações
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
};
