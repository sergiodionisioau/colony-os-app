"use client";

import Branding from './Branding';
import styles from './header.module.css';
import { useSidebar } from '@/context/SidebarContext';
import UserDropdown from './UserDropdown';
import { useState, useEffect } from 'react';

export default function Header() {
    const { toggleSidebar } = useSidebar();
    const [searchQuery, setSearchQuery] = useState('');
    const [showUserDropdown, setShowUserDropdown] = useState(false);
    const [isTopRowVisible, setIsTopRowVisible] = useState(true);
    const [isFullScreen, setIsFullScreen] = useState(false);

    useEffect(() => {
        const handleFullScreenChange = () => {
            setIsFullScreen(!!document.fullscreenElement);
        };
        document.addEventListener('fullscreenchange', handleFullScreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullScreenChange);
    }, []);

    const toggleFullScreen = () => {
        if (!document.fullscreenElement) {
            const elem = document.documentElement as any;
            const requestFS = elem.requestFullscreen || elem.webkitRequestFullscreen || elem.mozRequestFullScreen || elem.msRequestFullscreen;
            if (requestFS) {
                requestFS.call(elem).catch((err: any) => {
                    console.error("Fullscreen request failed:", err);
                });
            }
        } else {
            const doc = document as any;
            const exitFS = doc.exitFullscreen || doc.webkitExitFullscreen || doc.mozCancelFullScreen || doc.msExitFullscreen;
            if (exitFS) {
                exitFS.call(doc).catch((err: any) => {
                    console.error("Exit fullscreen failed:", err);
                });
            }
        }
    };

    return (
        <header className={styles.header}>
            {/* Top Row: Replicated Grafana Menu */}
            <div className={`${styles.topRow} ${!isTopRowVisible ? styles.collapsed : ''}`}>
                <div className={styles.left}>
                    <Branding size={24} />
                </div>

                <div className={styles.center}>
                </div>

                <div className={styles.right}>
                    <div className={styles.searchBar}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="11" cy="11" r="8" />
                            <path d="M21 21l-4.35-4.35" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search dashboards, users..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <span className={styles.searchKbd}>⌘ ctrl+k</span>
                    </div>
                    <div className={styles.actionIcons}>
                        <div className={styles.iconBtn} style={{ marginRight: '5px' }}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                                <line x1="12" y1="17" x2="12.01" y2="17" />
                            </svg>
                        </div>
                        <div className={styles.inviteBtn}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                                <circle cx="9" cy="7" r="4" />
                                <line x1="19" y1="8" x2="19" y2="14" />
                                <line x1="17" y1="11" x2="21" y2="11" />
                            </svg>
                            Invite
                        </div>
                        <div className={styles.iconBtn} title="AI Assistant">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
                            </svg>
                        </div>
                        <div className={styles.profileIconAlt} style={{ marginLeft: '5px' }} onClick={() => setShowUserDropdown(!showUserDropdown)}>
                            <div className={styles.avatarCircle}>H</div>
                            {showUserDropdown && <UserDropdown onClose={() => setShowUserDropdown(false)} />}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Row: Dashboard Toolbar */}
            <div className={styles.bottomRow}>
                <div className={styles.left}>
                    <div className={styles.hamburger} onClick={toggleSidebar}>
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <nav className={styles.breadcrumbs}>
                        <a href="#">Home</a>
                        <span className={styles.sep}>›</span>
                        <a href="#">Dashboards</a>
                        <span className={styles.sep}>
                            <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="9 18 15 12 9 6"></polyline>
                            </svg>
                        </span>
                        <span className={styles.active}>PoF Protocol - System Metrics</span>
                    </nav>
                    <div className={styles.toolbarActions}>
                        <div className={styles.iconBtn} title="Star">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                            </svg>
                        </div>
                        <div className={styles.iconBtn} title="Share">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="18" cy="5" r="3"></circle>
                                <circle cx="6" cy="12" r="3"></circle>
                                <circle cx="18" cy="19" r="3"></circle>
                                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                            </svg>
                        </div>
                    </div>
                </div>

                <div className={styles.right}>
                    <div className={styles.toolbarControls}>
                        <button className={styles.addBtn}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="12" y1="5" x2="12" y2="19" />
                                <line x1="5" y1="12" x2="19" y2="12" />
                            </svg>
                            <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: '4px' }}>
                                <polyline points="6 9 12 15 18 9"></polyline>
                            </svg>
                        </button>
                        <div className={styles.iconBtn} title="Settings">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                                <circle cx="12" cy="12" r="3" />
                            </svg>
                        </div>
                        <div className={styles.refreshGroup}>
                            <div className={styles.iconBtn} title="Refresh">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M23 4v6h-6" />
                                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                                </svg>
                            </div>
                            <div className={styles.refreshInterval}>
                                30s
                                <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: '4px' }}>
                                    <polyline points="6 9 12 15 18 9"></polyline>
                                </svg>
                            </div>
                        </div>
                        <div className={styles.iconBtn} title="Monitor">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="4" width="18" height="12" rx="2" ry="2" />
                                <line x1="8" y1="20" x2="16" y2="20" />
                                <line x1="12" y1="16" x2="12" y2="20" />
                            </svg>
                        </div>
                        <div className={styles.iconBtn} title={isFullScreen ? "Exit Fullscreen" : "Full Screen"} onClick={toggleFullScreen}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                {isFullScreen ? (
                                    <>
                                        <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                                    </>
                                ) : (
                                    <>
                                        <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                                    </>
                                )}
                            </svg>
                        </div>
                        <div className={`${styles.iconBtn} ${!isTopRowVisible ? styles.activeToggle : ''}`} title={isTopRowVisible ? "Collapse Header" : "Expand Header"} onClick={() => setIsTopRowVisible(!isTopRowVisible)}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: isTopRowVisible ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 0.2s' }}>
                                <path d="M18 15l-6-6-6 6" />
                            </svg>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
