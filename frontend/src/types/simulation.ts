/**
 * 模擬狀態資料結構
 * 對應 Backend Binary Protocol
 */

export interface SimulationState {
  // Header
  N: number;
  step: number;
  hasResources: boolean;
  hasObstacles: boolean;

  // Agent Data
  positions: Float32Array;   // N * 3
  velocities: Float32Array;  // N * 3
  types: Uint8Array;         // N
  energies: Float32Array;    // N
  targets: Int32Array;       // N
  groupLabels: Int32Array;   // N (NEW)

  // Statistics
  stats: {
    meanSpeed: number;
    stdSpeed: number;
    Rg: number;
    polarization: number;
    nGroups: number;
  };

  // Resources
  resources: Array<{
    position: [number, number, number];
    amount: number;
    radius: number;
    renewable: boolean;
  }>;
  
  // Group Statistics (NEW)
  groups: Array<{
    groupId: number;
    size: number;
    centroid: [number, number, number];
    velocity: [number, number, number];
    radius: number;
  }>;
}

/**
 * 模擬參數
 * 對應 Backend update_params payload
 */
export interface SimulationParams {
  // System Config
  systemType: '2D' | '3D' | 'Heterogeneous';
  N: number;
  
  // Physics
  Ca: number;    // Morse attraction
  Cr: number;    // Morse repulsion
  la: number;
  lr: number;
  rc: number;
  alpha: number; // Rayleigh friction
  v0: number;
  beta: number;  // Alignment
  eta: number;   // Noise
  boxSize: number;
  boundaryMode: 'pbc' | 'reflective' | 'absorbing';
  
  // Heterogeneity (optional)
  agentConfig?: {
    explorerRatio: number;
    followerRatio: number;
    enableFov: boolean;
    fovAngle: number;
    enableGoals: boolean;
    goalPosition: [number, number, number];
  };
  
  // Resources (optional)
  resources?: Array<{
    position: [number, number, number];
    amount: number;
    radius: number;
    renewable: boolean;
    replenishRate?: number;
    maxAmount?: number;
  }>;
}

/**
 * 控制命令類型
 */
export type ControlCommand =
  | { type: 'start' }
  | { type: 'pause' }
  | { type: 'reset' }
  | { type: 'update_params'; payload: SimulationParams };

/**
 * WebSocket 訊息類型
 */
export interface WSMessage {
  type: 'info' | 'error';
  message: string;
}

/**
 * Agent 類型常數
 */
export const AgentType = {
  FOLLOWER: 0,
  EXPLORER: 1,
  LEADER: 2,
} as const;

export type AgentTypeValue = typeof AgentType[keyof typeof AgentType];

/**
 * 預設參數
 */
export const DEFAULT_PARAMS: SimulationParams = {
  systemType: 'Heterogeneous',
  N: 100,
  Ca: 1.5,
  Cr: 2.0,
  la: 2.5,
  lr: 0.5,
  rc: 15.0,
  alpha: 2.0,
  v0: 1.0,
  beta: 1.0,
  eta: 0.0,
  boxSize: 50.0,
  boundaryMode: 'pbc',
  agentConfig: {
    explorerRatio: 0.3,
    followerRatio: 0.5,
    enableFov: true,
    fovAngle: 120.0,
    enableGoals: false,
    goalPosition: [0, 0, 0],
  },
};
