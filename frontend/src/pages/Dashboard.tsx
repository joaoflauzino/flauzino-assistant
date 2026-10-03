import React, { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { CheckSquare, Square, TrendingUp, TrendingDown, Scale, Percent } from 'lucide-react';
import api from '../services/api';
import type { Spent, SpendingLimit, PaymentMethod, Subscription, MonthlyBalanceSummary } from '../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

interface Category {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}

const getCurrentMonth = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
};

const generateMonthOptions = () => {
    const options = [];
    const now = new Date();
    for (let i = -12; i <= 12; i++) {
        const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const label = d.toLocaleString('pt-BR', { month: 'long', year: 'numeric' });
        options.push({
            value: `${year}-${month}`,
            label: label.charAt(0).toUpperCase() + label.slice(1)
        });
    }
    return options;
};

export const Dashboard = () => {
    const [spents, setSpents] = useState<Spent[]>([]);
    const [limits, setLimits] = useState<SpendingLimit[]>([]);
    const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
    const [monthlySummary, setMonthlySummary] = useState<MonthlyBalanceSummary | null>(null);
    const [loading, setLoading] = useState(true);

    const [referenceMonth, setReferenceMonth] = useState(getCurrentMonth());
    const [mode, setMode] = useState<'CIVIL_MONTH' | 'INVOICES' | 'CUSTOM'>('CIVIL_MONTH');
    
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
    const [selectedPaymentMethods, setSelectedPaymentMethods] = useState<Set<string>>(new Set());

    const [categoryNames, setCategoryNames] = useState<Record<string, string>>({});
    const [paymentMethodNames, setPaymentMethodNames] = useState<Record<string, string>>({});

    const fetchData = async () => {
        setLoading(true);
        try {
            let query = '';
            if (mode === 'CUSTOM') {
                query = '/spents/?size=1000';
                if (startDate) query += `&start_date=${startDate}`;
                if (endDate) query += `&end_date=${endDate}`;
            } else {
                query = `/spents/dashboard?reference_month=${referenceMonth}&mode=${mode}&size=1000`;
            }

            const targetSummaryMonth = mode === 'CUSTOM' && startDate ? startDate.substring(0, 7) : referenceMonth;

            const [spentsRes, limitsRes, subscriptionsRes, summaryRes] = await Promise.all([
                api.get(query),
                api.get('/limits/?size=1000'),
                api.get('/subscriptions/?active_only=true&size=1000'),
                api.get<MonthlyBalanceSummary>(`/incomes/summary?reference_month=${targetSummaryMonth}`).catch(() => null)
            ]);

            setSpents(spentsRes.data.items);
            setLimits(limitsRes.data.items);
            setSubscriptions(subscriptionsRes.data.items);
            if (summaryRes) {
                setMonthlySummary(summaryRes.data);
            }

            if (selectedCategories.size === 0) {
                const allCategories = Array.from(new Set([
                    ...spentsRes.data.items.map((s: Spent) => s.category),
                    ...limitsRes.data.items.map((l: SpendingLimit) => l.category),
                    ...subscriptionsRes.data.items.map((sub: Subscription) => sub.category)
                ]));
                setSelectedCategories(new Set(allCategories));
            }
            if (selectedPaymentMethods.size === 0) {
                const allPMs = Array.from(new Set([
                    ...spentsRes.data.items.map((s: Spent) => s.payment_method),
                    ...subscriptionsRes.data.items.map((sub: Subscription) => sub.payment_method)
                ]));
                setSelectedPaymentMethods(new Set(allPMs));
            }
        } catch (error) {
            console.error("Error fetching dashboard data", error);
        } finally {
            setLoading(false);
        }
    };

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

    const fetchPaymentMethods = async () => {
        try {
            const res = await api.get<{ items: PaymentMethod[] }>('/payment-methods/?size=1000');
            const pmMap = res.data.items.reduce((acc, pm) => {
                acc[pm.key] = pm.display_name;
                return acc;
            }, {} as Record<string, string>);
            setPaymentMethodNames(pmMap);
        } catch (error) {
            console.error("Error fetching payment methods", error);
        }
    };

    useEffect(() => {
        fetchCategories();
        fetchPaymentMethods();
    }, []);

    useEffect(() => {
        fetchData();
    }, [referenceMonth, mode]);

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
        const allCategories = Array.from(new Set([
            ...spents.map(s => s.category), 
            ...limits.map(l => l.category),
            ...subscriptions.map(sub => sub.category)
        ]));
        setSelectedCategories(new Set(allCategories));
    };

    const deselectAllCategories = () => {
        setSelectedCategories(new Set());
    };

    const togglePaymentMethod = (pm: string) => {
        const newSelected = new Set(selectedPaymentMethods);
        if (newSelected.has(pm)) {
            newSelected.delete(pm);
        } else {
            newSelected.add(pm);
        }
        setSelectedPaymentMethods(newSelected);
    };

    const selectAllPaymentMethods = () => {
        const allPMs = Array.from(new Set([
            ...spents.map(s => s.payment_method),
            ...subscriptions.map(sub => sub.payment_method)
        ]));
        setSelectedPaymentMethods(new Set(allPMs));
    };

    const deselectAllPaymentMethods = () => {
        setSelectedPaymentMethods(new Set());
    };

    if (loading) return <div style={{ color: 'white', fontSize: '1.2rem' }}>Carregando painel...</div>;

    const allCategories = Array.from(new Set([
        ...spents.map(s => s.category), 
        ...limits.map(l => l.category),
        ...subscriptions.map(sub => sub.category)
    ]));
    const categories = allCategories.filter(cat => selectedCategories.has(cat));

    const pmFilteredSpents = spents.filter(s => selectedPaymentMethods.has(s.payment_method));
    const pmFilteredSubscriptions = subscriptions.filter(sub => selectedPaymentMethods.has(sub.payment_method));

    const spentByCategory = categories.map(cat => {
        const spentSum = pmFilteredSpents.filter(s => s.category === cat).reduce((acc, curr) => acc + curr.amount, 0);
        const subSum = pmFilteredSubscriptions.filter(sub => sub.category === cat).reduce((acc, curr) => acc + curr.amount, 0);
        return spentSum + subSum;
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
        return spentByCategory[index];
    });

    const allPaymentMethods = Array.from(new Set([
        ...spents.map(s => s.payment_method),
        ...subscriptions.map(sub => sub.payment_method)
    ]));

    const filteredSpents = spents.filter(s => selectedCategories.has(s.category) && selectedPaymentMethods.has(s.payment_method));
    const filteredSubscriptions = subscriptions.filter(sub => selectedCategories.has(sub.category) && selectedPaymentMethods.has(sub.payment_method));
    const uniquePaymentMethods = Array.from(new Set([
        ...filteredSpents.map(s => s.payment_method),
        ...filteredSubscriptions.map(sub => sub.payment_method)
    ]));

    const barData = {
        labels: categories.map(cat => categoryNames[cat] || cat),
        datasets: [
            {
                label: 'Gasto',
                data: exactSpentScale,
                backgroundColor: 'rgba(239, 68, 68, 0.8)',
                borderRadius: 6,
                stack: 'Stack 0',
            },
            {
                label: 'Limite Restante',
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
                text: 'Uso do Orçamento por Categoria',
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

    // Gráfico comparativo Entradas vs Saídas
    const cashFlowChartData = {
        labels: ['Receitas (Entradas)', 'Despesas (Saídas)'],
        datasets: [
            {
                label: 'Total em R$',
                data: [
                    monthlySummary ? monthlySummary.total_incomes : 0,
                    monthlySummary ? monthlySummary.total_spents : 0,
                ],
                backgroundColor: ['rgba(34, 197, 94, 0.85)', 'rgba(239, 68, 68, 0.85)'],
                borderRadius: 8,
                barThickness: 50,
            }
        ]
    };

    const cashFlowChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            title: {
                display: true,
                text: 'Entradas vs Saídas do Mês',
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
                        return `Total: R$ ${context.raw.toFixed(2)}`;
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { color: '#e5e7eb', font: { size: 13, weight: 'bold' as const } }
            },
            y: {
                grid: { color: 'rgba(75, 85, 99, 0.2)' },
                ticks: {
                    color: '#9ca3af',
                    callback: function (value: any) {
                        return 'R$ ' + value.toLocaleString();
                    }
                }
            }
        }
    };

    const horizontalBarOptions = {
        indexAxis: 'y' as const,
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f3f4f6',
                bodyColor: '#e5e7eb',
                borderColor: '#374151',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: function (context: any) {
                        return `Gasto: R$ ${context.raw.toFixed(2)}`;
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { color: 'rgba(75, 85, 99, 0.2)' },
                ticks: {
                    color: '#9ca3af',
                    callback: function (value: any) {
                        return 'R$ ' + value.toLocaleString();
                    }
                }
            },
            y: {
                grid: { display: false },
                ticks: {
                    color: '#e5e7eb',
                    font: { size: 12 }
                }
            }
        }
    };

    const categoryDataList = categories.map((cat, index) => ({
        name: categoryNames[cat] || cat,
        amount: spentByCategory[index]
    }));

    const top5Categories = categoryDataList
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 5);

    const top5CategoriesData = {
        labels: top5Categories.map(c => c.name),
        datasets: [
            {
                label: 'Gasto',
                data: top5Categories.map(c => c.amount),
                backgroundColor: [
                    '#6366f1', '#ef4444', '#22c55e', '#f59e0b', '#ec4899'
                ],
                borderRadius: 4,
                barThickness: 20,
            },
        ],
    };

    const paymentMethodDataList = uniquePaymentMethods.map(pm => {
        const amountSpents = filteredSpents
            .filter(s => s.payment_method === pm)
            .reduce((acc, curr) => acc + curr.amount, 0);
        const amountSubs = filteredSubscriptions
            .filter(sub => sub.payment_method === pm)
            .reduce((acc, curr) => acc + curr.amount, 0);
        return {
            name: paymentMethodNames[pm] || pm,
            amount: amountSpents + amountSubs
        };
    });

    const top5PaymentMethods = paymentMethodDataList
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 5);

    const top5PaymentMethodsChartData = {
        labels: top5PaymentMethods.map(pm => pm.name),
        datasets: [
            {
                label: 'Gasto',
                data: top5PaymentMethods.map(pm => pm.amount),
                backgroundColor: [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'
                ],
                borderRadius: 4,
                barThickness: 20,
            },
        ],
    };

    const allItemsSet = new Set([
        ...filteredSpents.map(s => s.item_bought),
        ...filteredSubscriptions.map(sub => sub.name)
    ]);
    const itemDataList = Array.from(allItemsSet).map(item => {
        const amountSpents = filteredSpents
            .filter(s => s.item_bought === item)
            .reduce((acc, curr) => acc + curr.amount, 0);
        const amountSubs = filteredSubscriptions
            .filter(sub => sub.name === item)
            .reduce((acc, curr) => acc + curr.amount, 0);
        return {
            name: item,
            amount: amountSpents + amountSubs
        };
    });

    const top10Items = itemDataList
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 10);

    const top10ItemsChartData = {
        labels: top10Items.map(item => item.name),
        datasets: [
            {
                label: 'Gasto',
                data: top10Items.map(item => item.amount),
                backgroundColor: [
                    '#6366f1', '#ef4444', '#22c55e', '#f59e0b', '#ec4899',
                    '#3b82f6', '#10b981', '#8b5cf6', '#f97316', '#14b8a6'
                ],
                borderRadius: 4,
                barThickness: 20,
            },
        ],
    };

    const netBalance = monthlySummary?.net_balance ?? 0;
    const isPositiveBalance = monthlySummary ? monthlySummary.is_positive : netBalance >= 0;

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 700 }}>Painel</h1>

                <form onSubmit={handleFilter} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                    {mode === 'CUSTOM' ? (
                        <>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', fontWeight: 500 }}>Data Inicial</label>
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
                                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', fontWeight: 500 }}>Data Final</label>
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
                        </>
                    ) : (
                        <div>
                            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', fontWeight: 500 }}>Mês de Referência</label>
                            <select
                                value={referenceMonth}
                                onChange={e => setReferenceMonth(e.target.value)}
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
                            >
                                {generateMonthOptions().map(opt => (
                                    <option key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem', fontWeight: 500 }}>Modo de Visualização</label>
                        <select
                            value={mode}
                            onChange={e => setMode(e.target.value as 'CIVIL_MONTH' | 'INVOICES' | 'CUSTOM')}
                            style={{
                                padding: '0.6rem 0.8rem',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color)',
                                background: 'var(--bg-tertiary)',
                                color: 'white',
                                fontSize: '0.9rem',
                                cursor: 'pointer',
                                outline: 'none'
                            }}
                        >
                            <option value="CIVIL_MONTH">Mês Civil (1 a 31)</option>
                            <option value="INVOICES">Ciclo das Faturas</option>
                            <option value="CUSTOM">Período Customizado</option>
                        </select>
                    </div>
                    <button
                        type="submit"
                        style={{
                            padding: '0.6rem 1.2rem',
                            backgroundColor: 'var(--accent-color)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontWeight: 600,
                            fontSize: '0.9rem',
                            transition: 'all 0.2s'
                        }}
                    >
                        Filtrar
                    </button>
                </form>
            </div>

            {/* Top KPI Cards (Balanço Mensal Integrado) */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '1.2rem',
                marginBottom: '2rem'
            }}>
                {/* Receitas */}
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: '1px solid rgba(34, 197, 94, 0.2)',
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>RECEITAS DO MÊS</span>
                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(34, 197, 94, 0.15)' }}>
                            <TrendingUp size={20} color="#22c55e" />
                        </div>
                    </div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#22c55e', marginBottom: '0.25rem' }}>
                        R$ {monthlySummary ? monthlySummary.total_incomes.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '0,00'}
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Entradas financeiras registradas</span>
                </div>

                {/* Despesas */}
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>DESPESAS DO MÊS</span>
                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.15)' }}>
                            <TrendingDown size={20} color="#ef4444" />
                        </div>
                    </div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#ef4444', marginBottom: '0.25rem' }}>
                        R$ {monthlySummary ? monthlySummary.total_spents.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '0,00'}
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total de gastos e faturas</span>
                </div>

                {/* Saldo Líquido */}
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: `1px solid ${isPositiveBalance ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>RESULTADO LÍQUIDO</span>
                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: isPositiveBalance ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)' }}>
                            <Scale size={20} color={isPositiveBalance ? '#22c55e' : '#ef4444'} />
                        </div>
                    </div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700, color: isPositiveBalance ? '#22c55e' : '#ef4444', marginBottom: '0.25rem' }}>
                        {netBalance >= 0 ? '+' : ''} R$ {netBalance.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </div>
                    <span style={{
                        display: 'inline-block',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '6px',
                        backgroundColor: isPositiveBalance ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: isPositiveBalance ? '#22c55e' : '#ef4444'
                    }}>
                        {isPositiveBalance ? 'SUPERÁVIT (POSITIVO)' : 'DÉFICIT (NEGATIVO)'}
                    </span>
                </div>

                {/* Taxa de Economia */}
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>TAXA DE ECONOMIA</span>
                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(99, 102, 241, 0.15)' }}>
                            <Percent size={20} color="#6366f1" />
                        </div>
                    </div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#6366f1', marginBottom: '0.25rem' }}>
                        {monthlySummary ? monthlySummary.savings_rate.toFixed(1) : '0.0'}%
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Da receita total poupada</span>
                </div>
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
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Selecionar Categorias</h3>
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
                            Selecionar Todas
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
                            Desselecionar Todas
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

            {/* Payment Method Selection Panel */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                padding: '1.5rem',
                borderRadius: '12px',
                marginBottom: '2rem',
                border: '1px solid rgba(59, 130, 246, 0.1)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Selecionar Cartões / Métodos de Pagamento</h3>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button
                            type="button"
                            onClick={selectAllPaymentMethods}
                            style={{
                                padding: '0.4rem 1rem',
                                borderRadius: '6px',
                                border: '1px solid #3b82f6',
                                background: 'transparent',
                                color: '#3b82f6',
                                fontSize: '0.85rem',
                                fontWeight: 500,
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = '#3b82f6';
                                e.currentTarget.style.color = 'white';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.color = '#3b82f6';
                            }}
                        >
                            Selecionar Todos
                        </button>
                        <button
                            type="button"
                            onClick={deselectAllPaymentMethods}
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
                            Desselecionar Todos
                        </button>
                    </div>
                </div>

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                    gap: '0.75rem'
                }}>
                    {allPaymentMethods.map(pm => {
                        const isSelected = selectedPaymentMethods.has(pm);
                        return (
                            <div
                                key={pm}
                                onClick={() => togglePaymentMethod(pm)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.6rem',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '8px',
                                    background: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-tertiary)',
                                    border: `1.5px solid ${isSelected ? '#3b82f6' : 'transparent'}`,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    userSelect: 'none'
                                }}
                                onMouseEnter={(e) => {
                                    if (!isSelected) {
                                        e.currentTarget.style.background = 'rgba(59, 130, 246, 0.08)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isSelected) {
                                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                                    }
                                }}
                            >
                                {isSelected ? (
                                    <CheckSquare size={18} color="#3b82f6" />
                                ) : (
                                    <Square size={18} color="var(--text-secondary)" />
                                )}
                                <span style={{
                                    fontSize: '0.9rem',
                                    color: isSelected ? 'white' : 'var(--text-secondary)',
                                    fontWeight: isSelected ? 500 : 400
                                }}>
                                    {paymentMethodNames[pm] || pm}
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
                    <p style={{ fontSize: '1.1rem', margin: 0 }}>Nenhuma categoria selecionada. Por favor selecione pelo menos uma categoria para visualizar os gráficos.</p>
                </div>
            ) : (
                <>
                    {/* Linha de Balanço Comparativo e Orçamento */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '2rem', marginBottom: '2rem' }}>
                        <div style={{
                            backgroundColor: 'var(--bg-secondary)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(34, 197, 94, 0.15)',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                        }}>
                            <div style={{ height: '400px' }}>
                                <Bar data={cashFlowChartData} options={cashFlowChartOptions} />
                            </div>
                        </div>

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
                    </div>

                    {/* Bottom Row - 3 Charts */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                        <div style={{
                            backgroundColor: 'var(--bg-secondary)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(99, 102, 241, 0.1)',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                        }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Top 5 Despesas por Categoria</h3>
                            <div style={{ height: '320px' }}>
                                <Bar data={top5CategoriesData} options={horizontalBarOptions} />
                            </div>
                        </div>

                        <div style={{
                            backgroundColor: 'var(--bg-secondary)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(99, 102, 241, 0.1)',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                        }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Top 5 Gastos por Método</h3>
                            <div style={{ height: '320px' }}>
                                <Bar data={top5PaymentMethodsChartData} options={horizontalBarOptions} />
                            </div>
                        </div>

                        <div style={{
                            backgroundColor: 'var(--bg-secondary)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(99, 102, 241, 0.1)',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                        }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Top 10 Itens Comprados</h3>
                            <div style={{ height: '320px' }}>
                                <Bar data={top10ItemsChartData} options={horizontalBarOptions} />
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};
