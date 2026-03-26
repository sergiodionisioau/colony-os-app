"use client";

import { useEffect, useState } from 'react';
import styles from './stats.module.css';

export default function MarketTicker() {
    const [tickers, setTickers] = useState([
        { symbol: 'REVENUE', price: '12,402.1', change: '+1.2%', up: true },
        { symbol: 'AGENT_LOAD', price: '72.4%', change: '-0.5%', up: false },
        { symbol: 'PIPELINE_V', price: '842', change: '+5.4%', up: true },
        { symbol: 'STRICT_AUTH', price: '100.0%', change: '0.0%', up: true },
        { symbol: 'GPU_UTIL', price: '88.9%', change: '+2.1%', up: true },
    ]);

    useEffect(() => {
        const interval = setInterval(() => {
            setTickers(prev => prev.map(t => {
                const delta = (Math.random() - 0.5) * 0.1;
                const basePrice = parseFloat(t.price.replace(/[^0-9.]/g, ''));
                const newPrice = (basePrice + delta).toFixed(1);
                return { ...t, price: t.symbol.includes('%') ? `${newPrice}%` : newPrice };
            }));
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className={styles.tickerContainer}>
            <div className={styles.tickerTrack}>
                {tickers.map((t, i) => (
                    <div key={i} className={styles.tickerItem}>
                        <span className={styles.symbol}>{t.symbol}</span>
                        <span className={styles.price}>{t.price}</span>
                        <span className={t.up ? styles.up : styles.down}>{t.change}</span>
                    </div>
                ))}
                {/* Duplicate for seamless loop */}
                {tickers.map((t, i) => (
                    <div key={`dup-${i}`} className={styles.tickerItem}>
                        <span className={styles.symbol}>{t.symbol}</span>
                        <span className={styles.price}>{t.price}</span>
                        <span className={t.up ? styles.up : styles.down}>{t.change}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
