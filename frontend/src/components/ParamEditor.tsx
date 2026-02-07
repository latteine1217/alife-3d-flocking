/**
 * Parameter Editor Component
 * 動態調整模擬參數
 */

import { useState } from 'react';
import { useSimulationStore } from '../store/simulation-store';

export function ParamEditor() {
  const { params, updateParams, isConnected } = useSimulationStore();
  const [isExpanded, setIsExpanded] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<number>(0);

  const handleChange = (key: string, value: number) => {
    updateParams({ [key]: value });
    setLastUpdateTime(Date.now());
  };

  const sliderStyle = {
    width: '100%',
    height: '4px',
    borderRadius: '2px',
    outline: 'none',
    cursor: 'pointer',
  };

  const labelStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '5px',
    fontSize: '12px',
    color: '#a0aec0',
  };

  const sectionStyle = {
    marginBottom: '20px',
    paddingBottom: '15px',
    borderBottom: '1px solid #2d3748',
  };

  return (
    <div
      style={{
        padding: '20px',
        backgroundColor: '#1a1a1a',
        borderRadius: '8px',
        marginBottom: '20px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '15px',
        }}
      >
        <h2 style={{ margin: 0, color: '#fff' }}>Parameters</h2>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            padding: '6px 12px',
            backgroundColor: '#2d3748',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          {isExpanded ? '▲ Collapse' : '▼ Expand'}
        </button>
      </div>

      {!isConnected && (
        <div
          style={{
            padding: '10px',
            backgroundColor: '#742a2a',
            borderRadius: '4px',
            color: '#fed7d7',
            fontSize: '12px',
            marginBottom: '10px',
          }}
        >
          ⚠️ Connect to server to adjust parameters
        </div>
      )}
      
      {isConnected && Date.now() - lastUpdateTime < 2000 && (
        <div
          style={{
            padding: '10px',
            backgroundColor: '#2f855a',
            borderRadius: '4px',
            color: '#c6f6d5',
            fontSize: '12px',
            marginBottom: '10px',
          }}
        >
          ✅ Parameters updated! System will reinitialize.
        </div>
      )}

      {isExpanded && (
        <div style={{ opacity: isConnected ? 1 : 0.5 }}>
          {/* Physics Parameters */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, fontSize: '14px', color: '#fff' }}>
              Physics
            </h3>

            {/* Ca - Morse Attraction */}
            <div style={{ marginBottom: '15px' }}>
              <div style={labelStyle}>
                <span>Ca (Attraction)</span>
                <strong style={{ color: '#fff' }}>{params.Ca.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="0.1"
                value={params.Ca}
                onChange={(e) => handleChange('Ca', parseFloat(e.target.value))}
                disabled={!isConnected}
                style={sliderStyle}
              />
            </div>

            {/* Cr - Morse Repulsion */}
            <div style={{ marginBottom: '15px' }}>
              <div style={labelStyle}>
                <span>Cr (Repulsion)</span>
                <strong style={{ color: '#fff' }}>{params.Cr.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="0.1"
                value={params.Cr}
                onChange={(e) => handleChange('Cr', parseFloat(e.target.value))}
                disabled={!isConnected}
                style={sliderStyle}
              />
            </div>

            {/* v0 - Preferred Speed */}
            <div style={{ marginBottom: '15px' }}>
              <div style={labelStyle}>
                <span>v₀ (Preferred Speed)</span>
                <strong style={{ color: '#fff' }}>{params.v0.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="0.1"
                value={params.v0}
                onChange={(e) => handleChange('v0', parseFloat(e.target.value))}
                disabled={!isConnected}
                style={sliderStyle}
              />
            </div>

            {/* alpha - Friction */}
            <div style={{ marginBottom: '15px' }}>
              <div style={labelStyle}>
                <span>α (Friction)</span>
                <strong style={{ color: '#fff' }}>{params.alpha.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="0.1"
                value={params.alpha}
                onChange={(e) => handleChange('alpha', parseFloat(e.target.value))}
                disabled={!isConnected}
                style={sliderStyle}
              />
            </div>

            {/* beta - Alignment */}
            <div style={{ marginBottom: '15px' }}>
              <div style={labelStyle}>
                <span>β (Alignment)</span>
                <strong style={{ color: '#fff' }}>{params.beta.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="0.1"
                value={params.beta}
                onChange={(e) => handleChange('beta', parseFloat(e.target.value))}
                disabled={!isConnected}
                style={sliderStyle}
              />
            </div>

            {/* eta - Noise */}
            <div style={{ marginBottom: '15px' }}>
              <div style={labelStyle}>
                <span>η (Noise)</span>
                <strong style={{ color: '#fff' }}>{params.eta.toFixed(2)}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={params.eta}
                onChange={(e) => handleChange('eta', parseFloat(e.target.value))}
                disabled={!isConnected}
                style={sliderStyle}
              />
            </div>
          </div>

          {/* Agent Configuration */}
          {params.agentConfig && (
            <div style={sectionStyle}>
              <h3 style={{ marginTop: 0, fontSize: '14px', color: '#fff' }}>
                Agent Ratios
              </h3>

              {/* Explorer Ratio */}
              <div style={{ marginBottom: '15px' }}>
                <div style={labelStyle}>
                  <span>Explorer Ratio (Orange)</span>
                  <strong style={{ color: '#fff' }}>
                    {(params.agentConfig.explorerRatio * 100).toFixed(0)}%
                  </strong>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.agentConfig.explorerRatio}
                  onChange={(e) => {
                    const newRatio = parseFloat(e.target.value);
                    updateParams({
                      agentConfig: {
                        ...params.agentConfig!,
                        explorerRatio: newRatio,
                      },
                    });
                    setLastUpdateTime(Date.now());
                  }}
                  disabled={!isConnected}
                  style={sliderStyle}
                />
              </div>

              {/* Follower Ratio */}
              <div style={{ marginBottom: '15px' }}>
                <div style={labelStyle}>
                  <span>Follower Ratio (Blue)</span>
                  <strong style={{ color: '#fff' }}>
                    {(params.agentConfig.followerRatio * 100).toFixed(0)}%
                  </strong>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.agentConfig.followerRatio}
                  onChange={(e) => {
                    const newRatio = parseFloat(e.target.value);
                    updateParams({
                      agentConfig: {
                        ...params.agentConfig!,
                        followerRatio: newRatio,
                      },
                    });
                    setLastUpdateTime(Date.now());
                  }}
                  disabled={!isConnected}
                  style={sliderStyle}
                />
              </div>

              {/* FOV Angle */}
              <div style={{ marginBottom: '15px' }}>
                <div style={labelStyle}>
                  <span>FOV Angle (degrees)</span>
                  <strong style={{ color: '#fff' }}>
                    {params.agentConfig.fovAngle.toFixed(0)}°
                  </strong>
                </div>
                <input
                  type="range"
                  min="30"
                  max="360"
                  step="10"
                  value={params.agentConfig.fovAngle}
                  onChange={(e) => {
                    const newAngle = parseFloat(e.target.value);
                    updateParams({
                      agentConfig: {
                        ...params.agentConfig!,
                        fovAngle: newAngle,
                      },
                    });
                    setLastUpdateTime(Date.now());
                  }}
                  disabled={!isConnected}
                  style={sliderStyle}
                />
              </div>
            </div>
          )}

          {/* Quick Presets */}
          <div>
            <h3 style={{ marginTop: 0, fontSize: '14px', color: '#fff' }}>
              Quick Presets
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <button
                onClick={() => {
                  updateParams({
                    Ca: 1.5,
                    Cr: 2.0,
                    v0: 1.0,
                    alpha: 2.0,
                    beta: 1.0,
                    eta: 0.0,
                  });
                  setLastUpdateTime(Date.now());
                }}
                disabled={!isConnected}
                style={{
                  padding: '8px',
                  backgroundColor: '#4299e1',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isConnected ? 'pointer' : 'not-allowed',
                  fontSize: '11px',
                  opacity: isConnected ? 1 : 0.5,
                }}
              >
                Orderly
              </button>

              <button
                onClick={() => {
                  updateParams({
                    Ca: 1.0,
                    Cr: 1.5,
                    v0: 1.5,
                    alpha: 1.5,
                    beta: 2.0,
                    eta: 0.1,
                  });
                  setLastUpdateTime(Date.now());
                }}
                disabled={!isConnected}
                style={{
                  padding: '8px',
                  backgroundColor: '#f6ad55',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isConnected ? 'pointer' : 'not-allowed',
                  fontSize: '11px',
                  opacity: isConnected ? 1 : 0.5,
                }}
              >
                Flocking
              </button>

              <button
                onClick={() => {
                  updateParams({
                    Ca: 0.5,
                    Cr: 3.0,
                    v0: 2.0,
                    alpha: 1.0,
                    beta: 0.5,
                    eta: 0.3,
                  });
                  setLastUpdateTime(Date.now());
                }}
                disabled={!isConnected}
                style={{
                  padding: '8px',
                  backgroundColor: '#fc8181',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isConnected ? 'pointer' : 'not-allowed',
                  fontSize: '11px',
                  opacity: isConnected ? 1 : 0.5,
                }}
              >
                Chaotic
              </button>

              <button
                onClick={() => {
                  updateParams({
                    Ca: 2.5,
                    Cr: 1.0,
                    v0: 0.5,
                    alpha: 3.0,
                    beta: 0.1,
                    eta: 0.0,
                  });
                  setLastUpdateTime(Date.now());
                }}
                disabled={!isConnected}
                style={{
                  padding: '8px',
                  backgroundColor: '#9f7aea',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isConnected ? 'pointer' : 'not-allowed',
                  fontSize: '11px',
                  opacity: isConnected ? 1 : 0.5,
                }}
              >
                Clustering
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
