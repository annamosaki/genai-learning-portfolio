'use client';

import { useMemo } from 'react';

interface Node {
  id: string;
  label: string;
  type?: string;
  metadata?: Record<string, any>;
}

interface Edge {
  from: string;
  to: string;
  label?: string;
  weight?: number;
}

interface Graph {
  nodes: Node[];
  edges: Edge[];
}

interface GraphCanvasProps {
  graph: Graph;
}

export function GraphCanvas({ graph }: GraphCanvasProps) {
  const { nodes, edges } = graph;
  
  const layout = useMemo(() => {
    if (nodes.length === 0) return { nodes: [], edges: [] };
    
    // Simple force-directed layout
    const width = 400;
    const height = 300;
    const centerX = width / 2;
    const centerY = height / 2;
    
    // Position nodes in a circle if few nodes, or use a grid for many
    const layoutNodes = nodes.map((node, index) => {
      let x, y;
      
      if (nodes.length <= 8) {
        // Circular layout for small graphs
        const angle = (index * 2 * Math.PI) / nodes.length;
        const radius = Math.min(width, height) * 0.3;
        x = centerX + radius * Math.cos(angle);
        y = centerY + radius * Math.sin(angle);
      } else {
        // Grid layout for larger graphs
        const cols = Math.ceil(Math.sqrt(nodes.length));
        const row = Math.floor(index / cols);
        const col = index % cols;
        x = (width / (cols + 1)) * (col + 1);
        y = (height / (Math.ceil(nodes.length / cols) + 1)) * (row + 1);
      }
      
      return {
        ...node,
        x: Math.max(30, Math.min(width - 30, x)),
        y: Math.max(30, Math.min(height - 30, y)),
      };
    });
    
    // Create edge paths
    const layoutEdges = edges.map(edge => {
      const fromNode = layoutNodes.find(n => n.id === edge.from);
      const toNode = layoutNodes.find(n => n.id === edge.to);
      
      if (!fromNode || !toNode) return null;
      
      return {
        ...edge,
        x1: fromNode.x,
        y1: fromNode.y,
        x2: toNode.x,
        y2: toNode.y,
      };
    }).filter((edge): edge is NonNullable<typeof edge> => edge !== null);
    
    return { nodes: layoutNodes, edges: layoutEdges, width, height };
  }, [nodes, edges]);
  
  if (nodes.length === 0) {
    return (
      <div className="bg-panel border border-line rounded-lg p-8 text-center text-muted">
        <p>No graph nodes to display</p>
      </div>
    );
  }
  
  return (
    <div className="bg-panel border border-line rounded-lg p-4">
      <svg
        width={layout.width}
        height={layout.height}
        className="w-full"
        viewBox={`0 0 ${layout.width} ${layout.height}`}
      >
        {/* Edges */}
        <g>
          {layout.edges.map((edge, index) => (
            <g key={index}>
              <line
                x1={edge.x1}
                y1={edge.y1}
                x2={edge.x2}
                y2={edge.y2}
                stroke="rgba(148,163,184,0.4)"
                strokeWidth={edge.weight ? Math.max(1, edge.weight * 3) : 1}
                markerEnd="url(#arrowhead)"
              />
              {edge.label && (
                <text
                  x={(edge.x1 + edge.x2) / 2}
                  y={(edge.y1 + edge.y2) / 2}
                  fill="#8b9bb4"
                  fontSize="10"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="pointer-events-none"
                >
                  {edge.label}
                </text>
              )}
            </g>
          ))}
        </g>
        
        {/* Arrow marker */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              fill="rgba(148,163,184,0.4)"
            />
          </marker>
        </defs>
        
        {/* Nodes */}
        <g>
          {layout.nodes.map((node, index) => {
            const nodeType = node.type || 'default';
            const fillColor = nodeType === 'entity' ? '#3dffb5' : 
                             nodeType === 'concept' ? '#4cc9ff' : 
                             '#8b9bb4';
            
            return (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="20"
                  fill={fillColor}
                  fillOpacity="0.2"
                  stroke={fillColor}
                  strokeWidth="2"
                />
                <text
                  x={node.x}
                  y={node.y + 5}
                  fill="#e8eef7"
                  fontSize="11"
                  textAnchor="middle"
                  className="pointer-events-none font-medium"
                >
                  {node.label.length > 8 ? `${node.label.slice(0, 8)}...` : node.label}
                </text>
                
                {/* Tooltip on hover */}
                <title>
                  {`${node.label}${node.type ? ` (${node.type})` : ''}${
                    node.metadata ? `\n${JSON.stringify(node.metadata, null, 2)}` : ''
                  }`}
                </title>
              </g>
            );
          })}
        </g>
      </svg>
      
      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-xs text-muted">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-accent opacity-20 border border-accent"></div>
          <span>Entity</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-accent-2 opacity-20 border border-accent-2"></div>
          <span>Concept</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-muted opacity-20 border border-muted"></div>
          <span>Default</span>
        </div>
      </div>
    </div>
  );
}