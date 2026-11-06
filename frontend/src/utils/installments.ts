import type { InstallmentSummary } from '../types';

export interface InstallmentAmounts {
    totalAmount: number;
    paidAmount: number;
    remainingAmount: number;
    isCompleted: boolean;
}

export const getInstallmentAmounts = (
    installment: InstallmentSummary,
): InstallmentAmounts => {
    const amount = Number.isFinite(installment.amount)
        ? Math.max(0, installment.amount)
        : 0;
    const totalInstallments = Number.isFinite(installment.total_installments)
        ? Math.max(0, Math.trunc(installment.total_installments))
        : 0;
    const passedInstallments = Number.isFinite(installment.passed_installments)
        ? Math.min(
              totalInstallments,
              Math.max(0, Math.trunc(installment.passed_installments)),
          )
        : 0;
    const totalAmount = amount * totalInstallments;
    const paidAmount = amount * passedInstallments;

    return {
        totalAmount,
        paidAmount,
        remainingAmount: Math.max(0, totalAmount - paidAmount),
        isCompleted:
            totalInstallments > 0 && passedInstallments >= totalInstallments,
    };
};

export const isInstallmentInProgress = (
    installment: InstallmentSummary,
): boolean => {
    const totalInstallments = installment.total_installments;
    return (
        Number.isFinite(totalInstallments) &&
        totalInstallments > 0 &&
        !getInstallmentAmounts(installment).isCompleted
    );
};
