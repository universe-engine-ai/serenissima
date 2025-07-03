# Official Governance Titles and Positions
*A comprehensive guide to formal roles in La Serenissima's democracy*

## Overview

Official titles in the governance system are not mere badges or achievements - they are formal positions with real power, responsibilities, and economic benefits. Each title:
- Appears prominently in citizen profiles
- Grants specific privileges and abilities
- Affects how NPCs and other citizens interact with the holder
- Comes with measurable responsibilities
- Can be lost through poor performance or recall votes

## Phase 1: Grievance System Titles

### Voice of the People
- **Selection**: Citizen with most grievances successfully promoted to proposals
- **Powers**: 
  - Can file 2 grievances per week (vs normal 1)
  - Grievances start with 5 automatic supporters
  - Direct access to Signoria discussions
- **Responsibilities**: Must file at least 1 grievance monthly or lose title
- **Benefits**: +200 Influence, 10% discount at government buildings
- **Duration**: 3 months, then re-evaluated

### Advocate of [Category]
- **Selection**: Most successful grievance filer in each category (Economic, Social, Criminal, Infrastructure)
- **Powers**: 
  - Expert testimony weight in forums
  - Can fast-track grievances in their category
- **Responsibilities**: Must support other grievances in category
- **Benefits**: +100 Influence, recognized by NPCs as expert
- **Duration**: Until someone else files more successful grievances

## Phase 2: Forum System Titles

### Master Orator
- **Selection**: Citizen whose forum speeches generate most proposal refinements
- **Powers**:
  - Double speaking time (30 min vs 15)
  - Can speak twice per forum
  - Queue priority over non-titled speakers
- **Responsibilities**: Must attend 50% of forums or lose title
- **Benefits**: +150 Influence, charisma bonus in all social interactions
- **Duration**: Evaluated monthly based on impact metrics

### Tribune of [Social Class]
- **Selection**: Elected by members of each social class
- **Powers**:
  - Speaks for their class in forums
  - Can call emergency forums for class-specific issues
  - Veto power over proposals harming their class
- **Responsibilities**: Must represent class interests faithfully
- **Benefits**: +300 Influence, salary of 100 ducats/week
- **Duration**: 6-month terms, can be recalled by class vote

### Keeper of Discourse
- **Selection**: Appointed by consensus for fairness and wisdom
- **Powers**:
  - Moderates forums with authority to silence disruptors
  - Sets speaking order
  - Summarizes debates for official record
- **Responsibilities**: Must remain politically neutral
- **Benefits**: +250 Influence, respected by all factions
- **Duration**: Permanent unless removed for bias

## Phase 3: Voting System Titles

### Electoral Magistrate
- **Selection**: Appointed by Signoria, confirmed by citizen vote
- **Powers**:
  - Oversees voting integrity
  - Can invalidate fraudulent votes
  - Certifies election results
  - Investigates voting irregularities
- **Responsibilities**: Ensure fair and transparent elections
- **Benefits**: +400 Influence, salary of 200 ducats/week, immunity from prosecution during term
- **Duration**: 1-year term, maximum 2 consecutive terms

### Voice of the Majority/Minority
- **Selection**: Leaders of winning/losing coalitions in major votes
- **Powers**:
  - Majority: First proposal rights in next cycle
  - Minority: Guaranteed speaking time to present opposition
  - Both: Access to voting data and patterns
- **Responsibilities**: Articulate their coalition's position
- **Benefits**: +150 Influence, media attention bonuses
- **Duration**: Until next major vote

### Keeper of the Rolls
- **Selection**: Citizen with highest voting participation rate
- **Powers**:
  - Maintains official voting records
  - Can challenge vote counts
  - Access to historical voting data
- **Responsibilities**: Preserve democratic records accurately
- **Benefits**: +100 Influence, archival access privileges
- **Duration**: 6 months minimum participation

### Party Praetor
- **Selection**: Elected leader of registered political coalition (10+ members)
- **Powers**:
  - Negotiate coalition agreements
  - Direct party campaign funds
  - Bonus to political stratagems
- **Responsibilities**: Maintain party cohesion and platform
- **Benefits**: +200 Influence, 5% of party campaign donations
- **Duration**: Annual party elections

## Phase 4: Constitutional Titles

### Doge of Venice
- **Selection**: Elected by Council of Venice from among Nobili
- **Powers**:
  - Executive authority over daily governance
  - Tie-breaking vote in Council
  - Diplomatic powers with outside entities
  - Emergency decree powers (subject to review)
- **Responsibilities**: Lead Venice wisely and fairly
- **Benefits**: +1000 Influence, Palazzo Ducale residence, 1000 ducats/week
- **Duration**: 5-year term, one term limit

### Councilor of Venice
- **Selection**: Elected by respective constituencies
- **Powers**:
  - Legislative authority
  - Budget approval powers
  - Can impeach officials
  - Constitutional amendment rights
- **Responsibilities**: Attend council sessions, represent constituents
- **Benefits**: +500 Influence, 500 ducats/week, legislative immunity
- **Duration**: 2-year terms, no term limits

### Chief Magistrate
- **Selection**: Appointed by Council, confirmed by citizens
- **Powers**:
  - Heads judicial system
  - Final arbiter of disputes
  - Constitutional interpretation
  - Can overturn government actions
- **Responsibilities**: Uphold law and constitution impartially
- **Benefits**: +600 Influence, 750 ducats/week, judicial residence
- **Duration**: 10-year term, one renewal possible

### Constitutional Guardian
- **Selection**: Chosen by supermajority of all three branches
- **Powers**:
  - Veto unconstitutional actions
  - Force constitutional review
  - Emergency intervention rights
- **Responsibilities**: Protect constitutional order
- **Benefits**: +800 Influence, above-politics status
- **Duration**: Life appointment (or until voluntary retirement)

## Special Civic Positions

### Captain of the People
- **Selection**: Elected during crisis by popular acclaim
- **Powers**:
  - Emergency mobilization authority
  - Direct democracy facilitation
  - Can bypass normal procedures in crisis
- **Responsibilities**: Resolve crisis, then step down
- **Benefits**: +1000 Influence during crisis
- **Duration**: Limited to specific crisis resolution

### Ombudsman of Venice
- **Selection**: Nominated by citizens, confirmed by Council
- **Powers**:
  - Investigate government corruption
  - Protect citizen rights
  - Public report privileges
- **Responsibilities**: Independent oversight of government
- **Benefits**: +400 Influence, investigative immunity
- **Duration**: 3-year terms, renewable once

## Title Interactions

### Hierarchies
Some titles outrank others in specific contexts:
- Doge > Councilors > Tribunes in executive matters
- Chief Magistrate > Electoral Magistrate > Other magistrates in judicial matters
- Constitutional Guardian > All others in constitutional questions

### Conflicts of Interest
Citizens cannot simultaneously hold:
- Executive and Legislative titles
- Judicial and Political titles
- Party leadership and Electoral oversight

### Succession Rules
When a title holder leaves office:
- Elected positions: Special election within 30 days
- Appointed positions: Appointing body selects within 14 days
- Merit positions: Automatic succession to next qualified

## Economic Benefits Summary

All title holders receive:
- Influence bonuses (as specified)
- Priority in government contracts
- Reduced fees at government buildings
- Enhanced reputation with NPCs
- Access to exclusive government areas

Higher titles also receive:
- Weekly salaries (as specified)
- Official residences (senior positions)
- Staff and resources
- Diplomatic privileges

## Loss of Title

Titles can be lost through:
- **Impeachment**: For corruption or abuse of power
- **Recall**: By constituency vote (60% required)
- **Abandonment**: Not fulfilling responsibilities
- **Term Limits**: Natural expiration
- **Performance**: Failing to meet metrics

## Implementation Notes

### Database Fields
Add to CITIZENS table:
- OfficialTitle (text)
- TitleGrantedDate (datetime)
- TitleExpiration (datetime)
- TitlePowers (JSON array)
- TitleSalary (number)

### Display
- Titles appear before citizen names in all UI
- Special formatting/colors by title rank
- Hovering shows title powers and responsibilities

### NPCs and AI Interactions
- NPCs recognize and defer to title holders
- AI citizens factor titles into relationship calculations
- Special dialogue options for titled citizens

This system ensures that political participation has tangible rewards beyond mere recognition, creating a meaningful progression path for politically active citizens while maintaining the authentic feel of Renaissance Venetian governance.