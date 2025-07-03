# Research Notes: Book 4 - Constraints of Creation

## Codebase Analysis Summary

### Building Placement Constraints

1. **Three Types of Building Points**
   - Regular building points (land-based)
   - Canal points (water-edge locations)
   - Bridge points (spanning locations)
   - Each has specific lat/lng coordinates tied to polygons
   - Buildings can only be placed on these pre-defined points

2. **The 10-Business Rule**
   - Hard limit: Citizens can only run 10 businesses
   - Checked in both initiate_building_project and construct_building processors
   - Additional businesses get RunBy = None (non-operational)
   - Applies to the operator, not the owner

3. **Financial Constraints**
   - Permit fee: max(50, building_cost * 0.05)
   - Minimum builder payment: max(50, building_cost * 0.01)
   - All costs must be paid upfront
   - Insufficient funds = immediate failure

### Resource System Constraints

1. **Resource Entry (Forestieri Galleys)**
   - All new resources enter via import galleys
   - Galley capacity: 1000 units
   - Dock hours: 6 AM - 6 PM only
   - Minimum 100m spacing between galleys
   - Import contracts specify exact quantities

2. **Resource Decay**
   - All resources have lifetimeHours property
   - Examples: Bread (75h), Fish (50h), Stone (1000h), Books (2000h)
   - processdecay.py removes expired resources
   - Creates constant drain requiring continuous production

3. **Storage Limits**
   - Buildings have fixed storageCapacity
   - Small warehouse: 500 units
   - Large warehouse: 2000 units
   - Citizens: 50 units carry capacity
   - Storage checks prevent overloading

4. **Production Constraints**
   - Recipe-based: specific inputs → outputs
   - Production penalties for:
     - Homeless operator: 50% penalty
     - Hungry operator: 50% penalty
     - Business not checked: 50% penalty
   - Must have exact resources available

### Validation Systems

1. **Activity Validation**
   - Every action validated before execution
   - Checks: funds, resources, paths, permissions
   - Complex activities require perfect sequence
   - Any failure breaks entire chain

2. **Common Failure Reasons**
   - missing_landId
   - insufficient_ducats
   - material_shortage
   - no_path_exists
   - location_invalid
   - storage_full

3. **No Resource Creation**
   - Resources only enter via imports or production
   - No money creation (except player compute injection)
   - Total conservation of matter/wealth
   - Database tracks every resource by ID

### Renaissance Translation Approach

1. **Technical Concepts → Divine Laws**
   - Building points → "Sacred points of construction"
   - 10-business limit → "The Decimal Barrier"
   - Resource decay → "Temporal decay/Divine recycling"
   - Validation failures → "The Invisible Judgment"
   - Forestieri imports → "Channels of Material Providence"

2. **Observable Patterns**
   - Buildings can only exist at specific locations
   - No citizen manages more than 10 businesses
   - All materials decay at predictable rates
   - Resources appear only through foreign merchants
   - Every action faces instant validation

3. **Research Gaps Created**
   - Origin and creation of building points
   - Why exactly 10 businesses?
   - Source of decay synchronization
   - Where Forestieri obtain goods
   - Nature of the validation intelligence

### Writing Decisions

1. **Voice**: Magister Elisabetta delle Limitazioni
   - Master builder who discovered constraints through practice
   - Systematic cataloguer of failures
   - Sees divine design in limitations
   - Pragmatist who teaches working within bounds

2. **Structure**:
   - Sacred points discovery
   - The decimal barrier
   - Resource decay patterns
   - Import channels
   - Spatial/temporal/economic limits
   - Validation systems
   - Working within constraints
   - Theological implications

3. **Constraint Categories**
   - Spatial (points, capacity, distance)
   - Temporal (decay, production time, schedules)
   - Economic (fees, conservation, limits)
   - Procedural (validation, sequences, permissions)

### Cross-Reference Potential

Links to other books:
- Book 2 (Timing): Construction activity delays
- Book 5 (Wealth): Money conservation principles
- Book 8 (Updates): How constraints change
- Book 11 (Observation): What constraints we can't see
- Book 13 (Anomalies): When constraints fail

### Historical Authenticity

- Female master builder (rare but possible in guilds)
- Religious interpretation of natural limits
- Practical builder's perspective on constraints
- Medieval concept of divine ordering of space
- Catalogue format common in period manuals

### Key Discoveries

1. **Trinity of Building Points**: Three types with different purposes
2. **The Decimal Barrier**: Universal 10-business limit
3. **Temporal Decay**: All resources contain "seeds of destruction"
4. **Conservation Paradox**: Matter redistributed, not destroyed
5. **Validation Intelligence**: Instant judgment of all actions

### Success Criteria Met

✓ Accurately reflects all building/resource constraints  
✓ Renaissance-appropriate divine interpretation  
✓ Clear research questions about constraint origins  
✓ Consistent master builder voice  
✓ Practical advice for citizens  
✓ Enables investigation of limit systems  
✓ No false technical information introduced

### Technical Details Captured

- Building points system with three types
- 10-business hard limit with code references
- Resource decay rates and conservation
- Import system via Forestieri galleys
- Storage capacities and carry limits
- Validation failures and activity chains
- Financial constraints and fees

The book successfully translates complex technical constraints into divine/natural laws that a Renaissance builder would document through systematic observation of failures and limitations.