/**
 * GroupStatistics Component - Display active group information
 * 
 * 功能：
 * - 顯示當前活躍群組列表
 * - 展示群組 ID、大小、速度、位置
 * - 使用與 shader 相同的顏色 hash 顯示色塊
 */

import { useMemo } from 'react';
import { useSimulationStore } from '../store/simulation-store';

// 空陣列常量（避免每次 render 都創建新陣列）
const EMPTY_GROUPS: Array<{
  groupId: number;
  size: number;
  centroid: [number, number, number];
  velocity: [number, number, number];
  radius: number;
}> = [];

export function GroupStatistics() {
  const groups = useSimulationStore((state) => state.state?.groups ?? EMPTY_GROUPS);
  const selectedGroupId = useSimulationStore((state) => state.selectedGroupId);
  const selectGroup = useSimulationStore((state) => state.selectGroup);
  
  // 使用 useMemo 來避免不必要的重新計算
  const validGroups = useMemo(() => {
    return groups.filter(g => g.size >= 3);
  }, [groups]);
  
  // 按大小排序（使用 useMemo 避免每次 render 都排序）
  const sortedGroups = useMemo(() => {
    return [...validGroups].sort((a, b) => b.size - a.size);
  }, [validGroups]);
  
  // HSL to RGB 轉換（與 shader 相同）
  const hslToRgb = (h: number, s: number, l: number): string => {
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h * 6) % 2) - 1));
    const m = l - c / 2;
    
    let r = 0, g = 0, b = 0;
    const h6 = h * 6;
    
    if (h6 < 1) {
      r = c; g = x; b = 0;
    } else if (h6 < 2) {
      r = x; g = c; b = 0;
    } else if (h6 < 3) {
      r = 0; g = c; b = x;
    } else if (h6 < 4) {
      r = 0; g = x; b = c;
    } else if (h6 < 5) {
      r = x; g = 0; b = c;
    } else {
      r = c; g = 0; b = x;
    }
    
    r = Math.round((r + m) * 255);
    g = Math.round((g + m) * 255);
    b = Math.round((b + m) * 255);
    
    return `rgb(${r}, ${g}, ${b})`;
  };
  
  // Group ID to color（與 shader 相同的 hash）
  const groupToColor = (groupId: number): string => {
    const seed = groupId * 0.618033988749895; // Golden ratio
    const hue = seed - Math.floor(seed); // fract
    const saturation = 0.7;
    const lightness = 0.6;
    return hslToRgb(hue, saturation, lightness);
  };
  
  // 處理群組點擊
  const handleGroupClick = (groupId: number) => {
    // 如果點擊的是當前選中的群組，則取消選擇
    if (selectedGroupId === groupId) {
      selectGroup(null);
    } else {
      selectGroup(groupId);
    }
  };
  
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Groups ({sortedGroups.length})</h3>
      </div>
      
      {sortedGroups.length === 0 ? (
        <div style={styles.empty}>
          <p>No groups formed yet</p>
          <p style={styles.hint}>Wait for agents to cluster...</p>
        </div>
      ) : (
        <div style={styles.list}>
          {sortedGroups.map((group) => {
            const speed = Math.sqrt(
              group.velocity[0] ** 2 + 
              group.velocity[1] ** 2 + 
              group.velocity[2] ** 2
            );
            
            const isSelected = selectedGroupId === group.groupId;
            
            return (
              <div 
                key={group.groupId} 
                style={{
                  ...styles.groupCard,
                  ...(isSelected ? styles.groupCardSelected : {}),
                }}
                onClick={() => handleGroupClick(group.groupId)}
              >
                <div style={styles.groupHeader}>
                  <div
                    style={{
                      ...styles.colorSwatch,
                      backgroundColor: groupToColor(group.groupId),
                    }}
                  />
                  <span style={styles.groupId}>Group #{group.groupId}</span>
                </div>
                
                <div style={styles.groupStats}>
                  <div style={styles.stat}>
                    <span style={styles.statLabel}>Size:</span>
                    <span style={styles.statValue}>{group.size}</span>
                  </div>
                  <div style={styles.stat}>
                    <span style={styles.statLabel}>Speed:</span>
                    <span style={styles.statValue}>{speed.toFixed(2)}</span>
                  </div>
                  <div style={styles.stat}>
                    <span style={styles.statLabel}>Position:</span>
                    <span style={styles.statValue}>
                      ({group.centroid[0].toFixed(1)}, {group.centroid[1].toFixed(1)}, {group.centroid[2].toFixed(1)})
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// 樣式
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    borderRadius: '4px',
    overflow: 'hidden',
    maxHeight: '400px',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '12px',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
  },
  title: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#fff',
    fontFamily: 'monospace',
  },
  empty: {
    padding: '20px',
    textAlign: 'center',
    color: '#888',
    fontSize: '12px',
    fontFamily: 'monospace',
  },
  hint: {
    marginTop: '8px',
    fontSize: '11px',
    color: '#666',
  },
  list: {
    overflowY: 'auto',
    padding: '8px',
    flex: 1,
  },
  groupCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '4px',
    padding: '10px',
    marginBottom: '8px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  groupCardSelected: {
    backgroundColor: 'rgba(99, 179, 237, 0.2)',
    border: '2px solid #63b3ed',
    transform: 'scale(1.02)',
  },
  groupHeader: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '8px',
  },
  colorSwatch: {
    width: '16px',
    height: '16px',
    borderRadius: '2px',
    marginRight: '8px',
    border: '1px solid rgba(255, 255, 255, 0.3)',
  },
  groupId: {
    fontSize: '12px',
    fontWeight: 'bold',
    color: '#fff',
    fontFamily: 'monospace',
  },
  groupStats: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  stat: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
  statLabel: {
    color: '#aaa',
  },
  statValue: {
    color: '#fff',
    fontWeight: 'bold',
  },
};
