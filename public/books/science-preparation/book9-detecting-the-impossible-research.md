# Book 9: "Detecting the Impossible: Methods for Identifying Physics Changes" - Research Notes

## Author: Investigatore Giulio dell'Impossibile, natural philosopher

## Key Findings from Codebase Analysis

### 1. Observable Anomalies from System Changes

#### Activity Processing Failures
From activity processors, common error patterns when physics change:
- `log.error("Activity X is missing crucial data")` - Missing required fields
- `log.error("X not found")` - Entities vanishing unexpectedly
- `log.error("Validation failed")` - Constraint violations
- `log.warning("Skipping due to insufficient funds")` - Economic impossibilities

#### Validation Exceptions
Activity processors validate against current physics:
- Building placement constraints
- Resource availability checks
- Economic transaction validations
- Movement and location verification
- Temporal sequence validations

#### Anomaly Categories from Code
1. **Entity Disappearance**: Buildings/citizens/resources not found
2. **Constraint Violations**: Actions that should work but fail
3. **Economic Impossibilities**: Transactions failing despite sufficient funds
4. **Temporal Anomalies**: Activities completing too fast/slow
5. **Location Paradoxes**: Citizens in impossible positions

### 2. Detection Systems

#### Problem Detection API (detectProblems.py)
- Systematic scanning for anomalies
- Types detected:
  - Homeless citizens (should have homes but don't)
  - Workless citizens (should have jobs but don't)
  - Building operation failures
  - Resource discrepancies
  - Contract fulfillment issues

#### Auto-Resolution System (autoResolveProblems.py)
- Attempts to fix detected anomalies
- Tracks failure counts: `[Failures: N]`
- Escalates severity after repeated failures
- Creates notifications for unresolvable issues

#### Severity Classification
```python
SEVERITY_ORDER = {"Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Critical": 5}
```
- Problems escalate if repeatedly unresolvable
- Critical problems suggest fundamental physics changes

### 3. Detection Methods from Code

#### Systematic Monitoring
1. **Activity Success Rates**: Track activity failures by type
2. **Entity Existence Checks**: Regular verification that entities exist
3. **Constraint Testing**: Attempt known-valid actions
4. **Economic Balance**: Verify conservation laws
5. **Temporal Consistency**: Check activity durations

#### Error Pattern Analysis
From error logs:
- Sudden spike in specific error types
- New error messages never seen before
- Cascade failures across multiple systems
- Consistent failures of previously working actions

#### Verification Procedures
1. **Reproducibility**: Same action fails multiple times
2. **Scope**: Multiple citizens affected similarly
3. **Persistence**: Problem continues across time
4. **Escalation**: Auto-fix attempts fail repeatedly

### 4. False Positive Sources

#### Temporary Glitches
- Network timeouts
- Database connection issues
- Race conditions in concurrent processing
- Temporary resource locks

#### Natural Variations
- Economic fluctuations
- Normal statistical variance
- Citizen behavioral changes
- Seasonal patterns

### 5. True Physics Changes

#### Indicators from Code
1. **New Activity Types**: Processors for activities that didn't exist
2. **Modified Validation Rules**: Changed constraints in processors
3. **New Entity Types**: Buildings/resources not previously possible
4. **Altered Mechanics**: Different calculation methods
5. **System-Wide Effects**: All citizens affected simultaneously

#### Detection Through Failure Patterns
- Activities that always worked now always fail
- New activities suddenly possible
- Changed resource requirements
- Modified economic calculations
- Altered movement constraints

## Observable Phenomena for Book

1. **Activity Failure Spikes**: Sudden increases in failed activities
2. **Entity Vanishing**: Things that existed yesterday don't today
3. **Impossible Successes**: Actions that shouldn't work do
4. **Collective Behavioral Shifts**: All citizens act differently
5. **New Error Messages**: Notifications never seen before
6. **Resolution Failures**: Problems that can't be auto-fixed

## Natural Research Gaps

1. **Early Warning Systems**: How to detect changes before major disruptions?
2. **Change Classification**: Different types of physics modifications?
3. **Adaptation Timing**: When to accept vs. resist changes?
4. **Collective Verification**: How many observers needed for confirmation?
5. **Reversion Possibilities**: Can changes be undone?
6. **Prediction Algorithms**: Patterns that precede updates?

## Renaissance Translation Keys

- Error logs → "Violation records kept by divine scribes"
- Validation failures → "Natural law preventing impossible actions"
- Auto-resolution → "Heaven's attempts to restore order"
- Severity escalation → "Growing disturbance in reality's fabric"
- Problem detection → "Systematic search for anomalies"
- False positives → "Temporary illusions vs. true transformations"