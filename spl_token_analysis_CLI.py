import argparse
import asyncio
import aiohttp
from spl_token_analysis import get_token_details_async, process_tokens_concurrently
from spl_report_generator import create_pdf
import os
import json
import logging
from datetime import datetime

async def generate_single_report(token_address: str, output_dir: str = None, mitigation_file: str = None):
    """Generate a security report for a single token address"""
    if not output_dir:
        output_dir = os.getcwd()
    
    # Load mitigations if provided
    mitigations = {}
    if mitigation_file:
        try:
            with open(mitigation_file, 'r') as f:
                mitigations = json.load(f)
        except Exception as e:
            print(f"Error loading mitigation file: {e}")
            return
    
    async with aiohttp.ClientSession() as session:
        token_details, _ = await get_token_details_async(token_address, session)
        
        if isinstance(token_details, str):
            print(f"Error: {token_details}")
            return
            
        result_dict = token_details.to_dict()
        
        # Apply mitigations if available
        if token_address in mitigations:
            token_mitigations = mitigations[token_address]
            if 'mitigations' not in result_dict:
                result_dict['mitigations'] = {}
            
            for check, mitigation in token_mitigations.items():
                if isinstance(mitigation, dict):
                    result_dict['mitigations'][check] = {
                        'documentation': mitigation.get('documentation', ''),
                        'applied': mitigation.get('applied', False)
                    }
            
            # Recalculate security review based on mitigations
            has_unmitigated_risks = False
            if result_dict.get('freeze_authority'):
                if not result_dict['mitigations'].get('freeze_authority', {}).get('applied', False):
                    has_unmitigated_risks = True
            
            if "Token 2022" in result_dict.get('owner_program', ''):
                for feature in ['permanent_delegate', 'transfer_hook', 'confidential_transfers', 'transaction_fees']:
                    value = result_dict.get(feature)
                    if value not in [None, 0, 'None']:
                        if not result_dict['mitigations'].get(feature, {}).get('applied', False):
                            has_unmitigated_risks = True
                            break
            
            result_dict['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
        
        result_dict['reviewer_name'] = 'SPL-AUTOMATION'
        result_dict['confirmation_status'] = 'Confirmed'
        
        try:
            pdf_path = create_pdf(result_dict, output_dir)
            print(f"\nReport generated successfully: {pdf_path}")
            
            # Save JSON result
            json_output = f"token_analysis_{token_address}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(os.path.join(output_dir, json_output), 'w') as f:
                json.dump(result_dict, f, indent=2)
            print(f"Analysis results saved to: {json_output}")
            
        except Exception as e:
            print(f"Error generating report: {e}")

async def generate_batch_reports(input_file: str, output_dir: str = None, mitigation_file: str = None):
    """Generate security reports for multiple tokens from input file"""
    if not output_dir:
        output_dir = os.getcwd()
    
    # Load mitigations if provided
    mitigations = {}
    if mitigation_file:
        try:
            with open(mitigation_file, 'r') as f:
                mitigations = json.load(f)
            print(f"Loaded mitigations from {mitigation_file}")
        except Exception as e:
            print(f"Error loading mitigation file: {e}")
            return
        
    try:
        with open(input_file, 'r') as f:
            token_addresses = [line.strip() for line in f if line.strip()]
            
        print(f"\nProcessing {len(token_addresses)} tokens...")
        
        async with aiohttp.ClientSession() as session:
            results = await process_tokens_concurrently(token_addresses, session)
            
            # Generate timestamp for batch processing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Apply mitigations and generate reports
            for result in results:
                if result['status'] == 'success':
                    token_address = result['address']
                    result_dict = result.copy()
                    
                    # Apply mitigations if available
                    if token_address in mitigations:
                        token_mitigations = mitigations[token_address]
                        if 'mitigations' not in result_dict:
                            result_dict['mitigations'] = {}
                        
                        for check, mitigation in token_mitigations.items():
                            if isinstance(mitigation, dict):
                                result_dict['mitigations'][check] = {
                                    'documentation': mitigation.get('documentation', ''),
                                    'applied': mitigation.get('applied', False)
                                }
                        
                        # Recalculate security review
                        has_unmitigated_risks = False
                        if result_dict.get('freeze_authority'):
                            if not result_dict['mitigations'].get('freeze_authority', {}).get('applied', False):
                                has_unmitigated_risks = True
                        
                        if "Token 2022" in result_dict.get('owner_program', ''):
                            for feature in ['permanent_delegate', 'transfer_hook', 'confidential_transfers', 'transaction_fees']:
                                value = result_dict.get(feature)
                                if value not in [None, 0, 'None']:
                                    if not result_dict['mitigations'].get(feature, {}).get('applied', False):
                                        has_unmitigated_risks = True
                                        break
                        
                        result_dict['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
                    
                    result_dict['reviewer_name'] = 'SPL-AUTOMATION'
                    result_dict['confirmation_status'] = 'Confirmed'
                    
                    try:
                        pdf_path = create_pdf(result_dict, output_dir)
                        print(f"Generated report: {pdf_path}")
                    except Exception as e:
                        print(f"Error generating PDF for {token_address}: {e}")
                else:
                    print(f"Skipping PDF generation for {result['address']}: {result['error']}")
            
            # Save JSON results
            json_output = f"batch_results_{timestamp}.json"
            with open(os.path.join(output_dir, json_output), 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nBatch processing complete. Results saved to {json_output}")
            
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except Exception as e:
        print(f"Error during batch processing: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate Solana Token Security Report(s)')
    parser.add_argument('input', help='Token address or path to input file with token addresses')
    parser.add_argument('--batch', '-b', action='store_true', help='Process input as a batch file')
    parser.add_argument('--output', '-o', help='Output directory for the report(s)')
    parser.add_argument('--mitigation', '-m', help='JSON file containing mitigation documentation')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if args.output:
        os.makedirs(args.output, exist_ok=True)
    
    if args.batch:
        print(f"\nStarting batch processing from file: {args.input}")
        asyncio.run(generate_batch_reports(args.input, args.output, args.mitigation))
    else:
        print(f"\nGenerating security report for token: {args.input}")
        asyncio.run(generate_single_report(args.input, args.output, args.mitigation))

if __name__ == "__main__":
    main()
