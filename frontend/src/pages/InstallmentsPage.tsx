import { useEffect, useState } from 'react';
import { Layers, ChevronDown, ChevronRight } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import api from '../services/api';
import type { InstallmentSummary, Category, PaginatedResponse } from '../types';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export const InstallmentsPage = () => {
    const [summaries, setSummaries] = useState<InstallmentSummary[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const [summariesRes, categoriesRes] = await Promise.all([
                    api.get<InstallmentSummary[]>('/spents/installments-summary'),
                    api.get<PaginatedResponse<Category>>('/categories/?size=1000')
                ]);
                setSummaries(summariesRes.data);
                setCategories(categoriesRes.data.items);
            } catch (error) {
                console.error("Failed to fetch installments data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    // Create a map for category display names
    const categoryMap = categories.reduce((acc, cat) => {
        acc[cat.key] = cat.display_name;
        return acc;
    }, {} as Record<string, string>);

    // Group summaries by category
    const groupedSummaries = summaries.reduce((acc, summary) => {
        const categoryKey = summary.category || 'outros';
        const displayCategory = categoryMap[categoryKey] || categoryKey;
        if (!acc[displayCategory]) acc[displayCategory] = [];
        acc[displayCategory].push(summary);
        return acc;
    }, {} as Record<string, InstallmentSummary[]>);

    const toggleCategory = (category: string) => {
        setExpandedCategories(prev => ({
            ...prev,
            [category]: !prev[category]
        }));
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-900 flex items-center">
                    <Layers className="mr-2" /> Compras Parceladas
                </h1>
            </div>

            {loading ? (
                <div className="flex justify-center p-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                </div>
            ) : Object.keys(groupedSummaries).length === 0 ? (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
                    <p className="text-gray-500">Nenhuma compra parcelada em andamento.</p>
                </div>
            ) : (
                <div className="space-y-8">
                    {Object.entries(groupedSummaries).map(([category, items]) => {
                        const chartData = {
                            labels: items.map(i => i.item_bought),
                            datasets: [
                                {
                                    label: 'Parcelas Pagas',
                                    data: items.map(i => i.passed_installments),
                                    backgroundColor: 'rgba(34, 197, 94, 0.85)', // Green-500
                                    borderRadius: 4,
                                },
                                {
                                    label: 'Parcelas Restantes',
                                    data: items.map(i => Math.max(0, i.total_installments - i.passed_installments)),
                                    backgroundColor: 'rgba(226, 232, 240, 0.8)', // Slate-200
                                    borderRadius: 4,
                                }
                            ]
                        };

                        const chartOptions = {
                            indexAxis: 'y' as const,
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    stacked: true,
                                    ticks: {
                                        stepSize: 1
                                    },
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }
                                },
                                y: {
                                    stacked: true,
                                    grid: {
                                        display: false
                                    }
                                }
                            },
                            plugins: {
                                legend: {
                                    position: 'top' as const,
                                },
                                tooltip: {
                                    callbacks: {
                                        afterLabel: function(context: any) {
                                            const itemIndex = context.dataIndex;
                                            const item = items[itemIndex];
                                            return `Valor da parcela: R$ ${item.amount.toFixed(2)}`;
                                        }
                                    }
                                }
                            }
                        };

                        const isExpanded = expandedCategories[category] || false;

                        return (
                            <div key={category} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                                <div 
                                    className="bg-gray-50 px-6 py-4 border-b border-gray-100 cursor-pointer flex justify-between items-center hover:bg-gray-100 transition-colors"
                                    onClick={() => toggleCategory(category)}
                                >
                                    <h2 className="text-lg font-semibold text-gray-800 capitalize">{category}</h2>
                                    {isExpanded ? <ChevronDown size={20} className="text-gray-500" /> : <ChevronRight size={20} className="text-gray-500" />}
                                </div>
                                {isExpanded && (
                                    <div className="p-6" style={{ height: `${Math.max(200, items.length * 60 + 100)}px` }}>
                                        <Bar data={chartData} options={chartOptions} />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
