import { useEffect, useState } from 'react';
import { useSimulationStore } from './store/simulation-store';
import { ControlPanel } from './components/ControlPanel';
import { ParamEditor } from './components/ParamEditor';
import { Statistics } from './components/Statistics';
import { GroupStatistics } from './components/GroupStatistics';
import { Canvas3D } from './components/Canvas3D';
import { SystemBalanceCharts } from './components/SystemBalanceCharts';
import './App.css';

function App() {
  const { connect, disconnect, isConnected, state } = useSimulationStore();
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (state) {
      console.log(`Frame ${state.step}: N=${state.N}, Polarization=${state.stats.polarization.toFixed(3)}`);
    }
  }, [state]);

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      await connect();
      console.log('Successfully connected to server');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect';
      setError(errorMsg);
      console.error('Connection failed:', err);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = () => {
    disconnect();
    setError(null);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Flocking Control Station</h1>
          <p>Heterogeneous 3D Agent-Based Model with WebSocket + WebGPU</p>
        </div>
        {isConnected && (
          <button className="disconnect-btn" onClick={handleDisconnect}>
            Disconnect
          </button>
        )}
      </header>

      {!isConnected && (
        <section className="connect-panel">
          <h2>Connect to Backend</h2>
          <p>Make sure server is running at <code>ws://localhost:8765</code></p>
          <button
            className="connect-btn"
            onClick={handleConnect}
            disabled={isConnecting}
          >
            {isConnecting ? 'Connecting...' : 'Connect'}
          </button>

          {error && (
            <div className="connect-error">
              <strong>Error:</strong> {error}
              <div>Start backend: <code>./backend/start_server.sh</code></div>
            </div>
          )}
        </section>
      )}

      {isConnected && (
        <>
          <section className="app-main-grid">
            <aside className="side-panel left-panel">
              <ControlPanel />
              <ParamEditor />
              <GroupStatistics />
            </aside>

            <section className="canvas-panel">
              <Canvas3D />
            </section>
          </section>

          <section className="analytics-stack">
            <Statistics />
            <SystemBalanceCharts />
          </section>
        </>
      )}

      <footer className="app-footer">
        <p>Backend: Python + Taichi + WebSocket | Frontend: React + TypeScript + Zustand + WebGPU</p>
      </footer>
    </div>
  );
}

export default App;
