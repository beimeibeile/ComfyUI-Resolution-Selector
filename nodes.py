# coding=utf-8
"""
ComfyUI-Resolution-Selector 节点
=================================
DBW/Utils 工具类: 分辨率选择器（Live）。

仿照常见 "Resolution Selector (Live)" 节点:
  输入 aspect_ratio(宽高比) / megapixels(目标百万像素) / multiple(对齐倍数)
  -> 计算满足比例与像素目标的 width × height, 并向上对齐到 multiple 的倍数(保证实际像素 >= 目标)。

对齐策略(与参考实现一致):
  width  = ceil(sqrt(MP*1e6 * ratio) / multiple) * multiple
  height = ceil(width / ratio / multiple) * multiple
  例: 4:3 + 0.75MP + mult 32 -> 1024 × 768 (实际 0.786MP), 32 的倍数, 与参考图一致。
"""
import math

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

_CATEGORY = "DBW/Utils"

# 宽高比预设: label "W:H (说明)", 解析冒号前后数字
_ASPECT_RATIOS = [
    "1:1 (Square)",
    "4:3 (Standard)",
    "3:2",
    "16:9 (Landscape)",
    "21:9 (Ultrawide)",
    "3:4 (Portrait)",
    "2:3",
    "9:16 (Portrait)",
]


def _ratio_of(label: str) -> tuple:
    """从 '4:3 (Standard)' 或 '768×1024 (3:4)' 取 (w, h)。"""
    head = label.split("(")[0].strip()
    sep = "×" if "×" in head else ":"
    a, _, b = head.partition(sep)
    try:
        wa, hb = float(a), float(b)
        if wa > 0 and hb > 0:
            return wa, hb
    except Exception:
        pass
    return 4.0, 3.0


def _ceil_mult(x: float, multiple: int) -> int:
    """向上取整到 multiple 的倍数。"""
    m = max(1, int(int(multiple) or 1))
    return int(math.ceil(x / m)) * m


def _simplify_ratio(w: int, h: int) -> str:
    """宽高像素化简为最简整数比, 如 1024x768 -> '4:3'。"""
    g = math.gcd(w, h)
    if g == 0:
        return f"{w}:{h}"
    return f"{w // g}:{h // g}"


def resolve_resolution(aspect_ratio: str, megapixels: float, multiple: int,
                       image=None) -> dict:
    """
    核心计算: 返回 width/height/actual_mp/ratio_used/img_info。

    image: 可选 IMAGE 张量([B,H,W,C])。接入后以图片实际宽高比为准(忽略 aspect_ratio),
    返回图片原始宽高像素与最简比例。
    """
    if image is not None:
        img_w = int(image.shape[2])
        img_h = int(image.shape[1])
        ratio = (img_w / img_h) if img_h else 1.0
        img_info = f"{img_w}×{img_h} ({_simplify_ratio(img_w, img_h)})"
    else:
        w, h = _ratio_of(aspect_ratio)
        ratio = w / h
        img_info = None

    total_px = max(megapixels, 0.01) * 1_000_000
    width = _ceil_mult(math.sqrt(total_px * ratio), multiple)
    height = _ceil_mult(width / ratio, multiple)
    actual_mp = (width * height) / 1_000_000
    return {
        "width": int(width),
        "height": int(height),
        "actual_mp": actual_mp,
        "ratio_used": ratio,
        "img_info": img_info,
    }


class DBWResolutionSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "4:3 (Standard)", "tooltip": "输出宽高比(含方向)。接入 IMAGE 后由图片自动决定并禁用本项"}),
                "megapixels": ("FLOAT", {"default": 0.75, "min": 0.05, "max": 4.0, "step": 0.05,
                                         "tooltip": "目标总像素(百万)。实际结果向上取整, 可能略高于目标"}),
                "multiple": ("INT", {"default": 32, "min": 8, "max": 256, "step": 8,
                                     "tooltip": "宽高对齐倍数(Latent/分块常用 8/16/32/64)。结果保证是 multiple 的整数倍"}),
            },
            "optional": {
                "IMAGE": ("IMAGE", {"tooltip": "可选: 接入图片后自动识别其宽高像素, 按图片比例计算, 并禁用 aspect_ratio"}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("WIDTH", "HEIGHT", "ACTUAL_MP", "RATIO_LABEL", "IMG_INFO")
    FUNCTION = "resolve"
    CATEGORY = _CATEGORY

    @classmethod
    def VALIDATE_INPUTS(cls, aspect_ratio=None, megapixels=None, multiple=None, **kwargs):
        """
        宽松校验(返回 True 表示通过):
        aspect_ratio 运行中会被前端改写为图片比例(如 "768×1024 (3:4)"), 不在预设 combo 列表,
        若不加 VALIDATE_INPUTS, ComfyUI 的 combo 选项检查会报"无效输入"。
        参数名出现在签名中即跳过默认 combo/min/max 检查, 由本方法自行校验。
        注意: ComfyUI 0.34.x 要求通过时返回 True(返回 None 会报 custom_validation_failed)。
        """
        if aspect_ratio is None or not str(aspect_ratio).strip():
            return "aspect_ratio 不能为空"
        try:
            if megapixels is not None and not (0.05 <= float(megapixels) <= 4.0):
                return "megapixels 超出范围 0.05-4.0"
            if multiple is not None and not (8 <= int(multiple) <= 256):
                return "multiple 超出范围 8-256"
        except Exception:
            return "megapixels/multiple 必须为数字"
        return True

    def resolve(self, aspect_ratio, megapixels, multiple, IMAGE=None):
        # 注意: 参数名必须与 INPUT_TYPES 键名一致(大写 IMAGE), ComfyUI 按定义键名展开调用
        r = resolve_resolution(aspect_ratio, megapixels, multiple, image=IMAGE)
        label = f"{r['width']} × {r['height']} ({r['actual_mp']:.2f} MP)"
        img_info = r["img_info"] if r["img_info"] is not None else "—"
        results = (r["width"], r["height"], round(r["actual_mp"], 4), label, img_info)
        # ui 通道: 普通输出不会传给前端 onExecuted, 需经 ui 键回传, 前端才能禁用/更新 aspect_ratio 显示
        # 注意: ComfyUI 要求 ui 各键值为"列表"([y for x in uis for y in x[k]] 会遍历值), 必须包成数组
        return {
            "ui": {
                "img_info": [img_info],
                "width": [int(r["width"])],
                "height": [int(r["height"])],
                "actual_mp": [round(r["actual_mp"], 4)],
                "has_image": [bool(r["img_info"] is not None)],
            },
            "result": results,
        }


NODE_CLASS_MAPPINGS["DBW-ResolutionSelector"] = DBWResolutionSelector
NODE_DISPLAY_NAME_MAPPINGS["DBW-ResolutionSelector"] = "Resolution Selector (Live)"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
