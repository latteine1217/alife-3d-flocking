# 系統改進分析報告

**日期**: 2026-02-06  
**當前狀態**: WebGPU 可視化基本功能完成，粒子渲染正常

---

## 📊 系統現況總結

### ✅ 已完成功能
1. **Backend (Python + Taichi)**
   - 完整的 3D Morse potential + Rayleigh friction 物理引擎
   - 異質性 agent (Follower/Explorer/Leader)
   - FOV (視野限制)、Goal seeking、Foraging system
   - Obstacle system (SDF-based)
   - Group detection (Label propagation)
   - WebSocket 即時資料串流 (~30 FPS)

2. **Frontend (React + WebGPU)**
   - WebGPU 粒子渲染器 (instanced billboards)
   - 軌跡系統 (40 幀歷史)
   - 速度向量可視化 (黃色箭頭)
   - Orbit camera 控制 (左鍵旋轉、右鍵平移、滾輪縮放)
   - WebSocket 客戶端 (自動重連、二進制反序列化)
   - Zustand 全域狀態管理
   - 即時統計面板 (FPS、頻寬、物理指標)

3. **已修復的 Bug**
   - ✅ Closure trap 導致渲染循環無法讀取最新狀態
   - ✅ Backend 啟動時未初始化系統
   - ✅ 粒子大小過大問題
   - ✅ Trail 過短不明顯問題

---

## 🔍 可改進項目 (按優先級排序)

### 🔴 Critical (核心功能缺失)

#### 1. **參數編輯器無法使用**
**問題**: `ParamEditor.tsx` 存在但未檢查功能是否正常
**影響**: 使用者無法即時調整物理參數，限制了探索性實驗
**建議修復**:
- 檢查參數更新流程 (frontend → WebSocket → backend)
- 確認 backend 是否正確處理 `update_params` 命令
- 添加參數驗證與即時反饋
**預估工作量**: 2-3 小時

#### 2. **無法動態新增/移除障礙物和資源**
**問題**: 障礙物和資源系統存在但無 UI 控制
**影響**: 無法展示 ABM 的完整能力
**建議修復**:
- 在 Canvas3D 添加點擊放置資源/障礙物功能
- 創建 Obstacle/Resource 編輯面板
- 實作 backend 的動態新增/移除 API
**預估工作量**: 4-6 小時

#### 3. **Group Detection 未視覺化**
**問題**: Backend 有群組檢測但前端未顯示
**影響**: 無法看到集群結構演化
**建議修復**:
- 在 WebGPU renderer 添加群組邊界框或連線
- 用不同顏色標示不同群組
- 在 Statistics 面板顯示群組資訊
**預估工作量**: 3-4 小時

---

### 🟠 High Priority (體驗改善)

#### 4. **缺少互動式教學 / 預設場景**
**問題**: 新使用者不知道該看什麼、調什麼參數
**建議新增**:
- 預設場景選單 (Chaos → Order transition, Swarming, Foraging, etc.)
- 引導式教學 (第一次連線時顯示)
- 每個參數的 tooltip 說明
**預估工作量**: 4-5 小時

#### 5. **視覺化效果單調**
**問題**: 只有藍色粒子 + 白色軌跡 + 黃色箭頭，缺乏層次感
**建議改善**:
- Trail 根據粒子類型顯示不同顏色
- 粒子大小根據 energy 動態變化
- 添加 bloom/glow 效果 (高能量粒子發光)
- 添加群組內的連線 (鄰居關係視覺化)
- 改善 boundary box (虛線 + 半透明面)
**預估工作量**: 5-6 小時

#### 6. **效能監控與優化不足**
**問題**: 
- 無 GPU profiling
- 不知道瓶頸在哪裡 (CPU? GPU? Network?)
- 無幀率波動分析
**建議新增**:
- WebGPU timestamp queries (GPU timing)
- CPU/GPU 效能對比圖表
- 自動效能調整 (降低粒子數/trail長度)
**預估工作量**: 3-4 小時

---

### 🟡 Medium Priority (擴充功能)

#### 7. **缺少錄影/匯出功能**
**建議新增**:
- Canvas 錄影 (WebCodecs API 或 MediaRecorder)
- 快照截圖 (PNG export)
- 軌跡資料匯出 (CSV/JSON)
**預估工作量**: 3-4 小時

#### 8. **無法回放歷史狀態**
**建議新增**:
- 時間軸控制 (播放/暫停/倒轉)
- 儲存模擬快照 (checkpoint system)
- 比較不同時間點的統計
**預估工作量**: 6-8 小時

#### 9. **統計視覺化不夠豐富**
**問題**: Statistics 面板只顯示數字
**建議改善**:
- 添加即時折線圖 (Polarization、Rg、Speed over time)
- 速度分布直方圖
- Energy 分布熱力圖
**預估工作量**: 4-5 小時

#### 10. **缺少多模擬實例比較**
**建議新增**:
- 並排比較模式 (2-4 個獨立模擬)
- 參數掃描工具 (自動執行多組參數)
**預估工作量**: 8-10 小時

---

### 🟢 Low Priority (錦上添花)

#### 11. **美化 UI 設計**
- 統一配色方案
- 平滑動畫過渡
- Responsive design (支援小螢幕)
**預估工作量**: 4-6 小時

#### 12. **添加音效**
- 碰撞音效
- 背景音樂 (可選)
- 音量控制
**預估工作量**: 2-3 小時

#### 13. **VR/AR 支援**
- WebXR API 整合
- 3D 立體視覺
**預估工作量**: 10-15 小時

---

## 🐛 已知 Bug / 潛在問題

### 1. **Init 按鈕邏輯混亂**
**問題**: 系統已經自動初始化，但 UI 還有 Init 按鈕
**建議**: 移除 Init 按鈕或改為 "Reset" 按鈕

### 2. **斷線後無法自動重連**
**狀態**: WebSocket 有自動重連邏輯但未測試完全
**建議**: 強化錯誤處理與使用者提示

### 3. **Console Debug Log 過多**
**問題**: 每幀都在 log，影響效能
**建議**: 改用可切換的 debug mode

### 4. **Memory leak 風險**
**問題**: 
- `positionHistory` 陣列可能無限增長
- GPU buffer 可能未正確銷毀
**建議**: 添加 memory profiling 與定期清理機制

### 5. **Backend dt 硬編碼**
**問題**: dt = 0.1 寫死在 `simulation_manager.py`
**建議**: 改為可調整參數

---

## 🎯 優先執行建議 (下一階段)

### Phase 1: 核心功能補全 (1-2 天)
1. ✅ 修復參數編輯器
2. ✅ 實作 Group Detection 視覺化
3. ✅ 添加預設場景選單

### Phase 2: 體驗優化 (2-3 天)
4. ✅ 改善視覺效果 (彩色 trail、群組連線)
5. ✅ 添加互動教學
6. ✅ 效能監控面板

### Phase 3: 進階功能 (1 週)
7. ✅ 動態障礙物/資源編輯
8. ✅ 錄影匯出功能
9. ✅ 統計圖表化

---

## 📐 架構改善建議

### 1. **前後端 API 標準化**
**問題**: 目前 WebSocket 訊息格式較鬆散
**建議**: 
- 定義嚴格的 TypeScript interface + Python dataclass
- 使用 Protocol Buffers 或 MessagePack 取代 JSON
- API 版本控制

### 2. **狀態管理優化**
**問題**: Zustand store 邏輯分散
**建議**:
- 分離 UI state 和 simulation state
- 使用 middleware 處理 WebSocket 同步
- 添加 undo/redo 功能

### 3. **測試覆蓋率**
**問題**: 缺少前端單元測試
**建議**:
- 添加 Vitest 單元測試
- WebGPU renderer 的視覺回歸測試
- E2E 測試 (Playwright)

### 4. **文件化**
**問題**: 缺少 API 文件和開發者指南
**建議**:
- JSDoc / TSDoc 註解
- Storybook 組件展示
- Architecture Decision Records (ADR)

---

## 🔬 實驗功能探索

### 1. **Machine Learning 整合**
- 訓練 agent 學習最佳覓食策略
- 預測群組演化趨勢
- 異常檢測 (識別奇怪的行為模式)

### 2. **多物種系統**
- 捕食者-獵物動態
- 共生/競爭關係
- 演化機制

### 3. **實驗資料分析工具**
- 自動化參數掃描
- 相變檢測 (Chaos ↔ Order transition)
- 統計顯著性測試

---

## 📝 總結

**強項**:
- ✅ 堅實的物理引擎基礎
- ✅ 高效能 GPU 渲染
- ✅ 清晰的程式架構

**待改進**:
- ⚠️ 互動性不足 (參數編輯、場景切換)
- ⚠️ 視覺化單調 (需要更多色彩和層次)
- ⚠️ 缺少引導性內容 (教學、預設場景)

**下一步行動**:
1. 先修復 Critical 問題 (參數編輯器、群組視覺化)
2. 再優化體驗 (預設場景、視覺效果)
3. 最後擴充進階功能 (錄影、回放、圖表)
