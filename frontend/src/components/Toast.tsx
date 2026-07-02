import { useEffect, useState } from 'react';
import { X, AlertCircle, CheckCircle2, Info } from 'lucide-react';

export type ToastType = 'error' | 'success' | 'info';

export interface ToastMessage {
    id: number;
    message: string;
    type: ToastType;
}

let toastId = 0;
let addToastCallback: ((msg: string, type: ToastType) => void) | null = null;

export const showToast = (message: string, type: ToastType = 'error') => {
    if (addToastCallback) {
        addToastCallback(message, type);
    }
};

export const ToastContainer = () => {
    const [toasts, setToasts] = useState<ToastMessage[]>([]);

    useEffect(() => {
        addToastCallback = (message: string, type: ToastType) => {
            const id = ++toastId;
            setToasts(prev => [...prev, { id, message, type }]);

            setTimeout(() => {
                setToasts(prev => prev.filter(t => t.id !== id));
            }, 5000);
        };

        return () => {
            addToastCallback = null;
        };
    }, []);

    const removeToast = (id: number) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    const getStyle = (type: ToastType) => {
        switch (type) {
            case 'error':
                return { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.4)', icon: '#ef4444' };
            case 'success':
                return { bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.4)', icon: '#22c55e' };
            case 'info':
                return { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.4)', icon: '#3b82f6' };
        }
    };

    const getIcon = (type: ToastType) => {
        switch (type) {
            case 'error':
                return <AlertCircle size={20} color="#ef4444" />;
            case 'success':
                return <CheckCircle2 size={20} color="#22c55e" />;
            case 'info':
                return <Info size={20} color="#3b82f6" />;
        }
    };

    if (toasts.length === 0) return null;

    return (
        <div style={{
            position: 'fixed',
            top: '1.5rem',
            right: '1.5rem',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
            maxWidth: '420px',
            width: '100%'
        }}>
            {toasts.map(toast => {
                const style = getStyle(toast.type);
                return (
                    <div
                        key={toast.id}
                        style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '0.75rem',
                            padding: '1rem 1.25rem',
                            backgroundColor: style.bg,
                            border: `1px solid ${style.border}`,
                            borderRadius: '12px',
                            backdropFilter: 'blur(12px)',
                            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
                            animation: 'slideIn 0.3s ease-out',
                            color: 'var(--text-primary)',
                            fontSize: '0.9rem',
                            lineHeight: '1.4'
                        }}
                    >
                        <div style={{ flexShrink: 0, marginTop: '2px' }}>
                            {getIcon(toast.type)}
                        </div>
                        <div style={{ flex: 1 }}>
                            {toast.message}
                        </div>
                        <button
                            type="button"
                            onClick={() => removeToast(toast.id)}
                            style={{
                                flexShrink: 0,
                                padding: '0.25rem',
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                color: 'var(--text-secondary)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '4px',
                                transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'white'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
                        >
                            <X size={16} />
                        </button>
                    </div>
                );
            })}
        </div>
    );
};
