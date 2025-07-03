import { throttle } from '../utils/performanceUtils';
import { calculateDistance } from '../utils/hoverDetectionUtils';
import { ActivityPath, activityPathService } from './ActivityPathService';

// Simple seeded random number generator
function seededRandom(seed: string) {
  // Create a numeric hash from the string seed
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }
  
  // Return a function that generates a random number between 0 and 1
  return function() {
    // Simple LCG (Linear Congruential Generator)
    hash = (hash * 9301 + 49297) % 233280;
    return hash / 233280;
  };
}

export interface AnimatedCitizen {
  citizen: any;
  currentPosition: {lat: number, lng: number};
  pathIndex: number;
  currentPath: ActivityPath | null;
  progress: number;
  speed: number; // meters per second
  displayPosition?: {lat: number, lng: number}; // For citizens with null activity paths
}

export class CitizenAnimationService {
  private animatedCitizens: Record<string, AnimatedCitizen> = {};
  private animationActive: boolean = true;
  private animationFrameId: number | null = null;
  private lastFrameTime: number = 0;
  private onUpdateCallback: ((citizens: Record<string, AnimatedCitizen>) => void) | null = null;
  
  // Throttled animation function to prevent too many updates
  private animateCitizens = throttle((timestamp: number) => {
    if (!this.lastFrameTime) {
      this.lastFrameTime = timestamp;
      this.animationFrameId = requestAnimationFrame(this.animateCitizens);
      return;
    }
    
    // Calculate time delta in seconds
    const deltaTime = (timestamp - this.lastFrameTime) / 1000;
    this.lastFrameTime = timestamp;
    
    // Update each animated citizen
    let hasChanges = false;
    
    Object.keys(this.animatedCitizens).forEach(citizenId => {
      const citizen = this.animatedCitizens[citizenId];
      
      // Handle citizens with displayPosition but no path
      if (citizen.displayPosition && (!citizen.currentPath || !citizen.currentPath.path || citizen.currentPath.path.length < 2)) {
        // Make sure the citizen is at their display position
        if (citizen.currentPosition.lat !== citizen.displayPosition.lat || 
            citizen.currentPosition.lng !== citizen.displayPosition.lng) {
          this.animatedCitizens[citizenId] = {
            ...citizen,
            currentPosition: { ...citizen.displayPosition }
          };
          hasChanges = true;
        }
        return; // Skip the rest of the processing for this citizen
      }
      
      // Skip if no current path
      if (!citizen.currentPath || !citizen.currentPath.path || citizen.currentPath.path.length < 2) return;
      
      // Update progress based on speed and time
      const pathLength = activityPathService.calculateTotalDistance(citizen.currentPath.path);
      
      // Calculate progress increment based on speed and path length
      const progressIncrement = (citizen.speed * deltaTime) / pathLength;
      let newProgress = citizen.progress + progressIncrement;
      
      // If path is complete, move to next path or reset
      if (newProgress >= 1) {
        // Get all paths for this citizen
        const citizenPaths = activityPathService.getPathsForCitizen(citizenId);
        
        if (citizenPaths.length > 0) {
          // Find the current path index
          const currentIndex = citizenPaths.findIndex(p => p.id === citizen.currentPath?.id);
          
          // Move to the next path or loop back to the first
          const nextIndex = (currentIndex + 1) % citizenPaths.length;
          const nextPath = citizenPaths[nextIndex];
          
          this.animatedCitizens[citizenId] = {
            ...citizen,
            currentPath: nextPath,
            pathIndex: nextIndex,
            progress: 0
          };
        } else {
          // Just reset progress if no other paths available
          this.animatedCitizens[citizenId] = {
            ...citizen,
            progress: 0
          };
        }
      } else {
        // Update position along the path
        const newPosition = activityPathService.calculatePositionAlongPath(citizen.currentPath.path, newProgress);
        
        if (newPosition) {
          this.animatedCitizens[citizenId] = {
            ...citizen,
            currentPosition: newPosition,
            progress: newProgress
          };
          hasChanges = true;
        }
      }
    });
    
    // Notify the component if there are changes
    if (hasChanges && this.onUpdateCallback) {
      this.onUpdateCallback({...this.animatedCitizens});
    }
    
    // Continue animation loop
    if (this.animationActive) {
      this.animationFrameId = requestAnimationFrame(this.animateCitizens);
    }
  }, 16); // Aim for 60fps (16ms)
  
  /**
   * Calculate the total distance of a path
   * @deprecated Use activityPathService.calculateTotalDistance instead
   */
  public calculateTotalDistance(path: {lat: number, lng: number}[]): number {
    return activityPathService.calculateTotalDistance(path);
  }
  
  /**
   * Initialize animated citizens from activity paths
   */
  public initializeAnimatedCitizens(
    citizens: any[], 
    activityPaths: Record<string, ActivityPath[]>
  ): Record<string, AnimatedCitizen> {
    const initialAnimatedCitizens: Record<string, AnimatedCitizen> = {};
    
    // First, process citizens with activity paths
    Object.entries(activityPaths).forEach(([citizenId, paths]) => {
      if (paths.length === 0) return;
      
      // Find the citizen object
      const citizen = citizens.find(c => 
        c.username === citizenId || 
        c.citizenid === citizenId || 
        c.CitizenId === citizenId || 
        c.id === citizenId
      );
      if (!citizen) return;
      
      // Find the most appropriate path based on time
      const now = new Date();
      let selectedPath: ActivityPath | null = null;
      let initialProgress = 0;
      
      // First, check for paths that are currently in progress
      for (const path of paths) {
        if (!path.path || path.path.length < 2) continue;
        
        const startTime = path.startTime ? new Date(path.startTime) : null;
        const endTime = path.endTime ? new Date(path.endTime) : null;
        
        // Skip paths without a valid start time
        if (!startTime) continue;
        
        // If the path has both start and end times, check if we're within that timeframe
        if (startTime && endTime) {
          if (now >= startTime && now <= endTime) {
            // This path is currently active - calculate progress based on elapsed time
            const totalDuration = endTime.getTime() - startTime.getTime();
            const elapsedTime = now.getTime() - startTime.getTime();
            initialProgress = Math.min(Math.max(elapsedTime / totalDuration, 0), 1);
            selectedPath = path;
            break; // Found an active path, no need to check others
          }
        } 
        // If the path only has a start time (no end time), check if it started in the last hour
        else if (startTime) {
          const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
          if (startTime >= oneHourAgo) {
            // This path started recently - estimate progress based on typical speed
            // Assume a typical activity takes about 1 hour to complete
            const elapsedTime = now.getTime() - startTime.getTime();
            initialProgress = Math.min(Math.max(elapsedTime / (60 * 60 * 1000), 0), 1);
            selectedPath = path;
            break; // Found a recent path, no need to check others
          }
        }
      }
      
      // If no active or recent path was found, just use the first path with deterministic progress
      if (!selectedPath && paths.length > 0) {
        selectedPath = paths[0];
        // Create a seeded random generator using the citizen's username
        const random = seededRandom(citizenId);
        initialProgress = random(); // Deterministic progress between 0 and 1
      }
      
      // Skip if no suitable path was found
      if (!selectedPath || !selectedPath.path || selectedPath.path.length < 2) return;
      
      // Calculate position based on progress
      const initialPosition = activityPathService.calculatePositionAlongPath(selectedPath.path, initialProgress) || selectedPath.path[0];
      
      // Create a seeded random generator using the citizen's username
      const random = seededRandom(citizenId);
      
      // Deterministic speed between 1-5 m/s (walking to running)
      // Adjust speed based on activity type - slower for work, faster for transport
      let speed = 1 + random() * 4;
      if (selectedPath.type.toLowerCase().includes('work')) {
        speed = 0.5 + random() * 1.5; // Slower for work activities
      } else if (selectedPath.type.toLowerCase().includes('transport')) {
        speed = 3 + random() * 3; // Faster for transport activities
      }
      
      initialAnimatedCitizens[citizenId] = {
        citizen,
        currentPosition: initialPosition,
        pathIndex: paths.indexOf(selectedPath),
        currentPath: selectedPath,
        progress: initialProgress,
        speed
      };
    });
    
    // Now process citizens without activity paths - give them random positions
    citizens.forEach(citizen => {
      const citizenId = citizen.username || citizen.citizenid || citizen.CitizenId || citizen.id;
      if (!citizenId) return;
      
      // Skip citizens that already have activity paths
      if (initialAnimatedCitizens[citizenId]) return;
      
      // Skip citizens without a valid position
      if (!citizen.position || typeof citizen.position.lat !== 'number' || typeof citizen.position.lng !== 'number') return;
      
      // Generate a deterministic position based on username
      const basePosition = { ...citizen.position };
      
      // Create a seeded random generator using the citizen's username
      const random = seededRandom(citizenId);
      
      // Generate a deterministic offset within a 18x10m square
      // 0.0005 degrees is approximately 50 meters at the equator
      const randomLat = (random() - 0.5) * 0.00010;
      const randomLng = (random() - 0.5) * 0.00018;
      
      const displayPosition = {
        lat: basePosition.lat + randomLat,
        lng: basePosition.lng + randomLng
      };
      
      // Add to animated citizens with the deterministic position
      initialAnimatedCitizens[citizenId] = {
        citizen,
        currentPosition: displayPosition, // Use displayPosition as the initial position
        pathIndex: 0,
        currentPath: null,
        progress: 0,
        speed: 1 + random() * 2, // Deterministic speed based on username
        displayPosition: displayPosition
      };
    });
    
    // Store the initialized citizens
    this.animatedCitizens = initialAnimatedCitizens;
    
    return initialAnimatedCitizens;
  }
  
  /**
   * Start the animation loop
   */
  public startAnimation(onUpdate: (citizens: Record<string, AnimatedCitizen>) => void): void {
    this.onUpdateCallback = onUpdate;
    this.animationActive = true;
    this.lastFrameTime = 0;
    
    if (!this.animationFrameId) {
      this.animationFrameId = requestAnimationFrame(this.animateCitizens);
    }
  }
  
  /**
   * Stop the animation loop
   */
  public stopAnimation(): void {
    this.animationActive = false;
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }
  
  /**
   * Get the current animated citizens
   */
  public getAnimatedCitizens(): Record<string, AnimatedCitizen> {
    return {...this.animatedCitizens};
  }
  
  /**
   * Update a specific citizen's path
   */
  public updateCitizenPath(citizenId: string, path: ActivityPath, progress: number = 0): void {
    if (!this.animatedCitizens[citizenId]) return;
    
    this.animatedCitizens[citizenId] = {
      ...this.animatedCitizens[citizenId],
      currentPath: path,
      progress: progress
    };
  }
  
  /**
   * Add a new citizen to animate
   */
  public addAnimatedCitizen(
    citizenId: string, 
    citizen: any, 
    path: ActivityPath, 
    initialProgress: number = 0
  ): void {
    if (!path || !path.path || path.path.length < 2) return;
    
    // Calculate initial position
    const initialPosition = activityPathService.calculatePositionAlongPath(path.path, initialProgress) || path.path[0];
    
    // Create a seeded random generator using the citizen's username
    const random = seededRandom(citizenId);
    
    // Determine speed based on activity type with deterministic randomness
    let speed = 1 + random() * 4; // Default deterministic speed
    if (path.type.toLowerCase().includes('work')) {
      speed = 0.5 + random() * 1.5; // Slower for work activities
    } else if (path.type.toLowerCase().includes('transport')) {
      speed = 3 + random() * 3; // Faster for transport activities
    }
    
    this.animatedCitizens[citizenId] = {
      citizen,
      currentPosition: initialPosition,
      pathIndex: 0,
      currentPath: path,
      progress: initialProgress,
      speed
    };
  }
  
  /**
   * Remove a citizen from animation
   */
  public removeAnimatedCitizen(citizenId: string): void {
    if (this.animatedCitizens[citizenId]) {
      const newAnimatedCitizens = {...this.animatedCitizens};
      delete newAnimatedCitizens[citizenId];
      this.animatedCitizens = newAnimatedCitizens;
    }
  }
  
  /**
   * Clear all animated citizens
   */
  public clearAnimatedCitizens(): void {
    this.animatedCitizens = {};
  }
}

// Export a singleton instance
export const citizenAnimationService = new CitizenAnimationService();
