"use client";

import styles from './grafana.module.css';

export default function GrafanaDashboard() {
    return (
        <div className={styles.grafanaContainer}>
            <div className={styles.grafanaHeader}>
                <div className={styles.breadcrumbs}>
                    <span>Dashboards</span>
                    <span>›</span>
                    <span>GrafanaCloud</span>
                    <span>›</span>
                    <span className={styles.activeBreadcrumb}>Usage Insights - 1 - Overview</span>
                    <span className={styles.star}>☆</span>
                </div>
                <div className={styles.headerActions}>
                    <div className={styles.searchBox}>
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" /></svg>
                        <input type="text" placeholder="Search..." />
                        <span className={styles.kbd}>ctrl+k</span>
                    </div>
                    <div className={styles.timePicker}>
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" /></svg>
                        Last 24 hours ▾
                    </div>
                    <button className={styles.iconBtn}>
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" /></svg>
                        Refresh
                    </button>
                    <button className={`${styles.iconBtn} ${styles.blueBtn}`}>
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z" /></svg>
                        Share
                    </button>
                    <button className={styles.iconBtn}>Make editable</button>
                </div>
            </div>

            <div className={styles.dashboardBody}>
                <section className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <span>▾</span> Usage Insight KPI
                    </div>
                    <div className={styles.kpiGrid}>
                        <div className={styles.kpiCard}>
                            <div className={styles.cardHeader}>Total usage insights events</div>
                            <div className={styles.noData}>No data</div>
                        </div>
                        <div className={styles.kpiCard}>
                            <div className={styles.cardHeader}>Data sources Used</div>
                            <div className={styles.noData}>No data</div>
                        </div>
                        <div className={styles.kpiCard}>
                            <div className={styles.cardHeader}>Dashboards Used</div>
                            <div className={styles.noData}>No data</div>
                        </div>
                        <div className={styles.kpiCard}>
                            <div className={styles.cardHeader}>Users Seen</div>
                            <div className={styles.noData}>No data</div>
                        </div>
                    </div>
                </section>

                <section className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <span>▾</span> Usage Insight Details
                    </div>
                    <div className={styles.detailsGrid}>
                        <div className={`${styles.detailCard} ${styles.largeCard}`}>
                            <div className={styles.cardHeader}>Usage insights events</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>

                        <div className={styles.detailCard}>
                            <div className={styles.cardHeader}>Top 10 dashboards</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>
                        <div className={styles.detailCard}>
                            <div className={styles.cardHeader}>Top 10 data sources</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>
                        <div className={styles.detailCard}>
                            <div className={styles.cardHeader}>Top 10 users</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>

                        <div className={styles.detailCard}>
                            <div className={styles.cardHeader}>Top 10 dashboards with errors ⓘ</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>
                        <div className={styles.detailCard}>
                            <div className={styles.cardHeader}>Top 10 data sources with errors ⓘ</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>
                        <div className={styles.detailCard}>
                            <div className={styles.cardHeader}>Top 10 users seeing errors ⓘ</div>
                            <div className={styles.noDataText}>No data</div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
