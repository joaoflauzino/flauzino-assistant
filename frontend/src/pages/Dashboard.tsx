import React, { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import { CheckSquare, Square } from 'lucide-react';
import api from '../services/api';
import type { Spent, SpendingLimit } from '../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

// Category display names will be fetched from API
interface Category {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}

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

export const Dashboard = () => {
    const [spents, setSpents] = useState<Spent[]>([]);
    const [limits, setLimits] = useState<SpendingLimit[]>([]);
    const [loading, setLoading] = useState(true);

    // Initialize with current month dates
    const monthDates = getCurrentMonthDates();
    const [startDate, setStartDate] = useState(monthDates.start);
    const [endDate, setEndDate] = useState(monthDates.end);

    // Category selection state - all categories selected by default
    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());

    // Dynamic categories from API
    const [categoryNames, setCategoryNames] = useState<Record<string, string>>({});

    const fetchData = async () => {
        setLoading(true);
        try {
            let query = '/spents?size=1000';
            if (startDate) query += `&start_date=${startDate}`;
            if (endDate) query += `&end_date=${endDate}`;

            const [spentsRes, limitsRes] = await Promise.all([
                api.get(query),
                api.get('/limits?size=1000')
            ]);
            setSpents(spentsRes.data.items);
            setLimits(limitsRes.data.items);

            // Initialize selected categories with all available categories
            if (selectedCategories.size === 0) {
                const allCategories = Array.from(new Set([
                    ...spentsRes.data.items.map((s: Spent) => s.category),
                    ...limitsRes.data.items.map((l: SpendingLimit) => l.category)
                ]));
                setSelectedCategories(new Set(allCategories));
            }
        } catch (error) {
            console.error("Error fetching dashboard data", error);
        } finally {
            setLoading(false);
        }
    };

    // Fetch categories from API
    const fetchCategories = async () => {
        try {
            const res = await api.get<{ items: Category[] }>('/categories/');
            const categoryMap = res.data.items.reduce((acc, cat) => {
                acc[cat.key] = cat.display_name;
                return acc;
            }, {} as Record<string, string>);
            setCategoryNames(categoryMap);
        } catch (error) {
            console.error("Error fetching categories", error);
        }
    };

    useEffect(() => {
        // Fetch categories first
        fetchCategories();

        // Set dates to current month on initial mount
        const monthDates = getCurrentMonthDates();
        setStartDate(monthDates.start);
        setEndDate(monthDates.end);
    }, []); // Run only once on mount

    useEffect(() => {
        // Fetch data when dates are set or change
        if (startDate && endDate) {
            fetchData();
        }
    }, [startDate, endDate]); // Re-fetch when dates change

    const handleFilter = (e: React.FormEvent) => {
        e.preventDefault();
        fetchData();
    };

    const toggleCategory = (category: string) => {
        const newSelected = new Set(selectedCategories);
        if (newSelected.has(category)) {
            newSelected.delete(category);
        } else {
            newSelected.add(category);
        }
        setSelectedCategories(newSelected);
    };

    const selectAllCategories = () => {
        const allCategories = Array.from(new Set([...spents.map(s => s.category), ...limits.map(l => l.category)]));
        setSelectedCategories(new Set(allCategories));
    };

    const deselectAllCategories = () => {
        setSelectedCategories(new Set());
    };

    if (loading) return <div style={{ color: 'white', fontSize: '1.2rem' }}>Loading dashboard...</div>;

    // Process Data - filter by selected categories
    const allCategories = Array.from(new Set([...spents.map(s => s.category), ...limits.map(l => l.category)]));
    const categories = allCategories.filter(cat => selectedCategories.has(cat));

    const spentByCategory = categories.map(cat => {
        return spents.filter(s => s.category === cat).reduce((acc, curr) => acc + curr.amount, 0);
    });

    const limitByCategory = categories.map(cat => {
        const limit = limits.find(l => l.category === cat);
        return limit ? limit.amount : 0;
    });

    const remainingByCategory = categories.map((_cat, index) => {
        const limit = limitByCategory[index];
        const spent = spentByCategory[index];
        return Math.max(0, limit - spent);
    });

    const exactSpentScale = categories.map((_cat, index) => {
        const spent = spentByCategory[index];
        return spent;
    });

    const barData = {
        labels: categories.map(cat => categoryNames[cat] || cat),
        datasets: [
            {
                label: 'Spent',
                data: exactSpentScale,
                backgroundColor: 'rgba(239, 68, 68, 0.8)',
                borderRadius: 6,
                stack: 'Stack 0',
            },
            {
                label: 'Remaining Limit',
                data: remainingByCategory,
                backgroundColor: 'rgba(34, 197, 94, 0.6)',
                borderRadius: 6,
                stack: 'Stack 0',
            },
        ],
    };

    const barOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom' as const,
                labels: {
                    color: '#e5e7eb',
                    font: { size: 12 },
                    padding: 15
                }
            },
            title: {
                display: true,
                text: 'Budget Usage by Category',
                color: '#f3f4f6',
                font: { size: 16, weight: 'bold' as const },
                padding: 20
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f3f4f6',
                bodyColor: '#e5e7eb',
                borderColor: '#374151',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: function (context: any) {
                        return `${context.dataset.label}: R$ ${context.raw.toFixed(2)}`;
                    }
                }
            }
        },
        scales: {
            x: {
                stacked: true,
                grid: { color: 'rgba(75, 85, 99, 0.2)' },
                ticks: { color: '#9ca3af' }
            },
            y: {
                stacked: true,
                grid: { color: 'rgba(75, 85, 99, 0.2)' },
                ticks: {
                    color: '#9ca3af',
                    callback: function (value: any) {
                        return 'R$ ' + value.toLocaleString();
                    }
                }
            },
        }
    };

    const pieData = {
        labels: categories.map(cat => categoryNames[cat] || cat),
        datasets: [
            {
                data: spentByCategory,
                backgroundColor: [
                    '#6366f1', '#ef4444', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', '#f97316', '#06b6d4', '#84cc16'
                ],
                borderWidth: 2,
                borderColor: '#1f2937'
            },
        ],
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 700 }}>Dashboard</h1>

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

            {/* Category Selection Panel */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                padding: '1.5rem',
                borderRadius: '12px',
                marginBottom: '2rem',
                border: '1px solid rgba(99, 102, 241, 0.1)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Select Categories</h3>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button
                            onClick={selectAllCategories}
                            style={{
                                padding: '0.4rem 1rem',
                                borderRadius: '6px',
                                border: '1px solid var(--accent-color)',
                                background: 'transparent',
                                color: 'var(--accent-color)',
                                fontSize: '0.85rem',
                                fontWeight: 500,
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'var(--accent-color)';
                                e.currentTarget.style.color = 'white';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.color = 'var(--accent-color)';
                            }}
                        >
                            Select All
                        </button>
                        <button
                            onClick={deselectAllCategories}
                            style={{
                                padding: '0.4rem 1rem',
                                borderRadius: '6px',
                                border: '1px solid #ef4444',
                                background: 'transparent',
                                color: '#ef4444',
                                fontSize: '0.85rem',
                                fontWeight: 500,
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = '#ef4444';
                                e.currentTarget.style.color = 'white';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.color = '#ef4444';
                            }}
                        >
                            Deselect All
                        </button>
                    </div>
                </div>

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                    gap: '0.75rem'
                }}>
                    {allCategories.map(category => {
                        const isSelected = selectedCategories.has(category);
                        return (
                            <div
                                key={category}
                                onClick={() => toggleCategory(category)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.6rem',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '8px',
                                    background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-tertiary)',
                                    border: `1.5px solid ${isSelected ? 'var(--accent-color)' : 'transparent'}`,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    userSelect: 'none'
                                }}
                                onMouseEnter={(e) => {
                                    if (!isSelected) {
                                        e.currentTarget.style.background = 'rgba(99, 102, 241, 0.08)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isSelected) {
                                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                                    }
                                }}
                            >
                                {isSelected ? (
                                    <CheckSquare size={18} color="var(--accent-color)" />
                                ) : (
                                    <Square size={18} color="var(--text-secondary)" />
                                )}
                                <span style={{
                                    fontSize: '0.9rem',
                                    color: isSelected ? 'white' : 'var(--text-secondary)',
                                    fontWeight: isSelected ? 500 : 400
                                }}>
                                    {categoryNames[category] || category}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Charts */}
            {categories.length === 0 ? (
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '3rem',
                    borderRadius: '12px',
                    textAlign: 'center',
                    color: 'var(--text-secondary)'
                }}>
                    <p style={{ fontSize: '1.1rem', margin: 0 }}>No categories selected. Please select at least one category to view the charts.</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
                    <div style={{
                        backgroundColor: 'var(--bg-secondary)',
                        padding: '1.5rem',
                        borderRadius: '12px',
                        border: '1px solid rgba(99, 102, 241, 0.1)',
                        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                    }}>
                        <div style={{ height: '400px' }}>
                            <Bar data={barData} options={barOptions} />
                        </div>
                    </div>

                    <div style={{
                        backgroundColor: 'var(--bg-secondary)',
                        padding: '1.5rem',
                        borderRadius: '12px',
                        border: '1px solid rgba(99, 102, 241, 0.1)',
                        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                    }}>
                        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Expenses Distribution</h3>
                        <div style={{ height: '350px', display: 'flex', justifyContent: 'center' }}>
                            <Pie data={pieData} options={{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: {
                                        position: 'bottom' as const,
                                        labels: {
                                            color: '#e5e7eb',
                                            font: { size: 11 },
                                            padding: 10
                                        }
                                    },
                                    tooltip: {
                                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                        titleColor: '#f3f4f6',
                                        bodyColor: '#e5e7eb',
                                        borderColor: '#374151',
                                        borderWidth: 1,
                                        padding: 12,
                                        callbacks: {
                                            label: function (context: any) {
                                                const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
                                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                                return `${context.label}: R$ ${context.raw.toFixed(2)} (${percentage}%)`;
                                            }
                                        }
                                    }
                                }
                            }} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
