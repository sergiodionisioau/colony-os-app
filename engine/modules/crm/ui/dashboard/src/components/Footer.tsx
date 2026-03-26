"use client";

import React, { useState } from 'react';
import Branding from './Branding';
import styles from './footer.module.css';

export default function Footer() {
    const [isBodyVisible, setIsBodyVisible] = useState(true);

    return (
        <footer className={`${styles.footer} ${!isBodyVisible ? styles.footerCollapsed : ''}`}>
            <div className={`${styles.bodyWrapper} ${!isBodyVisible ? styles.collapsed : ''}`}>
                <div className={styles.content}>
                    <div className={styles.brand}>
                        <Branding size={28} />
                        <p className={styles.description}>Enterprise-ready AI verification</p>
                    </div>

                    <div className={styles.grid}>
                        <div className={styles.column}>
                            <h4>Products</h4>
                            <a href="#">PoF for Business</a>
                            <a href="#">PoF for Enterprise</a>
                            <a href="#">PoF for Institutions</a>
                            <a href="#">Admin Portal</a>
                        </div>
                        <div className={styles.column}>
                            <h4>Resources</h4>
                            <a href="#">Thesis</a>
                            <a href="#">White Paper</a>
                            <a href="#">Mission Statement</a>
                            <a href="#">Brand Assets</a>
                        </div>
                        <div className={styles.column}>
                            <h4>Developers</h4>
                            <a href="#">API Reference</a>
                            <a href="#">SDKs</a>
                            <a href="#">Status</a>
                            <a href="#">GitHub</a>
                        </div>
                        <div className={styles.column}>
                            <h4>Location</h4>
                            <div className={styles.locSelector}>
                                <span className={styles.globe}>🌐</span> AU English (Australia) <span className={styles.downArrow}>▾</span>
                            </div>
                            <div className={styles.followUs}>Follow us</div>
                            <div className={styles.socials}>
                                <svg viewBox="0 0 24 24" width="25" height="25" fill="currentColor">
                                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.045 4.126H5.078z" />
                                </svg>
                                <svg viewBox="0 0 24 24" width="25" height="25" fill="currentColor">
                                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.469h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                                </svg>
                                <svg viewBox="0 0 24 24" width="25" height="25" fill="currentColor">
                                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                                </svg>
                                <svg viewBox="0 0 24 24" width="25" height="25" fill="currentColor">
                                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 1.366.062 2.633.332 3.608 1.308.975.975 1.245 2.242 1.308 3.608.058 1.266.07 1.646.07 4.85s-.012 3.584-.07 4.85c-.062 1.366-.332 2.633-1.308 3.608-.975.975-2.242 1.245-3.608 1.308-1.266.058-1.646.07-4.85.07s-3.584-.012-4.85-.07c-1.366-.062-2.633-.332-3.608-1.308-.975-.975-1.245-2.242-1.308-3.608-.058-1.266-.07-1.646-.07-4.85s.012-3.584.07-4.85c.062-1.366.332-2.633 1.308-3.608.975-.975 2.242-1.245 3.608-1.308 1.266-.058 1.646-.07 4.85-.07zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.668-.072-4.948-.197-4.359-2.612-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z" />
                                </svg>
                                <svg viewBox="0 0 24 24" width="25" height="25" fill="currentColor">
                                    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.011-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div className={styles.bottomBar}>
                <div className={styles.copyright}>© 2026 ColonyAI LLC Ltd.</div>
                <div className={styles.bottomBarRight}>
                    <div className={styles.legal}>
                        <a href="#">Terms</a>
                        <a href="#">Privacy</a>
                    </div>
                    <div className={styles.iconBtn} title={isBodyVisible ? "Collapse Footer" : "Expand Footer"} onClick={() => setIsBodyVisible(!isBodyVisible)}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isBodyVisible ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                            <path d="M18 15l-6-6-6 6" />
                        </svg>
                    </div>
                </div>
            </div>
        </footer>
    );
}
