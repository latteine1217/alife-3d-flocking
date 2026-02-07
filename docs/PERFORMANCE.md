# 性能測試總結報告

## 測試日期
2026-02-06

## 測試目標
驗證 Cell List (v3b) 相對於暴力法 (v2) 的性能優勢

## 測試環境
- 硬體：macOS, Metal GPU
- Taichi 版本：1.7.4
- 測試規模：N = 100 - 1000

## 關鍵發現

### 1. 小規模測試結果 (N ≤ 1000)

| N   | v2 (ms/step) | v3b (ms/step) | Speedup |
|-----|--------------|---------------|---------|
| 100 | 0.07         | 0.08          | 0.84x   |
| 200 | 0.07         | 0.09          | 0.82x   |
| 300 | 0.08         | 0.09          | 0.87x   |
| 400 | 0.08         | 0.09          | 0.89x   |
| 500 | 0.08         | 0.09          | 0.86x   |
| 700 | -            | 0.09          | -       |
| 1000| -            | 0.13          | -       |

**結論：**
- ❌ v3b 在小規模下**反而更慢**
- 原因：Cell List 建構開銷 > 省下的計算時間

### 2. 複雜度測量

- **v2**: O(N^0.08) ≈ 常數時間
- **v3b**: O(N^0.15) ≈ 常數時間

**問題：**
兩者都未展現理論複雜度 (O(N²) vs O(N))，因為：
1. GPU kernel 啟動開銷主導執行時間
2. N ≤ 1000 對 GPU 來說太小，無法體現演算法複雜度差異

### 3. Cell List 實作驗證

v3b 成功在 Metal GPU 上運行，驗證了：
- ✅ 固定陣列 + atomic counter 方案可行
- ✅ 動態調整 box_size 可維持低 cell 密度 (avg ≈ 1.5/cell)
- ✅ 無 Dynamic SNode 依賴

## 技術限制

### 為何 N=1000 太小？

GPU 並行效率在 N > 10,000 才顯著：
- N=1000: ~1000 threads，無法充分利用 GPU (Metal GPU 可同時處理 10,000+ threads)
- Kernel 啟動開銷 (~0.05 ms) 無法攤銷

### 為何測試無法跑到 N=2000+？

遇到執行時間過長問題 (> 10 分鐘)，可能原因：
1. **記憶體瓶頸**：grid 數量增加導致記憶體訪問模式不連續
2. **max_per_cell 溢出**：某些 cell 超過預設的 32 個粒子上限（雖然有 4x 安全邊界）
3. **Taichi Metal 後端限制**：在大規模時可能觸發未知的 bug

## 結論

### 性能測試結論
在目前的測試規模 (N ≤ 1000)：
- **v2 (暴力法) 更快** (~0.07 ms/step)
- v3b (Cell List) 有 ~15% 的開銷 (~0.09 ms/step)

### 理論預測
根據複雜度分析，交叉點預計在：
- **N ≈ 5,000 - 10,000**

在此規模下：
- v2: ~O(N²) 會顯著變慢
- v3b: ~O(N) 可維持線性擴展

## 建議

### 短期建議（當前可行）
1. **使用 v2 作為生產版本**（對 N ≤ 1000）
   - 更快且程式碼更簡單
   - 無 Cell List 建構開銷

2. **保留 v3b 作為未來擴展準備**
   - 文件已完整記錄實作細節
   - 可在需要大規模模擬時啟用

### 中期建議（需要進一步開發）
如果需要驗證大規模性能：
1. **增加測試規模到 N > 5000**
   - 需要優化記憶體配置
   - 可能需要切換到 CUDA backend（比 Metal 穩定）

2. **實作混合策略**
   ```python
   if N < 1000:
       use v2  # 暴力法更快
   else:
       use v3b  # Cell List 佔優勢
   ```

### 長期建議（研究方向）
1. **探索 GPU-native 空間加速結構**
   - 使用 Taichi 的 Sparse SNode（需 CUDA）
   - 研究 BVH / Octree 等替代方案

2. **多 GPU 並行**
   - 空間分解策略
   - 跨 GPU 通訊最佳化

## 附件

- 性能曲線圖：`docs/performance_comparison.png`
- 測試腳本：
  - `experiments/quick_performance_test.py`
  - `experiments/large_scale_test.py`
  - `experiments/corrected_scale_test.py`

## 相關文件

- Cell List 技術報告：`docs/CELLLIST_V3B_REPORT.md`
- V2 功能報告：`docs/OPTIMIZED_V2_REPORT.md`
- 優化進度記錄：`docs/OPTIMIZATION_PROGRESS.md`
