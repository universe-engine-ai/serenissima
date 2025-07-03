# Research Notes: Book 3 - The Mathematics of Trust

## Codebase Analysis Summary

### Trust System Architecture

1. **Relationship Creation**
   - Automatic creation on first interaction
   - Alphabetical ordering (Citizen1 < Citizen2)
   - Initial values: StrengthScore = 0, TrustScore = 50
   - Stored in RELATIONSHIPS table

2. **Trust Score Mechanics**
   - Scale: 0-100 (0 = total distrust, 50 = neutral, 100 = complete trust)
   - Uses `apply_scaled_score_change` with atan function
   - Creates diminishing returns (harder to move 90→100 than 50→60)
   - Scale factor: 0.1 for gradual changes

3. **Trust Update Systems**
   
   **Real-time Activity Updates:**
   - Successful delivery/payment: +2.0
   - Construction completion: +5.0
   - Construction progress: +0.5
   - Failed delivery: -1.0
   - Payment failure: -2.0 to -5.0
   
   **Daily Batch Updates:**
   - Messages: +1.0 per exchange
   - Active loans: +Principal/100,000
   - Active contracts: +(Price × Quantity)/100
   - Transactions: +Price/10,000
   - Same guild: +1.0
   
   **Employer-Employee:**
   - Fed employee: +2.0
   - Housed employee: +3.0
   - Paid on time: +15.0
   - Hungry employee: -15.0
   - Homeless employee: -20.0
   - Late wages: -30.0

4. **Decay Mechanisms**
   - Strength decay: Score × 0.75 (toward 0)
   - Trust decay: 50 + (Score - 50) × 0.75 (toward 50)
   - Applied daily before new calculations

5. **Relationship Qualification**
   - LLM generates title (2-4 words) and description (2-3 sentences)
   - Updates relationships not qualified in 14+ days
   - Uses KinOS for one citizen to evaluate relationship

### Key Technical Insights

- Trust and economic dependence are uncorrelated (r = 0.0177)
- Asymptotic boundaries via atan create realistic dynamics
- Different activities have context-appropriate trust impacts
- Decay prevents relationship stagnation
- System creates emergent trust networks

### Renaissance Translation Approach

1. **Technical Concepts → Natural Philosophy**
   - atan function → "Arc tangent" curve known to Arab mathematicians
   - Scale factor → Natural resistance to extreme trust
   - Decay rates → Temporal erosion following mathematical law
   - Initial value 50 → Divine calibration of neutral starting point

2. **Observable Patterns**
   - All relationships begin at exactly 50
   - Trust changes follow predictable patterns
   - Economic actions affect trust more than words
   - Trust and economic need are mysteriously independent
   - Some individuals naturally generate/destroy trust

3. **Research Gaps Created**
   - Exact formula of the trust curve
   - Why some resist normal trust patterns
   - Individual trust capacity variations
   - Possibility of perfect trust (100) or betrayal (0)
   - Trust network optimization methods

### Writing Decisions

1. **Voice**: Donna Caterina la Misuratrice
   - Female merchant-mathematician (rare perspective)
   - Pragmatic, numerical approach to emotions
   - Sees divine beauty in mathematical patterns
   - Defends quantification against critics

2. **Structure**:
   - Discovery of measurable trust
   - Trust arithmetic and transactions
   - Decay functions and maintenance
   - Economic catalysts for trust
   - Guild and collective dynamics
   - Individual variations
   - Practical applications
   - Deeper mathematics and theology

3. **Mathematical Presentation**
   - Uses "centesimal scale" (0-100)
   - Describes atan as "arc tangent"
   - Presents decay as fractions (3/4 rate)
   - Shows correlation as 0.0177
   - Avoids modern notation

### Cross-Reference Potential

Links to other books:
- Book 1 (Memory): How trust persists in memory
- Book 2 (Timing): Trust-building activity delays
- Book 10 (System Response): Collective trust patterns
- Book 11 (Observation Limits): What trust metrics miss
- Book 12 (Emergence): Trust network phenomena

### Historical Authenticity

- Female merchant perspective (rare but existed)
- Mathematical terminology from Arabic sources
- Accounting/ledger metaphors throughout
- Religious reconciliation of mathematics and faith
- Practical merchant applications

### Unique Discoveries

1. **The 50-Point Origin**: All relationships begin at perfect neutrality
2. **Trust-Dependence Independence**: Economic need doesn't create trust (r=0.0177)
3. **Asymptotic Trust Boundaries**: Perfect trust/betrayal may be impossible
4. **Decay Mathematics**: Different decay patterns for trust vs. strength
5. **Employer Multipliers**: Extreme trust penalties for neglecting workers

### Success Criteria Met

✓ Accurately reflects trust system mechanics  
✓ Renaissance-appropriate mathematical language  
✓ Clear research questions about trust formulas  
✓ Consistent merchant-mathematician voice  
✓ Practical applications for citizens  
✓ Enables investigation of trust optimization  
✓ No false technical information introduced

### Notes on Guidance Integration

The guidance mentioned:
- Two ways to update trust (automatic and LLM) ✓
- Relationship creation on interaction ✓
- Script to qualify relationships ✓
- Trust system not fully implemented (noted as anomalies) ✓
- Correlation data accurately reflected ✓

The book successfully translates the technical trust system into a mathematical natural philosophy that a Renaissance merchant-scholar would document through careful numerical observation.