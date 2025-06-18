# Copyright 2025 noamasamreen

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, List
import base64
from functools import lru_cache
import asyncio
import aiohttp
import logging
import json
from solders.pubkey import Pubkey as PublicKey
import time
from asyncio import sleep

# Constants
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
MAX_RETRIES = 4
BASE_DELAY = 2.0  # 2 second between requests
RETRY_DELAY = 2.0  # Additional delay when rate limited

# Original constants
CONCURRENT_LIMIT = 1  # Back to original value
SESSION_TIMEOUT = aiohttp.ClientTimeout(total=30)

OWNER_LABELS = {
    TOKEN_PROGRAM: "Token Program",
    TOKEN_2022_PROGRAM: "Token 2022 Program"
}

async def get_metadata_account(mint_address: str) -> Tuple[PublicKey, int]:
    """Derive the metadata account address for a mint"""
    try:
        metadata_program_id = PublicKey.from_string(METADATA_PROGRAM_ID)
        mint_pubkey = PublicKey.from_string(mint_address)
        
        seeds = [
            b"metadata",
            bytes(metadata_program_id),
            bytes(mint_pubkey)
        ]
        
        return PublicKey.find_program_address(
            seeds,
            metadata_program_id
        )
    except Exception as e:
        logging.error(f"Error deriving metadata account: {e}")
        return None, None

async def get_metadata(session: aiohttp.ClientSession, mint_address: str) -> Optional[Dict]:
    """Fetch metadata for a token with more conservative retry logic"""
    for retry in range(MAX_RETRIES):
        try:
            # Add base delay before every request
            await sleep(BASE_DELAY)
            
            metadata_address, _ = await get_metadata_account(mint_address)
            if not metadata_address:
                logging.warning(f"Could not derive metadata address for {mint_address}")
                return None

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    str(metadata_address),
                    {"encoding": "base64"}
                ]
            }
            
            async with session.post(SOLANA_RPC_URL, json=payload) as response:
                if response.status == 429:  # Rate limit hit
                    if retry < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** retry)  # Exponential backoff
                        logging.warning(f"Rate limit hit in metadata fetch, waiting {wait_time} seconds...")
                        await sleep(wait_time)
                        continue
                    return None
                    
                if response.status != 200:
                    logging.warning(f"Non-200 status code: {response.status}")
                    return None
                    
                data = await response.json()
                if "result" not in data or not data["result"] or not data["result"]["value"]:
                    logging.warning("No metadata data returned from RPC")
                    return None

                # Parse the metadata account data
                account_data = data["result"]["value"]["data"][0]
                decoded_data = base64.b64decode(account_data)
                
                if len(decoded_data) < 8:  # Ensure we have enough data
                    logging.warning("Metadata data too short")
                    return None
                    
                try:
                    # Skip the first byte (discriminator)
                    offset = 1
                    
                    # Read update authority (32 bytes)
                    update_authority = str(PublicKey(decoded_data[offset:offset + 32]))
                    offset += 32
                    
                    # Skip mint address (32 bytes)
                    offset += 32
                    
                    # Read name length and name
                    name_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                    offset += 4
                    if name_length > 0:
                        name = decoded_data[offset:offset + name_length].decode('utf-8').rstrip('\x00')
                    else:
                        name = "N/A"
                    offset += name_length
                    
                    # Read symbol length and symbol
                    symbol_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                    offset += 4
                    if symbol_length > 0:
                        symbol = decoded_data[offset:offset + symbol_length].decode('utf-8').rstrip('\x00')
                    else:
                        symbol = "N/A"
                    
                    logging.info(f"Successfully parsed metadata - Name: {name}, Symbol: {symbol}")
                    return {
                        "name": name,
                        "symbol": symbol,
                        "update_authority": update_authority
                    }
                except UnicodeDecodeError as e:
                    logging.error(f"Error decoding metadata strings: {e}")
                    return None
                except Exception as e:
                    logging.error(f"Error parsing metadata: {e}")
                    return None
                
        except Exception as e:
            if retry < MAX_RETRIES - 1:
                await sleep(RETRY_DELAY * (retry + 1))
                continue
            logging.error(f"Error fetching metadata: {str(e)}")
            return None

@dataclass
class Token2022Extensions:
    permanent_delegate: Optional[str] = None
    transfer_fee: Optional[int] = None
    transfer_hook_authority: Optional[str] = None
    confidential_transfers_authority: Optional[str] = None

@dataclass
class MitigationDetails:
    documentation: str
    applied: bool = False

@dataclass
class TokenDetails:
    name: str
    symbol: str
    address: str
    owner_program: str
    freeze_authority: Optional[str]
    update_authority: Optional[str] = None
    extensions: Optional[Token2022Extensions] = None
    is_genuine_pump_fun_token: bool = False
    interacted_with: Optional[str] = None
    interacting_account: Optional[str] = None
    interaction_signature: Optional[str] = None
    security_review: str = "FAILED"
    token_graduated_to_raydium: bool = False
    mitigations: Dict[str, MitigationDetails] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        result = {
            'name': self.name,
            'symbol': self.symbol,
            'address': self.address,
            'owner_program': self.owner_program,
            'freeze_authority': self.freeze_authority,
            'update_authority': (f"{self.update_authority} (Pump.Fun Mint Authority)" 
                               if self.update_authority == "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM" 
                               else self.update_authority)
        }
        
        if self.extensions:
            result.update({
                'permanent_delegate': self.extensions.permanent_delegate,
                'transaction_fees': self.extensions.transfer_fee,
                'transfer_hook': self.extensions.transfer_hook_authority,
                'confidential_transfers': self.extensions.confidential_transfers_authority,
            })
        
        if self.update_authority == "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM":
            result['is_genuine_pump_fun_token'] = self.is_genuine_pump_fun_token
            result['token_graduated_to_raydium'] = self.token_graduated_to_raydium
            if self.is_genuine_pump_fun_token and self.interacted_with:
                result['interacted_with'] = self.interacted_with
                result['interacting_account'] = self.interacting_account
                result['interaction_signature'] = self.interaction_signature
        
        # Add mitigations to result
        result['mitigations'] = {
            check: {
                'documentation': mitigation.documentation,
                'applied': mitigation.applied
            }
            for check, mitigation in self.mitigations.items()
        }
        
        # Update security review based on mitigations
        has_unmitigated_risks = False
        if self.freeze_authority and not (self.mitigations.get('freeze_authority', MitigationDetails('')).applied):
            has_unmitigated_risks = True
        if self.extensions:
            if (self.extensions.permanent_delegate and 
                not self.mitigations.get('permanent_delegate', MitigationDetails('')).applied):
                has_unmitigated_risks = True
            if (self.extensions.transfer_hook_authority and 
                not self.mitigations.get('transfer_hook', MitigationDetails('')).applied):
                has_unmitigated_risks = True
            if (self.extensions.confidential_transfers_authority and 
                not self.mitigations.get('confidential_transfers', MitigationDetails('')).applied):
                has_unmitigated_risks = True
            if (self.extensions.transfer_fee not in [None, 0] and 
                not self.mitigations.get('transfer_fees', MitigationDetails('')).applied):
                has_unmitigated_risks = True
        
        result['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
        return result

@lru_cache(maxsize=100)
def get_owner_program_label(owner_address: str) -> str:
    """Cached helper function to get the label for owner program"""
    return OWNER_LABELS.get(owner_address, "Unknown Owner")

async def verify_pump_token(session: aiohttp.ClientSession, token_address: str, metadata: Optional[dict] = None) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """Verify if token is a genuine pump.fun token using new criteria"""
    PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
    RAYDIUM_AMM_PROGRAM = "EhhTKJ6M13fa4jc281HpdyiNpAHj8uvxymgZqGuDs9Jj"
    PUMP_UPDATE_AUTHORITY = "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
    
    # Step 1: Check update authority
    if not metadata or metadata.get("update_authority") != PUMP_UPDATE_AUTHORITY:
        logging.info(f"Token {token_address} failed update authority check")
        return False, None, None, None
        # Continue to Step 3
    
    # Step 3: Check Raydium token list if no Pump.fun interaction found
    #Moved step 3 before step 2 to optimize 
    logging.info(f"Pump.fun Token Checks: Checking Raydium graduation status")
    try:
        await asyncio.sleep(1)
        RAYDIUM_BASE_URL = "https://api-v3.raydium.io"
        RAYDIUM_MINT_INFO_ENDPOINT = "/mint/ids"
        
        async with session.get(f"{RAYDIUM_BASE_URL}{RAYDIUM_MINT_INFO_ENDPOINT}?mints={token_address}") as response:
            if response.status != 200:
                logging.error(f"Raydium API returned status {response.status}")
                return False, None, None, None
                
            raydium_data = await response.json()
            #logging.info(f"Raydium Token Info Response: {raydium_data}")
            
            # Check if response has data field and contains valid token info
            if (raydium_data.get("success") and 
                raydium_data.get("data") and 
                isinstance(raydium_data["data"], list) and 
                raydium_data["data"][0]):
                
                token_info = raydium_data["data"][0]
                logging.info(f"Pump.fun Token Checks: Token found in Raydium - Name: {token_info.get('name')}, Symbol: {token_info.get('symbol')}")
                return True, "raydium", None, None
            else:
                logging.info(f"Pump.fun Token Checks: Token not found in Raydium (not graduated)")
                #return False, None, None, None
    
    except Exception as e:
        logging.error(f"Error checking Raydium API: {str(e)}")
        return False, None, None, None        

    # Step 2: Check recent transactions for Pump.fun interaction
    try:
        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                token_address,
                {
                    "limit": 3,
                    "commitment": "confirmed"
                }
            ]
        }
        
    
        async with session.post(SOLANA_RPC_URL, json=params) as response:
            data = await response.json()
            if "result" not in data:
                logging.warning(f"No transaction data found for token {token_address}")
                # Continue to Step 3
            else:
                signatures = data["result"]
                logging.info(f"Pump.fun Token Checks: Found recent transactions")
                
                # Check each transaction for Pump.fun interaction
                for sig_info in signatures:
                    #logging.info(f"Checking transaction: {sig_info['signature']}")
                    tx_params = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [
                            sig_info['signature'],
                            {
                                "encoding": "jsonParsed",
                                "maxSupportedTransactionVersion": 0,
                                "commitment": "confirmed"
                            }
                        ]
                    }
                    async with session.post(SOLANA_RPC_URL, json=tx_params) as tx_response:
                        tx_data = await tx_response.json()
                        if "result" not in tx_data or not tx_data["result"]:
                            continue
                            
                        # Add detailed logging for debugging
                        accounts = tx_data["result"].get("meta", {}).get("loadedAddresses", {}).get("writable", [])
                        accounts.extend(tx_data["result"].get("meta", {}).get("loadedAddresses", {}).get("readonly", []))
                        accounts.extend(tx_data["result"].get("transaction", {}).get("message", {}).get("accountKeys", []))
                        
                        #logging.info(f"\nDetailed Transaction Info for {sig_info['signature']}:")
                        #logging.info("----------------------------------------")
                        
                        # Log all account details in the transaction and check for verification
                        #logging.info("Account Details:")
                        for idx, acc in enumerate(accounts):
                            try:
                                # Get account info for each address
                                acc_pubkey = acc if isinstance(acc, str) else acc.get('pubkey')
                                if not acc_pubkey:
                                    continue

                                acc_info_params = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "getAccountInfo",
                                    "params": [
                                        acc_pubkey,
                                        {
                                            "encoding": "jsonParsed",
                                            "commitment": "confirmed"
                                        }
                                    ]
                                }
                                await asyncio.sleep(1)
                                async with session.post(SOLANA_RPC_URL, json=acc_info_params) as acc_response:
                                    acc_data = await acc_response.json()
                                    if "result" not in acc_data or acc_data["result"] is None:
                                        #logging.info(f"No account info found for {acc_pubkey}")
                                        continue
                                        
                                    acc_info = acc_data["result"].get("value")
                                    if not acc_info:
                                        #logging.info(f"No value in account info for {acc_pubkey}")
                                        continue
                                        
                                    acc_owner = acc_info.get('owner')
                                    #acc_program = acc_info.get('data', {}).get('program') if isinstance(acc_info.get('data'), dict) else None
                                    
                                    #logging.info(f"Account {idx}:")
                                    #logging.info(f"  Pubkey: {acc_pubkey}")
                                    #logging.info(f"  Owner: {acc_owner}")
                                    #logging.info(f"  Program: {acc_program}")
                                    #logging.info(f"  Data Program: {acc_info.get('data', {}).get('program') if isinstance(acc_info.get('data'), dict) else 'N/A'}")
                                    #logging.info(f"  Signer: {acc.get('signer', False) if not isinstance(acc, str) else False}")
                                    #logging.info(f"  Writable: {acc.get('writable', False) if not isinstance(acc, str) else False}")
                                    #logging.info(f"  Raw Data: {acc_info}")  # Add this for debugging

                                    # Check for verification during the initial fetch
                                    if acc_owner == PUMP_PROGRAM:
                                        logging.info(f"Found account {acc_pubkey} owned by Pump.fun program in tx {sig_info['signature']}")
                                        return True, "pump.fun", acc_pubkey, sig_info['signature']

                            except Exception as e:
                                logging.error(f"Error fetching account info for account {idx}: {str(e)}")
                                continue
                        
                        # Log instruction details
                        instructions = tx_data["result"].get("transaction", {}).get("message", {}).get("instructions", [])
                        #logging.info("\nInstruction Details:")
                        #for idx, inst in enumerate(instructions):
                        #    logging.info(f"Instruction {idx}:")
                        #    logging.info(f"  Program ID: {inst.get('programId', 'N/A')}")
                        #    logging.info(f"  Accounts: {inst.get('accounts', [])}")
                        #    logging.info(f"  Data: {inst.get('data', 'N/A')}")
                        
                        #logging.info("----------------------------------------\n")
                        
                        # Now check each account's owner
                        for acc in accounts:
                            try:
                                acc_pubkey = acc if isinstance(acc, str) else acc.get('pubkey')
                                if not acc_pubkey:
                                    continue
                                    
                                acc_info_params = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "getAccountInfo",
                                    "params": [acc_pubkey, {"encoding": "jsonParsed"}]
                                }
                                
                                async with session.post(SOLANA_RPC_URL, json=acc_info_params) as acc_response:
                                    acc_data = await acc_response.json()
                                    if not acc_data.get("result", {}).get("value"):
                                        continue
                                        
                                    acc_owner = acc_data.get("result", {}).get("value", {}).get("owner")
                                    if not acc_owner:
                                        continue
                                    
                                    if acc_owner == PUMP_PROGRAM:
                                        logging.info(f"Found account {acc_pubkey} owned by Pump.fun program in tx {sig_info['signature']}")
                                        return True, "pump.fun", acc_pubkey, sig_info['signature']
                                    elif acc_owner == RAYDIUM_AMM_PROGRAM or acc_pubkey == RAYDIUM_AMM_PROGRAM:
                                        logging.info(f"Found Raydium AMM interaction in tx {sig_info['signature']}")
                                        return True, "raydium", acc_pubkey, sig_info['signature']
                            except Exception as e:
                                logging.error(f"Error checking account {acc_pubkey}: {str(e)}")
                                continue
                
                logging.info("Pump.fun Token Checks: No accounts owned by Pump.fun program found in recent transactions")
    
    except Exception as e:
        logging.error(f"Error checking transactions: {str(e)}")           
   
    
    return False, None, None, None

async def get_token_details_async(token_address: str, session: aiohttp.ClientSession) -> Tuple[TokenDetails, Optional[str]]:
    try:
        # First get metadata to check update authority
        metadata = await get_metadata(session, token_address)
        #logging.info(f"Metadata response: {metadata}")
        
        # Get token account info to check program features
        acc_info_params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                token_address,
                {"encoding": "jsonParsed"}
            ]
        }
        
        async with session.post(SOLANA_RPC_URL, json=acc_info_params) as response:
            acc_data = await response.json()
            if "result" in acc_data and acc_data["result"] and acc_data["result"]["value"]:
                # Process token data to get security review
                logging.info("Processing token account data for security review")
                token_details, owner_program = process_token_data(acc_data["result"]["value"], token_address)
                
                # Update token details with metadata if available
                if metadata:
                    token_details.name = metadata.get("name", token_details.name)
                    token_details.symbol = metadata.get("symbol", token_details.symbol)
                    token_details.update_authority = metadata.get("update_authority")
                    logging.info(f"Updated token details with metadata - Name: {token_details.name}, Symbol: {token_details.symbol}")
            else:
                logging.warning("No account data found for security review")
                token_details = TokenDetails(
                    name=metadata.get("name", "N/A") if metadata else "N/A",
                    symbol=metadata.get("symbol", "N/A") if metadata else "N/A",
                    address=token_address,
                    owner_program=TOKEN_PROGRAM,
                    freeze_authority=None,
                    update_authority=metadata.get("update_authority") if metadata else None,
                    security_review="FAILED"
                )
                owner_program = TOKEN_PROGRAM
            
        # Check if it's a potential pump token
        is_pump_authority = metadata and metadata.get("update_authority") == "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
        
        if is_pump_authority:
            logging.info(f"Pump.fun Token Checks: Potential pump token detected")
            is_genuine_pump_fun_token, interacted_with, interacting_account, interaction_signature = await verify_pump_token(session, token_address, metadata)
            
            token_details.is_genuine_pump_fun_token = is_genuine_pump_fun_token
            token_details.interacted_with = interacted_with
            token_details.interacting_account = interacting_account
            token_details.interaction_signature = interaction_signature
            token_details.token_graduated_to_raydium = (is_genuine_pump_fun_token and interacted_with == "raydium")
        
        return token_details, owner_program

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return TokenDetails(
            name="ERROR",
            symbol="ERROR",
            address=token_address,
            owner_program="Error",
            freeze_authority=None,
            security_review="FAILED"
        ), None

def process_token_data(account_data: Dict, token_address: str) -> Tuple[TokenDetails, str]:
    """Process the token data and return structured information"""
    # Check if this is a system account
    owner_program = account_data.get('owner', 'N/A')
    if owner_program == "11111111111111111111111111111111":
        return TokenDetails(
            name="N/A",
            symbol="N/A",
            address=token_address,
            owner_program="System Program",
            freeze_authority=None,
            security_review="NOT_A_TOKEN"
        ), owner_program

    # Check if it's a valid token program
    if owner_program not in [TOKEN_PROGRAM, TOKEN_2022_PROGRAM]:
        return TokenDetails(
            name="N/A",
            symbol="N/A",
            address=token_address,
            owner_program=f"{owner_program} (Not a token program)",
            freeze_authority=None,
            security_review="NOT_A_TOKEN"
        ), owner_program

    parsed_data = account_data.get("data", {}).get("parsed", {})
    owner_label = get_owner_program_label(owner_program)
    
    info = parsed_data.get("info", {})
    freeze_authority = info.get('freezeAuthority')
    
    base_details = TokenDetails(
        name=info.get('name', 'N/A'),
        symbol=info.get('symbol', 'N/A'),
        address=token_address,
        owner_program=f"{owner_program} ({owner_label})",
        freeze_authority=freeze_authority,
        extensions=None
    )

    # Set security review based on token program type
    if owner_program == TOKEN_PROGRAM:
        # For standard SPL tokens, PASSED if no freeze authority
        base_details.security_review = "PASSED" if freeze_authority is None else "FAILED"
        logging.info(f"Standard SPL token - Security review: {base_details.security_review}")
    elif owner_program == TOKEN_2022_PROGRAM:
        base_details = process_token_2022_extensions(base_details, info)
    else:
        base_details.security_review = "FAILED"

    return base_details, owner_program

def process_token_2022_extensions(token_details: TokenDetails, info: Dict) -> TokenDetails:
    """Process Token 2022 specific extensions"""
    extensions_info = info.get("extensions", [])
    extensions = Token2022Extensions()

    for extension in extensions_info:
        ext_type = extension.get("extension")
        state = extension.get("state", {})

        if ext_type == "tokenMetadata":
            token_details.name = state.get('name', token_details.name)
            token_details.symbol = state.get('symbol', token_details.symbol)
        elif ext_type == "permanentDelegate":
            extensions.permanent_delegate = state.get("delegate")
        elif ext_type == "transferFeeConfig":
            extensions.transfer_fee = state.get("newerTransferFee", {}).get("transferFeeBasisPoints")
        elif ext_type == "transferHook":
            extensions.transfer_hook_authority = state.get("authority")
        elif ext_type == "confidentialTransferMint":
            extensions.confidential_transfers_authority = state.get("authority")

    token_details.extensions = extensions

    # Set security review for Token 2022
    has_security_features = any([
        token_details.freeze_authority is not None,
        extensions.permanent_delegate is not None,
        extensions.transfer_hook_authority is not None,
        extensions.confidential_transfers_authority is not None,
        extensions.transfer_fee not in [None, 0]
    ])
    
    token_details.security_review = "FAILED" if has_security_features else "PASSED"
    logging.info(f"Token-2022 - Security review: {token_details.security_review}")
    return token_details

async def process_tokens_concurrently(token_addresses: List[str], session: aiohttp.ClientSession) -> List[Dict]:
    """Process multiple tokens concurrently with rate limiting"""
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    total_tokens = len(token_addresses)
    
    async def process_single_token(token_address: str, index: int) -> Dict:
        async with semaphore:
            logging.info(f"Processing token {index + 1}/{total_tokens} - {token_address}")
            details, owner_program = await get_token_details_async(token_address, session)
            if isinstance(details, TokenDetails):
                return {
                    'address': token_address,
                    'status': 'success',
                    **details.to_dict()
                }
            return {
                'address': token_address,
                'status': 'error',
                'error': str(details)
            }
    
    return await asyncio.gather(
        *(process_single_token(addr, idx) for idx, addr in enumerate(token_addresses))
    )

async def main():
    try:
        import sys
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            output_prefix = sys.argv[2] if len(sys.argv) > 2 else "spl_token_details"
            with open(input_file, 'r') as f:
                token_addresses = [line.strip() for line in f if line.strip()]
        else:
            token_address = input("Enter Solana token address: ").strip()
            token_addresses = [token_address]
            output_prefix = "single_token"
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_output = f"{output_prefix}_{timestamp}.json"
        log_output = f"{output_prefix}_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_output),
                logging.StreamHandler()
            ]
        )
        
        async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as session:
            results = await process_tokens_concurrently(token_addresses, session)
            
            # Write outputs
            with open(json_output, 'w') as f:
                json.dump(results, f, indent=2)
            
            logging.info(f"Analysis complete. Check {json_output} for results.")
            
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
