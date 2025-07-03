# Backend API Subprocess Usage Report

## Summary
The backend API contains three endpoints that execute external processes using `subprocess.run()`:

## 1. `/api/transfer-compute-solana` (POST)
- **Location**: `backend/app/main.py` lines 1948-2184
- **Purpose**: Transfer COMPUTE tokens to a wallet using Solana blockchain
- **Subprocess Call**: Executes `node scripts/transfer-compute.js`
- **Security Considerations**:
  - Takes wallet address and amount from request body
  - Creates temporary JSON file with transfer details
  - Has 30-second timeout protection
  - Handles errors from Node.js script execution

## 2. `/api/withdraw-compute-solana` (POST)
- **Location**: `backend/app/main.py` lines 2186-2306
- **Purpose**: Withdraw COMPUTE tokens from a wallet using Solana blockchain
- **Subprocess Call**: Executes `node scripts/withdraw-compute.js`
- **Security Considerations**:
  - Validates wallet existence and balance
  - Checks for active loans before allowing withdrawal
  - Creates temporary JSON file with withdrawal details
  - No timeout specified (potential risk)

## 3. `/api/cron-status` (GET)
- **Location**: `backend/app/main.py` lines 2447-2464
- **Purpose**: Check if income distribution cron job is set up
- **Subprocess Call**: Executes `crontab -l`
- **Security Considerations**:
  - Read-only operation
  - Only checks crontab contents
  - Returns status and crontab output

## Key Findings

### Direct Python Script Execution
- **No direct Python script execution found in API endpoints**
- The scheduler (`app/scheduler.py`) runs Python scripts but is not exposed via API
- All subprocess calls in API endpoints execute Node.js scripts or system commands

### Scheduler Context
- The `scheduler.py` file contains extensive subprocess usage for running backend scripts
- This runs as a background thread, not directly accessible via API
- Scripts are executed with controlled parameters and forced hour overrides

### Security Implications
1. **Node.js Script Execution**: The API executes external Node.js scripts for blockchain operations
2. **Temporary File Creation**: Both Solana endpoints create temporary JSON files which could be a security concern
3. **No Python Execution**: No API endpoints directly execute Python scripts via subprocess
4. **Timeout Protection**: Only one endpoint has timeout protection (transfer-compute-solana)

## Recommendations
1. Add timeout protection to the withdraw-compute-solana endpoint
2. Ensure temporary JSON files are properly cleaned up after use
3. Validate and sanitize all inputs before passing to subprocess commands
4. Consider using more secure IPC methods instead of temporary files