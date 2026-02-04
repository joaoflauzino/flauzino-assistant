import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, Wallet } from 'lucide-react';
import api from '../services/api';
import type { Spent, PaginatedResponse } from '../types';
import { Modal } from '../components/Modal';

export const SpentsPage = () => {
    const [spents, setSpents] = useState<Spent[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingSpent, setEditingSpent] = useState<Spent | null>(null);
    // Helper to get the first and last day of current month
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
        payment_method: '',
        payment_owner: '',
        location: ''
    });

    const fetchData = async (p: number) => {
        setLoading(true);
        try {
            let query = `/spents?page=${p}&size=10`;
            if (startDate) query += `&start_date=${startDate}`;
            if (endDate) query += `&end_date=${endDate}`;

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
        fetchData(page);
    }, [page]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                amount: parseFloat(formData.amount)
            };

            if (editingSpent) {
                await api.patch(`/spents/${editingSpent.id}`, payload);
            } else {
                await api.post('/spents', payload);
            }
            setIsModalOpen(false);
            setEditingSpent(null);
            setFormData({ category: '', amount: '', payment_method: '', payment_owner: '', location: '' });
            fetchData(page);
        } catch (error) {
            console.error("Error saving spent", error);
            alert("Failed to save spent");
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure?")) return;
        try {
            await api.delete(`/spents/${id}`);
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
            payment_method: spent.payment_method,
            payment_owner: spent.payment_owner,
            location: spent.location
        });
        setIsModalOpen(true);
    };

    const openCreate = () => {
        setEditingSpent(null);
        setFormData({ category: '', amount: '', payment_method: '', payment_owner: '', location: '' });
        setIsModalOpen(true);
    };

    const handleFilter = (e?: React.FormEvent) => {
        e?.preventDefault();
        setPage(1); // Reset to first page when filtering
        fetchData(1);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Spents</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Track and manage your expenses</p>
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <form onSubmit={handleFilter} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', fontWeight: 500 }}>Start Date</label>
                            <input
                                type="date"
                                value={startDate}
                                onChange={e => setStartDate(e.target.value)}
                                style={{
                                    padding: '0.6rem 0.8rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-tertiary)',
                                    color: 'white',
                                    fontSize: '0.9rem',
                                    transition: 'all 0.2s',
                                    cursor: 'pointer'
                                }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', fontWeight: 500 }}>End Date</label>
                            <input
                                type="date"
                                value={endDate}
                                onChange={e => setEndDate(e.target.value)}
                                style={{
                                    padding: '0.6rem 0.8rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-tertiary)',
                                    color: 'white',
                                    fontSize: '0.9rem',
                                    transition: 'all 0.2s',
                                    cursor: 'pointer'
                                }}
                            />
                        </div>
                        <button
                            type="submit"
                            style={{
                                backgroundColor: 'var(--accent-color)',
                                color: 'white',
                                height: '38px',
                                padding: '0 1.5rem',
                                borderRadius: '8px',
                                border: 'none',
                                fontWeight: 600,
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-1px)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                        >
                            Filter
                        </button>
                    </form>

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
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, marginBottom: '0.25rem' }}>Total Spents Found</p>
                        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0 }}>{totalItems}</h2>
                    </div>
                </div>
                {/* Optional: Add more stats here like "Total Amount" if we had that from API */}
            </div>

            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                overflow: 'hidden',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                display: 'flex',
                flexDirection: 'column',
                maxHeight: 'calc(100vh - 280px)' // Fixed height to enable scrolling
            }}>
                {loading ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        Loading spents...
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
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CATEGORY</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>AMOUNT</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>METHOD</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>OWNER</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>LOCATION</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>DATE</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>ACTIONS</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {spents.map((s) => (
                                        <tr key={s.id} style={{
                                            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                            transition: 'background-color 0.2s'
                                        }}
                                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)'}
                                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                        >
                                            <td style={{ padding: '1.25rem 1.5rem' }}>
                                                <span style={{
                                                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                                    padding: '0.25rem 0.6rem',
                                                    borderRadius: '4px',
                                                    fontSize: '0.85rem',
                                                    fontWeight: 500
                                                }}>
                                                    {s.category}
                                                </span>
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem', fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary)' }}>
                                                R$ {s.amount.toFixed(2)}
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>{s.payment_method}</td>
                                            <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>{s.payment_owner}</td>
                                            <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>{s.location}</td>
                                            <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)' }}>{new Date(s.created_at).toLocaleDateString()}</td>
                                            <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                    <button
                                                        onClick={() => openEdit(s)}
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
                                                        onClick={() => handleDelete(s.id)}
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
                                    ))}
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
                                    Showing page {page} of {totalPages}
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
                                        <ChevronLeft size={16} /> Previous
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
                                        Next <ChevronRight size={16} />
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
                    <Plus size={22} /> New Spent
                </button>
            </div>

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingSpent ? "Edit Spent" : "New Spent"}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Category</label>
                        <input
                            required
                            className="form-input"
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                            placeholder="e.g. food"
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
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Amount (R$)</label>
                        <input
                            required
                            type="number"
                            step="0.01"
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
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Method</label>
                            <input
                                required
                                value={formData.payment_method}
                                onChange={e => setFormData({ ...formData, payment_method: e.target.value })}
                                placeholder="e.g. Credit Card"
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
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Owner</label>
                            <input
                                required
                                value={formData.payment_owner}
                                onChange={e => setFormData({ ...formData, payment_owner: e.target.value })}
                                placeholder="e.g. Joao"
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
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Location</label>
                        <input
                            required
                            value={formData.location}
                            onChange={e => setFormData({ ...formData, location: e.target.value })}
                            placeholder="e.g. Supermarket"
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
                            {editingSpent ? "Update" : "Create"}
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
};
