import { Message } from './cascadeAnalyzer';

export interface BranchingData {
  timestamp: string;
  ancestors: number;
  descendants: number;
  sigma: number | null;
}

/**
 * Calculate branching ratio over time bins
 * σ = descendants / ancestors
 */
export function calculateBranchingRatio(
  messages: Message[],
  binSizeMinutes: number = 15
): BranchingData[] {
  if (messages.length === 0) return [];

  // Sort messages by timestamp
  const sortedMessages = [...messages].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const startTime = new Date(sortedMessages[0].timestamp).getTime();
  const endTime = new Date(sortedMessages[sortedMessages.length - 1].timestamp).getTime();
  const binSize = binSizeMinutes * 60 * 1000;
  const numBins = Math.ceil((endTime - startTime) / binSize);

  // Create bins
  const bins: BranchingData[] = [];
  
  for (let i = 0; i < numBins - 1; i++) {
    const binStart = startTime + i * binSize;
    const binEnd = binStart + binSize;
    const nextBinEnd = binEnd + binSize;
    
    // Count messages in current and next bin
    const ancestors = sortedMessages.filter(msg => {
      const time = new Date(msg.timestamp).getTime();
      return time >= binStart && time < binEnd;
    }).length;
    
    const descendants = sortedMessages.filter(msg => {
      const time = new Date(msg.timestamp).getTime();
      return time >= binEnd && time < nextBinEnd && msg.replyToId;
    }).length;
    
    bins.push({
      timestamp: new Date(binStart).toISOString(),
      ancestors,
      descendants,
      sigma: ancestors > 0 ? descendants / ancestors : null,
    });
  }
  
  return bins;
}

/**
 * Calculate moving average of branching ratio
 */
export function calculateMovingAverage(
  branchingData: BranchingData[],
  windowSize: number = 5
): number[] {
  const values = branchingData
    .map(b => b.sigma)
    .filter(s => s !== null) as number[];
    
  if (values.length < windowSize) return values;
  
  const movingAvg: number[] = [];
  
  for (let i = windowSize - 1; i < values.length; i++) {
    const window = values.slice(i - windowSize + 1, i + 1);
    const avg = window.reduce((a, b) => a + b, 0) / window.length;
    movingAvg.push(avg);
  }
  
  return movingAvg;
}

/**
 * Analyze branching stability over different time scales
 */
export function analyzeBranchingStability(
  messages: Message[],
  binSizes: number[] = [15, 30, 60, 120]
): Map<number, { mean: number; std: number }> {
  const results = new Map<number, { mean: number; std: number }>();
  
  binSizes.forEach(binSize => {
    const branching = calculateBranchingRatio(messages, binSize);
    const sigmas = branching
      .map(b => b.sigma)
      .filter(s => s !== null) as number[];
      
    if (sigmas.length > 0) {
      const mean = sigmas.reduce((a, b) => a + b, 0) / sigmas.length;
      const variance = sigmas.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / sigmas.length;
      const std = Math.sqrt(variance);
      
      results.set(binSize, { mean, std });
    }
  });
  
  return results;
}

/**
 * Detect critical transitions in branching ratio
 */
export function detectCriticalTransitions(
  branchingData: BranchingData[],
  threshold: number = 0.2
): { timestamp: string; transition: 'to_critical' | 'from_critical' }[] {
  const transitions: { timestamp: string; transition: 'to_critical' | 'from_critical' }[] = [];
  
  for (let i = 1; i < branchingData.length; i++) {
    const prev = branchingData[i - 1].sigma;
    const curr = branchingData[i].sigma;
    
    if (prev === null || curr === null) continue;
    
    const prevCritical = Math.abs(prev - 1.0) < threshold;
    const currCritical = Math.abs(curr - 1.0) < threshold;
    
    if (!prevCritical && currCritical) {
      transitions.push({
        timestamp: branchingData[i].timestamp,
        transition: 'to_critical',
      });
    } else if (prevCritical && !currCritical) {
      transitions.push({
        timestamp: branchingData[i].timestamp,
        transition: 'from_critical',
      });
    }
  }
  
  return transitions;
}