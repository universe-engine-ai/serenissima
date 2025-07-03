'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer
} from 'recharts';

interface TimeSeriesChartProps {
  data: any[];
  yField: string;
  xlabel: string;
  ylabel: string;
  criticalLine?: number;
}

export default function TimeSeriesChart({ data, yField, xlabel, ylabel, criticalLine }: TimeSeriesChartProps) {
  // Format timestamp for display
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
  };

  // Prepare data for chart
  const chartData = data.map(d => ({
    ...d,
    time: d.time || (d.timestamp ? formatTime(d.timestamp) : ''),
    value: d[yField] || d.value
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const value = payload[0].value;
      const color = criticalLine !== undefined
        ? value < criticalLine * 0.9 ? '#3b82f6' // blue
        : value > criticalLine * 1.1 ? '#dc2626' // red
        : '#10b981' // green
        : '#d97706'; // amber

      return (
        <div className="bg-white p-2 border border-amber-300 rounded shadow-md">
          <p className="text-xs text-amber-800">{label}</p>
          <p className="text-sm font-medium" style={{ color }}>
            {ylabel}: {value?.toFixed(3) || 'N/A'}
          </p>
        </div>
      );
    }
    return null;
  };

  // Color function for line
  const getLineColor = (value: number | null) => {
    if (value === null || criticalLine === undefined) return '#d97706';
    if (value < criticalLine * 0.9) return '#3b82f6';
    if (value > criticalLine * 1.1) return '#dc2626';
    return '#10b981';
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={chartData}
        margin={{ top: 5, right: 30, left: 20, bottom: 25 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#fef3c7" />
        <XAxis 
          dataKey="time" 
          tick={{ fontSize: 11, fill: '#92400e' }}
          label={{ value: xlabel, position: 'insideBottom', offset: -15, style: { fontSize: 12, fill: '#92400e' } }}
        />
        <YAxis 
          tick={{ fontSize: 11, fill: '#92400e' }}
          label={{ value: ylabel, angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#92400e' } }}
          domain={criticalLine ? [0, 'auto'] : ['auto', 'auto']}
        />
        <Tooltip content={<CustomTooltip />} />
        
        {criticalLine !== undefined && (
          <>
            <ReferenceLine 
              y={criticalLine} 
              stroke="#10b981" 
              strokeDasharray="5 5" 
              label={{ value: "Critical (σ = 1)", position: "right", fill: '#10b981', fontSize: 11 }}
            />
            <ReferenceLine 
              y={criticalLine * 0.9} 
              stroke="#3b82f6" 
              strokeDasharray="3 3"
              strokeOpacity={0.5}
            />
            <ReferenceLine 
              y={criticalLine * 1.1} 
              stroke="#dc2626" 
              strokeDasharray="3 3"
              strokeOpacity={0.5}
            />
          </>
        )}
        
        <Line 
          type="monotone" 
          dataKey="value" 
          stroke="#d97706"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#92400e' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}