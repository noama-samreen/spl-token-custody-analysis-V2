# Solana Token Custody Analyzer V2

A Python-based tool for analyzing Solana tokens, supporting both standard SPL tokens and Token-2022 program tokens, with special verification for Pump.Fun tokens.

## Features

### Token Analysis
- **Program Verification**:
  - Standard SPL Token Program
  - Token-2022 Program
- **Metadata Retrieval**:
  - Token name and symbol
  - Update authority
  - Program ownership

### Security Features Detection
- **Standard SPL Tokens**:
  - Freeze authority status
- **Token-2022 Program Extensions**:
  - Permanent delegate
  - Transaction fees
  - Transfer hook programming
  - Confidential transfers
  - Token metadata

### Pump.Fun Token Verification
- **Authority Verification**:
  - Update authority check against Pump.Fun authority
- **Program Interaction**:
  - Verification of Pump.Fun program interaction
  - Raydium AMM program interaction detection
- **Token Status**:
  - Genuine Pump.Fun token verification
  - Raydium graduation status using Raydium API https://api-v3.raydium.io/docs/
  - Transaction signature tracking
  - Interacting account details

## Project Structure

### Core Components
- `spl_token_analysis.py`: Core token analysis library
  - Token data structures and models
  - RPC interaction logic
  - Security review calculations
  - Mitigation handling

- `spl_token_analysis_cli.py`: Command-line interface
  - Single and batch token analysis
  - Report generation
  - Mitigation file processing
  - JSON and PDF output generation

- `spl_report_generator.py`: PDF report generation
  - Detailed security analysis reports
  - Risk assessment documentation
  - Mitigation documentation
  - Visual presentation of results

- `app.py`: Streamlit web interface
  - Interactive token analysis
  - Real-time mitigation management
  - Dynamic security review updates
  - Report download options

## Usage

### Command Line Interface
```bash
# Single token analysis and report
python spl_token_analysis_cli.py <token_address> --output ./reports

# Batch processing
python spl_token_analysis_cli.py tokens.txt --batch --output ./reports

# Analysis with mitigations
python spl_token_analysis_cli.py <token_address> --output ./reports --mitigation mitigations.json

# Batch processing with mitigations
python spl_token_analysis_cli.py tokens.txt --batch --output ./reports --mitigation mitigations.json
```

### CLI Arguments
- `input`: Token address or path to input file with token addresses
- `--batch, -b`: Process input as a batch file containing multiple token addresses
- `--output, -o`: Output directory for reports and JSON results (optional, defaults to current directory)
- `--mitigation, -m`: JSON file containing mitigation documentation

### Web Interface
```bash
# Start the Streamlit web application
streamlit run app.py
```

### Output Files
- **PDF Reports**: Individual PDF reports for each token
- **JSON Results**: 
  - Single token: `token_analysis_ADDRESS_TIMESTAMP.json`
  - Batch processing: `batch_results_TIMESTAMP.json`
- Reports include:
  - Token details and metadata
  - Security review status
  - Risk assessment
  - Applied mitigations (if any)

### Mitigation File Format
```json
{
  "token_address_1": {
    "freeze_authority": {
      "documentation": "Freeze authority is controlled by multisig [view details](https://example.com)",
      "applied": true
    }
  },
  "token_address_2": {
    "transfer_hook": {
      "documentation": "Transfer hook is audited by XYZ Labs [audit report](https://example.com)",
      "applied": true
    },
    "permanent_delegate": {
      "documentation": "Permanent delegate is required for protocol operations [docs](https://example.com)",
      "applied": true
    }
  }
}
```

## Security Review Criteria

### Standard SPL Tokens
- PASSED: No freeze authority
- FAILED: Has freeze authority

### Token-2022 Program
- PASSED: No security-sensitive features
- FAILED: Has any of:
  - Freeze authority
  - Permanent delegate
  - Transfer hook
  - Confidential transfers
  - Non-zero transfer fees

### Pump.Fun Verification
- Checks update authority
- Verifies program interactions
- Tracks Raydium graduation status

## Technical Details

### Dependencies
- Python 3.8+
- aiohttp: For async HTTP requests
- solders: For Solana public key operations
- reportlab: For PDF report generation
- streamlit: For web interface
- logging: For detailed operation logging

### Configuration
- Customizable RPC endpoint
- Adjustable rate limits
- Configurable retry parameters
- Concurrent processing limits

## Error Handling
- Robust retry mechanism
- Rate limit handling
- Detailed error logging
- Graceful failure recovery
