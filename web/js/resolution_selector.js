// DBW-ResolutionSelector Live 前端扩展:
// 仿照 "Resolution Selector (Live)": 参数变化时实时计算并显示 width × height (MP)。
// 计算逻辑与 nodes.py resolve_resolution 保持同一公式(ceil 对齐到 multiple 倍数),
// 显示在节点标题, 打开节点即可见, 无需执行。
import { app } from "../../../scripts/app.js";

const CLS = "DBW-ResolutionSelector";

function ratioOf(label) {
    const head = String(label || "").split("(")[0].trim();
    const [a, b] = head.split(":");
    const wa = parseFloat(a), hb = parseFloat(b);
    return (Number.isFinite(wa) && Number.isFinite(hb) && wa > 0 && hb > 0) ? [wa, hb] : [4, 3];
}

function ceilMult(x, m) {
    const k = Math.max(1, Math.trunc(m));
    return Math.ceil(x / k) * k;
}

function compute(label, mp, mult) {
    const [w, h] = ratioOf(label);
    const ratio = w / h;
    const total = Math.max(mp, 0.01) * 1e6;
    const width = ceilMult(Math.sqrt(total * ratio), mult);
    const height = ceilMult(width / ratio, mult);
    return { width, height, mp: (width * height) / 1e6 };
}

app.registerExtension({
    name: "DBW.ResolutionSelector.Live",

    nodeCreated(node) {
        if (node.comfyClass !== CLS) return;

        const update = () => {
            if (!node.widgets) return;
            const ar = node.widgets.find((w) => w.name === "aspect_ratio");
            const mp = node.widgets.find((w) => w.name === "megapixels");
            const mu = node.widgets.find((w) => w.name === "multiple");
            if (!ar || !mp || !mu) return;
            const r = compute(ar.value, mp.value, mu.value);
            node.title = `Resolution Selector · ${r.width} × ${r.height} (${r.mp.toFixed(2)} MP)`;
            node.setDirtyCanvas?.(true, true);
        };

        // 三个参数任意变化 → 实时刷新
        for (const w of node.widgets) {
            if (["aspect_ratio", "megapixels", "multiple"].includes(w.name)) {
                const orig = w.callback;
                w.callback = function (...args) {
                    const r = orig ? orig.apply(this, args) : undefined;
                    update();
                    return r;
                };
            }
        }

        // 初始渲染(节点创建时 widget 可能尚未就绪)
        setTimeout(update, 200);
        setTimeout(update, 800);
    },
});
