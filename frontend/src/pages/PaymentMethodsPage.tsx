import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, CreditCard } from 'lucide-react';
import api from '../services/api';
import type { PaymentMethod, PaginatedResponse } from '../types';
import { Modal } from '../components/Modal';

export const PaymentMethodsPage = () => {
    const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingMethod, setEditingMethod] = useState<PaymentMethod | null>(null);

    // Form State
    const [formData, setFormData] = useState({
        key: '',
        display_name: ''
    });

    const fetchData = async (p: number) => {
        setLoading(true);
        try {
            const query = `/payment-methods/?page=${p}&size=10`;
            const response = await api.get<PaginatedResponse<PaymentMethod>>(query);
            setPaymentMethods(response.data.items);
            setTotalPages(response.data.pages);
            setTotalItems(response.data.total);
        } catch (error) {
            console.error("Failed to fetch payment methods", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(page);
    }, [page]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingMethod) {
                await api.put(`/payment-methods/${editingMethod.id}`, formData);
            } else {
                await api.post('/payment-methods/', formData);
            }
            setIsModalOpen(false);
            setEditingMethod(null);
            setFormData({ key: '', display_name: '' });
            fetchData(page);
        } catch (error) {
            console.error("Error saving payment method", error);
            alert("Failed to save payment method. Ensure the key is unique.");
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Tem certeza? This might affect existing spents linked to this payment method.")) return;
        try {
            await api.delete(`/payment-methods/${id}`);
            fetchData(page);
        } catch (error) {
            console.error("Error deleting payment method", error);
            alert("Failed to delete payment method.");
        }
    };

    const openEdit = (method: PaymentMethod) => {
        setEditingMethod(method);
        setFormData({
            key: method.key,
            display_name: method.display_name
        });
        setIsModalOpen(true);
    };

    const openCreate = () => {
        setEditingMethod(null);
        setFormData({ key: '', display_name: '' });
        setIsModalOpen(true);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Métodos de Pagamento</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Manage payment methods and cards</p>
                </div>

                <button
                    onClick={openCreate}
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
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                >
                    <Plus size={20} /> Novo Método de Pagamento
                </button>
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
                        <CreditCard size={24} color="var(--accent-color)" />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, marginBottom: '0.25rem' }}>Total de Métodos de Pagamento</p>
                        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>{totalItems}</h2>
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
                maxHeight: 'calc(100vh - 250px)' // Fixed height to enable scrolling
            }}>
                {loading ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        Carregando métodos de pagamento...
                    </div>
                ) : (
                    <>
                        <div style={{ overflowX: 'auto', overflowY: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{
                                        textAlign: 'left',
                                        borderBottom: '1px solid var(--border-color)',
                                        backgroundColor: 'var(--bg-secondary)', // Opaque background for sticky header
                                        position: 'sticky',
                                        top: 0,
                                        zIndex: 10
                                    }}>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>KEY IDENTIFIER</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>NOME DE EXIBIÇÃO</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>AÇÕES</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {paymentMethods.length === 0 ? (
                                        <tr>
                                            <td colSpan={3} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                                No payment methods found. Create one to get started!
                                            </td>
                                        </tr>
                                    ) : (
                                        paymentMethods.map((pm) => (
                                            <tr key={pm.id} style={{
                                                borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                                transition: 'background-color 0.2s'
                                            }}
                                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)'}
                                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                            >
                                                <td style={{ padding: '1.25rem 1.5rem' }}>
                                                    <span style={{
                                                        fontFamily: 'monospace',
                                                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                                        padding: '0.25rem 0.5rem',
                                                        borderRadius: '4px',
                                                        fontSize: '0.85rem'
                                                    }}>
                                                        {pm.key}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontWeight: 500, fontSize: '1rem' }}>{pm.display_name}</td>
                                                <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                        <button
                                                            onClick={() => openEdit(pm)}
                                                            title="Edit"
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
                                                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(245, 158, 11, 0.2)'}
                                                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(245, 158, 11, 0.1)'}
                                                        >
                                                            <Edit2 size={16} color="#f59e0b" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleDelete(pm.id)}
                                                            title="Delete"
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

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingMethod ? "Editar Método de Pagamento" : "Novo Método de Pagamento"}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Key Identifier</label>
                        <input
                            required
                            className="form-input"
                            value={formData.key}
                            onChange={e => setFormData({ ...formData, key: e.target.value })}
                            placeholder="e.g. itau"
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
                        <small style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.5rem', display: 'block' }}>
                            Unique identifier used by the system (e.g. nubank, itau).
                        </small>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Nome de Exibição</label>
                        <input
                            required
                            className="form-input"
                            value={formData.display_name}
                            onChange={e => setFormData({ ...formData, display_name: e.target.value })}
                            placeholder="e.g. Itaú"
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
                            onClick={() => setIsModalOpen(false)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                backgroundColor: 'transparent',
                                color: 'var(--text-secondary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 500
                            }}
                        >
                            Cancel
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
                                fontWeight: 600,
                                minWidth: '100px'
                            }}
                        >
                            {editingMethod ? "Update" : "Create"}
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
};
