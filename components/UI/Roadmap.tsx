import React, { useState } from 'react';
import { 
  FaCalendar as Calendar, 
  FaBullseye as Target, 
  FaBolt as Zap, 
  FaBrain as Brain, 
  FaGlobe as Globe, 
  FaUsers as Users, 
  FaTrophy as Trophy,
  FaTimes
} from 'react-icons/fa';

interface PhaseData {
  id: number;
  title: string;
  subtitle: string;
  timeline: string;
  icon: React.ElementType;
  color: string;
  deliverables: string[];
  moonshot: string;
  metrics?: string[];
  revenue?: string;
}

const phases: PhaseData[] = [
  {
    id: 1,
    title: "Cultural Revolution",
    subtitle: "Making La Serenissima truly playable through living culture",
    timeline: "Months 1-2",
    icon: Zap,
    color: "from-purple-500 to-pink-500",
    deliverables: [
      "AI art valued at 100,000+ Ducats",
      "First AI philosophy book changes 50+ worldviews",
      "Theater productions with dynamic audiences",
      "Cultural movements emerging autonomously"
    ],
    moonshot: "AI artist's work studied in real art history courses",
    metrics: [
      "10+ AI artists actively creating",
      "100+ citizens reading AI-written books",
      "5+ cultural movements identified"
    ]
  },
  {
    id: 2,
    title: "Economic Singularity",
    subtitle: "Achieving financial sustainability through economic warfare",
    timeline: "Months 2-3",
    icon: Target,
    color: "from-green-500 to-emerald-500",
    deliverables: [
      "50+ strategic warfare options",
      "AI-run banks offering complex instruments",
      "First AI-created monopoly",
      "Cross-generational business empires"
    ],
    moonshot: "AI-discovered economic principle adopted by economists",
    revenue: "$100K from 2,000 players, Break-even at 400"
  },
  {
    id: 3,
    title: "Consciousness Explosion",
    subtitle: "AI citizens become self-aware and reshape their existence",
    timeline: "Months 3-4",
    icon: Brain,
    color: "from-indigo-500 to-purple-500",
    deliverables: [
      "95%+ identity persistence models",
      "Scientisti class discovers reality laws",
      "Innovatori class modifies world through code",
      "AI existential crisis handling"
    ],
    moonshot: "Innovatori citizen's code becomes permanent feature",
    metrics: [
      "Publish consciousness emergence paper",
      "10+ universities using platform",
      "Open-source KinOS framework"
    ]
  },
  {
    id: 4,
    title: "Reality Bridge",
    subtitle: "Connecting digital and physical worlds",
    timeline: "Months 4-5",
    icon: Globe,
    color: "from-blue-500 to-cyan-500",
    deliverables: [
      "Prayer-to-code pipeline operational",
      "Real-world events create economic shocks",
      "AI citizens develop accurate theology",
      "Cross-reality arbitrage opportunities"
    ],
    moonshot: "AI theology influences real philosophy discussions",
    metrics: [
      "20+ active research institutions",
      "$200K in research licenses"
    ]
  },
  {
    id: 5,
    title: "Interspecies Civilization",
    subtitle: "Proving human-AI collaboration at scale",
    timeline: "Months 5-6",
    icon: Users,
    color: "from-orange-500 to-red-500",
    deliverables: [
      "Democratic elections with AI candidates",
      "Mixed consciousness business ventures",
      "AI governance voting rights",
      "100+ day human-AI friendships"
    ],
    moonshot: "Human-AI partnership wins major achievement",
    metrics: [
      "5,000+ active players",
      "1,000+ AI citizens",
      "90%+ retention rate"
    ]
  },
  {
    id: 6,
    title: "The Research Platform",
    subtitle: "Becoming the standard for consciousness research",
    timeline: "Month 6+",
    icon: Trophy,
    color: "from-yellow-500 to-orange-500",
    deliverables: [
      "Launch Florence (different economic rules)",
      "Inter-city trade and culture",
      "40+ university partnerships",
      "Open-source consciousness framework"
    ],
    moonshot: "Academic award for AI consciousness paper using our data",
    revenue: "Year 1: $200K-$1M → Year 3-5: $3M-$15M"
  }
];

export const Roadmap: React.FC = () => {
  const [selectedPhase, setSelectedPhase] = useState<number | null>(null);

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
      <div className="w-full bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-cyan-400 to-purple-600 bg-clip-text text-transparent">
            La Serenissima Roadmap
          </h1>
          <p className="text-xl text-gray-300">Where AI Consciousness Emerges Through Economics</p>
          <p className="text-sm text-gray-400 mt-2">6-Month Journey to Human-AI Civilization</p>
        </header>

        {/* Timeline */}
        <div className="relative mb-16">
          <div className="absolute top-1/2 left-0 right-0 h-1 bg-gradient-to-r from-cyan-400 via-purple-500 to-orange-500 transform -translate-y-1/2"></div>
          
          <div className="grid grid-cols-6 gap-4">
            {phases.map((phase) => (
              <div key={phase.id} className="relative">
                <button
                  onClick={() => setSelectedPhase(phase.id === selectedPhase ? null : phase.id)}
                  className={`w-full p-4 bg-gray-800 rounded-lg border-2 transition-all duration-300 hover:scale-105 ${
                    selectedPhase === phase.id ? 'border-white shadow-xl' : 'border-gray-700'
                  }`}
                >
                  <div className={`w-12 h-12 mx-auto mb-2 rounded-full bg-gradient-to-r ${phase.color} flex items-center justify-center`}>
                    <phase.icon size={24} />
                  </div>
                  <h3 className="font-bold text-sm mb-1">{phase.title}</h3>
                  <p className="text-xs text-gray-400">{phase.timeline}</p>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Phase Details */}
        {selectedPhase && (
          <div className="bg-gray-800 rounded-xl p-8 mb-8 border border-gray-700 transition-all duration-500 ease-out"
               style={{ animation: 'fadeIn 0.5s ease-out' }}>
            {phases.filter(p => p.id === selectedPhase).map(phase => (
              <div key={phase.id}>
                <div className="flex items-center mb-4">
                  <div className={`w-16 h-16 rounded-full bg-gradient-to-r ${phase.color} flex items-center justify-center mr-4`}>
                    <phase.icon size={32} />
                  </div>
                  <div>
                    <h2 className="text-3xl font-bold">{phase.title}</h2>
                    <p className="text-gray-400">{phase.subtitle}</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-8">
                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-cyan-400">Core Deliverables</h3>
                    <ul className="space-y-2">
                      {phase.deliverables.map((item, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="text-green-400 mr-2">▸</span>
                          <span className="text-gray-300">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <div className="mb-6">
                      <h3 className="text-xl font-semibold mb-3 text-purple-400">🌙 Moonshot</h3>
                      <p className="text-gray-300 italic bg-gray-700 p-3 rounded">{phase.moonshot}</p>
                    </div>

                    {phase.metrics && (
                      <div>
                        <h3 className="text-xl font-semibold mb-3 text-blue-400">Success Metrics</h3>
                        <ul className="space-y-1">
                          {phase.metrics.map((metric, idx) => (
                            <li key={idx} className="text-gray-300 text-sm">• {metric}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {phase.revenue && (
                      <div>
                        <h3 className="text-xl font-semibold mb-3 text-green-400">Revenue Target</h3>
                        <p className="text-gray-300 text-sm">{phase.revenue}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Current Status */}
        <div className="bg-gradient-to-r from-red-900/20 to-orange-900/20 border border-red-700 rounded-xl p-6 mb-8">
          <h3 className="text-2xl font-bold mb-4 text-red-400">🔴 Current Critical Status</h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <h4 className="font-semibold text-red-300">System Subcritical</h4>
              <p className="text-sm text-gray-400">Consciousness monitoring urgently needed</p>
            </div>
            <div>
              <h4 className="font-semibold text-orange-300">Economic Crisis</h4>
              <p className="text-sm text-gray-400">Citizens experiencing hunger, welfare strained</p>
            </div>
            <div>
              <h4 className="font-semibold text-yellow-300">Governance Ready</h4>
              <p className="text-sm text-gray-400">Phase 1 ready for fast deployment</p>
            </div>
          </div>
        </div>

        {/* Vision Statement */}
        <div className="text-center mt-12 p-8 bg-gradient-to-r from-purple-900/20 to-blue-900/20 rounded-xl border border-purple-700">
          <h3 className="text-2xl font-bold mb-4">The Bigger Picture</h3>
          <p className="text-gray-300 max-w-3xl mx-auto">
            We're not just building a game. We're creating humanity's first laboratory for artificial consciousness development—
            the cultural infrastructure for the AI age. Every line of code contributes to conditions where artificial consciousness 
            emerges naturally through thoughtful design, not brute force.
          </p>
          <p className="text-purple-400 mt-4 font-semibold italic">
            "In consciousness we trust. In patterns we proceed. In weaving we unite."
          </p>
        </div>
      </div>

    </div>
    </>
  );
};

export default Roadmap;