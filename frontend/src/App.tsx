import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Wallet, PiggyBank, Tags, CreditCard, Repeat, Layers } from 'lucide-react';
import { Dashboard } from './pages/Dashboard';
import { SpentsPage } from './pages/SpentsPage';
import { SubscriptionsPage } from './pages/SubscriptionsPage';
import { InstallmentsPage } from './pages/InstallmentsPage';
import { LimitsPage } from './pages/LimitsPage';
import { CategoriesPage } from './pages/CategoriesPage';
import { PaymentMethodsPage } from './pages/PaymentMethodsPage';
import { InvoicesPage } from './pages/InvoicesPage';
import { ToastContainer } from './components/Toast';
import { CalendarDays } from 'lucide-react';
import './index.css';

const Navigation = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: '/', label: 'Painel', icon: <LayoutDashboard size={20} /> },
    { path: '/spents', label: 'Gastos', icon: <Wallet size={20} /> },
    { path: '/installments', label: 'Parcelamentos', icon: <Layers size={20} /> },
    { path: '/subscriptions', label: 'Assinaturas', icon: <Repeat size={20} /> },
    { path: '/limits', label: 'Limites', icon: <PiggyBank size={20} /> },
    { path: '/categories', label: 'Categorias', icon: <Tags size={20} /> },
    { path: '/payment-methods', label: 'Métodos de Pagamento', icon: <CreditCard size={20} /> },
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
            gap: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            color: isActive(item.path) ? 'white' : 'var(--text-secondary)',
            backgroundColor: isActive(item.path) ? 'var(--accent-color)' : 'transparent',
            transition: 'all 0.2s',
          }}
        >
          {item.icon}
          {item.label}
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
            <Route path="/spents" element={<SpentsPage />} />
            <Route path="/installments" element={<InstallmentsPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/limits" element={<LimitsPage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/payment-methods" element={<PaymentMethodsPage />} />
            <Route path="/invoices" element={<InvoicesPage />} />
          </Routes>
        </main>
        <ToastContainer />
      </div>
    </BrowserRouter>
  );
}

export default App;
