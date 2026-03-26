"use client";

import { useEffect, useState, useRef } from 'react';
import styles from './stats.module.css';

export default function ProfitChart() {
    const [data, setData] = useState<number[]>([]);
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        // Generate initial data
        const initial = Array.from({ length: 20 }, () => Math.random() * 60 + 20);
        setData(initial);

        // Update data every 3s
        const interval = setInterval(() => {
            setData(prev => {
                const next = [...prev.slice(1), Math.random() * 60 + 20];
                return next;
            });
        }, 3000);

        return () => clearInterval(interval);
    }, []);

    const points = data.map((val, i) => `${(i * 100) / (data.length - 1)},${100 - val}`).join(' ');

    return (
        <div className={styles.chartContainer}>
            <div className={styles.chartHeader}>
                <h4>REAL-TIME AGENT EFFICIENCY</h4>
                <div className={styles.chartLegend}>
                    <span>● NOMINAL</span>
                    <span>● STRESS</span>
                </div>
            </div>
            <div className={styles.svgWrapper}>
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" className={styles.svg}>
                    <defs>
                        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="rgba(59, 130, 246, 0.4)" />
                            <stop offset="100%" stopColor="transparent" />
                        </linearGradient>
                    </defs>
                    <polyline
                        fill="url(#chartGradient)"
                        stroke="none"
                        points={`0,100 ${points} 100,100`}
                    />
                    <polyline
                        className={styles.line}
                        fill="none"
                        stroke="var(--accent-blue)"
                        strokeWidth="1"
                        points={points}
                    />
                </svg>
                <div className={styles.gridOverlay}>
                    <span></span><span></span><span></span><span></span>
                </div>
            </div>
        </div>
    );
}
