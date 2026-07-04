"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Core, ElementDefinition, Layouts, StylesheetJson } from "cytoscape";
import type { LiveGraph } from "@/types/api";

const GRAPH_STYLE: StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-valign": "bottom",
      "text-margin-y": 4,
      "font-size": 9,
      color: "#94a3b8",
      "background-color": "#1e2a3d",
      width: 28,
      height: 28,
      "border-width": 2,
      "border-color": "#06b6d4",
    },
  },
  {
    selector: "node[?isVictim]",
    style: {
      "background-color": "#f43f5e",
      "border-color": "#fb7185",
      width: 40,
      height: 40,
    },
  },
  {
    selector: "node[?isSource]",
    style: {
      "border-color": "#8b5cf6",
    },
  },
  {
    selector: "edge",
    style: {
      width: "mapData(weight, 0, 10, 1, 4)",
      "line-color": "#334155",
      "target-arrow-color": "#334155",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      opacity: 0.7,
    },
  },
];

function toElements(graph: LiveGraph): ElementDefinition[] {
  const elements: ElementDefinition[] = [];
  for (const n of graph.nodes) {
    elements.push({
      data: {
        id: String(n.id),
        label: n.ip.split(".").slice(-2).join("."),
        isVictim: n.is_victim,
        isSource: n.is_source,
        degree: n.degree,
      },
    });
  }
  graph.edges.forEach((e, i) => {
    elements.push({
      data: {
        id: `e-${e.source}-${e.target}-${i}`,
        source: String(e.source),
        target: String(e.target),
        weight: e.weight,
      },
    });
  });
  return elements;
}

function graphSignature(graph: LiveGraph) {
  return `${graph.victim_ip}:${graph.nodes.length}:${graph.edges.length}:${graph.is_attack}`;
}

function stopLayout(layout: Layouts | null) {
  if (!layout) return;
  try {
    layout.stop();
  } catch {
    /* layout may already be stopped */
  }
}

function safeDestroy(cy: Core | null) {
  if (!cy || cy.destroyed()) return;
  try {
    cy.stop(true, true);
  } catch {
    /* ignore */
  }
  try {
    cy.destroy();
  } catch {
    /* ignore */
  }
}

export function CytoscapeGraph({ graph }: { graph: LiveGraph | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const layoutRef = useRef<Layouts | null>(null);
  const signature = useMemo(() => (graph ? graphSignature(graph) : ""), [graph]);

  useEffect(() => {
    if (!containerRef.current || !graph?.nodes?.length) return;

    let cancelled = false;
    let debounceTimer: ReturnType<typeof setTimeout>;

    const applyGraph = async () => {
      const cytoscape = (await import("cytoscape")).default;
      if (cancelled || !containerRef.current) return;

      stopLayout(layoutRef.current);
      layoutRef.current = null;

      let cy = cyRef.current;
      const elements = toElements(graph);
      const isFirstMount = !cy || cy.destroyed();

      if (isFirstMount) {
        safeDestroy(cy);
        cy = cytoscape({
          container: containerRef.current,
          elements,
          style: GRAPH_STYLE,
          minZoom: 0.3,
          maxZoom: 3,
        });
        cyRef.current = cy;
      } else if (cy) {
        const instance = cy;
        instance.batch(() => {
          instance.elements().remove();
          instance.add(elements);
        });
      }

      const edgeColor = graph.is_attack ? "#f43f5e" : "#334155";
      if (!cy) return;
      cy.style().selector("edge").style("line-color", edgeColor).update();
      cy.style().selector("edge").style("target-arrow-color", edgeColor).update();

      const layout = cy.layout({
        name: "cose",
        animate: !isFirstMount ? false : true,
        animationDuration: 400,
        padding: 30,
        fit: true,
      });
      layoutRef.current = layout;
      layout.run();
    };

    debounceTimer = setTimeout(() => {
      applyGraph().catch(() => {
        /* ignore async errors after unmount */
      });
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(debounceTimer);
      stopLayout(layoutRef.current);
      layoutRef.current = null;
      try {
        cyRef.current?.stop(true, true);
      } catch {
        /* ignore */
      }
    };
  }, [signature, graph]);

  useEffect(() => {
    return () => {
      stopLayout(layoutRef.current);
      safeDestroy(cyRef.current);
      cyRef.current = null;
      layoutRef.current = null;
    };
  }, []);

  if (!graph?.nodes?.length) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center rounded-xl border border-dashed border-border bg-panel/40 text-sm text-muted">
        Waiting for network graph data…
      </div>
    );
  }

  return (
    <div className="relative h-full min-h-[400px] w-full overflow-hidden rounded-xl border border-border bg-canvas">
      <div ref={containerRef} className="h-full w-full" />
      {graph.is_attack && (
        <div className="absolute right-3 top-3 rounded-lg border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger backdrop-blur-sm">
          Suspicious activity on {graph.victim_ip}
        </div>
      )}
    </div>
  );
}
