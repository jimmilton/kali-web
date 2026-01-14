'use client';

import { useCallback, useMemo, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow,
  Panel,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';

import { AssetNode } from './asset-node';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react';

const nodeTypes = {
  asset: AssetNode,
};

const nodeWidth = 180;
const nodeHeight = 80;

// Layout nodes using dagre
function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 50 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

interface AssetGraphProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick?: (nodeId: string) => void;
}

function AssetGraphInner({ nodes: initialNodes, edges: initialEdges, onNodeClick }: AssetGraphProps) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  // Apply layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    return getLayoutedElements(
      initialNodes.map((n) => ({ ...n, type: 'asset' })),
      initialEdges.map((e) => ({
        ...e,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#888', strokeWidth: 2 },
        labelStyle: { fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: 'white', fillOpacity: 0.8 },
      }))
    );
  }, [initialNodes, initialEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = getLayoutedElements(
      initialNodes.map((n) => ({ ...n, type: 'asset' })),
      initialEdges.map((e) => ({
        ...e,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#888', strokeWidth: 2 },
        labelStyle: { fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: 'white', fillOpacity: 0.8 },
      }))
    );
    setNodes(newNodes);
    setEdges(newEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  // Count nodes by type
  const typeStats = useMemo(() => {
    const stats: Record<string, number> = {};
    nodes.forEach((node) => {
      const type = node.data?.asset_type || 'unknown';
      stats[type] = (stats[type] || 0) + 1;
    });
    return stats;
  }, [nodes]);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            const colors: Record<string, string> = {
              host: '#22c55e',
              domain: '#3b82f6',
              subdomain: '#8b5cf6',
              url: '#f97316',
              service: '#06b6d4',
              network: '#eab308',
              endpoint: '#ec4899',
              certificate: '#6366f1',
              technology: '#14b8a6',
            };
            return colors[node.data?.asset_type] || '#888';
          }}
        />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />

        {/* Top panel with stats */}
        <Panel position="top-left" className="flex gap-2 flex-wrap">
          {Object.entries(typeStats).map(([type, count]) => (
            <Badge key={type} variant="outline" className="text-xs">
              {type}: {count}
            </Badge>
          ))}
        </Panel>

        {/* Controls panel */}
        <Panel position="top-right" className="flex gap-1">
          <Button variant="outline" size="icon" onClick={() => zoomIn()}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => zoomOut()}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => fitView()}>
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => {
              const { nodes: newNodes, edges: newEdges } = getLayoutedElements(nodes, edges);
              setNodes(newNodes);
              setEdges(newEdges);
              setTimeout(() => fitView(), 50);
            }}
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        </Panel>
      </ReactFlow>
    </div>
  );
}

export function AssetGraph(props: AssetGraphProps) {
  return (
    <ReactFlowProvider>
      <AssetGraphInner {...props} />
    </ReactFlowProvider>
  );
}
