import { Button } from '../components/Button';
import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronLeft, ChevronRight, Tags } from 'lucide-react';
import api from '../services/api';
import type { Category, PaginatedResponse } from '../types';
import { Modal } from '../components/Modal';

export const CategoriesPage = () => {
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState<Category | null>(null);
    const [itemToDelete, setItemToDelete] = useState<string | null>(null);

    // Form State
    const [formData, setFormData] = useState({
        key: '',
        display_name: ''
    });

    const fetchData = async (p: number) => {
        setLoading(true);
        try {
            const query = `/categories/?page=${p}&size=10`;
            const response = await api.get<PaginatedResponse<Category>>(query);
            setCategories(response.data.items);
            setTotalPages(response.data.pages);
            setTotalItems(response.data.total);
        } catch (error) {
            console.error("Failed to fetch categories", error);
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
            if (editingCategory) {
                await api.put(`/categories/${editingCategory.id}`, formData);
            } else {
                await api.post('/categories/', formData);
            }
            setIsModalOpen(false);
            setEditingCategory(null);
            setFormData({ key: '', display_name: '' });
            fetchData(page);
        } catch (error) {
            console.error("Error saving category", error);
        }
    };

    const handleDelete = (id: string) => {
        setItemToDelete(id);
    };

    const confirmDelete = async () => {
        if (!itemToDelete) return;
        try {
            await api.delete(`/categories/${itemToDelete}`);
            setItemToDelete(null);
            fetchData(page);
        } catch (error) {
            console.error("Error deleting category", error);
        }
    };

    const openEdit = (category: Category) => {
        setEditingCategory(category);
        setFormData({
            key: category.key,
            display_name: category.display_name
        });
        setIsModalOpen(true);
    };

    const openCreate = () => {
        setEditingCategory(null);
        setFormData({ key: '', display_name: '' });
        setIsModalOpen(true);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: 0 }}>Categorias</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Gerencie suas categorias de gastos</p>
                </div>

                <Button variant="primary"
                    onClick={openCreate}


                >
                    <Plus size={20} /> Nova Categoria
                </Button>
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
                        <Tags size={24} color="var(--accent-color)" />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, marginBottom: '0.25rem' }}>Total de Categorias</p>
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
                        Carregando categorias...
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
                                    {categories.length === 0 ? (
                                        <tr>
                                            <td colSpan={3} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                                Nenhuma categoria encontrada. Crie uma para começar!
                                            </td>
                                        </tr>
                                    ) : (
                                        categories.map((c) => (
                                            <tr key={c.id} style={{
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
                                                        {c.key}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '1.25rem 1.5rem', fontWeight: 500, fontSize: '1rem' }}>{c.display_name}</td>
                                                <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                                    <Button
                                                        type="button"
                                                        onClick={(e) => { e.stopPropagation(); openEdit(c); }}
                                                        title="Editar"
                                                        style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)' }}

                                                    >
                                                        <Edit2 size={16} color="#f59e0b" />
                                                    </Button>
                                                    <Button
                                                        type="button"
                                                        onClick={(e) => { e.stopPropagation(); handleDelete(c.id); }}
                                                        title="Excluir"
                                                        style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)' }}

                                                    >
                                                        <Trash2 size={16} color="#ef4444" />
                                                    </Button>
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

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingCategory ? "Editar Categoria" : "Nova Categoria"}>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Identificador (Key)</label>
                        <input
                            required
                            className="form-input"
                            value={formData.key}
                            onChange={e => setFormData({ ...formData, key: e.target.value })}
                            placeholder="e.g. food_dining"
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                        <small style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.5rem', display: 'block' }}>
                            Identificador único usado pelo sistema (ex: food, transport).
                        </small>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Nome de Exibição</label>
                        <input
                            required
                            className="form-input"
                            value={formData.display_name}
                            onChange={e => setFormData({ ...formData, display_name: e.target.value })}
                            placeholder="e.g. Food & Dining"
                            style={{ width: '100%', border: '1px solid var(--border-color)', color: 'white' }}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                        <Button
                            type="button"
                            onClick={() => setIsModalOpen(false)}
                            style={{ backgroundColor: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                        >
                            Cancelar
                        </Button>
                        <Button variant="primary"
                            type="submit"
                            style={{ minWidth: '100px' }}
                        >
                            {editingCategory ? "Salvar" : "Criar"}
                        </Button>
                    </div>
                </form>
            </Modal>

            <Modal isOpen={!!itemToDelete} onClose={() => setItemToDelete(null)} title="Confirmar Exclusão">
                <div style={{ padding: '1rem 0' }}>
                    <p style={{ color: 'var(--text-primary)', fontSize: '1rem', marginBottom: '2rem' }}>
                        Tem certeza que deseja excluir esta categoria? Gastos vinculados a ela podem ser afetados.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <Button
                            type="button"
                            onClick={() => setItemToDelete(null)}
                            style={{ backgroundColor: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                        >
                            Cancelar
                        </Button>
                        <Button variant="danger"
                            type="button"
                            onClick={confirmDelete}
                            style={{ minWidth: '100px' }}
                        >
                            Excluir
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
};
