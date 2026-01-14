'use client';

import { useCallback, useState, useRef, DragEvent, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { nodeTypes } from './nodes';
import { NodeSidebar } from './node-sidebar';
import { NodeProperties } from './node-properties';
import { Button } from '@/components/ui/button';
import { Save, Play, Undo, Redo, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WorkflowBuilderProps {
  initialNodes?: Node[];
  initialEdges?: Edge[];
  tools?: Array<{ slug: string; name: string }>;
  onSave?: (nodes: Node[], edges: Edge[]) => void;
  onRun?: () => void;
  readOnly?: boolean;
}

let nodeId = 0;
const getNodeId = () => `node_${nodeId++}`;

function WorkflowBuilderInner({
  initialNodes = [],
  initialEdges = [],
  tools = [],
  onSave,
  onRun,
  readOnly = false,
}: WorkflowBuilderProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [history, setHistory] = useState<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Initialize node ID counter based on existing nodes
  useEffect(() => {
    if (initialNodes.length > 0) {
      const maxId = initialNodes.reduce((max, node) => {
        const match = node.id.match(/node_(\d+)/);
        if (match) {
          return Math.max(max, parseInt(match[1]));
        }
        return max;
      }, 0);
      nodeId = maxId + 1;
    }
  }, [initialNodes]);

  const saveToHistory = useCallback(() => {
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({ nodes: [...nodes], edges: [...edges] });
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  }, [nodes, edges, history, historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setNodes(history[newIndex].nodes);
      setEdges(history[newIndex].edges);
    }
  }, [historyIndex, history, setNodes, setEdges]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setNodes(history[newIndex].nodes);
      setEdges(history[newIndex].edges);
    }
  }, [historyIndex, history, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge({ ...params, animated: true }, eds));
      saveToHistory();
    },
    [setEdges, saveToHistory]
  );

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: getNodeId(),
        type,
        position,
        data: { label: `${type.charAt(0).toUpperCase() + type.slice(1)} Node` },
      };

      setNodes((nds) => nds.concat(newNode));
      saveToHistory();
    },
    [screenToFlowPosition, setNodes, saveToHistory]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const onNodeDataUpdate = useCallback(
    (nodeId: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === nodeId) {
            return { ...node, data: { ...node.data, ...data } };
          }
          return node;
        })
      );
      // Update selected node reference
      setSelectedNode((prev) => {
        if (prev && prev.id === nodeId) {
          return { ...prev, data: { ...prev.data, ...data } };
        }
        return prev;
      });
    },
    [setNodes]
  );

  const deleteSelectedNode = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((node) => node.id !== selectedNode.id));
      setEdges((eds) =>
        eds.filter(
          (edge) =>
            edge.source !== selectedNode.id && edge.target !== selectedNode.id
        )
      );
      setSelectedNode(null);
      saveToHistory();
    }
  }, [selectedNode, setNodes, setEdges, saveToHistory]);

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(nodes, edges);
    }
  }, [nodes, edges, onSave]);

  return (
    <div className="flex h-full">
      {/* Left Sidebar - Node Types */}
      {!readOnly && (
        <div className="w-56 border-r">
          <NodeSidebar />
        </div>
      )}

      {/* Main Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center justify-between p-2 border-b">
          <div className="flex items-center gap-1">
            {!readOnly && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={undo}
                  disabled={historyIndex <= 0}
                >
                  <Undo className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={redo}
                  disabled={historyIndex >= history.length - 1}
                >
                  <Redo className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={deleteSelectedNode}
                  disabled={!selectedNode}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!readOnly && onSave && (
              <Button variant="outline" size="sm" onClick={handleSave}>
                <Save className="h-4 w-4 mr-1" />
                Save
              </Button>
            )}
            {onRun && (
              <Button size="sm" onClick={onRun}>
                <Play className="h-4 w-4 mr-1" />
                Run Workflow
              </Button>
            )}
          </div>
        </div>

        {/* React Flow Canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={readOnly ? undefined : onNodesChange}
            onEdgesChange={readOnly ? undefined : onEdgesChange}
            onConnect={readOnly ? undefined : onConnect}
            onDrop={readOnly ? undefined : onDrop}
            onDragOver={readOnly ? undefined : onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            nodesDraggable={!readOnly}
            nodesConnectable={!readOnly}
            elementsSelectable={true}
          >
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const colors: Record<string, string> = {
                  tool: '#22c55e',
                  condition: '#eab308',
                  delay: '#3b82f6',
                  notification: '#a855f7',
                  parallel: '#f97316',
                  loop: '#06b6d4',
                  manual: '#ec4899',
                };
                return colors[node.type || 'tool'] || '#888';
              }}
            />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>
      </div>

      {/* Right Sidebar - Properties */}
      {!readOnly && (
        <div className="w-72 border-l">
          <NodeProperties
            node={selectedNode}
            tools={tools}
            onUpdate={onNodeDataUpdate}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
    </div>
  );
}

export function WorkflowBuilder(props: WorkflowBuilderProps) {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderInner {...props} />
    </ReactFlowProvider>
  );
}
