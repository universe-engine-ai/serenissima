'use client';

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer
} from 'recharts';

interface HistogramProps {
  data: number[];
  xlabel: string;
  ylabel: string;
  bins: number;
  criticalLine?: number;
}

export default function Histogram({ data, xlabel, ylabel, bins, criticalLine }: HistogramProps) {
  const histogramData = useMemo(() => {
    if (data.length === 0) return [];

    // Calculate bin size and range
    const min = Math.min(...data);
    const max = Math.max(...data);
    const binSize = (max - min) / bins;

    // Initialize bins
    const histogram = new Array(bins).fill(0).map((_, i) => ({
      binStart: min + i * binSize,
      binEnd: min + (i + 1) * binSize,
      count: 0,
      label: ''
    }));

    // Count values in each bin
    data.forEach(value => {
      const binIndex = Math.min(Math.floor((value - min) / binSize), bins - 1);
      if (binIndex >= 0 && binIndex < bins) {
        histogram[binIndex].count++;
      }
    });

    // Add labels
    histogram.forEach((bin, i) => {
      if (i === 0) {
        bin.label = `${bin.binStart.toFixed(2)}`;
      } else if (i === bins - 1) {
        bin.label = `${bin.binEnd.toFixed(2)}`;
      } else if (i % Math.ceil(bins / 5) === 0) {
        bin.label = `${bin.binStart.toFixed(2)}`;
      }
    });

    return histogram;
  }, [data, bins]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-2 border border-amber-300 rounded shadow-md">
          <p className="text-xs text-amber-800">
            Range: {data.binStart.toFixed(3)} - {data.binEnd.toFixed(3)}
          </p>
          <p className="text-sm font-medium text-amber-700">
            Count: {data.count}
          </p>
        </div>
      );
    }
    return null;
  };

  // Color function for bars
  const getBarColor = (bin: any) => {
    if (criticalLine === undefined) return '#d97706';
    const binCenter = (bin.binStart + bin.binEnd) / 2;
    if (binCenter < criticalLine * 0.9) return '#3b82f6';
    if (binCenter > criticalLine * 1.1) return '#dc2626';
    return '#10b981';
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={histogramData}
        margin={{ top: 5, right: 30, left: 20, bottom: 40 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#fef3c7" />
        <XAxis 
          dataKey="label"
          tick={{ fontSize: 11, fill: '#92400e' }}
          label={{ 
            value: xlabel, 
            position: 'insideBottom', 
            offset: -10, 
            style: { fontSize: 12, fill: '#92400e' } 
          }}
        />
        <YAxis 
          tick={{ fontSize: 11, fill: '#92400e' }}
          label={{ 
            value: ylabel, 
            angle: -90, 
            position: 'insideLeft', 
            style: { fontSize: 12, fill: '#92400e' } 
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        
        {criticalLine !== undefined && (
          <ReferenceLine 
            x={criticalLine.toFixed(2)} 
            stroke="#10b981" 
            strokeDasharray="5 5"
            label={{ 
              value: "Critical", 
              position: "top", 
              fill: '#10b981', 
              fontSize: 11 
            }}
          />
        )}
        
        <Bar 
          dataKey="count" 
          fill="#d97706"
          shape={(props: any) => {
            const { x, y, width, height, payload } = props;
            const color = getBarColor(payload);
            return (
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={color}
                stroke="#92400e"
                strokeWidth={0.5}
              />
            );
          }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}