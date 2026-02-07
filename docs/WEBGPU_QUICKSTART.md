# React + WebGPU 整合 - 快速開始

**目標**: 3 週內完成高效能 Web Dashboard  
**技術棧**: React + TypeScript + WebGPU + Python WebSocket Backend  
**預期效能**: 50+ FPS @ N=500

---

## 📦 專案結構

```
alife/
├── src/                    # 現有 Taichi Solver (不修改)
├── backend/                # 新增：WebSocket Server
│   ├── server.py
│   ├── serializer.py
│   ├── simulation_manager.py
│   └── requirements.txt
├── frontend/               # 新增：React + WebGPU Frontend
│   ├── src/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── store/
│   │   └── types/
│   └── package.json
└── docs/
    └── WEBGPU_INTEGRATION_PLAN.md  # 詳細計畫
```

---

## 🚀 立即開始（30 分鐘）

### Step 1: 建立 Backend 目錄結構

```bash
cd /Users/latteine/Documents/coding/alife
mkdir -p backend
cd backend

# 建立檔案
touch server.py serializer.py simulation_manager.py requirements.txt
```

### Step 2: 安裝 Backend 依賴

```bash
# backend/requirements.txt 內容：
cat > requirements.txt << 'EOF'
websockets==12.0
lz4==4.3.2
EOF

# 安裝
uv pip install -r requirements.txt
```

### Step 3: 複製 Week 1 程式碼

從 `docs/WEBGPU_INTEGRATION_PLAN.md` 複製以下程式碼到對應檔案：
- `server.py` (第 470-580 行)
- `serializer.py` (第 200-350 行)
- `simulation_manager.py` (第 590-720 行)

### Step 4: 測試 Backend

```bash
cd backend
uv run python server.py

# 預期輸出：
# Server started at ws://localhost:8765
```

### Step 5: 建立 Frontend 專案

```bash
cd /Users/latteine/Documents/coding/alife
mkdir frontend
cd frontend

# 使用 Vite 初始化
npm create vite@latest . -- --template react-ts

# 安裝依賴
npm install
npm install zustand @webgpu/types gl-matrix

# 啟動開發伺服器
npm run dev
```

---

## 📋 3 週里程碑

### Week 1: Backend + 資料層 ✅
- [x] WebSocket Server (Day 1-2)
- [x] 序列化器 (Day 3-4)
- [x] Frontend 初始化 + WebSocket Client (Day 5-7)

**檢查點**:
```bash
# Backend 測試
cd backend && uv run python server.py

# 另一終端測試連線
wscat -c ws://localhost:8765
> {"type": "update_params", "payload": {"systemType": "Heterogeneous", "N": 100}}
> {"type": "start"}
# 應該收到二進位資料流
```

### Week 2: WebGPU 渲染引擎 🎨
- [ ] WebGPU 初始化與 Pipeline 建立
- [ ] 粒子渲染系統（Point Cloud）
- [ ] 相機控制（OrbitControls）
- [ ] 基本光照與著色

**目標效能**: 60 FPS @ N=300

### Week 3: UI 整合 + 優化 🎯
- [ ] 參數控制面板
- [ ] 統計資訊顯示
- [ ] 資源/障礙物渲染
- [ ] 效能優化與測試

**交付標準**: 可部署的 Web 應用

---

## 🔧 關鍵技術決策

### 1. 為什麼用 WebSocket 而非 HTTP?
✅ **即時性**: 每秒 30-60 幀，WebSocket 延遲 < 5ms  
❌ HTTP: 每次請求開銷 ~50ms

### 2. 為什麼用二進位而非 JSON?
✅ **效能**: 二進位 3.4 KB/frame vs JSON 15 KB/frame  
✅ **解析速度**: ArrayBuffer 無需 parse

### 3. 為什麼用 WebGPU 而非 Three.js?
✅ **效能**: WebGPU 直接 GPU compute，比 Three.js 快 2-3 倍  
✅ **靈活性**: 完全控制 rendering pipeline

### 4. 為什麼不修改現有 Solver?
✅ **風險控制**: Solver 已測試完善，不應因前端需求而改動  
✅ **職責分離**: Backend 只負責包裝與傳輸

---

## 📊 效能預期

| N值 | Streamlit | WebGPU (預期) | 提升 |
|-----|-----------|---------------|------|
| 100 | 35 FPS | 60 FPS | 1.7x |
| 200 | 25 FPS | 60 FPS | 2.4x |
| 500 | 12 FPS | 50 FPS | 4.2x |
| 1000 | 5 FPS | 30 FPS | 6x |

**瓶頸分析**:
- **現在**: Streamlit (Python → Plotly) + 完整資料重傳
- **之後**: Taichi (GPU) → Binary WebSocket → WebGPU (GPU)
- **關鍵**: 資料停留在 GPU，減少 CPU-GPU 傳輸

---

## 🐛 常見問題

### Q1: WebSocket 連線失敗
```bash
# 檢查伺服器是否運行
netstat -an | grep 8765

# 檢查防火牆
# macOS: System Settings → Network → Firewall
```

### Q2: 序列化速度慢 (< 60 FPS)
```python
# 使用 cProfile 分析
python -m cProfile -s cumtime server.py

# 檢查 to_numpy() 是否過於頻繁
# 考慮使用 .to_numpy() 的 async 版本
```

### Q3: WebGPU 不支援
```javascript
// 檢查瀏覽器支援
if (!navigator.gpu) {
  alert('WebGPU not supported. Use Chrome 113+ or Safari 18+');
}
```

### Q4: 前端收到資料但解析錯誤
```typescript
// 檢查 endianness
const view = new DataView(buffer);
const N = view.getUint32(0, true);  // true = little-endian
```

---

## 📚 參考資源

### WebGPU 學習
- [WebGPU Fundamentals](https://webgpufundamentals.org/)
- [WebGPU Samples](https://webgpu.github.io/webgpu-samples/)
- [WGSL Spec](https://www.w3.org/TR/WGSL/)

### React + WebGPU
- [react-webgpu](https://github.com/visgl/react-webgpu)
- [WebGPU Particles Demo](https://github.com/gnikoloff/webgpu-particles)

### WebSocket (Python)
- [websockets docs](https://websockets.readthedocs.io/)
- [asyncio tutorial](https://docs.python.org/3/library/asyncio.html)

---

## 🎯 下一步

### 今天 (1 小時)
1. 建立 `backend/` 目錄
2. 複製 Week 1 程式碼
3. 測試 WebSocket Server 能正常啟動

### 明天 (2 小時)
1. 完成 `serializer.py` 實作
2. 測試序列化速度 (> 100 FPS)
3. 初始化 Frontend 專案

### 本週末 (4 小時)
1. 實作 WebSocket Client (TypeScript)
2. 實作狀態管理 (Zustand)
3. 建立基本 UI 框架
4. **Week 1 完成！** 🎉

---

## 💬 需要幫助？

如果在實作過程中遇到問題：

1. **檢查詳細文件**: `docs/WEBGPU_INTEGRATION_PLAN.md`
2. **執行測試**: `uv run python test_serializer.py`
3. **查看 Console**: 前端 F12 → Console，後端終端機輸出
4. **對照範例**: 參考 Streamlit 版本的資料處理邏輯

---

**準備好開始了嗎？** 🚀

建議順序：
1. 先完成 Backend (確保資料能正確輸出)
2. 再做 Frontend (確保資料能正確接收)
3. 最後整合 WebGPU (確保渲染效能)

**估計總開發時間**: 
- 熟練前端開發者: **15-20 小時**
- 初次接觸 WebGPU: **25-30 小時**

**預期成果**:
一個能展示給全世界的高效能集群模擬 Web 應用！ 🌐✨
