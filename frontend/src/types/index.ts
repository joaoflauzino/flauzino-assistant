export interface Spent {
    id: string;
    category: string;
    amount: number;
    payment_method: string;
    payment_owner: string;
    item_bought: string;
    location: string;
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

export interface PaymentMethod {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}

export interface PaymentOwner {
    id: string;
    key: string;
    display_name: string;
    created_at: string;
}
