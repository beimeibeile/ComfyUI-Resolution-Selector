# ComfyUI-Resolution-Selector

DBW/Utils 工具类子工程：**分辨率选择器（Live）**。

仿照常见 "Resolution Selector (Live)" 节点：按宽高比 + 目标百万像素，计算满足条件的
`width × height`，并**向上对齐到 multiple 的倍数**（保证实际像素 ≥ 目标，适配 Latent / 分块尺寸约束）。

## 节点

| 节点 | 分类 | 输入 | 输出 |
|---|---|---|---|
| `DBW-ResolutionSelector` | `DBW/Utils` | aspect_ratio / megapixels / multiple | WIDTH / HEIGHT / ACTUAL_MP / RATIO_LABEL |

- `aspect_ratio`：预设宽高比（含方向）：1:1、4:3、3:2、16:9、21:9、3:4、2:3、9:16。
- `megapixels`：目标总像素（百万），实际结果向上取整，可能略高于目标。
- `multiple`：宽高对齐倍数（8-256，默认 32），结果保证是 multiple 的整数倍。
- **Live**：参数变化实时在节点标题显示 `1024 × 768 (0.79 MP)`，无需执行即可预览。

## 计算逻辑

```
width  = ceil(sqrt(megapixels*1e6 * ratio) / multiple) * multiple
height = ceil(width / ratio / multiple) * multiple
```

验证（与参考图一致）：
- 4:3 + 0.75MP + mult 32 → **1024 × 768**（0.79MP，32 的整数倍）
- 16:9 + 0.5MP + mult 64 → 960 × 576

前端 `web/js/resolution_selector.js` 与 `nodes.py` 共用同一公式，标题显示与执行输出一致。

## 安装（软链，勿拷贝）

```bat
mklink /J "D:\Ai\ComfyUI-aki-v3.2\ComfyUI\custom_nodes\ComfyUI-Resolution-Selector" "D:\DobaoWork_Project\ComfyUI-Nodes\ComfyUI-Resolution-Selector"
```

重启 ComfyUI 后节点出现在 `DBW/Utils` 分类下。

## 目录结构

```
ComfyUI-Resolution-Selector/
├── nodes.py                    # DBW-ResolutionSelector 节点 + 计算
├── __init__.py                 # WEB_DIRECTORY + 注册
├── web/js/resolution_selector.js  # Live 实时显示
├── pyproject.toml              # 依赖(无运行时第三方依赖, 纯标准库)
└── README.md
```
