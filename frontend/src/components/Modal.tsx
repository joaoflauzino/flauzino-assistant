import React from 'react';
import { X } from 'lucide-react';
import { Button } from './Button';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
}

export const Modal = ({ isOpen, onClose, title, children }: ModalProps) => {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-dialog">
                <div className="modal-header">
                    <h2 style={{ margin: 0 }}>{title}</h2>
                    <Button type="button" variant="icon" onClick={onClose} title="Fechar">
                        <X size={24} />
                    </Button>
                </div>
                <div className="modal-body">{children}</div>
            </div>
        </div>
    );
};
