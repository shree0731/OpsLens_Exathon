import React, { useMemo, useCallback, useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  ConnectionLineType,
  BackgroundVariant,
} from '@xyflow/react';
import dagre from 'dagre';
import { SourceNode } from './nodes/SourceNode';
import { JobNode } from './nodes/JobNode';
import { TableNode } from './nodes/TableNode';
import { MartNode } from './nodes/MartNode';
import { DashboardNode } from './nodes/DashboardNode';
import { BlastRadiusBanner } from './BlastRadiusBanner';
import { NodeSidePanel } from './NodeSidePanel';
import { Skeleton } from '../common/Skeleton';
import { EmptyState } from '../common/EmptyState';
import { SecondaryButton } from '../common/SecondaryButton';
import { RefreshCw, AlertCircle } from 'lucide-react';
import type { LineageGraphResponse, LineageNode } from '../../types/api';

const NODE_WIDTH = 230;
const NODE_HEIGHT = 86;

const nodeTypes = {
  source: SourceNode,
  job: JobNode,
  table: TableNode,
  mart: MartNode,
  dashboard: DashboardNode,
};

interface LineageCanvasProps {
  data?: LineageGraphResponse;
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  onRetry: () => void;
}

// Dagre layout computation: left-to-right
function getLayoutedElements(nodesData: LineageNode[], edgesData: any[]) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: 'LR',
    align: 'DL',
    nodesep: 45,
    ranksep: 90,
    marginx: 40,
    marginy: 40,
  });

  nodesData.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edgesData.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes: Node[] = nodesData.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      id: node.id,
      type: node.type,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
      data: {
        ...node,
      },
    };
  });

  const layoutedEdges: Edge[] = edgesData.map((edge) => ({
    id: edge.edge_id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: false,
    style: { stroke: '#94A3B8', strokeWidth: 1.5 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 14,
      height: 14,
      color: '#94A3B8',
    },
    data: {
      relation: edge.relation || edge.relation_type,
    },
  }));

  return { nodes: layoutedNodes, edges: layoutedEdges };
}

export const LineageCanvas: React.FC<LineageCanvasProps> = ({
  data,
  isLoading,
  isError,
  error,
  onRetry,
}) => {
  const [searchParams] = useSearchParams();
  const urlNodeParam = searchParams.get('node');

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(urlNodeParam);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (urlNodeParam) {
      setSelectedNodeId(urlNodeParam);
    }
  }, [urlNodeParam]);

  // Collect all affected node IDs from any node with an active blast radius or open alert
  const activeBlastRadius = useMemo(() => {
    if (!data?.nodes) return null;
    // Find node with direct alerts or degraded status
    const alertedNode = data.nodes.find(
      (n) => n.active_alerts && n.active_alerts.length > 0 && n.blast_radius
    );
    if (alertedNode && alertedNode.blast_radius) {
      return {
        originId: alertedNode.id,
        originLabel: alertedNode.label,
        summary: alertedNode.blast_radius.summary,
        affectedIds: new Set(alertedNode.blast_radius.affected_node_ids),
      };
    }
    // Fallback: check banner_blast if provided
    if (data.banner_blast) {
      return {
        originId: data.banner_blast.node_id,
        originLabel: data.banner_blast.label,
        summary: data.banner_blast.summary,
        affectedIds: new Set(data.banner_blast.affected_node_ids),
      };
    }
    return null;
  }, [data]);

  // Synchronize data and apply dagre layout
  useEffect(() => {
    if (!data?.nodes || data.nodes.length === 0) return;

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      data.nodes,
      data.edges
    );

    // Apply blast radius highlighting and dimming
    const styledNodes = layoutedNodes.map((n) => {
      const isOrigin = activeBlastRadius?.originId === n.id;
      const isAffected = activeBlastRadius?.affectedIds.has(n.id);
      const isDimmed =
        activeBlastRadius !== null && !isOrigin && !isAffected;

      return {
        ...n,
        data: {
          ...n.data,
          isSelected: selectedNodeId === n.id,
          isBlastAffected: isAffected,
          isDimmed,
        },
      };
    });

    const styledEdges = layoutedEdges.map((e) => {
      // If edge connects to or within affected nodes, turn red and animate
      const affectsTarget =
        activeBlastRadius &&
        (activeBlastRadius.originId === e.source || activeBlastRadius.affectedIds.has(e.source)) &&
        activeBlastRadius.affectedIds.has(e.target);

      if (affectsTarget) {
        return {
          ...e,
          animated: true,
          style: { stroke: '#EF4444', strokeWidth: 2.5 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 16,
            height: 16,
            color: '#EF4444',
          },
        };
      }

      return {
        ...e,
        style: activeBlastRadius ? { stroke: '#CBD5E1', strokeWidth: 1.5 } : { stroke: '#94A3B8', strokeWidth: 1.5 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: activeBlastRadius ? '#CBD5E1' : '#94A3B8',
        },
      };
    });

    setNodes(styledNodes);
    setEdges(styledEdges);
  }, [data, activeBlastRadius, selectedNodeId, setNodes, setEdges]);

  // Handle node selection
  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const selectedNodeData = useMemo(() => {
    if (!selectedNodeId || !data?.nodes) return null;
    return data.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, data]);

  // Find upstream & downstream dependencies for sidepanel
  const { upstreamNodes, downstreamNodes } = useMemo(() => {
    if (!selectedNodeId || !data) return { upstreamNodes: [], downstreamNodes: [] };

    const nodesMap = new Map(data.nodes.map((n) => [n.id, n]));
    const up = data.edges
      .filter((e) => e.target === selectedNodeId)
      .map((e) => ({
        id: e.source,
        label: nodesMap.get(e.source)?.label || e.source,
        type: nodesMap.get(e.source)?.type || 'unknown',
      }));

    const down = data.edges
      .filter((e) => e.source === selectedNodeId)
      .map((e) => ({
        id: e.target,
        label: nodesMap.get(e.target)?.label || e.target,
        type: nodesMap.get(e.target)?.type || 'unknown',
      }));

    return { upstreamNodes: up, downstreamNodes: down };
  }, [selectedNodeId, data]);

  // Loading State
  if (isLoading && (!data || data.nodes.length === 0)) {
    return (
      <div className="h-full w-full bg-white rounded-2xl border border-slate-200/80 p-8 flex flex-col items-center justify-center space-y-4 shadow-soft">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full max-w-4xl" />
        <p className="text-sm text-slate-400">Loading lineage dependency graph from Exasol...</p>
      </div>
    );
  }

  // Error State
  if (isError) {
    return (
      <div className="h-full w-full bg-white rounded-2xl border border-slate-200/80 p-8 flex flex-col items-center justify-center space-y-4 shadow-soft">
        <div className="p-3 bg-rose-50 text-rose-600 rounded-full">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h3 className="text-base font-semibold text-slate-900">Failed to Connect to OpsLens API</h3>
        <p className="text-sm text-slate-500 max-w-md text-center">
          {error?.message || 'Could not fetch lineage graph. Please verify that the FastAPI backend is running on port 8000.'}
        </p>
        <SecondaryButton onClick={onRetry} icon={<RefreshCw className="w-4 h-4" />}>
          Retry Connection
        </SecondaryButton>
      </div>
    );
  }

  // Empty State
  if (!data?.nodes || data.nodes.length === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <EmptyState
          title="Lineage Graph Empty"
          description="No lineage edges or nodes found in OPSLENS.LINEAGE_EDGES."
          action={
            <SecondaryButton onClick={onRetry} icon={<RefreshCw className="w-4 h-4" />}>
              Reload
            </SecondaryButton>
          }
        />
      </div>
    );
  }

  return (
    <div className="relative h-full w-full bg-white rounded-2xl border border-slate-200/80 shadow-soft overflow-hidden">
      {/* Blast Radius Active Banner */}
      <BlastRadiusBanner
        banner={
          activeBlastRadius
            ? {
                node_id: activeBlastRadius.originId,
                label: activeBlastRadius.originLabel,
                summary: activeBlastRadius.summary,
                affected_node_ids: Array.from(activeBlastRadius.affectedIds),
              }
            : null
        }
        banners={data?.banners || []}
        onShowDetails={(nid) => setSelectedNodeId(nid)}
      />

      {/* React Flow Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.8}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        connectionLineType={ConnectionLineType.SmoothStep}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#E2E8F0" />
        <Controls position="bottom-left" showInteractive={false} />
        <MiniMap
          position="bottom-right"
          nodeColor={(n: any) => {
            const st = n.data?.status || 'GREEN';
            if (st === 'RED') return '#EF4444';
            if (st === 'AMBER') return '#F59E0B';
            return '#10B981';
          }}
          className="!bg-white/90 !rounded-xl !border !border-slate-200 !shadow-soft overflow-hidden"
          maskColor="rgba(241, 245, 249, 0.65)"
        />
      </ReactFlow>

      {/* SidePanel Drawer for Node Details */}
      <NodeSidePanel
        node={selectedNodeData}
        onClose={() => setSelectedNodeId(null)}
        onSelectNode={(nid) => setSelectedNodeId(nid)}
        upstreamNodes={upstreamNodes}
        downstreamNodes={downstreamNodes}
      />
    </div>
  );
};
