"use client";

import React from 'react';
import styles from './userDropdown.module.css';

interface UserDropdownProps {
    onClose: () => void;
}

const UserDropdown = ({ onClose }: UserDropdownProps) => {
    return (
        <div className={styles.dropdownOverlay} onClick={onClose}>
            <div className={styles.dropdownMenu} onClick={(e) => e.stopPropagation()}>
                <div className={styles.section}>
                    <div className={styles.sectionTitle}>Account</div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" /><path d="M12 18V6" /></svg>
                        <span>Buy Tokens</span>
                    </div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L21 2" /></svg>
                        <span>API Keys</span>
                    </div>
                </div>

                <div className={styles.upgradeBanner}>
                    <div className={styles.upgradeLeft}>
                        <div className={styles.shieldIcon}>
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5zm-1 15.5L7.5 14l1.41-1.41L11 14.67l4.59-4.59L17 11.5l-6 6z" /></svg>
                        </div>
                        <div className={styles.upgradeText}>
                            <div className={styles.upgradeTitle}>Upgrade to Pro</div>
                            <div className={styles.upgradeSubtitle}>Unlock new capabilities</div>
                        </div>
                    </div>
                    <button className={styles.upgradeBtn}>Upgrade</button>
                </div>

                <div className={styles.section}>
                    <div className={styles.sectionTitle}>Settings</div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" /><path d="M3 5v14a2 2 0 0 0 2 2h16v-5" /><path d="M18 12a2 2 0 0 0 0 4h4v-4h-4Z" /></svg>
                        <span>Tokenomics</span>
                    </div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" /></svg>
                        <span>Pricing</span>
                    </div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" /></svg>
                        <span>Billing</span>
                    </div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
                        <span>Settings</span>
                    </div>
                    <div className={styles.menuItem}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="9" y1="3" x2="9" y2="21" /></svg>
                        <span>Enterprise</span>
                    </div>
                </div>

                <div className={styles.divider} />

                <div className={`${styles.menuItem} ${styles.signOut}`}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                    <span>Sign out</span>
                </div>

                <div className={styles.footer}>
                    <div className={styles.toggleRow}>
                        <div className={styles.toggleBtn}>A↓</div>
                        <div className={`${styles.toggleBtn} ${styles.active}`}>A</div>
                        <div className={styles.toggleBtn}>A↑</div>
                    </div>
                    <div className={styles.toggleRow}>
                        <div className={styles.toggleBtn}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg>
                        </div>
                        <div className={`${styles.toggleBtn} ${styles.active}`}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
                        </div>
                        <div className={styles.toggleBtn}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UserDropdown;
