import { NextResponse } from 'next/server';
import { getAirtableBase } from '@/lib/airtable';

interface CitizenData {
  id: string;
  username: string;
  firstName: string;
  lastName: string;
  socialClass: string;
  imageUrl?: string;
  coatOfArmsImageUrl?: string;
}

interface RelationshipData {
  id: string;
  citizen1: string;
  citizen2: string;
  trustScore: number;
  strengthScore: number;
  notes?: string;
}

interface RelevancyData {
  id: string;
  relevancyId: string;
  title: string;
  description: string;
  score: number;
  asset: string;
  assetType: string;
  category: string;
  type: string;
  targetCitizen: string;
  relevantToCitizen: string;
  timeHorizon: string;
  notes?: string;
  createdAt: string;
}

interface ProblemData {
  id: string;
  problemId: string;
  citizen: string;
  assetType: string;
  asset: string;
  severity: number;
  status: string;
  type: string;
  title: string;
  description: string;
}

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.citizen1 || !data.citizen2) {
      return NextResponse.json(
        { success: false, error: 'Both citizen usernames are required' },
        { status: 400 }
      );
    }
    
    const citizen1 = data.citizen1;
    const citizen2 = data.citizen2;
    
    // Get Airtable base
    const base = getAirtableBase();
    
    // Fetch citizen data
    const citizensTable = base('CITIZENS');
    const [citizen1Data, citizen2Data] = await Promise.all([
      fetchCitizenData(citizensTable, citizen1),
      fetchCitizenData(citizensTable, citizen2)
    ]);
    
    if (!citizen1Data || !citizen2Data) {
      return NextResponse.json(
        { success: false, error: 'One or both citizens not found' },
        { status: 404 }
      );
    }
    
    // Fetch relationship data
    const relationshipsTable = base('RELATIONSHIPS');
    const relationship = await fetchRelationshipData(relationshipsTable, citizen1, citizen2);
    
    // Default values if no relationship record exists
    let trustScore = 50; // Neutral trust
    let strengthScore = 0; // No relationship strength
    let relationshipNotes = '';
    
    if (relationship) {
      trustScore = relationship.trustScore;
      strengthScore = relationship.strengthScore;
      relationshipNotes = relationship.notes || '';
    }
    
    // Fetch relevancies
    const relevanciesTable = base('RELEVANCIES');
    const [relevancies1to2, relevancies2to1] = await Promise.all([
      fetchRelevancyData(relevanciesTable, citizen1, citizen2),
      fetchRelevancyData(relevanciesTable, citizen2, citizen1)
    ]);
    
    // Fetch problems involving both citizens
    const problemsTable = base('PROBLEMS');
    const problems = await fetchProblemsInvolvingBoth(problemsTable, citizen1, citizen2);
    
    // Analyze social class dynamics
    const socialClassDynamics = analyzeSocialClassDynamics(citizen1Data.socialClass, citizen2Data.socialClass);
    
    // Analyze relevancy patterns
    const relevancyAnalysis = analyzeRelevancies(relevancies1to2, relevancies2to1);
    
    // Analyze problems
    const problemAnalysis = analyzeProblems(problems, citizen1, citizen2);
    
    // Determine relationship title and description
    const { title, description } = determineRelationship(
      trustScore,
      strengthScore,
      socialClassDynamics,
      relevancyAnalysis,
      problemAnalysis,
      relationshipNotes,
      citizen1Data,
      citizen2Data
    );
    
    return NextResponse.json({
      success: true,
      relationship: {
        title,
        description,
        strength: strengthScore,
        trust: trustScore,
        socialClassDynamics,
        relevancyAnalysis,
        problemAnalysis
      }
    });
  } catch (error) {
    console.error('Error in relationship evaluation:', error);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

async function fetchCitizenData(table: any, username: string): Promise<CitizenData | null> {
  try {
    const records = await table.select({
      filterByFormula: `{Username} = '${username}'`,
      maxRecords: 1
    }).firstPage();
    
    if (records.length === 0) {
      return null;
    }
    
    const record = records[0];
    return {
      id: record.id,
      username: record.get('Username'),
      firstName: record.get('FirstName'),
      lastName: record.get('LastName'),
      socialClass: record.get('SocialClass'),
      imageUrl: record.get('ImageUrl'),
      coatOfArmsImageUrl: record.get('CoatOfArmsImageUrl')
    };
  } catch (error) {
    console.error(`Error fetching citizen data for ${username}:`, error);
    return null;
  }
}

async function fetchRelationshipData(
  table: any,
  citizen1: string,
  citizen2: string
): Promise<RelationshipData | null> {
  try {
    const records = await table.select({
      filterByFormula: `OR(
        AND({Citizen1} = '${citizen1}', {Citizen2} = '${citizen2}'),
        AND({Citizen1} = '${citizen2}', {Citizen2} = '${citizen1}')
      )`,
      maxRecords: 1
    }).firstPage();
    
    if (records.length === 0) {
      return null;
    }
    
    const record = records[0];
    return {
      id: record.id,
      citizen1: record.get('Citizen1'),
      citizen2: record.get('Citizen2'),
      trustScore: record.get('TrustScore') || 50,
      strengthScore: record.get('StrengthScore') || 0,
      notes: record.get('Notes')
    };
  } catch (error) {
    console.error(`Error fetching relationship data for ${citizen1} and ${citizen2}:`, error);
    return null;
  }
}

async function fetchRelevancyData(
  table: any,
  fromCitizen: string,
  toCitizen: string
): Promise<RelevancyData[]> {
  try {
    const relevancies: RelevancyData[] = [];
    
    await new Promise((resolve, reject) => {
      table.select({
        filterByFormula: `AND({relevantToCitizen} = '${fromCitizen}', {targetCitizen} = '${toCitizen}')`
      }).eachPage(
        function page(records: any[], fetchNextPage: () => void) {
          records.forEach(record => {
            relevancies.push({
              id: record.id,
              relevancyId: record.get('relevancyId'),
              title: record.get('title'),
              description: record.get('description'),
              score: record.get('score') || 0,
              asset: record.get('asset'),
              assetType: record.get('assetType'),
              category: record.get('category'),
              type: record.get('type'),
              targetCitizen: record.get('targetCitizen'),
              relevantToCitizen: record.get('relevantToCitizen'),
              timeHorizon: record.get('timeHorizon'),
              notes: record.get('notes'),
              createdAt: record.get('createdAt')
            });
          });
          fetchNextPage();
        },
        function done(err: Error | null) {
          if (err) {
            reject(err);
          } else {
            resolve(null);
          }
        }
      );
    });
    
    return relevancies;
  } catch (error) {
    console.error(`Error fetching relevancy data from ${fromCitizen} to ${toCitizen}:`, error);
    return [];
  }
}

async function fetchProblemsInvolvingBoth(
  table: any,
  citizen1: string,
  citizen2: string
): Promise<ProblemData[]> {
  try {
    const problems: ProblemData[] = [];
    
    await new Promise((resolve, reject) => {
      table.select({
        filterByFormula: `OR(
          AND({citizen} = '${citizen1}', FIND('${citizen2}', {description}) > 0),
          AND({citizen} = '${citizen2}', FIND('${citizen1}', {description}) > 0)
        )`
      }).eachPage(
        function page(records: any[], fetchNextPage: () => void) {
          records.forEach(record => {
            problems.push({
              id: record.id,
              problemId: record.get('problemId'),
              citizen: record.get('citizen'),
              assetType: record.get('assetType'),
              asset: record.get('asset'),
              severity: record.get('severity') || 0,
              status: record.get('status'),
              type: record.get('type'),
              title: record.get('title'),
              description: record.get('description')
            });
          });
          fetchNextPage();
        },
        function done(err: Error | null) {
          if (err) {
            reject(err);
          } else {
            resolve(null);
          }
        }
      );
    });
    
    return problems;
  } catch (error) {
    console.error(`Error fetching problems involving ${citizen1} and ${citizen2}:`, error);
    return [];
  }
}

function analyzeSocialClassDynamics(class1: string, class2: string): string {
  const classes = ['Nobili', 'Cittadini', 'Popolani'];
  const class1Index = classes.indexOf(class1);
  const class2Index = classes.indexOf(class2);
  
  if (class1Index === class2Index) {
    return `Equal social standing as ${class1}`;
  } else if (class1Index < class2Index) {
    return `Social superiority (${class1} to ${class2})`;
  } else {
    return `Social deference (${class1} to ${class2})`;
  }
}

function analyzeRelevancies(
  relevancies1to2: RelevancyData[],
  relevancies2to1: RelevancyData[]
): string {
  if (relevancies1to2.length === 0 && relevancies2to1.length === 0) {
    return 'No significant mutual relevancies';
  }
  
  const totalScore1to2 = relevancies1to2.reduce((sum, rel) => sum + rel.score, 0);
  const totalScore2to1 = relevancies2to1.reduce((sum, rel) => sum + rel.score, 0);
  
  if (totalScore1to2 > totalScore2to1 * 2) {
    return 'Highly asymmetric relevance (first citizen finds second much more relevant)';
  } else if (totalScore2to1 > totalScore1to2 * 2) {
    return 'Highly asymmetric relevance (second citizen finds first much more relevant)';
  } else if (totalScore1to2 > totalScore2to1 * 1.5) {
    return 'Moderately asymmetric relevance (first citizen finds second more relevant)';
  } else if (totalScore2to1 > totalScore1to2 * 1.5) {
    return 'Moderately asymmetric relevance (second citizen finds first more relevant)';
  } else {
    return 'Relatively balanced mutual relevance';
  }
}

function analyzeProblems(
  problems: ProblemData[],
  citizen1: string,
  citizen2: string
): string {
  if (problems.length === 0) {
    return 'No shared problems';
  }
  
  const problemsByCitizen1 = problems.filter(p => p.citizen === citizen1);
  const problemsByCitizen2 = problems.filter(p => p.citizen === citizen2);
  
  if (problemsByCitizen1.length > 0 && problemsByCitizen2.length > 0) {
    return 'Mutual problems affecting both citizens';
  } else if (problemsByCitizen1.length > 0) {
    return `Problems primarily affecting ${citizen1} that involve ${citizen2}`;
  } else {
    return `Problems primarily affecting ${citizen2} that involve ${citizen1}`;
  }
}

function determineRelationship(
  trustScore: number,
  strengthScore: number,
  socialClassDynamics: string,
  relevancyAnalysis: string,
  problemAnalysis: string,
  relationshipNotes: string,
  citizen1Data: CitizenData,
  citizen2Data: CitizenData
): { title: string; description: string } {
  // Normalize scores to 0-100 scale if they're not already
  const normalizedStrength = Math.min(100, Math.max(0, strengthScore));
  const normalizedTrust = Math.min(100, Math.max(0, trustScore));
  
  // Special case for ConsiglioDeiDieci and GondolaDrifter
  if (
    (citizen1Data.username === "ConsiglioDeiDieci" && citizen2Data.username === "GondolaDrifter") ||
    (citizen2Data.username === "ConsiglioDeiDieci" && citizen1Data.username === "GondolaDrifter")
  ) {
    if (normalizedStrength < 1 && normalizedTrust < 40) {
      return {
        title: "Distant Observer",
        description: "They maintain a respectful distance from the Consiglio's affairs, as is appropriate for their station, while fulfilling their obligations to the Republic. Our interactions are infrequent but formal, characterized by the proper deference expected when a popolani addresses the Consiglio dei Dieci."
      };
    }
  }
  
  // Very low strength relationship (0-1)
  if (normalizedStrength < 1) {
    if (normalizedTrust < 40) {
      return {
        title: "Distant Observer",
        description: "They remain at the periphery of our awareness, with minimal interaction and limited significance to our operations. Our relationship is characterized by formal distance and a lack of meaningful engagement, as befits their current standing relative to our interests."
      };
    } else if (normalizedTrust < 60) {
      return {
        title: "Casual Acquaintance",
        description: "They have had limited interaction with us thus far, but what little contact exists has been conducted appropriately. Our relationship is nascent and undefined, with potential for development should circumstances align with the interests of La Serenissima."
      };
    } else {
      return {
        title: "Potential Ally",
        description: "Though our interaction has been minimal, there exists a foundation of goodwill that could be cultivated into a more substantial connection. We view their activities favorably from a distance, recognizing potential alignment in our interests that may warrant closer association in the future."
      };
    }
  }
  
  // Low strength relationship (1-25)
  else if (normalizedStrength < 25) {
    if (normalizedTrust < 30) {
      return {
        title: "Wary Association",
        description: "We maintain necessary but guarded interactions, approaching each engagement with appropriate caution. Their actions are observed with vigilance, as our limited history has not yet established sufficient grounds for confidence in their reliability or intentions."
      };
    } else if (normalizedTrust < 50) {
      return {
        title: "Formal Connection",
        description: "We maintain a proper and structured relationship defined primarily by our respective positions within Venetian society. Our interactions follow established protocols and expectations, with neither particular warmth nor notable tension characterizing our limited engagements."
      };
    } else if (normalizedTrust < 70) {
      return {
        title: "Cordial Relations",
        description: "We engage with them on generally positive terms, finding our limited interactions to be conducted with mutual respect and appropriate courtesy. While our connection remains relatively superficial, it is marked by a pleasant professional rapport that serves our respective interests adequately."
      };
    } else {
      return {
        title: "Favorable Contact",
        description: "We regard them with positive disposition despite our limited direct engagement. Their conduct in our interactions has consistently demonstrated reliability and proper respect, establishing a foundation of goodwill that could support expanded cooperation should circumstances warrant."
      };
    }
  }
  
  // Moderate strength relationship (25-50)
  else if (normalizedStrength < 50) {
    if (normalizedTrust < 30) {
      return {
        title: "Guarded Interaction",
        description: "We maintain significant but cautious engagement, recognizing the necessity of our connection while remaining alert to potential complications. Their actions are monitored with appropriate scrutiny, as our substantial interactions require vigilance to protect our interests within this complex relationship."
      };
    } else if (normalizedTrust < 50) {
      return {
        title: "Professional Association",
        description: "We maintain a substantive working relationship characterized by proper conduct and mutual respect for our respective positions. Our interactions are productive and follow expected conventions, with a focus on the practical matters that connect our interests in Venetian society."
      };
    } else if (normalizedTrust < 70) {
      return {
        title: "Reliable Collaborator",
        description: "We engage in consistent and productive cooperation, finding their conduct to be generally dependable and aligned with expectations. Our relationship has developed a foundation of reliability through repeated positive interactions, allowing for effective coordination on matters of shared concern."
      };
    } else {
      return {
        title: "Valued Partner",
        description: "We hold them in positive regard based on a history of constructive engagement and demonstrated reliability. Their consistent adherence to agreements and appropriate respect for our position has established a relationship of meaningful trust that serves our mutual interests effectively."
      };
    }
  }
  
  // High strength relationship (50-100)
  else {
    if (normalizedTrust < 30) {
      return {
        title: "Necessary Adversary",
        description: "We maintain extensive engagement despite significant reservations about their reliability or intentions. Our deeply intertwined interests necessitate ongoing interaction, which we approach with strategic caution and careful management to protect our position while navigating this complex relationship."
      };
    } else if (normalizedTrust < 50) {
      return {
        title: "Strategic Alliance",
        description: "We maintain a substantial relationship based primarily on pragmatic alignment of interests rather than personal affinity. Our extensive interactions are governed by careful calculation of mutual benefit, with each party maintaining appropriate vigilance while recognizing the value of continued cooperation."
      };
    } else if (normalizedTrust < 70) {
      return {
        title: "Trusted Associate",
        description: "We engage in extensive cooperation characterized by established reliability and mutual respect. Their consistent demonstration of competence and appropriate conduct has built a relationship of significant trust, allowing for effective collaboration across the many domains where our interests intersect."
      };
    } else {
      return {
        title: "Essential Ally",
        description: "We maintain a relationship of exceptional importance marked by high confidence in their reliability and intentions. Their consistent demonstration of trustworthiness across our extensive interactions has established them as a valued ally whose cooperation is integral to our operations and objectives."
      };
    }
  }
}
