/**
 * Main App Component
 * Flocking Simulation WebSocket Client
 */

import { useEffect, useState } from 'react';
import { useSimulationStore } from './store/simulation-store';
import { ControlPanel } from './components/ControlPanel';
import { ParamEditor } from './components/ParamEditor';
import { Statistics } from './components/Statistics';
import { GroupStatistics } from './components/GroupStatistics';
import { Canvas3D } from './components/Canvas3D';
import './App.css';

function App() {
  const { connect, disconnect, isConnected, state } = useSimulationStore();
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Log state updates to console (for debugging)
  useEffect(() => {
    if (state) {
      console.log(`Frame ${state.step}: N=${state.N}, Polarization=${state.stats.polarization.toFixed(3)}`);
    }
  }, [state]);

  /**
   * 連線到伺服器
   */
  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      await connect();
      console.log('✅ Successfully connected to server');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect';
      setError(errorMsg);
      console.error('❌ Connection failed:', err);
    } finally {
      setIsConnecting(false);
    }
  };

  /**
   * 斷開連線
   */
  const handleDisconnect = () => {
    disconnect();
    setError(null);
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0f1419',
      color: '#fff',
      padding: '20px',
    }}>
      {/* Header */}
      <header style={{
        marginBottom: '30px',
        borderBottom: '2px solid #2d3748',
        paddingBottom: '20px',
      }}>
        <h1 style={{ margin: 0, fontSize: '32px' }}>
          🐦 Flocking Simulation
        </h1>
        <p style={{ margin: '10px 0 0 0', color: '#a0aec0' }}>
          Heterogeneous 3D Agent-Based Model with WebSocket + WebGPU
        </p>
      </header>

      {/* Connection Panel */}
      {!isConnected && (
        <div style={{
          padding: '30px',
          backgroundColor: '#1a1a1a',
          borderRadius: '8px',
          marginBottom: '20px',
          textAlign: 'center',
        }}>
          <h2 style={{ marginTop: 0 }}>Connect to Server</h2>
          <p style={{ color: '#a0aec0', marginBottom: '20px' }}>
            Make sure the backend server is running at <code>ws://localhost:8765</code>
          </p>

          <button
            onClick={handleConnect}
            disabled={isConnecting}
            style={{
              padding: '15px 40px',
              fontSize: '18px',
              fontWeight: 'bold',
              backgroundColor: isConnecting ? '#4a5568' : '#4299e1',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: isConnecting ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {isConnecting ? '⏳ Connecting...' : '🔌 Connect'}
          </button>

          {error && (
            <div style={{
              marginTop: '20px',
              padding: '15px',
              backgroundColor: '#742a2a',
              borderRadius: '6px',
              color: '#fed7d7',
            }}>
              <strong>Error:</strong> {error}
              <br />
              <br />
              <small>
                Start the backend with: <code>./backend/start_server.sh</code>
              </small>
            </div>
          )}
        </div>
      )}

      {/* Main Content */}
      {isConnected && (
        <>
          {/* Disconnect Button */}
          <div style={{ marginBottom: '20px', textAlign: 'right' }}>
            <button
              onClick={handleDisconnect}
              style={{
                padding: '10px 20px',
                fontSize: '14px',
                backgroundColor: '#742a2a',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              🔌 Disconnect
            </button>
          </div>

          {/* Grid Layout: Control | Canvas | Statistics */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '320px 1fr 320px',
            gap: '20px',
            height: '600px',
            marginBottom: '20px',
          }}>
            {/* Left: Control Panel + Param Editor + Group Statistics */}
            <div style={{ overflow: 'auto' }}>
              <ControlPanel />
              <ParamEditor />
              <div style={{ marginTop: '20px' }}>
                <GroupStatistics />
              </div>
            </div>

            {/* Center: 3D Canvas */}
            <div style={{
              backgroundColor: '#0a0a0a',
              borderRadius: '8px',
              overflow: 'hidden',
            }}>
              <Canvas3D />
            </div>

            {/* Right: Statistics */}
            <div style={{ overflow: 'auto' }}>
              <Statistics />
            </div>
          </div>

          {/* Debug Console */}
          <div style={{
            marginTop: '20px',
            padding: '20px',
            backgroundColor: '#1a1a1a',
            borderRadius: '8px',
            fontFamily: 'monospace',
            fontSize: '12px',
            color: '#a0aec0',
          }}>
            <h3 style={{ marginTop: 0, color: '#fff' }}>Debug Console</h3>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {state ? (
                `Frame: ${state.step}
Particles: ${state.N}
Position[0]: (${state.positions[0].toFixed(2)}, ${state.positions[1].toFixed(2)}, ${state.positions[2].toFixed(2)})
Velocity[0]: (${state.velocities[0].toFixed(2)}, ${state.velocities[1].toFixed(2)}, ${state.velocities[2].toFixed(2)})
Mean Speed: ${state.stats.meanSpeed.toFixed(3)}
Polarization: ${state.stats.polarization.toFixed(3)}
Rg: ${state.stats.Rg.toFixed(2)}
Groups: ${state.stats.nGroups}
Resources: ${state.resources.length}
Has Resources: ${state.hasResources}
Has Obstacles: ${state.hasObstacles}`
              ) : (
                'No data received yet...\nPress Start to begin simulation.'
              )}
            </pre>
          </div>
        </>
      )}

      {/* Footer */}
      <footer style={{
        marginTop: '40px',
        paddingTop: '20px',
        borderTop: '1px solid #2d3748',
        textAlign: 'center',
        color: '#718096',
        fontSize: '14px',
      }}>
        <p>
          Backend: Python + Taichi + WebSocket | Frontend: React + TypeScript + Zustand + WebGPU
        </p>
        <p style={{ margin: '5px 0 0 0' }}>
          WebGPU 3D visualization with orbit camera controls
        </p>
      </footer>
    </div>
  );
}

export default App;

