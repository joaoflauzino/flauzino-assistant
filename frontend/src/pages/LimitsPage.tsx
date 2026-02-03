import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight } from 'lucide-react';
import api from '../services/api';
import type { SpendingLimit, PaginatedResponse } from '../types';
import { Modal } from '../components/Modal';

export const LimitsPage = () => {
    const [limits, setLimits] = useState<SpendingLimit[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingLimit, setEditingLimit] = useState<SpendingLimit | null>(null);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    const [formData, setFormData] = useState({
        category: '',
        amount: ''
    });

    const fetchData = async (p: number) => {
        setLoading(true);
        try {
            let query = `/limits?page=${p}&size=10`;
            if (startDate) query += `&start_date=${startDate}`;
            if (endDate) query += `&end_date=${endDate}`;

            const response = await api.get<PaginatedResponse<SpendingLimit>>(query);
            setLimits(response.data.items);
            setTotalPages(response.data.pages);
        } catch (error) {
            console.error("Failed to fetch limits", error);
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

            if (editingLimit) {
                await api.patch(`/limits/${editingLimit.id}`, payload);
            } else {
                await api.post('/limits', payload);
            }
            setIsModalOpen(false);
            setEditingLimit(null);
            setFormData({ category: '', amount: '' });
            fetchData(page);
        } catch (error) {
            console.error("Error saving limit", error);
            alert("Failed to save limit");
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure?")) return;
        try {
            await api.delete(`/limits/${id}`);
            fetchData(page);
        } catch (error) {
            console.error("Error deleting limit", error);
        }
    };

    const openEdit = (limit: SpendingLimit) => {
        setEditingLimit(limit);
        setFormData({
            category: limit.category,
            amount: limit.amount.toString()
        });
        setIsModalOpen(true);
    };

    const openCreate = () => {
        setEditingLimit(null);
        setFormData({ category: '', amount: '' });
        setIsModalOpen(true);
    };

    const handleFilter = (e?: React.FormEvent) => {
        e?.preventDefault();
        setPage(1);
        fetchData(1);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1>Limits</h1>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <form onSubmit={handleFilter} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
                        <div>
                            <input
                                type="date"
                                value={startDate}
                                onChange={e => setStartDate(e.target.value)}
                                style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-tertiary)', color: 'white' }}
                            />
                        </div>
                        <div>
                            <input
                                type="date"
                                value={endDate}
                                onChange={e => setEndDate(e.target.value)}
                                style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-tertiary)', color: 'white' }}
                            />
                        </div>
                        <button type="submit" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'white', height: '38px', border: '1px solid var(--border-color)' }}>Filter</button>
                    </form>
                    <button
                        onClick={openCreate}
                        style={{
                            backgroundColor: 'var(--accent-color)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            height: '38px'
                        }}
                    >
                        <Plus size={20} /> New Limit
                    </button>
                </div>
            </div>

            {loading ? (
                <p>Loading...</p>
            ) : (
                <>
                    <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '2rem' }}>
                        <thead>
                            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                                <th style={{ padding: '1rem' }}>Category</th>
                                <th style={{ padding: '1rem' }}>Limit Amount</th>
                                <th style={{ padding: '1rem', textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {limits.map((l) => (
                                <tr key={l.id} style={{ borderBottom: '1px solid var(--bg-tertiary)' }}>
                                    <td style={{ padding: '1rem' }}>{l.category}</td>
                                    <td style={{ padding: '1rem', fontWeight: 'bold' }}>R$ {l.amount.toFixed(2)}</td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                            <button onClick={() => openEdit(l)} style={{ padding: '0.4rem', backgroundColor: 'transparent' }}><Edit2 size={18} color="var(--warning)" /></button>
                                            <button onClick={() => handleDelete(l.id)} style={{ padding: '0.4rem', backgroundColor: 'transparent' }}><Trash2 size={18} color="var(--danger)" /></button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', alignItems: 'center' }}>
                        <button disabled={page === 1} onClick={() => setPage(page - 1)} style={{ display: 'flex', alignItems: 'center' }}>
                            <ChevronLeft size={20} /> Previous
                        </button>
                        <span>Page {page} of {totalPages}</span>
                        <button disabled={page === totalPages} onClick={() => setPage(page + 1)} style={{ display: 'flex', alignItems: 'center' }}>
                            Next <ChevronRight size={20} />
                        </button>
                    </div>
                </>
            )}

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingLimit ? "Edit Limit" : "New Limit"}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Category</label>
                        <input
                            required
                            className="form-input"
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                            placeholder="e.g. food"
                            style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'white' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Amount</label>
                        <input
                            required
                            type="number"
                            step="0.01"
                            className="form-input"
                            value={formData.amount}
                            onChange={e => setFormData({ ...formData, amount: e.target.value })}
                            placeholder="0.00"
                            style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'white' }}
                        />
                    </div>

                    <button type="submit" style={{ marginTop: '1rem', backgroundColor: 'var(--accent-color)', color: 'white' }}>
                        {editingLimit ? "Update" : "Create"}
                    </button>
                </form>
            </Modal>
        </div>
    );
};
