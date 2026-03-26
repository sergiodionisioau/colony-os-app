"use client";

import MarketTicker from "@/components/MarketTicker";
import ProfitChart from "@/components/ProfitChart";
import HITLApproval from "@/components/HITLApproval";
import GrafanaDashboard from "@/components/GrafanaDashboard";
import styles from "./page.module.css";
import { useState } from 'react';

export default function Home() {
  const [view, setView] = useState<'dashboard' | 'metrics'>('metrics');

  const handleAction = (action: string) => {
    console.log(`HITL Action: ${action}`);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.mainContent}>
        <MarketTicker />

        <div className={styles.viewSwitcher}>
          <button
            className={view === 'dashboard' ? styles.activeTab : styles.tab}
            onClick={() => setView('dashboard')}
          >
            CONTROL CENTER
          </button>
          <button
            className={view === 'metrics' ? styles.activeTab : styles.tab}
            onClick={() => setView('metrics')}
          >
            OBSERVABILITY (GRAFANA)
          </button>
        </div>

        {view === 'dashboard' ? (
          <>
            <div className={styles.dashboardHeader}>
              <div className={styles.titleSection}>
                <h1>Revenue Command Center</h1>
                <p>Real-time monitoring of autonomous agent fleets and market signals.</p>
              </div>
              <div className={styles.systemStatus}>
                <span className={styles.pulse}></span>
                SYSTEM ONLINE
              </div>
            </div>

            <div className={styles.grid}>
              <div className={styles.leftCol}>
                <div className={styles.statsGrid}>
                  <div className={styles.card}>
                    <h3>Active Pipelines</h3>
                    <div className={styles.stat}>24</div>
                    <div className={styles.trend}>+12% vs last 24h</div>
                  </div>
                  <div className={styles.card}>
                    <h3>Confidence Score</h3>
                    <div className={styles.stat}>94.2%</div>
                    <div className={styles.trend}>NOMINAL</div>
                  </div>
                </div>

                <div className={styles.hitlWrapper}>
                  <HITLApproval onAction={handleAction} />
                </div>
              </div>

              <div className={styles.rightCol}>
                <div className={styles.terminal}>
                  <div className={styles.terminalHeader}>
                    <span>AGENT_FLEET_MONITOR.log</span>
                    <div className={styles.terminalDots}>
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                  <div className={styles.terminalBody}>
                    <p className={styles.log}>[2026-03-13 17:52:23] INITIALIZING Agent(Prospector-01)...</p>
                    <p className={styles.log}>[2026-03-13 17:52:25] SCANNED 42 entities in 1.2s</p>
                    <p className={styles.log}>[2026-03-13 17:52:27] <span className={styles.high}>HIGH_INTENT</span> DETECTED: ent_9901 (Funding Signal)</p>
                    <p className={styles.log}>[2026-03-13 17:52:28] STAGING Pipeline (PIPE_ent_9901_0)...</p>
                    <p className={styles.log}>[2026-03-13 17:52:30] WAITING_FOR_HITL_APPROVAL...</p>
                    <p className={styles.logLine}>_</p>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <GrafanaDashboard />
        )}
      </div>
    </div>
  );
}
