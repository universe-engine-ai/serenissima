import React, { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useRouter } from 'next/router';

interface MapNode {
  id: string;
  name: string;
  path: string;
  type: 'directory' | 'file';
  description?: string;
  role?: string;
  children?: MapNode[];
}

interface CodebaseMapViewerProps {
  onClose?: () => void;
  standalone?: boolean;
}

const CodebaseMapViewer: React.FC<CodebaseMapViewerProps> = ({ onClose, standalone = false }) => {
  const [mapData, setMapData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<MapNode | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchMapData = async () => {
      try {
        const response = await fetch('/api/codebase-map');
        if (!response.ok) {
          throw new Error('Failed to fetch codebase map data');
        }
        const data = await response.json();
        setMapData(data);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    };

    fetchMapData();
  }, []);

  useEffect(() => {
    if (mapData && svgRef.current) {
      renderVisualization();
    }
  }, [mapData]);

  const processStructureToNodes = (structure: any, parentPath = ''): MapNode[] => {
    const nodes: MapNode[] = [];
    
    Object.entries(structure).forEach(([key, value]: [string, any]) => {
      if (key === 'important_files' && Array.isArray(value)) {
        value.forEach((file: any) => {
          nodes.push({
            id: file.path,
            name: file.path.split('/').pop() || '',
            path: file.path,
            type: 'file',
            description: file.role || '',
            role: file.role
          });
        });
      } else if (typeof value === 'object' && value !== null) {
        const currentPath = value.path || `${parentPath}/${key}`;
        const node: MapNode = {
          id: currentPath,
          name: key,
          path: currentPath,
          type: 'directory',
          description: value.description || '',
          children: []
        };

        if (value.sub_directories) {
          node.children = [
            ...processStructureToNodes(value.sub_directories, currentPath)
          ];
        }

        if (value.important_files) {
          node.children = [
            ...(node.children || []),
            ...value.important_files.map((file: any) => ({
              id: file.path,
              name: file.path.split('/').pop() || '',
              path: file.path,
              type: 'file',
              description: file.role || '',
              role: file.role
            }))
          ];
        }

        nodes.push(node);
      }
    });

    return nodes;
  };

  const renderVisualization = () => {
    if (!svgRef.current || !mapData) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll('*').remove();

    const width = 1000;
    const height = 800;
    const margin = { top: 20, right: 120, bottom: 20, left: 120 };

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Process data into hierarchical structure
    const hierarchyData = {
      id: 'root',
      name: mapData.project_name,
      path: '/',
      type: 'directory' as const,
      description: mapData.description,
      children: processStructureToNodes(mapData.structure)
    };

    // Create hierarchy
    const root = d3.hierarchy(hierarchyData);
    
    // Create tree layout
    const treeLayout = d3.tree().size([height - margin.top - margin.bottom, width - margin.left - margin.right]);
    
    // Compute the tree layout
    const treeData = treeLayout(root);
    
    // Add links between nodes
    svg.selectAll('.link')
      .data(treeData.links())
      .enter()
      .append('path')
      .attr('class', 'link')
      .attr('d', d => {
        return `M${d.source.y},${d.source.x}
                C${(d.source.y + d.target.y) / 2},${d.source.x}
                 ${(d.source.y + d.target.y) / 2},${d.target.x}
                 ${d.target.y},${d.target.x}`;
      })
      .attr('fill', 'none')
      .attr('stroke', '#ccc')
      .attr('stroke-width', 1.5);
    
    // Add nodes
    const nodes = svg.selectAll('.node')
      .data(treeData.descendants())
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('transform', d => `translate(${d.y},${d.x})`)
      .on('click', (event, d) => {
        setSelectedNode(d.data);
      });
    
    // Add circles for nodes
    nodes.append('circle')
      .attr('r', 5)
      .attr('fill', d => d.data.type === 'directory' ? '#4299e1' : '#f6ad55')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);
    
    // Add labels for nodes
    nodes.append('text')
      .attr('dy', '.31em')
      .attr('x', d => d.children ? -8 : 8)
      .attr('text-anchor', d => d.children ? 'end' : 'start')
      .text(d => d.data.name)
      .style('font-size', '12px')
      .style('fill', '#333');
  };

  const handleNodeClick = (path: string) => {
    // This could navigate to a file viewer or editor component
    console.log(`Navigate to: ${path}`);
    // router.push(`/code-viewer?path=${encodeURIComponent(path)}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
        <strong className="font-bold">Error!</strong>
        <span className="block sm:inline"> {error}</span>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-lg ${standalone ? 'p-6 max-w-6xl mx-auto my-8' : 'p-4'}`}>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-800">
          {mapData?.project_name || 'Codebase Map'} Visualization
        </h2>
        {onClose && (
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      
      <div className="flex flex-col md:flex-row gap-4">
        <div className="md:w-3/4 overflow-auto border border-gray-200 rounded-lg">
          <svg ref={svgRef} className="w-full h-[800px]"></svg>
        </div>
        
        <div className="md:w-1/4">
          {selectedNode && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-medium text-gray-900">{selectedNode.name}</h3>
              <p className="text-sm text-gray-600 mt-1">{selectedNode.path}</p>
              
              {selectedNode.description && (
                <div className="mt-3">
                  <h4 className="text-sm font-medium text-gray-700">Description:</h4>
                  <p className="text-sm text-gray-600 mt-1">{selectedNode.description}</p>
                </div>
              )}
              
              {selectedNode.role && (
                <div className="mt-3">
                  <h4 className="text-sm font-medium text-gray-700">Role:</h4>
                  <p className="text-sm text-gray-600 mt-1">{selectedNode.role}</p>
                </div>
              )}
              
              {selectedNode.type === 'file' && (
                <button
                  onClick={() => handleNodeClick(selectedNode.path)}
                  className="mt-4 px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
                >
                  View File
                </button>
              )}
            </div>
          )}
          
          {!selectedNode && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm">Select a node from the visualization to view details.</p>
            </div>
          )}
          
          <div className="mt-4 bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-gray-900">Legend</h3>
            <div className="mt-2 space-y-2">
              <div className="flex items-center">
                <div className="w-4 h-4 rounded-full bg-blue-500 mr-2"></div>
                <span className="text-sm text-gray-600">Directory</span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 rounded-full bg-orange-400 mr-2"></div>
                <span className="text-sm text-gray-600">File</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-4 text-sm text-gray-500">
        <p>Last updated: {mapData?.last_updated || 'Unknown'}</p>
        <p>Visualization version: {mapData?.visualization_version || '1.0'}</p>
      </div>
    </div>
  );
};

export default CodebaseMapViewer;
