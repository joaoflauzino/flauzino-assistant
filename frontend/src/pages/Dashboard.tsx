import React, { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { CheckSquare, Square, TrendingUp, TrendingDown, Scale, Percent, Landmark, CreditCard as CreditCardIcon } from 'lucide-react';
import api from '../services/api';
import type { Spent, SpendingLimit, Account, CreditCard, Subscription, MonthlyBalanceSummary, IncomeCategory } from '../types';

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
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [creditCards, setCreditCards] = useState<CreditCard[]>([]);
    const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
    const [selectedCreditCards, setSelectedCreditCards] = useState<Set<string>>(new Set());

    const [categoryNames, setCategoryNames] = useState<Record<string, string>>({});
    const [incomeCategoryNames, setIncomeCategoryNames] = useState<Record<string, string>>({});
    const [selectedIncomeCategories, setSelectedIncomeCategories] = useState<Set<string>>(new Set());
    const [paymentMethodNames, setPaymentMethodNames] = useState<Record<string, string>>({});

    const fetchData = async () => {
        setLoading(true);
        try {
            let query = '';
            let summaryQuery = '';
            if (mode === 'CUSTOM') {
                query = '/spents/?size=1000';
                if (startDate) query += `&start_date=${startDate}`;
                if (endDate) query += `&end_date=${endDate}`;

                summaryQuery = '/incomes/summary?';
                if (startDate) summaryQuery += `&start_date=${startDate}`;
                if (endDate) summaryQuery += `&end_date=${endDate}`;
            } else {
                query = `/spents/dashboard?reference_month=${referenceMonth}&mode=${mode}&size=1000`;
                summaryQuery = `/incomes/summary?reference_month=${referenceMonth}`;
            }

            const [spentsRes, limitsRes, subscriptionsRes, summaryRes] = await Promise.all([
                api.get(query),
                api.get('/limits/?size=1000'),
                api.get('/subscriptions/?active_only=true&size=1000'),
                api.get<MonthlyBalanceSummary>(summaryQuery).catch(() => null)
            ]);

            setSpents(spentsRes.data.items);
            setLimits(limitsRes.data.items);
            setSubscriptions(subscriptionsRes.data.items);
            if (summaryRes) {
                setMonthlySummary(summaryRes.data);
                if (summaryRes.data.incomes_by_category) {
                    const incCats = Object.keys(summaryRes.data.incomes_by_category);
                    setSelectedIncomeCategories(prev => prev.size === 0 ? new Set(incCats) : prev);
                }
            }

            if (selectedCategories.size === 0) {
                const allCategories = Array.from(new Set([
                    ...spentsRes.data.items.map((s: Spent) => s.category),
                    ...limitsRes.data.items.map((l: SpendingLimit) => l.category),
                    ...subscriptionsRes.data.items.map((sub: Subscription) => sub.category)
                ]));
                setSelectedCategories(new Set(allCategories));
            }
            if (selectedAccounts.size === 0 && accounts.length > 0) {
                setSelectedAccounts(new Set([...accounts.map(a => a.id), 'outros']));
            }
            if (selectedCreditCards.size === 0 && creditCards.length > 0) {
                setSelectedCreditCards(new Set(creditCards.map(c => c.id)));
            }
        } catch (error) {
            console.error("Error fetching dashboard data", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchCategories = async () => {
        try {
            const [res, incRes] = await Promise.all([
                api.get<{ items: Category[] }>('/categories/'),
                api.get<{ items: IncomeCategory[] }>('/income-categories/?size=200').catch(() => ({ data: { items: [] } })),
            ]);
            const categoryMap = res.data.items.reduce((acc, cat) => {
                acc[cat.key] = cat.display_name;
                return acc;
            }, {} as Record<string, string>);
            setCategoryNames(categoryMap);

            const incMap = (incRes.data.items || []).reduce((acc, cat) => {
                acc[cat.key] = cat.display_name;
                return acc;
            }, {} as Record<string, string>);
            setIncomeCategoryNames(incMap);
        } catch (error) {
            console.error("Error fetching categories", error);
        }
    };

    const fetchAccountsAndCards = async () => {
        try {
            const [accRes, cardRes] = await Promise.all([
                api.get<{ items: Account[] }>('/accounts/?size=1000').catch(() => ({ data: { items: [] } })),
                api.get<{ items: CreditCard[] }>('/credit-cards/?size=1000').catch(() => ({ data: { items: [] } })),
            ]);
            const accItems = accRes.data.items || [];
            const cardItems = cardRes.data.items || [];
            setAccounts(accItems);
            setCreditCards(cardItems);

            const pmMap: Record<string, string> = {};
            accItems.forEach(a => {
                pmMap[a.key] = `${a.name} (${a.bank.toUpperCase()})`;
            });
            cardItems.forEach(c => {
                pmMap[c.key] = c.name;
            });
            setPaymentMethodNames(pmMap);

            setSelectedAccounts(prev => (prev.size === 0 ? new Set([...accItems.map(a => a.id), 'outros']) : prev));
            setSelectedCreditCards(prev => (prev.size === 0 ? new Set(cardItems.map(c => c.id)) : prev));
        } catch (error) {
            console.error("Error fetching accounts and cards", error);
        }
    };

    useEffect(() => {
        fetchCategories();
        fetchAccountsAndCards();
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

    const toggleIncomeCategory = (cat: string) => {
        const next = new Set(selectedIncomeCategories);
        if (next.has(cat)) {
            next.delete(cat);
        } else {
            next.add(cat);
        }
        setSelectedIncomeCategories(next);
    };

    const selectAllIncomeCategories = () => {
        const all = Object.keys(monthlySummary?.incomes_by_category || {});
        setSelectedIncomeCategories(new Set(all));
    };

    const deselectAllIncomeCategories = () => {
        setSelectedIncomeCategories(new Set());
    };

    const cardKeySet = new Set(creditCards.map(c => c.key));
    const cardIdSet = new Set(creditCards.map(c => c.id));
    const accountKeySet = new Set(accounts.map(a => a.key));
    const accountIdSet = new Set(accounts.map(a => a.id));

    const isCreditCardItem = (item: Spent | Subscription) => {
        if (item.credit_card_id && cardIdSet.has(item.credit_card_id)) return true;
        if (item.payment_method && cardKeySet.has(item.payment_method)) return true;
        if (item.payment_type === 'CREDIT') return true;
        return false;
    };

    const getItemCardId = (item: Spent | Subscription): string => {
        if (item.credit_card_id && cardIdSet.has(item.credit_card_id)) return item.credit_card_id;
        const found = creditCards.find(c => c.key === item.payment_method);
        return found ? found.id : (item.credit_card_id || item.payment_method);
    };

    const getItemAccountId = (item: Spent | Subscription): string => {
        if (item.account_id && accountIdSet.has(item.account_id)) return item.account_id;
        const found = accounts.find(a => a.key === item.payment_method);
        return found ? found.id : (item.account_id || item.payment_method || 'outros');
    };

    const isItemIncluded = (item: Spent | Subscription) => {
        if (isCreditCardItem(item)) {
            const cardId = getItemCardId(item);
            return selectedCreditCards.has(cardId);
        } else {
            const accId = getItemAccountId(item);
            return selectedAccounts.has(accId);
        }
    };

    // Extra non-card keys found in spents/subs (e.g. 'dinheiro', 'outros')
    const extraNonCardKeys = Array.from(new Set([
        ...spents.filter(s => !isCreditCardItem(s)).map(s => s.payment_method),
        ...subscriptions.filter(s => !isCreditCardItem(s)).map(s => s.payment_method)
    ])).filter(key => key && !accountKeySet.has(key) && !accounts.some(a => a.id === key));

    const accountsDisplayList = [
        ...accounts.map(a => ({ id: a.id, name: `${a.name} (${a.bank.toUpperCase()})`, key: a.key })),
        ...extraNonCardKeys.map(key => ({ id: key, name: paymentMethodNames[key] || key.charAt(0).toUpperCase() + key.slice(1), key }))
    ];

    // Only display accounts and credit cards that ACTUALLY have data in the loaded dataset
    const activeAccountIdsOrKeys = new Set([
        ...spents.filter(s => !isCreditCardItem(s)).map(s => getItemAccountId(s)),
        ...subscriptions.filter(sub => !isCreditCardItem(sub)).map(sub => getItemAccountId(sub))
    ]);
    const availableAccounts = accountsDisplayList.filter(
        a => activeAccountIdsOrKeys.has(a.id) || (a.key && activeAccountIdsOrKeys.has(a.key))
    );

    const activeCardIdsOrKeys = new Set([
        ...spents.filter(s => isCreditCardItem(s)).map(s => getItemCardId(s)),
        ...subscriptions.filter(sub => isCreditCardItem(sub)).map(sub => getItemCardId(sub))
    ]);
    const availableCreditCards = creditCards.filter(
        c => activeCardIdsOrKeys.has(c.id) || (c.key && activeCardIdsOrKeys.has(c.key))
    );

    const toggleAccount = (id: string) => {
        const next = new Set(selectedAccounts);
        if (next.has(id)) {
            next.delete(id);
        } else {
            next.add(id);
        }
        setSelectedAccounts(next);
    };

    const selectAllAccounts = () => {
        setSelectedAccounts(new Set(availableAccounts.map(a => a.id)));
    };

    const deselectAllAccounts = () => {
        setSelectedAccounts(new Set());
    };

    const toggleCreditCard = (id: string) => {
        const next = new Set(selectedCreditCards);
        if (next.has(id)) {
            next.delete(id);
        } else {
            next.add(id);
        }
        setSelectedCreditCards(next);
    };

    const selectAllCreditCards = () => {
        setSelectedCreditCards(new Set(availableCreditCards.map(c => c.id)));
    };

    const deselectAllCreditCards = () => {
        setSelectedCreditCards(new Set());
    };

    if (loading) return <div style={{ color: 'white', fontSize: '1.2rem' }}>Carregando painel...</div>;

    const allCategories = Array.from(new Set([
        ...spents.map(s => s.category), 
        ...limits.map(l => l.category),
        ...subscriptions.map(sub => sub.category)
    ]));
    const categories = allCategories.filter(cat => selectedCategories.has(cat));

    const pmFilteredSpents = spents.filter(s => isItemIncluded(s));
    const pmFilteredSubscriptions = subscriptions.filter(sub => isItemIncluded(sub));

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

    const filteredSpents = spents.filter(s => selectedCategories.has(s.category) && isItemIncluded(s));
    const filteredSubscriptions = subscriptions.filter(sub => selectedCategories.has(sub.category) && isItemIncluded(sub));

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

    const totalFilteredIncomes = monthlySummary?.incomes_by_category
        ? Object.entries(monthlySummary.incomes_by_category)
            .filter(([cat]) => selectedIncomeCategories.has(cat))
            .reduce((sum, [, amt]) => sum + amt, 0)
        : (monthlySummary?.total_incomes ?? 0);

    const totalFilteredSpents = monthlySummary ? monthlySummary.total_spents : 0;
    const netBalance = Math.round((totalFilteredIncomes - totalFilteredSpents) * 100) / 100;
    const isPositiveBalance = netBalance >= 0;
    const savingsRate = totalFilteredIncomes > 0
        ? Math.round((netBalance / totalFilteredIncomes) * 1000) / 10
        : 0;

    // Gráfico comparativo Entradas vs Saídas
    const cashFlowChartData = {
        labels: ['Receitas (Entradas)', 'Despesas (Saídas)'],
        datasets: [
            {
                label: 'Total em R$',
                data: [
                    totalFilteredIncomes,
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

    const cardSpendMap: Record<string, number> = {};
    filteredSpents.filter(s => isCreditCardItem(s)).forEach(s => {
        const card = creditCards.find(c => c.id === s.credit_card_id || c.key === s.payment_method);
        const name = card ? card.name : (paymentMethodNames[s.payment_method] || s.payment_method || 'Cartão');
        cardSpendMap[name] = (cardSpendMap[name] || 0) + s.amount;
    });
    filteredSubscriptions.filter(sub => isCreditCardItem(sub)).forEach(sub => {
        const card = creditCards.find(c => c.id === sub.credit_card_id || c.key === sub.payment_method);
        const name = card ? card.name : (paymentMethodNames[sub.payment_method] || sub.payment_method || 'Cartão');
        cardSpendMap[name] = (cardSpendMap[name] || 0) + sub.amount;
    });

    const top5Cards = Object.entries(cardSpendMap)
        .map(([name, amount]) => ({ name, amount }))
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 5);

    const top5CardsChartData = {
        labels: top5Cards.map(o => o.name),
        datasets: [
            {
                label: 'Gasto no Cartão',
                data: top5Cards.map(o => o.amount),
                backgroundColor: [
                    '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'
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
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>RECEITAS {mode === 'CUSTOM' ? 'DO PERÍODO' : 'DO MÊS'}</span>
                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(34, 197, 94, 0.15)' }}>
                            <TrendingUp size={20} color="#22c55e" />
                        </div>
                    </div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#22c55e', marginBottom: '0.25rem' }}>
                        R$ {totalFilteredIncomes.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>DESPESAS {mode === 'CUSTOM' ? 'DO PERÍODO' : 'DO MÊS'}</span>
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
                        {savingsRate.toFixed(1)}%
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Da receita total poupada</span>
                </div>
            </div>

            {/* Income Categories Filter Card (Sempre que houver receitas registradas) */}
            {monthlySummary && Object.keys(monthlySummary.incomes_by_category || {}).length > 0 && (
                <div style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '1.5rem',
                    borderRadius: '12px',
                    border: '1px solid rgba(34, 197, 94, 0.25)',
                    marginBottom: '2rem'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem', flexWrap: 'wrap', gap: '0.8rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                            <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(34, 197, 94, 0.15)' }}>
                                <TrendingUp size={20} color="#22c55e" />
                            </div>
                            <div>
                                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Categorias de Receitas</h3>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    Filtre fontes de renda consideradas no painel (ex: desmarque premiações/bônus para ver balanço sem extras)
                                </span>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.6rem' }}>
                            <button
                                type="button"
                                onClick={selectAllIncomeCategories}
                                style={{
                                    padding: '0.4rem 0.9rem',
                                    borderRadius: '6px',
                                    border: '1px solid #22c55e',
                                    background: 'transparent',
                                    color: '#22c55e',
                                    fontSize: '0.82rem',
                                    fontWeight: 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                            >
                                Todas
                            </button>
                            <button
                                type="button"
                                onClick={deselectAllIncomeCategories}
                                style={{
                                    padding: '0.4rem 0.9rem',
                                    borderRadius: '6px',
                                    border: '1px solid #ef4444',
                                    background: 'transparent',
                                    color: '#ef4444',
                                    fontSize: '0.82rem',
                                    fontWeight: 500,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                            >
                                Nenhuma
                            </button>
                        </div>
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                        gap: '0.75rem'
                    }}>
                        {Object.entries(monthlySummary.incomes_by_category).map(([catKey, amount]) => {
                            const isSelected = selectedIncomeCategories.has(catKey);
                            const displayName = incomeCategoryNames[catKey] || catKey.charAt(0).toUpperCase() + catKey.slice(1);
                            return (
                                <div
                                    key={catKey}
                                    onClick={() => toggleIncomeCategory(catKey)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        padding: '0.75rem 1rem',
                                        borderRadius: '8px',
                                        background: isSelected ? 'rgba(34, 197, 94, 0.12)' : 'var(--bg-tertiary)',
                                        border: `1.5px solid ${isSelected ? '#22c55e' : 'transparent'}`,
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        userSelect: 'none'
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                        {isSelected ? (
                                            <CheckSquare size={18} color="#22c55e" />
                                        ) : (
                                            <Square size={18} color="var(--text-secondary)" />
                                        )}
                                        <span style={{
                                            fontSize: '0.9rem',
                                            color: isSelected ? 'white' : 'var(--text-secondary)',
                                            fontWeight: isSelected ? 500 : 400
                                        }}>
                                            {displayName}
                                        </span>
                                    </div>
                                    <span style={{
                                        fontSize: '0.85rem',
                                        fontWeight: 600,
                                        color: isSelected ? '#22c55e' : 'var(--text-secondary)'
                                    }}>
                                        R$ {amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

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

            {/* Two Distinct Panels: Contas Bancárias & Cartões de Crédito (Só aparecem se houver dados correspondentes) */}
            {(availableAccounts.length > 0 || availableCreditCards.length > 0) && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: (availableAccounts.length > 0 && availableCreditCards.length > 0)
                        ? 'repeat(auto-fit, minmax(360px, 1fr))'
                        : '1fr',
                    gap: '1.5rem',
                    marginBottom: '2rem'
                }}>
                    {/* Bloco 1: Contas Bancárias (se houver dados) */}
                    {availableAccounts.length > 0 && (
                        <div style={{
                            backgroundColor: 'var(--bg-secondary)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                        }}>
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(16, 185, 129, 0.15)' }}>
                                            <Landmark size={20} color="#10b981" />
                                        </div>
                                        <div>
                                            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>Contas Bancárias</h3>
                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Débitos, Pix e Movimentação</span>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        <button
                                            type="button"
                                            onClick={selectAllAccounts}
                                            style={{
                                                padding: '0.3rem 0.75rem',
                                                borderRadius: '6px',
                                                border: '1px solid #10b981',
                                                background: 'transparent',
                                                color: '#10b981',
                                                fontSize: '0.8rem',
                                                fontWeight: 500,
                                                cursor: 'pointer',
                                            }}
                                        >
                                            Todas
                                        </button>
                                        <button
                                            type="button"
                                            onClick={deselectAllAccounts}
                                            style={{
                                                padding: '0.3rem 0.75rem',
                                                borderRadius: '6px',
                                                border: '1px solid #ef4444',
                                                background: 'transparent',
                                                color: '#ef4444',
                                                fontSize: '0.8rem',
                                                fontWeight: 500,
                                                cursor: 'pointer',
                                            }}
                                        >
                                            Nenhuma
                                        </button>
                                    </div>
                                </div>

                                <div style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))',
                                    gap: '0.6rem'
                                }}>
                                    {availableAccounts.map(acc => {
                                        const isSelected = selectedAccounts.has(acc.id);
                                        return (
                                            <div
                                                key={acc.id}
                                                onClick={() => toggleAccount(acc.id)}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    padding: '0.6rem 0.8rem',
                                                    borderRadius: '8px',
                                                    background: isSelected ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-tertiary)',
                                                    border: `1.5px solid ${isSelected ? '#10b981' : 'transparent'}`,
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s',
                                                    userSelect: 'none'
                                                }}
                                            >
                                                {isSelected ? (
                                                    <CheckSquare size={16} color="#10b981" />
                                                ) : (
                                                    <Square size={16} color="var(--text-secondary)" />
                                                )}
                                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    <span style={{
                                                        fontSize: '0.85rem',
                                                        color: isSelected ? 'white' : 'var(--text-secondary)',
                                                        fontWeight: isSelected ? 500 : 400
                                                    }}>
                                                        {acc.name}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Bloco 2: Cartões de Crédito (se houver dados) */}
                    {availableCreditCards.length > 0 && (
                        <div style={{
                            backgroundColor: 'var(--bg-secondary)',
                            padding: '1.5rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(59, 130, 246, 0.2)',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                        }}>
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                        <div style={{ padding: '0.4rem', borderRadius: '8px', backgroundColor: 'rgba(59, 130, 246, 0.15)' }}>
                                            <CreditCardIcon size={20} color="#3b82f6" />
                                        </div>
                                        <div>
                                            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>Cartões de Crédito</h3>
                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Faturas e Parcelas</span>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        <button
                                            type="button"
                                            onClick={selectAllCreditCards}
                                            style={{
                                                padding: '0.3rem 0.75rem',
                                                borderRadius: '6px',
                                                border: '1px solid #3b82f6',
                                                background: 'transparent',
                                                color: '#3b82f6',
                                                fontSize: '0.8rem',
                                                fontWeight: 500,
                                                cursor: 'pointer',
                                            }}
                                        >
                                            Todos
                                        </button>
                                        <button
                                            type="button"
                                            onClick={deselectAllCreditCards}
                                            style={{
                                                padding: '0.3rem 0.75rem',
                                                borderRadius: '6px',
                                                border: '1px solid #ef4444',
                                                background: 'transparent',
                                                color: '#ef4444',
                                                fontSize: '0.8rem',
                                                fontWeight: 500,
                                                cursor: 'pointer',
                                            }}
                                        >
                                            Nenhum
                                        </button>
                                    </div>
                                </div>

                                <div style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))',
                                    gap: '0.6rem'
                                }}>
                                    {availableCreditCards.map(cc => {
                                        const isSelected = selectedCreditCards.has(cc.id);
                                        return (
                                            <div
                                                key={cc.id}
                                                onClick={() => toggleCreditCard(cc.id)}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    padding: '0.6rem 0.8rem',
                                                    borderRadius: '8px',
                                                    background: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-tertiary)',
                                                    border: `1.5px solid ${isSelected ? '#3b82f6' : 'transparent'}`,
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s',
                                                    userSelect: 'none'
                                                }}
                                            >
                                                {isSelected ? (
                                                    <CheckSquare size={16} color="#3b82f6" />
                                                ) : (
                                                    <Square size={16} color="var(--text-secondary)" />
                                                )}
                                                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    <span style={{
                                                        fontSize: '0.85rem',
                                                        color: isSelected ? 'white' : 'var(--text-secondary)',
                                                        fontWeight: isSelected ? 500 : 400
                                                    }}>
                                                        {cc.name}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

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
                            border: '1px solid rgba(59, 130, 246, 0.15)',
                            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                            display: 'flex',
                            flexDirection: 'column',
                        }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Top Gastos por Cartão</h3>
                            {top5Cards.length === 0 ? (
                                <div style={{
                                    height: '320px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-secondary)',
                                    textAlign: 'center',
                                    fontSize: '0.9rem',
                                    padding: '1.5rem',
                                }}>
                                    Nenhum gasto em cartão de crédito no período selecionado.
                                </div>
                            ) : (
                                <div style={{ height: '320px' }}>
                                    <Bar data={top5CardsChartData} options={horizontalBarOptions} />
                                </div>
                            )}
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
