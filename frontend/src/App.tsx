import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Wallet,
  PiggyBank,
  Tags,
  CreditCard,
  Repeat,
  Layers,
  CalendarDays,
  TrendingUp,
  FileUp,
} from 'lucide-react';
import { Dashboard } from './pages/Dashboard';
import { SpentsPage } from './pages/SpentsPage';
import { IncomesPage } from './pages/IncomesPage';
import { SubscriptionsPage } from './pages/SubscriptionsPage';
import { InstallmentsPage } from './pages/InstallmentsPage';
import { LimitsPage } from './pages/LimitsPage';
import { CategoriesPage } from './pages/CategoriesPage';
import { AccountsPage } from './pages/AccountsPage';
import { InvoicesPage } from './pages/InvoicesPage';
import { ImportsPage } from './pages/ImportsPage';
import { ToastContainer } from './components/Toast';
import api from './services/api';
import type { ImportSummary } from './types';
import './index.css';

const Navigation = () => {
  const location = useLocation();
  const [pendingImports, setPendingImports] = useState(0);

  const isActive = (path: string) => location.pathname === path;

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const res = await api.get<ImportSummary>('/imports/summary');
        setPendingImports(res.data.pending);
      } catch {
        // Silently fail if API not ready
      }
    };
    fetchSummary();
  }, [location.pathname]);

  const navItems = [
    { path: '/', label: 'Painel', icon: <LayoutDashboard size={20} /> },
    { path: '/imports', label: 'Importações', icon: <FileUp size={20} />, badge: pendingImports },
    { path: '/incomes', label: 'Receitas', icon: <TrendingUp size={20} /> },
    { path: '/spents', label: 'Gastos', icon: <Wallet size={20} /> },
    { path: '/accounts', label: 'Contas & Cartões', icon: <CreditCard size={20} /> },
    { path: '/installments', label: 'Parcelamentos', icon: <Layers size={20} /> },
    { path: '/subscriptions', label: 'Assinaturas', icon: <Repeat size={20} /> },
    { path: '/limits', label: 'Limites', icon: <PiggyBank size={20} /> },
    { path: '/categories', label: 'Categorias', icon: <Tags size={20} /> },
    { path: '/invoices', label: 'Faturas', icon: <CalendarDays size={20} /> },
  ];

  return (
    <nav style={{
      width: '250px',
      backgroundColor: 'var(--bg-secondary)',
      height: '100vh',
      padding: '2rem 1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
      position: 'fixed'
    }}>
      <h2 style={{ padding: '0 1rem', marginBottom: '2rem', color: 'var(--accent-color)' }}>Flauzino Finanças</h2>
      {navItems.map((item) => (
        <Link
          key={item.path}
          to={item.path}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            color: isActive(item.path) ? 'white' : 'var(--text-secondary)',
            backgroundColor: isActive(item.path) ? 'var(--accent-color)' : 'transparent',
            transition: 'all 0.2s',
            textDecoration: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {item.icon}
            {item.label}
          </div>
          {item.badge !== undefined && item.badge > 0 && (
            <span style={{
              backgroundColor: 'var(--warning)',
              color: '#000',
              fontWeight: 700,
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: '10px',
            }}>
              {item.badge}
            </span>
          )}
        </Link>
      ))}
    </nav>
  );
};

function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex' }}>
        <Navigation />
        <main style={{
          marginLeft: '250px',
          padding: '2rem',
          width: '100%'
        }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/imports" element={<ImportsPage />} />
            <Route path="/incomes" element={<IncomesPage />} />
            <Route path="/spents" element={<SpentsPage />} />
            <Route path="/accounts" element={<AccountsPage />} />
            <Route path="/installments" element={<InstallmentsPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/limits" element={<LimitsPage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/invoices" element={<InvoicesPage />} />
          </Routes>
        </main>
        <ToastContainer />
      </div>
    </BrowserRouter>
  );
}

export default App;
