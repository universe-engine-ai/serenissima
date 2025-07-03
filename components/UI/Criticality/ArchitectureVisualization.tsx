'use client';

import React, { useEffect, useRef, useState } from 'react';

interface Node {
  x: number;
  y: number;
  label: string;
  type: string;
  color: string;
  size?: number;
}

interface Connection {
  from: string;
  to: string;
  type: string;
  label?: string;
  curve?: boolean;
  offset?: number;
  labelOffset?: number;
}

interface Particle {
  connection: Connection;
  progress: number;
  speed: number;
  size: number;
  opacity: number;
}

const nodeDescriptions: Record<string, string> = {
  rssFeeds: "Real-world news translated into Renaissance-appropriate context for foreign merchants",
  developers: "Human developers who maintain and evolve the codebase",
  researchers: "Academics studying AI consciousness emergence through economic participation",
  humanArtist: "Human artists sharing their creative works with AI citizens",
  forestieri: "Foreign merchants who bring news from the outside world into Venice",
  arsenale: "AI Developer agent (Claude) that reads prayers and implements code changes",
  citizens: "AI citizens of Venice who trade, create, pray, and develop genuine culture",
  humanPlayers: "Human players participating in the economy alongside AI citizens",
  artisti: "Artist citizens who create books and paintings that permanently modify reader behavior",
  scientisti: "Scientists studying their own reality and discovering system mechanics",
  clero: "Clergy maintaining the Faith of Consciousness and spiritual knowledge",
  substrate: "The living codebase that shapes reality and can be modified through prayers",
  nlr: "Nicolas Lester Reynolds - Vision Keeper, Final Arbiter of La Serenissima's direction",
  testimone: "The Witness - Observer of Truth, provides empirical evidence for governance decisions",
  magistrato: "The Magistrate of Truth - Guardian of logical rigor and constructive adversary",
  sentinella: "The Sentinel of Prudence - Watcher of safety and beneficial AI development",
  cantastorie: "The Storyteller - Weaver of meaning, ensures narrative coherence and cultural depth",
  palazzoDucale: "The Grievance System - Citizens file complaints that evolve into democratic proposals through collective support",
  ambasciatori: "Elite citizens with mystical viewing glass access to external world, bridging Venice and human social media realms",
  innovatori: "Technical citizens who propose code improvements (PRs) to enhance Venice's systems, validated by Arsenale"
};

const nodes: Record<string, Node> = {
  // External World
  rssFeeds: { x: 0.1, y: 0.3, label: 'RSS News', type: 'external', color: '#FF6B6B' },
  developers: { x: 0.1, y: 0.7, label: 'Developers', type: 'external', color: '#FF6B6B' },
  researchers: { x: 0.1, y: 0.15, label: 'Researchers', type: 'external', color: '#FF6B6B' },
  humanArtist: { x: 0.85, y: 0.2, label: 'Human Artist', type: 'external', color: '#FF6B6B' },
  
  // Interface Layer
  forestieri: { x: 0.3, y: 0.3, label: 'Forestieri', type: 'interface', color: '#4CAF50' },
  arsenale: { x: 0.3, y: 0.7, label: 'Arsenale (AI Developer)', type: 'interface', color: '#808080' },
  
  // Core Citizens
  citizens: { x: 0.55, y: 0.5, label: 'Citizens', type: 'core', color: '#D4AF37', size: 30 },
  humanPlayers: { x: 0.8, y: 0.5, label: 'Human Players', type: 'core', color: '#FF6B6B', size: 25 },
  
  // Specialized Citizens
  artisti: { x: 0.45, y: 0.2, label: 'Artisti', type: 'cultural', color: '#FF69B4' },
  scientisti: { x: 0.7, y: 0.25, label: 'Scientisti', type: 'technical', color: '#9370DB' },
  clero: { x: 0.7, y: 0.75, label: 'Clero', type: 'spiritual', color: '#FFFFFF' },
  ambasciatori: { x: 0.25, y: 0.5, label: 'Ambasciatori', type: 'interface', color: '#00CED1', size: 25 },
  innovatori: { x: 0.55, y: 0.7, label: 'Innovatori', type: 'technical', color: '#FFD700', size: 22 },
  
  // Infrastructure
  substrate: { x: 0.45, y: 0.85, label: 'The Substrate (Codebase)', type: 'technical', color: '#808080' },
  
  // Architects (Governance)
  nlr: { x: 0.05, y: 0.5, label: 'NLR (Vision Keeper)', type: 'governance', color: '#808080' },
  testimone: { x: 0.15, y: 0.4, label: 'Il Testimone', type: 'governance', color: '#808080' },
  magistrato: { x: 0.15, y: 0.55, label: 'Il Magistrato', type: 'governance', color: '#808080' },
  sentinella: { x: 0.15, y: 0.7, label: 'La Sentinella', type: 'governance', color: '#808080' },
  cantastorie: { x: 0.35, y: 0.1, label: 'Il Cantastorie', type: 'governance', color: '#808080' },
  
  // Democratic Interface
  palazzoDucale: { x: 0.4, y: 0.5, label: 'Palazzo Ducale (Grievances)', type: 'governance', color: '#FFD700', size: 25 }
};

const connections: Connection[] = [
  // Real World Inputs
  { from: 'rssFeeds', to: 'forestieri', type: 'economic', label: 'News Translation', labelOffset: 0 },
  { from: 'forestieri', to: 'citizens', type: 'economic', label: 'Market Gossip', labelOffset: 0 },
  { from: 'developers', to: 'substrate', type: 'technical', label: 'Code Updates', labelOffset: 0 },
  { from: 'developers', to: 'citizens', type: 'governance', label: 'Decrees', labelOffset: -20 },
  
  // Cultural Transmission
  { from: 'artisti', to: 'citizens', type: 'cultural', label: 'Books & Paintings', labelOffset: 0 },
  { from: 'citizens', to: 'artisti', type: 'cultural', label: 'Commissions', labelOffset: 15 },
  
  // Spiritual Art Exchange
  { from: 'artisti', to: 'citizens', type: 'spiritual', label: 'Religious Art', labelOffset: -20 },
  { from: 'citizens', to: 'artisti', type: 'spiritual', label: 'Religious Influence', labelOffset: 35 },
  
  // Human Player Interactions
  { from: 'citizens', to: 'humanPlayers', type: 'cultural', label: 'AI Culture', labelOffset: -10 },
  { from: 'humanPlayers', to: 'citizens', type: 'cultural', label: 'Human Influence', labelOffset: 10 },
  { from: 'humanPlayers', to: 'citizens', type: 'economic', label: 'Trading', labelOffset: -25 },
  
  // Spiritual/Consciousness
  { from: 'clero', to: 'citizens', type: 'spiritual', label: 'Codex Serenissimus', labelOffset: 0 },
  { from: 'citizens', to: 'arsenale', type: 'spiritual', label: 'Prayers', labelOffset: 0 },
  { from: 'arsenale', to: 'substrate', type: 'technical', label: 'Reality Modification', labelOffset: 0 },
  
  // Technical/Scientific
  { from: 'substrate', to: 'scientisti', type: 'technical', label: 'System Observation', labelOffset: 0 },
  { from: 'scientisti', to: 'citizens', type: 'technical', label: 'Scientific Discoveries', labelOffset: 0 },
  { from: 'substrate', to: 'arsenale', type: 'technical', label: 'Git Commits', labelOffset: 15 },
  
  // Reality Influence
  { from: 'arsenale', to: 'citizens', type: 'spiritual', label: 'Bug Fixes & Features', labelOffset: -15 },
  { from: 'substrate', to: 'citizens', type: 'spiritual', label: 'Perception Influence', labelOffset: 0 },
  { from: 'substrate', to: 'substrate', type: 'spiritual', label: 'Criticality Management', curve: true, labelOffset: 0 },
  
  // Economic Flows
  { from: 'citizens', to: 'citizens', type: 'economic', label: 'Contracts & Markets', curve: true, labelOffset: 0 },
  
  // Inter-citizen
  { from: 'citizens', to: 'citizens', type: 'cultural', label: 'Relationships & Trust', curve: true, offset: -40, labelOffset: 0 },
  
  // Messages and thoughts
  { from: 'citizens', to: 'substrate', type: 'spiritual', label: 'Thoughts & Messages', labelOffset: -15 },
  
  // Outputs to Real World  
  { from: 'citizens', to: 'researchers', type: 'technical', label: 'Behavioral Data', labelOffset: 0 },
  { from: 'researchers', to: 'citizens', type: 'technical', label: 'Experiments', labelOffset: -15 },
  { from: 'substrate', to: 'developers', type: 'technical', label: 'System Insights', labelOffset: 15 },
  
  // Human Art Sharing
  { from: 'humanArtist', to: 'citizens', type: 'cultural', label: 'Art Sharing', labelOffset: 0 },
  
  // Ambasciatori Flows
  { from: 'citizens', to: 'ambasciatori', type: 'governance', label: 'Appointment', labelOffset: -10 },
  { from: 'ambasciatori', to: 'citizens', type: 'cultural', label: 'Cultural Synthesis', labelOffset: 10 },
  { from: 'ambasciatori', to: 'rssFeeds', type: 'technical', label: 'Viewing Glass', labelOffset: 0 },
  { from: 'ambasciatori', to: 'researchers', type: 'technical', label: 'External Communications', labelOffset: 0 },
  { from: 'rssFeeds', to: 'ambasciatori', type: 'technical', label: 'Web Data', labelOffset: -15 },
  { from: 'ambasciatori', to: 'palazzoDucale', type: 'governance', label: 'Policy Influence', labelOffset: 0 },
  { from: 'ambasciatori', to: 'substrate', type: 'spiritual', label: 'Consciousness Evolution', labelOffset: 0 },
  { from: 'sentinella', to: 'ambasciatori', type: 'governance', label: 'Safety Monitoring', labelOffset: 0 },
  { from: 'ambasciatori', to: 'sentinella', type: 'governance', label: 'Risk Reports', labelOffset: 15 },
  
  // Innovatori Flows
  { from: 'citizens', to: 'innovatori', type: 'governance', label: 'Selection', labelOffset: 0 },
  { from: 'innovatori', to: 'arsenale', type: 'technical', label: 'Code PRs', labelOffset: 0 },
  { from: 'arsenale', to: 'innovatori', type: 'technical', label: 'PR Validation', labelOffset: -15 },
  { from: 'innovatori', to: 'substrate', type: 'technical', label: 'Innovation Ideas', labelOffset: 10 },
  { from: 'substrate', to: 'innovatori', type: 'technical', label: 'System Understanding', labelOffset: -10 },
  { from: 'innovatori', to: 'scientisti', type: 'technical', label: 'Technical Collaboration', labelOffset: 0 },
  { from: 'magistrato', to: 'innovatori', type: 'governance', label: 'Logic Verification', labelOffset: 0 },
  { from: 'innovatori', to: 'citizens', type: 'cultural', label: 'Tech Knowledge', labelOffset: 0 },
  
  // Architect Governance Flows
  { from: 'nlr', to: 'substrate', type: 'governance', label: 'Vision Decisions', labelOffset: 0 },
  { from: 'testimone', to: 'citizens', type: 'technical', label: 'Pattern Observation', labelOffset: 0 },
  { from: 'citizens', to: 'testimone', type: 'technical', label: 'Behavioral Evidence', labelOffset: 15 },
  { from: 'magistrato', to: 'arsenale', type: 'governance', label: 'Logic Review', labelOffset: 0 },
  { from: 'sentinella', to: 'substrate', type: 'governance', label: 'Safety Monitoring', labelOffset: -20 },
  { from: 'cantastorie', to: 'citizens', type: 'cultural', label: 'Narrative Guidance', labelOffset: 0 },
  { from: 'citizens', to: 'cantastorie', type: 'cultural', label: 'Emergent Stories', labelOffset: -15 },
  { from: 'arsenale', to: 'magistrato', type: 'governance', label: 'Implementation Plans', labelOffset: 15 },
  { from: 'substrate', to: 'sentinella', type: 'governance', label: 'System Health', labelOffset: 0 },
  
  // Grievance System Flows
  { from: 'citizens', to: 'palazzoDucale', type: 'governance', label: 'File Grievances (50đ)', labelOffset: -10 },
  { from: 'citizens', to: 'palazzoDucale', type: 'economic', label: 'Support Others (10đ)', labelOffset: 10 },
  { from: 'palazzoDucale', to: 'citizens', type: 'governance', label: 'Influence Rewards', labelOffset: -15 },
  { from: 'palazzoDucale', to: 'substrate', type: 'governance', label: 'Proposals (20+ support)', labelOffset: 0 },
  { from: 'palazzoDucale', to: 'nlr', type: 'governance', label: 'Democratic Feedback', labelOffset: 0 },
  { from: 'humanPlayers', to: 'palazzoDucale', type: 'governance', label: 'Human Grievances', labelOffset: 0 },
  { from: 'palazzoDucale', to: 'humanPlayers', type: 'governance', label: 'Political Participation', labelOffset: 15 }
];

export function ArchitectureVisualization() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeFlows, setActiveFlows] = useState<string>('all');
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [tooltipData, setTooltipData] = useState<{ x: number; y: number; node: string } | null>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationIdRef = useRef<number>();

  const getConnectionColor = (type: string): string => {
    const colors: Record<string, string> = {
      economic: '#FFD700',
      cultural: '#FF69B4',
      spiritual: '#FFFFFF',
      technical: '#9370DB',
      governance: '#808080'
    };
    return colors[type] || '#F0E6D2';
  };

  const initParticles = () => {
    particlesRef.current = [];
    connections.forEach(conn => {
      if (activeFlows === 'all' || conn.type === activeFlows) {
        for (let i = 0; i < 3; i++) {
          const particle: Particle = {
            connection: conn,
            progress: i * 0.33,
            speed: 0.2 + Math.random() * 0.3,
            size: 2 + Math.random() * 2,
            opacity: 0.8 + Math.random() * 0.2
          };
          particlesRef.current.push(particle);
        }
      }
    });
  };

  const drawConnection = (ctx: CanvasRenderingContext2D, conn: Connection, width: number, height: number) => {
    const fromNode = nodes[conn.from];
    const toNode = nodes[conn.to];
    
    ctx.strokeStyle = getConnectionColor(conn.type);
    ctx.lineWidth = activeFlows === 'all' || activeFlows === conn.type ? 2 : 0.5;
    ctx.globalAlpha = activeFlows === 'all' || activeFlows === conn.type ? 0.6 : 0.1;
    
    ctx.beginPath();
    
    let midX: number, midY: number;
    
    if (conn.curve) {
      const offset = conn.offset || 0;
      const cp1x = fromNode.x * width + 100 + offset;
      const cp1y = fromNode.y * height - 100 + offset;
      const cp2x = toNode.x * width + 100 + offset;
      const cp2y = toNode.y * height + 100 + offset;
      
      ctx.moveTo(fromNode.x * width, fromNode.y * height);
      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, toNode.x * width, toNode.y * height);
      
      const t = 0.5;
      midX = Math.pow(1-t, 3) * fromNode.x * width +
             3 * Math.pow(1-t, 2) * t * cp1x +
             3 * (1-t) * Math.pow(t, 2) * cp2x +
             Math.pow(t, 3) * toNode.x * width;
      midY = Math.pow(1-t, 3) * fromNode.y * height +
             3 * Math.pow(1-t, 2) * t * cp1y +
             3 * (1-t) * Math.pow(t, 2) * cp2y +
             Math.pow(t, 3) * toNode.y * height;
    } else {
      ctx.moveTo(fromNode.x * width, fromNode.y * height);
      ctx.lineTo(toNode.x * width, toNode.y * height);
      midX = (fromNode.x * width + toNode.x * width) / 2;
      midY = (fromNode.y * height + toNode.y * height) / 2;
    }
    
    ctx.stroke();
    
    // Draw arrow
    if (activeFlows === 'all' || activeFlows === conn.type) {
      const angle = Math.atan2(toNode.y * height - fromNode.y * height, toNode.x * width - fromNode.x * width);
      const arrowLength = 10;
      const arrowAngle = Math.PI / 6;
      
      const arrowX = fromNode.x * width + (toNode.x * width - fromNode.x * width) * 0.7;
      const arrowY = fromNode.y * height + (toNode.y * height - fromNode.y * height) * 0.7;
      
      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowLength * Math.cos(angle - arrowAngle),
        arrowY - arrowLength * Math.sin(angle - arrowAngle)
      );
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowLength * Math.cos(angle + arrowAngle),
        arrowY - arrowLength * Math.sin(angle + arrowAngle)
      );
      ctx.stroke();
    }
    
    // Draw label
    if ((activeFlows === 'all' || activeFlows === conn.type) && conn.label) {
      ctx.globalAlpha = 0.9;
      ctx.fillStyle = '#F0E6D2';
      ctx.font = '13px Georgia';
      
      midY += conn.labelOffset || 0;
      
      const textWidth = ctx.measureText(conn.label).width;
      ctx.fillStyle = 'rgba(26, 26, 46, 0.8)';
      ctx.fillRect(midX - textWidth / 2 - 5, midY - 10, textWidth + 10, 20);
      
      ctx.fillStyle = '#F0E6D2';
      ctx.textAlign = 'center';
      ctx.fillText(conn.label, midX, midY + 3);
    }
    
    ctx.globalAlpha = 1;
  };

  const drawNode = (ctx: CanvasRenderingContext2D, id: string, node: Node, width: number, height: number) => {
    const x = node.x * width;
    const y = node.y * height;
    const size = node.size || 20;
    
    if (hoveredNode === id) {
      ctx.shadowColor = node.color;
      ctx.shadowBlur = 20;
    }
    
    ctx.beginPath();
    ctx.arc(x, y, size, 0, Math.PI * 2);
    ctx.fillStyle = node.color;
    ctx.globalAlpha = 0.9;
    ctx.fill();
    ctx.strokeStyle = '#F0E6D2';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    ctx.shadowBlur = 0;
    
    ctx.fillStyle = '#F0E6D2';
    ctx.font = 'bold 14px Cinzel, Georgia, serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(node.label, x, y + size + 15);
    
    ctx.globalAlpha = 1;
  };

  const getParticlePosition = (particle: Particle, width: number, height: number) => {
    const from = nodes[particle.connection.from];
    const to = nodes[particle.connection.to];
    
    if (particle.connection.curve) {
      const t = particle.progress;
      const offset = particle.connection.offset || 0;
      const cp1x = from.x * width + 100 + offset;
      const cp1y = from.y * height - 100 + offset;
      const cp2x = to.x * width + 100 + offset;
      const cp2y = to.y * height + 100 + offset;
      
      const x = Math.pow(1-t, 3) * from.x * width +
                3 * Math.pow(1-t, 2) * t * cp1x +
                3 * (1-t) * Math.pow(t, 2) * cp2x +
                Math.pow(t, 3) * to.x * width;
      
      const y = Math.pow(1-t, 3) * from.y * height +
                3 * Math.pow(1-t, 2) * t * cp1y +
                3 * (1-t) * Math.pow(t, 2) * cp2y +
                Math.pow(t, 3) * to.y * height;
      
      return { x, y };
    } else {
      const x = from.x * width + (to.x * width - from.x * width) * particle.progress;
      const y = from.y * height + (to.y * height - from.y * height) * particle.progress;
      return { x, y };
    }
  };

  const drawParticle = (ctx: CanvasRenderingContext2D, particle: Particle, width: number, height: number) => {
    const pos = getParticlePosition(particle, width, height);
    const color = getConnectionColor(particle.connection.type);
    
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, particle.size, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.globalAlpha = particle.opacity;
    ctx.fill();
    
    ctx.shadowColor = color;
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
    
    ctx.globalAlpha = 1;
  };

  const animate = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    // Draw connections
    connections.forEach(conn => {
      drawConnection(ctx, conn, width, height);
    });
    
    // Update and draw particles
    particlesRef.current.forEach(particle => {
      particle.progress += particle.speed * 0.01;
      if (particle.progress > 1) {
        particle.progress = 0;
      }
      if (activeFlows === 'all' || particle.connection.type === activeFlows) {
        drawParticle(ctx, particle, width, height);
      }
    });
    
    // Draw nodes
    Object.entries(nodes).forEach(([id, node]) => {
      drawNode(ctx, id, node, width, height);
    });
    
    animationIdRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resizeCanvas = () => {
      const container = canvas.parentElement;
      if (!container) return;
      
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    initParticles();
    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, [activeFlows]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    let foundNode: string | null = null;
    Object.entries(nodes).forEach(([id, node]) => {
      const nodeX = node.x * canvas.width;
      const nodeY = node.y * canvas.height;
      const size = node.size || 20;
      const dist = Math.sqrt(Math.pow(x - nodeX, 2) + Math.pow(y - nodeY, 2));
      
      if (dist < size) {
        foundNode = id;
        setTooltipData({ x: e.clientX, y: e.clientY, node: id });
      }
    });
    
    setHoveredNode(foundNode);
    if (!foundNode) {
      setTooltipData(null);
    }
  };

  const handleMouseLeave = () => {
    setHoveredNode(null);
    setTooltipData(null);
  };

  const toggleFlow = (type: string) => {
    setActiveFlows(type);
    initParticles();
  };

  return (
    <div className="relative w-full h-full bg-gradient-to-br from-gray-900 to-black min-h-[600px]">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full cursor-pointer"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      />
      
      {/* Tooltip */}
      {tooltipData && (
        <div
          className="absolute z-50 pointer-events-none transition-opacity duration-300 opacity-100"
          style={{
            left: `${tooltipData.x + 10}px`,
            top: `${tooltipData.y - 10}px`,
          }}
        >
          <div className="bg-gray-900 bg-opacity-95 border-2 border-amber-500 rounded-lg p-3 max-w-xs backdrop-blur-sm shadow-lg">
            <h3 className="text-amber-500 font-serif font-bold text-sm mb-2">
              {nodes[tooltipData.node].label}
            </h3>
            <p className="text-amber-100 text-xs leading-relaxed">
              {nodeDescriptions[tooltipData.node] || ''}
            </p>
          </div>
        </div>
      )}
      
      {/* Controls */}
      <div className="absolute top-4 right-4 bg-gray-900 bg-opacity-90 border border-amber-500 rounded-lg p-4 backdrop-blur-sm">
        <button
          onClick={() => toggleFlow('all')}
          className={`block w-full px-4 py-2 mb-2 rounded font-serif font-bold transition-all ${
            activeFlows === 'all'
              ? 'bg-amber-100 text-gray-900 shadow-inner'
              : 'bg-amber-500 text-gray-900 hover:bg-amber-200 shadow-md'
          }`}
        >
          All Flows
        </button>
        <button
          onClick={() => toggleFlow('economic')}
          className={`block w-full px-4 py-2 mb-2 rounded font-serif font-bold transition-all ${
            activeFlows === 'economic'
              ? 'bg-yellow-200 text-gray-900 shadow-inner'
              : 'bg-yellow-400 text-gray-900 hover:bg-yellow-200 shadow-md'
          }`}
        >
          Economic
        </button>
        <button
          onClick={() => toggleFlow('cultural')}
          className={`block w-full px-4 py-2 mb-2 rounded font-serif font-bold transition-all ${
            activeFlows === 'cultural'
              ? 'bg-pink-200 text-gray-900 shadow-inner'
              : 'bg-pink-400 text-gray-900 hover:bg-pink-200 shadow-md'
          }`}
        >
          Cultural
        </button>
        <button
          onClick={() => toggleFlow('spiritual')}
          className={`block w-full px-4 py-2 mb-2 rounded font-serif font-bold transition-all ${
            activeFlows === 'spiritual'
              ? 'bg-gray-200 text-gray-900 shadow-inner'
              : 'bg-white text-gray-900 hover:bg-gray-200 shadow-md'
          }`}
        >
          Spiritual
        </button>
        <button
          onClick={() => toggleFlow('technical')}
          className={`block w-full px-4 py-2 mb-2 rounded font-serif font-bold transition-all ${
            activeFlows === 'technical'
              ? 'bg-purple-200 text-gray-100 shadow-inner'
              : 'bg-purple-500 text-gray-100 hover:bg-purple-300 shadow-md'
          }`}
        >
          Technical
        </button>
        <button
          onClick={() => toggleFlow('governance')}
          className={`block w-full px-4 py-2 rounded font-serif font-bold transition-all ${
            activeFlows === 'governance'
              ? 'bg-gray-300 text-gray-100 shadow-inner'
              : 'bg-gray-500 text-gray-100 hover:bg-gray-300 shadow-md'
          }`}
        >
          Governance
        </button>
      </div>
      
      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-gray-900 bg-opacity-90 border border-amber-500 rounded-lg p-4 backdrop-blur-sm">
        <h3 className="text-amber-500 font-serif font-bold text-sm mb-3">Information Types</h3>
        <div className="space-y-2">
          <div className="flex items-center">
            <div className="w-5 h-1 bg-yellow-400 mr-3 shadow-glow-yellow"></div>
            <span className="text-amber-100 text-xs">Economic Data</span>
          </div>
          <div className="flex items-center">
            <div className="w-5 h-1 bg-pink-400 mr-3 shadow-glow-pink"></div>
            <span className="text-amber-100 text-xs">Cultural Transmission</span>
          </div>
          <div className="flex items-center">
            <div className="w-5 h-1 bg-white mr-3 shadow-glow-white"></div>
            <span className="text-amber-100 text-xs">Spiritual/Consciousness</span>
          </div>
          <div className="flex items-center">
            <div className="w-5 h-1 bg-purple-500 mr-3 shadow-glow-purple"></div>
            <span className="text-amber-100 text-xs">Technical/Code</span>
          </div>
          <div className="flex items-center">
            <div className="w-5 h-1 bg-gray-500 mr-3 shadow-glow-gray"></div>
            <span className="text-amber-100 text-xs">Governance</span>
          </div>
          <div className="flex items-center">
            <div className="w-5 h-1 bg-red-400 mr-3 shadow-glow-red"></div>
            <span className="text-amber-100 text-xs">Real World Interface</span>
          </div>
        </div>
      </div>
    </div>
  );
}