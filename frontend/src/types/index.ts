export interface Spent {
    id: string;
    category: string;
    amount: number;
    payment_method: string;
    payment_type?: string;
    account_id?: string;
    credit_card_id?: string;
    item_bought: string;
    location?: string | null;
    is_installment?: boolean;
    current_installment?: number;
    total_installments?: number;
    installment_id?: string;
    created_at: string;
}

export interface Subscription {
    id: string;
    name: string;
    category: string;
    amount: number;
    payment_method: string;
    payment_type?: string;
    account_id?: string;
    credit_card_id?: string;
    is_active: boolean;
    created_at: string;
}

export interface SpendingLimit {
    id: string;
    category: string;
    amount: number;
    created_at: string;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    pages: number;
}

export interface Category {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}

export interface IncomeCategory {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}

export interface Income {
    id: string;
    description: string;
    amount: number;
    category: string;
    payment_method?: string;
    account_id?: string;
    received_at: string;
    created_at: string;
}

export interface MonthlyBalanceSummary {
    reference_month: string;
    total_incomes: number;
    total_spents: number;
    net_balance: number;
    is_positive: boolean;
    savings_rate: number;
    incomes_by_category: Record<string, number>;
    spents_by_category: Record<string, number>;
}

export interface Account {
    id: string;
    key: string;
    name: string;
    bank: string;
    owner: string;
    type: string;
    created_at?: string;
    credit_cards?: CreditCard[];
}

export interface CreditCard {
    id: string;
    key: string;
    name: string;
    account_id: string;
    account_name?: string;
    closing_day: number;
    due_day: number;
    credit_limit: number;
    created_at?: string;
}

export interface PaymentMethod {
    id: string;
    key: string;
    display_name: string;
    is_credit_card: boolean;
    closing_day?: number;
    due_day?: number;
    created_at: string;
}

export interface Invoice {
    id: string;
    payment_method_key: string;
    reference_month: string;
    real_closing_date: string;
    real_due_date: string;
    status: string;
    created_at: string;
}

export interface PaymentOwner {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}

export interface InstallmentSummary {
    installment_id: string;
    category: string;
    item_bought: string;
    amount: number;
    total_installments: number;
    passed_installments: number;
}

export interface PossibleDuplicateInfo {
    type: 'spent' | 'income';
    id: string;
    label: string;
    amount: number;
    date: string;
}

export interface StagedTransaction {
    id: string;
    batch_id: string;
    account_id?: string | null;
    credit_card_id?: string | null;
    occurred_at: string;
    posted_at?: string | null;
    raw_title: string;
    raw_description?: string | null;
    merchant: string;
    amount: number;
    direction: 'IN' | 'OUT';
    kind: 'EXPENSE' | 'INCOME' | 'TRANSFER' | 'INVOICE_PAYMENT' | 'REFUND';
    payment_type: string;
    suggested_category?: string | null;
    suggestion_source?: 'RULE' | 'MEMORY' | 'LLM' | null;
    confidence?: number | null;
    category?: string | null;
    description: string;
    location?: string | null;
    status: 'PENDING' | 'APPROVED' | 'COMMITTED' | 'IGNORED' | 'LINKED';
    possible_duplicate?: PossibleDuplicateInfo | null;
    committed_spent_id?: string | null;
    committed_income_id?: string | null;
}

export interface ImportBatch {
    id: string;
    filename: string;
    parser: string;
    account_id?: string | null;
    account_name?: string | null;
    period_start?: string | null;
    period_end?: string | null;
    total_rows: number;
    new_rows: number;
    duplicate_rows: number;
    possible_duplicates: number;
    ai_used: boolean;
    created_at: string;
    counts: {
        pending?: number;
        approved?: number;
        committed?: number;
        ignored?: number;
        linked?: number;
    };
}

export interface ImportSummary {
    pending: number;
    approved: number;
}

export interface BulkActionResult {
    updated: number;
    skipped: number;
    errors: { id: string; error: string }[];
}

export interface CommitResult {
    committed_spents: number;
    committed_incomes: number;
    processed_without_record: number;
    failed: { id: string; error: string }[];
}
