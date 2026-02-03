import React, { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import api from '../services/api';
import type { Spent, SpendingLimit } from '../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

export const Dashboard = () => {
    const [spents, setSpents] = useState<Spent[]>([]);
    const [limits, setLimits] = useState<SpendingLimit[]>([]);
    const [loading, setLoading] = useState(true);
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

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
        } catch (error) {
            console.error("Error fetching dashboard data", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleFilter = (e: React.FormEvent) => {
        e.preventDefault();
        fetchData();
    };

    if (loading) return <div style={{ color: 'white' }}>Loading dashboard...</div>;

    // Process Data
    const categories = Array.from(new Set([...spents.map(s => s.category), ...limits.map(l => l.category)]));

    const spentByCategory = categories.map(cat => {
        return spents.filter(s => s.category === cat).reduce((acc, curr) => acc + curr.amount, 0);
    });

    const limitByCategory = categories.map(cat => {
        const limit = limits.find(l => l.category === cat);
        return limit ? limit.amount : 0;
    });

    const remainingByCategory = categories.map((cat, index) => {
        const limit = limitByCategory[index];
        const spent = spentByCategory[index];
        return Math.max(0, limit - spent);
    });

    const exactSpentScale = categories.map((cat, index) => {
        const spent = spentByCategory[index];
        return spent;
    });

    const barData = {
        labels: categories,
        datasets: [
            {
                label: 'Spent',
                data: exactSpentScale,
                backgroundColor: 'rgba(239, 68, 68, 0.7)',
                stack: 'Stack 0',
            },
            {
                label: 'Remaining Limit',
                data: remainingByCategory,
                backgroundColor: 'rgba(34, 197, 94, 0.5)',
                stack: 'Stack 0',
            },
        ],
    };

    const barOptions = {
        responsive: true,
        plugins: {
            legend: { position: 'bottom' as const },
            title: { display: true, text: 'Budget Usage (Stacked)' },
            tooltip: {
                callbacks: {
                    label: function (context: any) {
                        return `${context.dataset.label}: R$ ${context.raw.toFixed(2)}`;
                    }
                }
            }
        },
        scales: {
            x: { stacked: true },
            y: { stacked: true },
        }
    };

    const pieData = {
        labels: categories,
        datasets: [
            {
                data: spentByCategory,
                backgroundColor: [
                    '#6366f1', '#ef4444', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6'
                ],
            },
        ],
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 style={{ margin: 0 }}>Dashboard</h1>

                <form onSubmit={handleFilter} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Start Date</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={e => setStartDate(e.target.value)}
                            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-tertiary)', color: 'white' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>End Date</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={e => setEndDate(e.target.value)}
                            style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-tertiary)', color: 'white' }}
                        />
                    </div>
                    <button type="submit" style={{ backgroundColor: 'var(--accent-color)', color: 'white', height: '36px' }}>Filter</button>
                </form>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '1.5rem', borderRadius: '12px' }}>
                    <h3 style={{ marginBottom: '1rem' }}>Budget Overview</h3>
                    <Bar data={barData} options={barOptions} />
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '1.5rem', borderRadius: '12px' }}>
                    <h3 style={{ marginBottom: '1rem' }}>Expenses Distribution</h3>
                    <div style={{ height: '300px', display: 'flex', justifyContent: 'center' }}>
                        <Pie data={pieData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' as const } } }} />
                    </div>
                </div>
            </div>
        </div>
    );
};
