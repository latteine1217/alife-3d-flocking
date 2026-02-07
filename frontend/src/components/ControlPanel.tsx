/**
 * Control Panel Component
 * 控制模擬的初始化、啟動/暫停、停止
 */

import { useSimulationStore } from '../store/simulation-store';

export function ControlPanel() {
  const { 
    isConnected, 
    isRunning, 
    isInitialized,
    init, 
    toggleRunning, 
    stop 
  } = useSimulationStore();

  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      marginBottom: '20px',
    }}>
      <h2 style={{ marginTop: 0, color: '#fff' }}>Controls</h2>
      
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {/* Init Button */}
        <button
          onClick={init}
          disabled={!isConnected || isInitialized}
          style={{
            padding: '12px 24px',
            fontSize: '16px',
            fontWeight: 'bold',
            backgroundColor: isInitialized ? '#4a5568' : '#4299e1',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: !isConnected || isInitialized ? 'not-allowed' : 'pointer',
            opacity: !isConnected || isInitialized ? 0.5 : 1,
            transition: 'all 0.2s',
          }}
        >
          🎯 Init
        </button>

        {/* Start/Pause Toggle Button */}
        <button
          onClick={toggleRunning}
          disabled={!isConnected || !isInitialized}
          style={{
            padding: '12px 24px',
            fontSize: '16px',
            fontWeight: 'bold',
            backgroundColor: !isInitialized ? '#4a5568' : (isRunning ? '#f6ad55' : '#48bb78'),
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: !isConnected || !isInitialized ? 'not-allowed' : 'pointer',
            opacity: !isConnected || !isInitialized ? 0.5 : 1,
            transition: 'all 0.2s',
          }}
        >
          {isRunning ? '⏸ Pause' : '▶ Start'}
        </button>

        {/* Stop Button */}
        <button
          onClick={stop}
          disabled={!isConnected || !isInitialized}
          style={{
            padding: '12px 24px',
            fontSize: '16px',
            fontWeight: 'bold',
            backgroundColor: !isInitialized ? '#4a5568' : '#fc8181',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: !isConnected || !isInitialized ? 'not-allowed' : 'pointer',
            opacity: !isConnected || !isInitialized ? 0.5 : 1,
            transition: 'all 0.2s',
          }}
        >
          ⏹ Stop
        </button>
      </div>

      {/* Connection Status */}
      <div style={{
        marginTop: '15px',
        padding: '10px',
        backgroundColor: isConnected ? '#22543d' : '#742a2a',
        borderRadius: '4px',
        color: '#fff',
        fontSize: '14px',
      }}>
        <strong>Status:</strong> {isConnected ? '✅ Connected' : '❌ Disconnected'}
        {isInitialized && ' • 🎯 Initialized'}
        {isRunning && ' • 🏃 Running'}
      </div>
    </div>
  );
}
