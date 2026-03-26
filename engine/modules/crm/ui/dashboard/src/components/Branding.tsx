import React from 'react';
import styles from './branding.module.css';

interface BrandingProps {
    className?: string;
    showText?: boolean;
    size?: number;
}

export const ColonyLogo = ({ size = 28 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="hexagon-shadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="1.5" floodOpacity="0.3" />
            </filter>
        </defs>

        {/* Pyramid arrangement of 3 solid hexagons with precise 1px line separation */}
        {/* Top Center */}
        <path
            className={styles.hexagon}
            d="M32 4 L44 11 V25 L32 32 L20 25 V11 L32 4 Z"
            fill="#3b82f6"
            filter="url(#hexagon-shadow)"
        />
        {/* Bottom Left - Nudged to create 1px gap */}
        <path
            className={styles.hexagon}
            d="M19 28 L31 35 V49 L19 56 L7 49 V35 L19 28 Z"
            fill="#3b82f6"
            filter="url(#hexagon-shadow)"
        />
        {/* Bottom Right - Nudged to create 1px gap */}
        <path
            className={styles.hexagon}
            d="M45 28 L57 35 V49 L45 56 L33 49 V35 L45 28 Z"
            fill="#3b82f6"
            filter="url(#hexagon-shadow)"
        />
    </svg>
);

export default function Branding({ className, showText = true, size = 28 }: BrandingProps) {
    return (
        <div className={`${styles.brandingContainer} ${className || ''}`}>
            <ColonyLogo size={size} />
            {showText && (
                <span className={styles.brandText}>Colony OS</span>
            )}
        </div>
    );
}
