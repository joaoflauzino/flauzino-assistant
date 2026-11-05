import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react';

export type ButtonVariant = 'default' | 'primary' | 'success' | 'danger' | 'secondary' | 'icon';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    children: ReactNode;
}

export const Button = ({
    variant = 'default',
    className = '',
    title,
    children,
    style,
    ...props
}: ButtonProps) => (
    <button
        {...props}
        title={title}
        aria-label={props['aria-label'] ?? title}
        style={getSemanticStyle(style)}
        className={`ui-button ui-button--${variant} ${className}`.trim()}
    >
        {children}
    </button>
);

function getSemanticStyle(style: CSSProperties | undefined): CSSProperties | undefined {
    if (!style) return undefined;

    const semanticStyle = { ...style };
    const sharedProperties: (keyof CSSProperties)[] = [
        'alignItems',
        'boxShadow',
        'cursor',
        'display',
        'fontFamily',
        'fontSize',
        'fontWeight',
        'gap',
        'height',
        'justifyContent',
        'lineHeight',
        'minHeight',
        'padding',
        'paddingBlock',
        'paddingBottom',
        'paddingInline',
        'paddingLeft',
        'paddingRight',
        'paddingTop',
        'borderRadius',
        'transition',
    ];

    for (const property of sharedProperties) delete semanticStyle[property];

    return semanticStyle;
}
