/**
 * Pointer and gesture interaction for the cognitive canvas.
 *
 * Owns mouse listeners and observer-only navigation state. Rendering and
 * simulation scheduling stay in cognition-controller.js.
 */
import { orbitCamera, zoomCamera } from './cognition-3d.js';
import { polygonContains } from './cognitive-regions.js';
import { recordObserverUsage } from './cognitive-refinement.js';
import { graph, observerUsage } from './state.js';

export function createCognitionInteraction({
  onInvalidate3D = () => {},
  onRebuild = () => {},
  onRenderInspector = () => {},
  onSchedule = () => {},
} = {}) {
  let windowMouseMove = null;
  let windowMouseUp = null;

  function installGraphListeners(canvas) {
    let isPanning = false, isDragging = false, draggedNode = null;
    let pressedNode = null;
    let panStartX = 0, panStartY = 0, dragDist = 0;
    let orbitLastX = 0, orbitLastY = 0;
  
    function canvasCoords(event) {
      const rect = canvas.getBoundingClientRect();
      const sx = rect.width > 0 ? canvas.width / rect.width : 1;
      const sy = rect.height > 0 ? canvas.height / rect.height : 1;
      return { x: (event.clientX - rect.left) * sx, y: (event.clientY - rect.top) * sy };
    }
    function findNode(mx, my) {
      if (graph.dimension === '3d') {
        const projected = [...(graph.projected3d?.values?.() ?? [])];
        projected.sort((a,b) => a.depth - b.depth);
        for (let i = projected.length - 1; i >= 0; i--) {
          const item = projected[i];
          if (Math.hypot(item.x - mx, item.y - my) <= item.radius + 7) return item.node;
        }
        return null;
      }
      const wx = (mx - graph.panX) / graph.scale;
      const wy = (my - graph.panY) / graph.scale;
      for (let i = graph.nodes.length - 1; i >= 0; i--) {
        const n = graph.nodes[i];
        if (graph.detailVisibleIds && !graph.detailVisibleIds.has(n.id)) continue;
        if (Math.hypot(n.x - wx, n.y - wy) <= n.radius + 6) return n;
      }
      return null;
    }

    function findRegion(mx, my) {
      const areas = graph.dimension === '3d'
        ? (graph.atlasRegionHitAreas3d ?? [])
        : (graph.atlasRegionHitAreas2d ?? []);
      const point = graph.dimension === '3d'
        ? { x: mx, y: my }
        : {
            x: (mx - graph.panX) / graph.scale,
            y: (my - graph.panY) / graph.scale,
          };
      let best = null;
      for (const area of areas) {
        if (!polygonContains(area.polygon ?? [], point.x, point.y)) continue;
        if (!best || area.radius < best.radius) best = area;
      }
      return best;
    }
  
    canvas.addEventListener('wheel', ev => {
      ev.preventDefault();
      graph.manualViewOverride = true;
      graph.autoFramePending = false;
      if (graph.dimension === '3d') {
        onInvalidate3D?.();
        graph.camera3d = zoomCamera(graph.camera3d, ev.deltaY, {
          sceneRadius: graph.sceneRadius3d,
        });
      } else {
        const factor = ev.deltaY < 0 ? 1.12 : 0.89;
        const ns = Math.min(5, Math.max(0.2, graph.scale * factor));
        const { x, y } = canvasCoords(ev);
        graph.panX = x - (x - graph.panX) * (ns / graph.scale);
        graph.panY = y - (y - graph.panY) * (ns / graph.scale);
        graph.scale = ns;
      }
      graph.alpha = Math.max(graph.alpha, 0.1);
      onSchedule?.();
    }, { passive: false });
  
    canvas.addEventListener('mousedown', ev => {
      if (ev.button !== 0) return;
      const { x, y } = canvasCoords(ev);
      const node = findNode(x, y);
      dragDist = 0;
      pressedNode = node;
      if (graph.dimension === '3d') {
        if (!node) {
          onInvalidate3D?.();
          graph.manualViewOverride = true;
          graph.autoFramePending = false;
          isPanning = true;
          orbitLastX = x;
          orbitLastY = y;
          canvas.style.cursor = 'grabbing';
        }
        return;
      }
      if (node) { isDragging = true; draggedNode = node; node.pinned = true; node.vx = node.vy = 0; }
      else { graph.manualViewOverride = true; graph.autoFramePending = false; isPanning = true; panStartX = x - graph.panX; panStartY = y - graph.panY; canvas.style.cursor = 'grabbing'; }
    });
  
    // Window listeners outlive the canvas, so keep explicit references and
    // remove them during unmount/remount. This prevents listener accumulation.
    if (windowMouseMove) window.removeEventListener('mousemove', windowMouseMove);
    if (windowMouseUp) window.removeEventListener('mouseup', windowMouseUp);
  
    windowMouseMove = ev => {
      const { x, y } = canvasCoords(ev);
      if (graph.dimension === '3d') {
        if (isPanning) {
          const dx = x - orbitLastX;
          const dy = y - orbitLastY;
          dragDist += Math.abs(dx) + Math.abs(dy);
          onInvalidate3D?.();
          graph.camera3d = orbitCamera(graph.camera3d, dx, dy);
          orbitLastX = x;
          orbitLastY = y;
          graph.alpha = Math.max(graph.alpha, 0.08);
          onSchedule?.();
        } else {
          graph.hoveredNode = findNode(x, y);
          canvas.style.cursor = graph.hoveredNode ? 'pointer' : 'grab';
          onSchedule?.();
        }
        return;
      }
      if (isDragging && draggedNode) {
        dragDist += Math.abs(ev.movementX) + Math.abs(ev.movementY);
        draggedNode.x = (x - graph.panX) / graph.scale;
        draggedNode.y = (y - graph.panY) / graph.scale;
        draggedNode.vx = draggedNode.vy = 0;
        graph.alpha = Math.max(graph.alpha, 0.4);
        onSchedule?.();
      } else if (isPanning) {
        graph.panX = x - panStartX;
        graph.panY = y - panStartY;
        onSchedule?.();
      } else {
        graph.hoveredNode = findNode(x, y);
        canvas.style.cursor = graph.hoveredNode ? 'pointer' : 'grab';
        onSchedule?.();
      }
    };
  
    windowMouseUp = ev => {
      const clicked = pressedNode && dragDist < 5 ? pressedNode : null;
      const coords = canvasCoords(ev);
      const clickedRegion = !clicked && dragDist < 5
        ? findRegion(coords.x, coords.y)
        : null;
      if (draggedNode) { draggedNode.pinned = false; draggedNode = null; }
      if (clicked) {
        graph.selectedNodeId = graph.selectedNodeId === clicked.id ? null : clicked.id;
        if (graph.selectedNodeId) recordObserverUsage(observerUsage, 'selection');
        const graphCanvas = document.getElementById('mind-cognition-canvas');
        if (graphCanvas) onRebuild?.(graphCanvas.width || 900, graphCanvas.height || 600);
        onRenderInspector?.();
        graph.alpha = Math.max(graph.alpha, 0.08);
        onSchedule?.();
      } else if (clickedRegion) {
        recordObserverUsage(observerUsage, 'region-focus');
        graph.focusedSectorId = graph.focusedSectorId === clickedRegion.id
          ? null
          : clickedRegion.id;
        graph.selectedNodeId = null;
        graph.autoFramePending = true;
        graph.manualViewOverride = false;
        onRenderInspector?.();
        graph.alpha = Math.max(graph.alpha, 0.12);
        onSchedule?.();
      } else if (!pressedNode && dragDist < 5) {
        graph.selectedNodeId = null;
        graph.focusedSectorId = null;
        onRenderInspector?.();
      }
      pressedNode = null;
      isDragging = false; isPanning = false;
      canvas.style.cursor = 'grab';
    };
  
    window.addEventListener('mousemove', windowMouseMove);
    window.addEventListener('mouseup', windowMouseUp);
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Regime Compass (adapted from observatory/render/regime-compass.js)
  // ─────────────────────────────────────────────────────────────────────────────
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Snapshot ingestion (simplified projection from instance stream)
  // ─────────────────────────────────────────────────────────────────────────────
  

  function dispose() {
    if (windowMouseMove) {
      window.removeEventListener('mousemove', windowMouseMove);
      windowMouseMove = null;
    }
    if (windowMouseUp) {
      window.removeEventListener('mouseup', windowMouseUp);
      windowMouseUp = null;
    }
  }

  return {
    install: installGraphListeners,
    dispose,
  };
}
