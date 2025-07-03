'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface LogLogPlotProps {
  data: { size: number; count: number }[];
  xlabel: string;
  ylabel: string;
  expectedSlope?: number;
}

export default function LogLogPlot({ data, xlabel, ylabel, expectedSlope }: LogLogPlotProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return;

    // Clear previous content
    d3.select(svgRef.current).selectAll('*').remove();

    // Set dimensions and margins
    const margin = { top: 20, right: 80, bottom: 50, left: 70 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = svgRef.current.clientHeight - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current);
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare data - aggregate by size
    const sizeMap = new Map<number, number>();
    data.forEach(d => {
      sizeMap.set(d.size, (sizeMap.get(d.size) || 0) + d.count);
    });

    const plotData = Array.from(sizeMap.entries())
      .map(([size, count]) => ({ size, count }))
      .filter(d => d.size > 0 && d.count > 0)
      .sort((a, b) => a.size - b.size);

    if (plotData.length === 0) return;

    // Create log scales
    const xScale = d3.scaleLog()
      .domain([
        Math.min(...plotData.map(d => d.size)),
        Math.max(...plotData.map(d => d.size))
      ])
      .range([0, width])
      .nice();

    const yScale = d3.scaleLog()
      .domain([
        Math.min(...plotData.map(d => d.count)),
        Math.max(...plotData.map(d => d.count))
      ])
      .range([height, 0])
      .nice();

    // Add axes
    const xAxis = d3.axisBottom(xScale)
      .ticks(5)
      .tickFormat(d3.format('.0f'));

    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat(d3.format('.0f'));

    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis)
      .append('text')
      .attr('x', width / 2)
      .attr('y', 40)
      .attr('fill', '#92400e')
      .style('text-anchor', 'middle')
      .text(xlabel);

    g.append('g')
      .call(yAxis)
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -50)
      .attr('x', -height / 2)
      .attr('fill', '#92400e')
      .style('text-anchor', 'middle')
      .text(ylabel);

    // Add grid lines
    g.append('g')
      .attr('class', 'grid')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis.tickSize(-height).tickFormat(() => ''))
      .style('stroke-dasharray', '3,3')
      .style('opacity', 0.3);

    g.append('g')
      .attr('class', 'grid')
      .call(yAxis.tickSize(-width).tickFormat(() => ''))
      .style('stroke-dasharray', '3,3')
      .style('opacity', 0.3);

    // Plot data points
    g.selectAll('.dot')
      .data(plotData)
      .enter().append('circle')
      .attr('class', 'dot')
      .attr('cx', d => xScale(d.size))
      .attr('cy', d => yScale(d.count))
      .attr('r', 4)
      .attr('fill', '#d97706')
      .attr('stroke', '#92400e')
      .attr('stroke-width', 1);

    // Add power law fit line if we have enough points
    if (plotData.length > 3 && expectedSlope) {
      // Simple power law fit: y = a * x^slope
      const logData = plotData.map(d => ({
        x: Math.log(d.size),
        y: Math.log(d.count)
      }));

      // Calculate intercept for the expected slope
      const meanLogX = d3.mean(logData, d => d.x) || 0;
      const meanLogY = d3.mean(logData, d => d.y) || 0;
      const intercept = meanLogY - expectedSlope * meanLogX;

      // Generate fit line
      const xMin = Math.min(...plotData.map(d => d.size));
      const xMax = Math.max(...plotData.map(d => d.size));
      const fitLine = [
        { x: xMin, y: Math.exp(intercept + expectedSlope * Math.log(xMin)) },
        { x: xMax, y: Math.exp(intercept + expectedSlope * Math.log(xMax)) }
      ];

      const line = d3.line<{x: number, y: number}>()
        .x(d => xScale(d.x))
        .y(d => yScale(d.y));

      g.append('path')
        .datum(fitLine)
        .attr('fill', 'none')
        .attr('stroke', '#dc2626')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '5,5')
        .attr('d', line);

      // Add legend
      const legend = g.append('g')
        .attr('transform', `translate(${width - 120}, 20)`);

      legend.append('line')
        .attr('x1', 0)
        .attr('x2', 20)
        .attr('y1', 0)
        .attr('y2', 0)
        .attr('stroke', '#dc2626')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '5,5');

      legend.append('text')
        .attr('x', 25)
        .attr('y', 4)
        .attr('fill', '#92400e')
        .style('font-size', '12px')
        .text(`Slope: ${expectedSlope}`);
    }

    // Calculate actual slope
    if (plotData.length > 2) {
      const logData = plotData.map(d => ({
        x: Math.log(d.size),
        y: Math.log(d.count)
      }));

      const n = logData.length;
      const sumX = d3.sum(logData, d => d.x);
      const sumY = d3.sum(logData, d => d.y);
      const sumXY = d3.sum(logData, d => d.x * d.y);
      const sumX2 = d3.sum(logData, d => d.x * d.x);

      const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);

      g.append('text')
        .attr('x', width - 120)
        .attr('y', 45)
        .attr('fill', '#92400e')
        .style('font-size', '12px')
        .text(`Actual: ${slope.toFixed(2)}`);
    }

  }, [data, xlabel, ylabel, expectedSlope]);

  return (
    <svg ref={svgRef} className="w-full h-full" />
  );
}