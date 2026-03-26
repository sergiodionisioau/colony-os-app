"use client";

import { useState } from 'react';
import styles from './hitl.module.css';

interface HITLApprovalProps {
    onAction: (action: string) => void;
}

export default function HITLApproval({ onAction }: HITLApprovalProps) {
    const [status, setStatus] = useState<'pending' | 'approved' | 'rejected'>('pending');

    const handleAction = (action: 'approved' | 'rejected') => {
        setStatus(action);
        onAction(action === 'approved' ? 'Approved' : 'Rejected');

        // Reset after some time for demo purposes
        if (action === 'approved') {
            setTimeout(() => setStatus('pending'), 10000);
        }
    };

    return (
        <div className={styles.container}>
            {status !== 'pending' && (
                <div className={`${styles.overlay} ${styles.active}`}>
                    <div className={status === 'approved' ? styles.checkmark : styles.cross}>
                        {status === 'approved' ? '✓' : '×'}
                    </div>
                    <h2>Decision {status.charAt(0).toUpperCase() + status.slice(1)}</h2>
                    <p>{status === 'approved' ? 'Executing agentic outreach pipeline...' : 'Action cancelled by human intervention.'}</p>
                </div>
            )}

            <div className={styles.badgeRow}>
                <div className={styles.badgeConfidence}>AI Confidence: 92%</div>
                <div className={styles.badgeImpact}>Strategic Impact: HIGH</div>
            </div>

            <div className={styles.content}>
                <h2>Propose Outreach: Sarah Chen</h2>
                <p>
                    Targeting <strong>Platform Engineering Lead</strong> at <strong>Acme Corp</strong>.
                    Intent signals detected from <code>pricing</code> page visits and recent <code>Series B</code> funding news.
                    <br /><br />
                    <strong>Agent Strategy:</strong> Account-level penetration via technical value-prop sequence.
                </p>
            </div>

            <div className={styles.actions}>
                <button
                    className={styles.btnReject}
                    onClick={() => handleAction('rejected')}
                    disabled={status !== 'pending'}
                >
                    Reject
                </button>
                <button
                    className={styles.btnApprove}
                    onClick={() => handleAction('approved')}
                    disabled={status !== 'pending'}
                >
                    Approve Action
                </button>
            </div>
        </div>
    );
}
