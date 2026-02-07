/**
 * Canvas3D Component - WebGPU 3D Visualization
 * 
 * 功能：
 * - 初始化 WebGPU renderer
 * - 處理滑鼠/滾輪事件（相機控制）
 * - 從 Zustand store 接收模擬資料並渲染
 * - 60 FPS 渲染循環
 */

import { useEffect, useRef, useState } from 'react';
import { WebGPURenderer } from '../lib/webgpu-renderer';
import { OrbitCamera } from '../lib/camera';
import { useSimulationStore } from '../store/simulation-store';

export function Canvas3D() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<WebGPURenderer | null>(null);
  const cameraRef = useRef<OrbitCamera | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  
  const simulationState = useSimulationStore((state) => state.state);
  const selectedGroupId = useSimulationStore((state) => state.selectedGroupId);
  
  // DEBUG: Log whenever simulationState changes
  useEffect(() => {
    console.log(`🟣 Canvas3D: simulationState changed:`, simulationState ? `N=${simulationState.N}` : 'null');
  }, [simulationState]);
  
  // 當選中的群組改變時，通知 renderer
  useEffect(() => {
    const renderer = rendererRef.current;
    if (renderer) {
      renderer.setSelectedGroupId(selectedGroupId);
    }
  }, [selectedGroupId]);
  
  const [isWebGPUSupported, setIsWebGPUSupported] = useState(true);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trailsEnabled, setTrailsEnabled] = useState(true);
  const [resourcesEnabled, setResourcesEnabled] = useState(true);
  const [colorMode, setColorMode] = useState<'type' | 'group'>('type'); // NEW: Color mode state
  const [groupBoundariesEnabled, setGroupBoundariesEnabled] = useState(false); // NEW: Group boundaries state
  const [groupArrowsEnabled, setGroupArrowsEnabled] = useState(false); // NEW: Group velocity arrows state
  
  // 滑鼠狀態
  const mouseStateRef = useRef({
    isLeftDown: false,
    isRightDown: false,
    lastX: 0,
    lastY: 0,
  });
  
  // 初始化 WebGPU
  useEffect(() => {
    console.log('🚀 Canvas3D useEffect triggered');
    const canvas = canvasRef.current;
    if (!canvas) {
      console.log('❌ Canvas ref is null, skipping initialization');
      return;
    }
    console.log('✅ Canvas ref obtained, proceeding with initialization');
    
    // 檢查 WebGPU 支援
    if (!navigator.gpu) {
      setIsWebGPUSupported(false);
      setIsInitializing(false);
      setError('WebGPU not supported. Please use Chrome 113+ or Edge 113+.');
      return;
    }
    
    const init = async () => {
      try {
        // 等待 DOM 完全渲染
        await new Promise((resolve) => setTimeout(resolve, 100));
        
        // 設定 canvas 大小
        const dpr = window.devicePixelRatio || 1;
        const width = canvas.clientWidth || 800;
        const height = canvas.clientHeight || 600;
        
        console.log(`📐 Canvas size: ${width}x${height}, DPR: ${dpr}`);
        
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        
        // 初始化 renderer
        console.log('🚀 Initializing WebGPU renderer...');
        const renderer = new WebGPURenderer();
        await renderer.init(canvas);
        rendererRef.current = renderer;
        
        // Debug: Expose to window for testing
        if (typeof window !== 'undefined') {
          (window as any).testRenderer = renderer;
        }
        
        // 初始化相機
        const camera = new OrbitCamera(
          undefined, // target = [0, 0, 0]
          150,       // distance
          45,        // azimuth
          30         // elevation
        );
        cameraRef.current = camera;
        
        console.log('🔄 Setting isInitializing to false...');
        setIsInitializing(false);
        console.log('✅ Canvas3D initialized');
        console.log('📊 Current state - isInitializing:', false, 'isWebGPUSupported:', isWebGPUSupported, 'error:', error);
        
        // 開始渲染循環
        startRenderLoop();
      } catch (err) {
        console.error('❌ WebGPU initialization failed:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        setIsInitializing(false);
      }
    };
    
    init();
    
    // 清理
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (rendererRef.current) {
        rendererRef.current.destroy();
      }
    };
  }, []);
  
  // 監聽初始化狀態變化（debug）
  useEffect(() => {
    console.log('🔔 isInitializing changed to:', isInitializing);
  }, [isInitializing]);
  
  // 渲染循環
  const startRenderLoop = () => {
    const render = () => {
      const canvas = canvasRef.current;
      const renderer = rendererRef.current;
      const camera = cameraRef.current;
      
      if (!canvas || !renderer || !camera) {
        animationFrameRef.current = requestAnimationFrame(render);
        return;
      }
      
      // 🔧 FIX: 每幀從 store 直接讀取最新狀態，避免 closure 陷阱
      const currentState = useSimulationStore.getState().state;
      
      // 如果有新的模擬資料，更新粒子
      if (currentState && currentState.N > 0) {
        // DEBUG: 每秒記錄一次
        if (Math.random() < 0.016) {
          console.log(`🔔 Canvas3D calling updateParticles: N=${currentState.N}, positions.length=${currentState.positions.length}`);
        }
        renderer.updateParticles({
          positions: currentState.positions,
          velocities: currentState.velocities,
          types: currentState.types,
          groupLabels: currentState.groupLabels, // NEW: Pass group labels
          boxSize: useSimulationStore.getState().params.boxSize || 50.0, // 動態讀取 boxSize
          resources: currentState.hasResources ? currentState.resources : undefined,
          groups: currentState.groups, // NEW: Pass group statistics
        });
      } else {
        // DEBUG: 每秒記錄一次
        if (Math.random() < 0.016) {
          console.log(`⚠️ Canvas3D skipping updateParticles: state=${!!currentState}, N=${currentState?.N}`);
        }
      }
      
      // 計算矩陣
      const aspect = canvas.width / canvas.height;
      const viewMatrix = camera.getViewMatrix();
      const projMatrix = camera.getProjectionMatrix(aspect);
      
      // 渲染（始終渲染，即使是測試粒子）
      renderer.render(viewMatrix, projMatrix);
      
      animationFrameRef.current = requestAnimationFrame(render);
    };
    
    render();
  };
  
  // 處理滑鼠按下
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const mouseState = mouseStateRef.current;
    
    if (e.button === 0) {
      // 左鍵：旋轉
      mouseState.isLeftDown = true;
    } else if (e.button === 2) {
      // 右鍵：平移
      mouseState.isRightDown = true;
      e.preventDefault();
    }
    
    mouseState.lastX = e.clientX;
    mouseState.lastY = e.clientY;
  };
  
  // 處理滑鼠移動
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const mouseState = mouseStateRef.current;
    const camera = cameraRef.current;
    
    if (!camera) return;
    
    const dx = e.clientX - mouseState.lastX;
    const dy = e.clientY - mouseState.lastY;
    
    if (mouseState.isLeftDown) {
      // 旋轉
      camera.rotate(dx, dy);
    } else if (mouseState.isRightDown) {
      // 平移
      const canvas = canvasRef.current;
      if (canvas) {
        camera.pan(dx, dy, canvas.clientWidth);
      }
    }
    
    mouseState.lastX = e.clientX;
    mouseState.lastY = e.clientY;
  };
  
  // 處理滑鼠放開
  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const mouseState = mouseStateRef.current;
    
    if (e.button === 0) {
      mouseState.isLeftDown = false;
    } else if (e.button === 2) {
      mouseState.isRightDown = false;
    }
  };
  
  // 禁用右鍵選單
  const handleContextMenu = (e: React.MouseEvent<HTMLCanvasElement>) => {
    e.preventDefault();
  };
  
  // 視窗大小變化時調整 canvas
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const renderer = rendererRef.current;
      if (!canvas || !renderer) return;
      
      const dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth * dpr;
      const height = canvas.clientHeight * dpr;
      
      renderer.resize(width, height);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // 添加原生 wheel 事件監聽器（支援 preventDefault）
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const handleWheel = (e: WheelEvent) => {
      const camera = cameraRef.current;
      if (!camera) return;
      
      e.preventDefault();
      
      // 正值 = 縮小，負值 = 放大
      const delta = e.deltaY > 0 ? 0.1 : -0.1;
      camera.zoom(delta);
    };
    
    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheel);
  }, []);
  
  // 重置相機
  const handleResetCamera = () => {
    const camera = cameraRef.current;
    if (camera) {
      camera.reset();
      console.log('🔄 Camera reset to default position');
    }
  };
  
  // 切換 trails
  const handleToggleTrails = () => {
    const renderer = rendererRef.current;
    if (renderer) {
      const newState = !trailsEnabled;
      renderer.setEnableTrails(newState);
      setTrailsEnabled(newState);
      console.log(`🎨 Trails ${newState ? 'enabled' : 'disabled'}`);
    }
  };
  
  // 切換 resources
  const handleToggleResources = () => {
    const renderer = rendererRef.current;
    if (renderer) {
      const newState = !resourcesEnabled;
      renderer.setEnableResources(newState);
      setResourcesEnabled(newState);
      console.log(`💎 Resources ${newState ? 'enabled' : 'disabled'}`);
    }
  };
  
  // 切換 color mode (NEW)
  const handleToggleColorMode = () => {
    const renderer = rendererRef.current;
    if (renderer) {
      const newMode = colorMode === 'type' ? 'group' : 'type';
      renderer.setColorMode(newMode);
      setColorMode(newMode);
      console.log(`🎨 Color mode: ${newMode}`);
    }
  };
  
  // 切換 group boundaries (NEW)
  const handleToggleGroupBoundaries = () => {
    const renderer = rendererRef.current;
    if (renderer) {
      const newState = !groupBoundariesEnabled;
      renderer.setEnableGroupBoundaries(newState);
      setGroupBoundariesEnabled(newState);
      console.log(`🔮 Group boundaries ${newState ? 'enabled' : 'disabled'}`);
    }
  };
  
  // 切換 group velocity arrows (NEW)
  const handleToggleGroupArrows = () => {
    const renderer = rendererRef.current;
    if (renderer) {
      const newState = !groupArrowsEnabled;
      renderer.setEnableGroupVelocityArrows(newState);
      setGroupArrowsEnabled(newState);
      console.log(`➡️ Group arrows ${newState ? 'enabled' : 'disabled'}`);
    }
  };
  
  // 渲染 UI
  if (!isWebGPUSupported) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <h3>❌ WebGPU Not Supported</h3>
          <p>{error}</p>
          <p>Please use Chrome 113+ or Edge 113+</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <h3>❌ Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }
  
  return (
    <div style={styles.container}>
      {/* Canvas 始終渲染，這樣 ref 才能被賦值 */}
      <canvas
        ref={canvasRef}
        style={styles.canvas}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onContextMenu={handleContextMenu}
      />
      
      {/* Loading overlay（初始化時顯示） */}
      {isInitializing && (
        <div style={styles.loadingOverlay}>
          <div style={styles.loading}>
            <h3>⏳ Initializing WebGPU...</h3>
            <p style={{ marginTop: '10px', fontSize: '12px', color: '#888' }}>
              Check console (F12) for progress
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                marginTop: '20px',
                padding: '10px 20px',
                background: '#444',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              🔄 Refresh Page
            </button>
          </div>
        </div>
      )}
      
      {/* 控制按鈕（簡潔版） */}
      {!isInitializing && (
        <div style={styles.controls}>
          <button
            onClick={handleResetCamera}
            style={{
              padding: '8px 16px',
              backgroundColor: '#4299e1',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              width: '100%',
            }}
          >
            🔄 Reset Camera
          </button>
          
          <button
            onClick={handleToggleTrails}
            style={{
              marginTop: '8px',
              padding: '8px 16px',
              backgroundColor: trailsEnabled ? '#48bb78' : '#4a5568',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              width: '100%',
            }}
          >
            {trailsEnabled ? '✨ Trails' : '⭕ Trails'}
          </button>
          
          <button
            onClick={handleToggleColorMode}
            style={{
              marginTop: '8px',
              padding: '8px 16px',
              backgroundColor: colorMode === 'group' ? '#9f7aea' : '#ed8936',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              width: '100%',
            }}
          >
            {colorMode === 'type' ? '🎭 By Type' : '🌈 By Group'}
          </button>
          
          <button
            onClick={handleToggleGroupBoundaries}
            style={{
              marginTop: '8px',
              padding: '8px 16px',
              backgroundColor: groupBoundariesEnabled ? '#805ad5' : '#4a5568',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              width: '100%',
            }}
          >
            {groupBoundariesEnabled ? '🔮 Boundaries' : '⭕ Boundaries'}
          </button>
          
          <button
            onClick={handleToggleGroupArrows}
            style={{
              marginTop: '8px',
              padding: '8px 16px',
              backgroundColor: groupArrowsEnabled ? '#38b2ac' : '#4a5568',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              width: '100%',
            }}
          >
            {groupArrowsEnabled ? '➡️ Arrows' : '⭕ Arrows'}
          </button>
          
          <button
            onClick={handleToggleResources}
            style={{
              marginTop: '8px',
              padding: '8px 16px',
              backgroundColor: resourcesEnabled ? '#38a169' : '#4a5568',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              width: '100%',
            }}
          >
            {resourcesEnabled ? '💎 Resources' : '⭕ Resources'}
          </button>
        </div>
      )}
      
      {/* 粒子數量顯示 */}
      {!isInitializing && simulationState && (
        <div style={styles.info}>
          <p>Particles: {simulationState.N}</p>
          <p>Step: {simulationState.step}</p>
        </div>
      )}
    </div>
  );
}

// 樣式
const styles = {
  container: {
    position: 'relative' as const,
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0a0a0a',
  },
  canvas: {
    width: '100%',
    height: '100%',
    cursor: 'grab',
  },
  loadingOverlay: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(10, 10, 10, 0.95)',
    zIndex: 1000,
  },
  loading: {
    textAlign: 'center' as const,
    color: '#888',
  },
  error: {
    textAlign: 'center' as const,
    color: '#f88',
    padding: '20px',
  },
  controls: {
    position: 'absolute' as const,
    bottom: '10px',
    right: '10px',  // 改到右下角
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    color: '#fff',
    padding: '10px',
    borderRadius: '4px',
    fontSize: '12px',
    fontFamily: 'monospace',
    maxWidth: '200px',
  },
  info: {
    position: 'absolute' as const,
    top: '10px',
    left: '10px',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    color: '#fff',
    padding: '10px',
    borderRadius: '4px',
    fontSize: '12px',
    fontFamily: 'monospace',
  },
};
