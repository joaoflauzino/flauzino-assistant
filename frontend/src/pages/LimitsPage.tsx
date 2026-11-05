import { Button } from '../components/Button';
import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, PiggyBank } from 'lucide-react';
import api from '../services/api';
import type { SpendingLimit, PaginatedResponse, Category } from '../types';
import { Modal } from '../components/Modal';

export const LimitsPage = () => {
    const [limits, setLimits] = useState<SpendingLimit[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingLimit, setEditingLimit] = useState<SpendingLimit | null>(null);
    const [itemToDelete, setItemToDelete] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        category: '',
        amount: ''
    });

    const categoryMap = categories.reduce((acc, cat) => {
        acc[cat.key] = cat.display_name;
        return acc;
    }, {} as Record<string, string>);

    const fetchData = async (p: number) => {
        setLoading(true);
        try {
            const query = `/limits/?page=${p}&size=10`;

            const response = await api.get<PaginatedResponse<SpendingLimit>>(query);
            setLimits(response.data.items);
            setTotalPages(response.data.pages);
            setTotalItems(response.data.total);
        } catch (error) {
            console.error("Failed to fetch limits", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const res = await api.get<PaginatedResponse<Category>>('/categories/?size=1000');
                setCategories(res.data.items);
            } catch (error) {
                console.error("Failed to fetch categories", error);
            }
        };
        fetchCategories();
    }, []);

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
                await api.post('/limits/', payload);
            }
            setIsModalOpen(false);
            setEditingLimit(null);
            setFormData({ category: '', amount: '' });
            fetchData(page);
        } catch (error) {
            console.error("Error saving limit", error);
        }
    };

    const handleDelete = (id: string) => {
        setItemToDelete(id);
    };

    const confirmDelete = async () => {
        if (!itemToDelete) return;
        try {
            await api.delete(`/limits/${itemToDelete}`);
            setItemToDelete(null);
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

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Limites</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Set budget goals for categories</p>
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <Button variant="primary"
                        onClick={openCreate}


                    >
                        <Plus size={20} /> Novo Limite
                    </Button>
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
                        <PiggyBank size={24} color="var(--accent-color)" />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, marginBottom: '0.25rem' }}>Active Limits</p>
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
                maxHeight: 'calc(100vh - 280px)' // Fixed height to enable scrolling
            }}>
                {loading ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        Carregando limites...
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
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>CATEGORIA</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem' }}>LIMIT AMOUNT</th>
                                        <th style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.9rem', textAlign: 'right' }}>AÇÕES</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {limits.map((l) => (
                                        <tr key={l.id} style={{
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
                                                    {categoryMap[l.category] || l.category}
                                                </span>
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem', fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary)' }}>
                                                R$ {l.amount.toFixed(2)}
                                            </td>
                                            <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                    <Button
                                                        type="button"
                                                        onClick={(e) => { e.stopPropagation(); openEdit(l); }}
                                                        title="Editar limite"
                                                        style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)' }}

                                                    >
                                                        <Edit2 size={16} color="#f59e0b" />
                                                    </Button>
                                                    <Button
                                                        type="button"
                                                        onClick={(e) => { e.stopPropagation(); handleDelete(l.id); }}
                                                        title="Excluir limite"
                                                        style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)' }}

                                                    >
                                                        <Trash2 size={16} color="#ef4444" />
                                                    </Button>
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
                                    Mostrando página {page} de {totalPages}
                                </span>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <Button
                                        disabled={page === 1}
                                        onClick={() => setPage(page - 1)}
                                        style={{ border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-primary)' }}
                                    >
                                        <ChevronLeft size={16} /> Anterior
                                    </Button>
                                    <Button
                                        disabled={page === totalPages}
                                        onClick={() => setPage(page + 1)}
                                        style={{ border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-primary)' }}
                                    >
                                        Próximo <ChevronRight size={16} />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingLimit ? "Editar Limite" : "Novo Limite"}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Categoria</label>
                        <select
                            required
                            className="form-input"
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white', appearance: 'none' }}
                        >
                            <option value="" disabled>Selecione uma categoria...</option>
                            {formData.category && !categories.some(c => c.key === formData.category) && (
                                <option value={formData.category}>{formData.category}</option>
                            )}
                            {categories.map(c => (
                                <option key={c.id} value={c.key}>{c.display_name}</option>
                            ))}
                        </select>
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
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <Button
                            type="button"
                            onClick={() => setIsModalOpen(false)}
                            style={{ backgroundColor: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                        >
                            Cancel
                        </Button>
                        <Button variant="primary"
                            type="submit"
                            style={{ minWidth: '100px' }}
                        >
                            {editingLimit ? "Update" : "Create"}
                        </Button>
                    </div>
                </form>
            </Modal>

            <Modal isOpen={!!itemToDelete} onClose={() => setItemToDelete(null)} title="Confirmar Exclusão">
                <div style={{ padding: '1rem 0' }}>
                    <p style={{ color: 'var(--text-primary)', fontSize: '1rem', marginBottom: '2rem' }}>
                        Tem certeza que deseja excluir este limite? Essa ação não pode ser desfeita.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <Button type="button" onClick={() => setItemToDelete(null)} style={{ backgroundColor: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}>Cancelar</Button>
                        <Button variant="danger" type="button" onClick={confirmDelete} style={{ minWidth: '100px' }}>Excluir</Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
};
