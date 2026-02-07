/**
 * Statistics Component
 * 顯示模擬統計資訊
 */

import { useSimulationStore } from '../store/simulation-store';

export function Statistics() {
  const { state, fps, bandwidth } = useSimulationStore();

  if (!state) {
    return (
      <div style={{
        padding: '20px',
        backgroundColor: '#1a1a1a',
        borderRadius: '8px',
        color: '#888',
        textAlign: 'center',
      }}>
        No simulation data
      </div>
    );
  }

  const { N, step, stats } = state;

  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
    }}>
      <h2 style={{ marginTop: 0, color: '#fff' }}>Statistics</h2>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
      }}>
        {/* System Info */}
        <StatCard label="Particles" value={N.toString()} />
        <StatCard label="Step" value={step.toString()} />
        <StatCard label="FPS" value={fps.toFixed(1)} color="#48bb78" />
        <StatCard label="Bandwidth" value={`${bandwidth.toFixed(1)} KB/s`} />
        
        {/* Physics Stats */}
        <StatCard 
          label="Mean Speed" 
          value={stats.meanSpeed.toFixed(3)} 
          subtitle={`± ${stats.stdSpeed.toFixed(3)}`}
        />
        <StatCard 
          label="Polarization" 
          value={stats.polarization.toFixed(3)} 
          color={stats.polarization > 0.5 ? '#48bb78' : '#fc8181'}
        />
        <StatCard label="Rg" value={stats.Rg.toFixed(2)} />
        <StatCard label="Groups" value={stats.nGroups.toString()} />
      </div>

      {/* Agent Types Distribution */}
      <AgentDistribution types={state.types} />
    </div>
  );
}

/**
 * Individual stat card
 */
function StatCard({ 
  label, 
  value, 
  subtitle, 
  color = '#fff' 
}: { 
  label: string; 
  value: string; 
  subtitle?: string;
  color?: string;
}) {
  return (
    <div style={{
      padding: '15px',
      backgroundColor: '#2d3748',
      borderRadius: '6px',
    }}>
      <div style={{
        fontSize: '12px',
        color: '#a0aec0',
        marginBottom: '5px',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '24px',
        fontWeight: 'bold',
        color,
      }}>
        {value}
      </div>
      {subtitle && (
        <div style={{
          fontSize: '14px',
          color: '#718096',
          marginTop: '2px',
        }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}

/**
 * Agent type distribution
 */
function AgentDistribution({ types }: { types: Uint8Array }) {
  // Count agent types
  const counts = { follower: 0, explorer: 0, leader: 0 };
  for (let i = 0; i < types.length; i++) {
    switch (types[i]) {
      case 0: counts.follower++; break;
      case 1: counts.explorer++; break;
      case 2: counts.leader++; break;
    }
  }

  const total = types.length;

  return (
    <div style={{
      marginTop: '20px',
      padding: '15px',
      backgroundColor: '#2d3748',
      borderRadius: '6px',
    }}>
      <h3 style={{ marginTop: 0, color: '#fff', fontSize: '16px' }}>
        Agent Types
      </h3>
      
      <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
        <TypeBadge 
          label="Follower" 
          count={counts.follower} 
          total={total}
          color="#63b3ed"
        />
        <TypeBadge 
          label="Explorer" 
          count={counts.explorer} 
          total={total}
          color="#f6ad55"
        />
        <TypeBadge 
          label="Leader" 
          count={counts.leader} 
          total={total}
          color="#fc8181"
        />
      </div>
    </div>
  );
}

function TypeBadge({ 
  label, 
  count, 
  total, 
  color 
}: { 
  label: string; 
  count: number; 
  total: number; 
  color: string;
}) {
  const percentage = total > 0 ? (count / total * 100).toFixed(1) : '0.0';
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
    }}>
      <div style={{
        width: '12px',
        height: '12px',
        backgroundColor: color,
        borderRadius: '50%',
      }} />
      <span style={{ color: '#fff', fontSize: '14px' }}>
        <strong>{label}:</strong> {count} ({percentage}%)
      </span>
    </div>
  );
}
