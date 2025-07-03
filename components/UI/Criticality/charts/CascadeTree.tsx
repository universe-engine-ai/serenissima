'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Cascade } from '@/lib/services/criticality/cascadeAnalyzer';

interface CascadeTreeProps {
  cascade: Cascade;
}

interface TreeNode {
  name: string;
  message: string;
  time: string;
  children?: TreeNode[];
}

export default function CascadeTree({ cascade }: CascadeTreeProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    // Clear previous content
    d3.select(svgRef.current).selectAll('*').remove();

    // Convert cascade to tree structure
    const convertToTreeData = (c: Cascade): TreeNode => ({
      name: `${c.rootMessage.sender} → ${c.rootMessage.receiver}`,
      message: c.rootMessage.content.substring(0, 50) + '...',
      time: new Date(c.rootMessage.timestamp).toLocaleTimeString(),
      children: c.children.map(child => convertToTreeData(child))
    });

    const treeData = convertToTreeData(cascade);

    // Set dimensions
    const margin = { top: 20, right: 120, bottom: 20, left: 120 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = svgRef.current.clientHeight - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current);
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create tree layout
    const treeLayout = d3.tree<TreeNode>()
      .size([height, width]);

    // Create hierarchy
    const root = d3.hierarchy(treeData);
    const treeNodes = treeLayout(root);

    // Add links
    const link = g.selectAll('.link')
      .data(treeNodes.links())
      .enter().append('path')
      .attr('class', 'link')
      .attr('d', d3.linkHorizontal<any, any>()
        .x(d => d.y)
        .y(d => d.x))
      .attr('fill', 'none')
      .attr('stroke', '#d97706')
      .attr('stroke-width', 2);

    // Add nodes
    const node = g.selectAll('.node')
      .data(treeNodes.descendants())
      .enter().append('g')
      .attr('class', 'node')
      .attr('transform', d => `translate(${d.y},${d.x})`);

    // Add circles
    node.append('circle')
      .attr('r', 6)
      .attr('fill', d => d.children ? '#d97706' : '#fbbf24')
      .attr('stroke', '#92400e')
      .attr('stroke-width', 2);

    // Add labels
    node.append('text')
      .attr('dy', '.35em')
      .attr('x', d => d.children ? -13 : 13)
      .style('text-anchor', d => d.children ? 'end' : 'start')
      .style('font-size', '11px')
      .style('fill', '#92400e')
      .text(d => d.data.name);

    // Add time labels
    node.append('text')
      .attr('dy', '1.5em')
      .attr('x', d => d.children ? -13 : 13)
      .style('text-anchor', d => d.children ? 'end' : 'start')
      .style('font-size', '9px')
      .style('fill', '#d97706')
      .style('font-style', 'italic')
      .text(d => d.data.time);

    // Add hover effect
    node.on('mouseover', function(event, d) {
      d3.select(this).select('circle')
        .transition()
        .duration(200)
        .attr('r', 8);
      
      // Show tooltip
      const tooltip = g.append('g')
        .attr('id', 'tooltip');
      
      const rect = tooltip.append('rect')
        .attr('x', d.y + 15)
        .attr('y', d.x - 20)
        .attr('rx', 4)
        .attr('ry', 4)
        .attr('fill', 'white')
        .attr('stroke', '#d97706')
        .attr('stroke-width', 1);
      
      const text = tooltip.append('text')
        .attr('x', d.y + 20)
        .attr('y', d.x - 5)
        .style('font-size', '11px')
        .style('fill', '#92400e')
        .text(d.data.message);
      
      const bbox = text.node()?.getBBox();
      if (bbox) {
        rect.attr('width', bbox.width + 10)
          .attr('height', bbox.height + 10)
          .attr('x', bbox.x - 5)
          .attr('y', bbox.y - 5);
      }
    })
    .on('mouseout', function(event, d) {
      d3.select(this).select('circle')
        .transition()
        .duration(200)
        .attr('r', 6);
      
      g.select('#tooltip').remove();
    });

    // Add cascade stats
    const stats = g.append('g')
      .attr('transform', `translate(${width - 100}, 20)`);

    stats.append('rect')
      .attr('x', -10)
      .attr('y', -15)
      .attr('width', 110)
      .attr('height', 70)
      .attr('fill', '#fef3c7')
      .attr('stroke', '#d97706')
      .attr('rx', 4);

    stats.append('text')
      .attr('y', 0)
      .style('font-size', '12px')
      .style('font-weight', 'bold')
      .style('fill', '#92400e')
      .text('Cascade Stats');

    stats.append('text')
      .attr('y', 20)
      .style('font-size', '11px')
      .style('fill', '#92400e')
      .text(`Size: ${cascade.totalSize}`);

    stats.append('text')
      .attr('y', 35)
      .style('font-size', '11px')
      .style('fill', '#92400e')
      .text(`Depth: ${cascade.depth}`);

    stats.append('text')
      .attr('y', 50)
      .style('font-size', '11px')
      .style('fill', '#92400e')
      .text(`Duration: ${cascade.duration.toFixed(0)}m`);

  }, [cascade]);

  return (
    <svg ref={svgRef} className="w-full h-full" />
  );
}