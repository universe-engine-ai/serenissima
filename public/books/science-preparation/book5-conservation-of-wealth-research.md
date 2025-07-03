# Book 5: "The Conservation of Wealth" - Research Notes

## Author: Maestro Lorenzo della Circolazione, economic philosopher

## Key Findings from Codebase Analysis

### 1. Money Creation - Immigration Only
- New citizens arrive with 10,000-100,000 ducats (generateCitizen.py, line 186)
- This is the ONLY way new ducats enter the system
- Immigration script creates new citizens with initial wealth
- No other mechanism creates ducats from nothing

### 2. Transaction Mechanics - Perfect Conservation
Every transaction follows this pattern (fetch_resource_processor.py, lines 319-321):
```python
tables['citizens'].update(buyer_citizen_record['id'], {'Ducats': buyer_ducats - total_cost})
tables['citizens'].update(seller_citizen_record['id'], {'Ducats': seller_ducats + total_cost})
```
- Buyer loses exact amount seller gains
- Transaction record created for every transfer
- No rounding or fees that destroy money

### 3. Treasury Redistribution - Circulation Not Creation
- Daily redistribution of 1% of ConsiglioDeiDieci treasury (treasuryRedistribution.py)
- Money moves FROM treasury TO citizens
- Distribution by social class: Nobili 40%, Cittadini 30%, Popolani 20%, Facchini 10%
- Fixed daily payments: Scientisti 2500, Clero 2000
- Total wealth remains constant

### 4. Loan System - Temporal Redistribution
- Daily loan payments transfer from borrower to lender (dailyloanpayments.py)
- Interest doesn't create money, just redistributes it over time
- Failed payments due to insufficient funds - money can't be created

### 5. Leaving Venice - Money Retained
- Citizens leaving Venice keep their ducats (leave_venice_processor.py)
- Resources liquidated at import prices (sold to "Italia")
- Ducats stay in system, just marked InVenice=FALSE

### 6. Activity-Based Transfers
Multiple activities involve ducat transfers:
- Gondola rides - passenger pays gondolier
- Building maintenance - owner pays treasury
- Wages - employer pays employees
- Rent - tenant pays landlord
- Market purchases - buyer pays seller
- Taxes on various activities

### 7. Validation and Constraints
- All transfers check sufficient funds before executing
- Transactions fail if buyer lacks funds
- No overdrafts or negative balances possible
- Every ducat movement tracked in TRANSACTIONS table

## Observable Phenomena for the Book
1. Total city wealth can be calculated by summing all citizen ducats
2. This total only changes when new citizens arrive
3. Individual wealth fluctuates but city total remains constant (except immigration)
4. Failed transactions due to insufficient funds are observable
5. Wealth concentration patterns emerge over time
6. Economic velocity measurable through transaction frequency

## Natural Research Gaps for Citizens
1. Why does wealth appear with new arrivals? (They don't know about blockchain)
2. What prevents wealth creation through other means?
3. Is there an optimal wealth distribution for city prosperity?
4. How does wealth concentration affect economic velocity?
5. What are the long-term effects of the redistribution system?
6. Can mathematical models predict wealth flow patterns?

## Renaissance Translation Keys
- Closed-loop economy → "Divine ordinance preventing false abundance"
- Transaction validation → "Sacred mathematics governing honest exchange"
- Immigration wealth → "Fortune that travelers bring from distant lands"
- Conservation principle → "Immutable law that wealth transforms but never multiplies"
- Failed transactions → "Heaven's prevention of impossible exchanges"