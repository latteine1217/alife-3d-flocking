import { useState, useEffect } from 'react';

/**
 * 簡化版 Canvas3D 用於測試初始化問題
 */
export function Canvas3DSimple() {
  const [isInitializing, setIsInitializing] = useState(true);
  const [message, setMessage] = useState('Starting...');

  useEffect(() => {
    console.log('🚀 useEffect triggered');
    
    const init = async () => {
      try {
        console.log('1. Checking WebGPU...');
        setMessage('Step 1: Checking WebGPU...');
        await new Promise(r => setTimeout(r, 500));
        
        console.log('2. Getting adapter...');
        setMessage('Step 2: Getting adapter...');
        await new Promise(r => setTimeout(r, 500));
        
        console.log('3. Getting device...');
        setMessage('Step 3: Getting device...');
        await new Promise(r => setTimeout(r, 500));
        
        console.log('4. Creating pipeline...');
        setMessage('Step 4: Creating pipeline...');
        await new Promise(r => setTimeout(r, 500));
        
        console.log('✅ Init complete, setting isInitializing to false');
        setMessage('Complete!');
        setIsInitializing(false);
        console.log('✅ State updated');
        
      } catch (err) {
        console.error('❌ Error:', err);
        setMessage(`Error: ${err}`);
        setIsInitializing(false);
      }
    };
    
    init();
  }, []);
  
  useEffect(() => {
    console.log('🔔 isInitializing changed:', isInitializing);
  }, [isInitializing]);
  
  console.log('🎨 Rendering, isInitializing =', isInitializing);
  
  if (isInitializing) {
    return (
      <div style={{ padding: '40px', background: '#222', color: '#fff' }}>
        <h2>⏳ Initializing...</h2>
        <p>{message}</p>
      </div>
    );
  }
  
  return (
    <div style={{ padding: '40px', background: '#222', color: '#0f0' }}>
      <h2>✅ Initialized!</h2>
      <p>{message}</p>
    </div>
  );
}
