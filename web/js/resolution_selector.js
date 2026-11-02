// DBW-ResolutionSelector Live 前端扩展:
// 1) 无 IMAGE: 参数变化实时计算并显示 width × height (MP), 标题实时预览。
// 2) 接入 IMAGE: 执行后读取后端返回的 IMG_INFO(宽高像素+比例), aspect_ratio 禁用并显示该信息;
//    断开 IMAGE 后恢复可用。计算逻辑与 nodes.py 保持一致(ceil 对齐到 multiple 倍数)。
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

        const ar = () => node.widgets?.find((w) => w.name === "aspect_ratio");

        const update = () => {
            const w = ar();
            const mp = node.widgets?.find((w) => w.name === "megapixels");
            const mu = node.widgets?.find((w) => w.name === "multiple");
            if (!w || !mp || !mu) return;
            const r = compute(w.value, mp.value, mu.value);
            node.title = `Resolution Selector · ${r.width} × ${r.height} (${r.mp.toFixed(2)} MP)`;
            node.setDirtyCanvas?.(true, true);
        };

        // 三个参数任意变化 → 实时刷新(仅无 IMAGE 时有效, 有 IMAGE 时 aspect_ratio 已禁用)
        for (const w of node.widgets || []) {
            if (["aspect_ratio", "megapixels", "multiple"].includes(w.name)) {
                const orig = w.callback;
                w.callback = function (...args) {
                    const r = orig ? orig.apply(this, args) : undefined;
                    update();
                    return r;
                };
            }
        }

        // 执行完成: 读取节点 ui 通道回传(普通输出不会发给前端, 必须走 ui)
        // ComfyUI 的 ui 值都是数组, 需解包首元素
        const onExecuted = node.onExecuted;
        node.onExecuted = function (executed) {
            if (onExecuted) onExecuted.apply(this, arguments);
            const w = ar();
            if (!w) return;
            const first = (x) => (Array.isArray(x) ? x[0] : x);
            const info = first(executed?.img_info);
            const hasImg = first(executed?.has_image) === true;
            if (hasImg && info && info !== "—" && info.includes("×")) {
                w.value = info;          // 例: "768×1024 (3:4)"
                w.disabled = true;       // 禁用, 由图片决定
                const W = Number(first(executed?.width)), H = Number(first(executed?.height));
                if (Number.isFinite(W) && Number.isFinite(H) && W > 0) {
                    node.title = `Resolution Selector · ${W} × ${H} (${(+first(executed?.actual_mp)).toFixed(2)} MP)`;
                }
            } else {
                w.disabled = false;      // 无图片: 恢复手动选择
                update();
            }
            node.setDirtyCanvas?.(true, true);
        };

        // IMAGE 输入断开: 立即恢复 aspect_ratio 可编辑
        const onConn = node.onConnectionsChange;
        node.onConnectionsChange = function (type, slot, _, linked, linkInfo) {
            if (onConn) onConn.apply(this, arguments);
            if (type === LiteGraph.INPUT && linkInfo?.name === "IMAGE" && !linked) {
                const w = ar();
                if (w) { w.disabled = false; update(); }
            }
        };

        // 初始渲染(节点创建时 widget 可能尚未就绪)
        setTimeout(update, 200);
        setTimeout(update, 800);
    },
});
