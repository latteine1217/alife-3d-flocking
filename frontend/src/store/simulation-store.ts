/**
 * Zustand Store
 * 全域狀態管理
 */

import { create } from 'zustand';
import type { SimulationState, SimulationParams } from '../types/simulation';
import { DEFAULT_PARAMS } from '../types/simulation';
import { FlockingWebSocket } from '../lib/websocket-client';

interface SimulationStore {
  // WebSocket
  ws: FlockingWebSocket | null;
  isConnected: boolean;
  
  // Simulation state
  state: SimulationState | null;
  params: SimulationParams;
  isRunning: boolean;
  isInitialized: boolean; // 是否已初始化系統
  
  // UI state
  selectedGroupId: number | null; // 當前選中的群組 ID
  
  // Stats
  fps: number;
  bandwidth: number; // KB/s
  
  // Actions
  connect: (url?: string) => Promise<void>;
  disconnect: () => void;
  init: () => void;
  toggleRunning: () => void;
  stop: () => void;
  updateParams: (params: Partial<SimulationParams>) => void;
  setState: (state: SimulationState) => void;
  selectGroup: (groupId: number | null) => void; // 選擇群組
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  // Initial state
  ws: null,
  isConnected: false,
  state: null,
  params: DEFAULT_PARAMS,
  isRunning: false,
  isInitialized: false,
  selectedGroupId: null,
  fps: 0,
  bandwidth: 0,

  /**
   * 連線到 Backend
   */
  connect: async (url = 'ws://localhost:8765') => {
    const { ws: existingWs } = get();
    
    // 如果已連線，先斷開
    if (existingWs) {
      existingWs.disconnect();
    }

    // 建立新連線
    const ws = new FlockingWebSocket(url);

    // 註冊事件處理
    ws.onConnect(() => {
      console.log('Store: Connected to server');
      set({ isConnected: true });
      
      // 連接成功後立即發送初始化參數
      const { params } = get();
      console.log('📤 Sending initial params:', params);
      ws.send({
        type: 'update_params',
        payload: params,
      });
      
      // 標記為已初始化
      set({ isInitialized: true });
      console.log('🎯 System auto-initialized');
    });

    ws.onDisconnect(() => {
      console.log('Store: Disconnected from server');
      set({ isConnected: false, isRunning: false });
    });

    ws.onState((state) => {
      console.log(`🟢 Store: onState callback triggered! N=${state.N}, positions.length=${state.positions.length}`);
      
      // 更新狀態
      set({ state });
      
      // DEBUG: Verify state was actually set
      const currentState = get().state;
      console.log(`🟢 Store: state updated in store. Verification: state.N=${currentState?.N}`);
      
      // 更新 FPS
      const stats = ws.getStats();
      set({ 
        fps: Math.round(stats.fps * 10) / 10,
        bandwidth: Math.round(stats.avgFrameSize * stats.fps / 1024 * 10) / 10,
      });
    });

    ws.onError((error) => {
      console.error('Store: WebSocket error', error);
    });

    // 連線
    try {
      await ws.connect();
      set({ ws });
    } catch (error) {
      console.error('Store: Failed to connect', error);
      throw error;
    }
  },

  /**
   * 斷開連線
   */
  disconnect: () => {
    const { ws } = get();
    if (ws) {
      ws.disconnect();
      set({ 
        ws: null, 
        isConnected: false, 
        isRunning: false, 
        isInitialized: false,
        state: null 
      });
    }
  },

  /**
   * 初始化模擬系統
   */
  init: () => {
    const { ws, isConnected } = get();
    if (!ws || !isConnected) {
      console.error('Not connected to server');
      return;
    }

    // 發送初始化命令（重置系統）
    ws.send({ type: 'reset' });
    set({ isInitialized: true, isRunning: false });
    console.log('🎯 System initialized');
  },

  /**
   * 切換運行/暫停
   */
  toggleRunning: () => {
    const { ws, isConnected, isInitialized, isRunning } = get();
    if (!ws || !isConnected || !isInitialized) {
      console.error('System not ready');
      return;
    }

    if (isRunning) {
      // 暫停
      ws.send({ type: 'pause' });
      set({ isRunning: false });
      console.log('⏸ Simulation paused');
    } else {
      // 啟動
      ws.send({ type: 'start' });
      set({ isRunning: true });
      console.log('▶ Simulation started');
    }
  },

  /**
   * 停止模擬（清空狀態）
   */
  stop: () => {
    const { ws, isConnected } = get();
    if (!ws || !isConnected) {
      console.error('Not connected to server');
      return;
    }

    // 暫停 + 清空本地狀態
    ws.send({ type: 'pause' });
    set({ 
      isRunning: false, 
      isInitialized: false, 
      state: null,
      fps: 0,
      bandwidth: 0
    });
    console.log('⏹ Simulation stopped');
  },

  /**
   * 更新參數
   */
  updateParams: (newParams: Partial<SimulationParams>) => {
    const { ws, isConnected, params } = get();
    
    // 合併參數
    const updatedParams = { ...params, ...newParams };
    set({ params: updatedParams });

    // 如果已連線，發送更新命令
    if (ws && isConnected) {
      ws.send({
        type: 'update_params',
        payload: updatedParams,
      });
    }
  },

  /**
   * 直接設定狀態（用於測試）
   */
  setState: (state: SimulationState) => {
    console.log('🔧 setState called manually with N=', state.N);
    set({ state });
  },

  /**
   * 選擇群組（用於高亮顯示）
   */
  selectGroup: (groupId: number | null) => {
    set({ selectedGroupId: groupId });
    console.log('🎯 Selected group:', groupId);
  },
}));

// Export for browser console testing
if (typeof window !== 'undefined') {
  (window as any).testStore = useSimulationStore;
}
