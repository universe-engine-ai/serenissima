import { NextResponse } from 'next/server';

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
    
    // For now, we'll return mock data based on the citizen usernames
    // In a real implementation, this would query a database or call a backend service
    
    // Generate a deterministic but seemingly random value based on the two usernames
    const generateValue = (str1: string, str2: string, max: number) => {
      const combined = str1 + str2;
      let hash = 0;
      for (let i = 0; i < combined.length; i++) {
        hash = ((hash << 5) - hash) + combined.charCodeAt(i);
        hash |= 0; // Convert to 32bit integer
      }
      return Math.abs(hash % max);
    };
    
    const strength = generateValue(data.citizen1, data.citizen2, 1000);
    const trust = generateValue(data.citizen2, data.citizen1, 100);
    
    // Determine relationship title and description based on strength and trust
    let title, description;
    
    // Very strong relationship (500+)
    if (strength >= 500) {
      if (trust >= 75) {
        title = "Steadfast Allies";
        description = `A relationship of exceptional strength (${strength}) and high trust (${trust}), characterized by consistent mutual support and aligned interests. Their interactions show a pattern of reliable cooperation and shared objectives across multiple domains of Venetian society.`;
      } else if (trust >= 50) {
        title = "Strategic Partners";
        description = `A powerful alliance (${strength}) with moderate trust (${trust}), built on mutual benefit rather than personal affinity. They collaborate effectively on matters of shared interest while maintaining some strategic distance in other areas.`;
      } else {
        title = "Complicated Powerbrokers";
        description = `Despite their significant connection (${strength}), low trust (${trust}) creates a complex dynamic of interdependence mixed with caution. Their relationship is characterized by necessary cooperation tempered by strategic wariness.`;
      }
    }
    // Strong relationship (300-499)
    else if (strength >= 300) {
      if (trust >= 75) {
        title = "Trusted Collaborators";
        description = `A strong relationship (${strength}) with high trust (${trust}), marked by reliable cooperation and mutual respect. They work together effectively and maintain open communication across their shared interests.`;
      } else if (trust >= 50) {
        title = "Pragmatic Allies";
        description = `A solid connection (${strength}) with moderate trust (${trust}), based primarily on practical considerations and mutual advantage. Their collaboration is effective but measured, with each maintaining independent interests.`;
      } else {
        title = "Cautious Associates";
        description = `Despite meaningful interaction (${strength}), low trust (${trust}) creates a relationship of necessary but careful engagement. They maintain connection where beneficial while remaining vigilant about potential conflicts.`;
      }
    }
    // Moderate relationship (100-299)
    else if (strength >= 100) {
      if (trust >= 75) {
        title = "Friendly Acquaintances";
        description = `A moderate connection (${strength}) with surprisingly high trust (${trust}), suggesting a positive but limited relationship. Their interactions, while not extensive, are characterized by goodwill and potential for growth.`;
      } else if (trust >= 50) {
        title = "Casual Associates";
        description = `A developing relationship (${strength}) with reasonable trust (${trust}), typical of Venetian business or social acquaintances. They interact occasionally with standard courtesy and conventional expectations.`;
      } else {
        title = "Distant Contacts";
        description = `A limited connection (${strength}) with low trust (${trust}), suggesting minimal meaningful interaction. They acknowledge each other's existence in Venetian society but maintain significant distance.`;
      }
    }
    // Weak relationship (0-99)
    else {
      if (trust >= 50) {
        title = "Potential Allies";
        description = `Though their interaction has been minimal (${strength}), relatively high trust (${trust}) suggests untapped potential. They view each other favorably despite limited engagement, creating opportunity for future connection.`;
      } else {
        title = "Passing Strangers";
        description = `With minimal connection (${strength}) and low trust (${trust}), they operate largely in separate spheres of Venetian life. Their relationship is characterized by indifference rather than either goodwill or animosity.`;
      }
    }
    
    return NextResponse.json({
      success: true,
      relationship: {
        title,
        description,
        strength,
        trust
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
