import argparse
import asyncio
import aiohttp
from spl_token_analysis import get_token_details_async, process_tokens_concurrently
from spl_report_generator import create_pdf
import os
import json
from datetime import datetime

async def generate_single_report(token_address: str, output_dir: str = None):
    """Generate a security report for a single token address"""
    if not output_dir:
        output_dir = os.getcwd()
    
    async with aiohttp.ClientSession() as session:
        token_details, _ = await get_token_details_async(token_address, session)
        
        if isinstance(token_details, str):
            print(f"Error: {token_details}")
            return
            
        result_dict = token_details.to_dict()
        result_dict['reviewer_name'] = 'SPL-AUTOMATION'
        result_dict['confirmation_status'] = 'Confirmed'
        
        try:
            pdf_path = create_pdf(result_dict, output_dir)
            print(f"\nReport generated successfully: {pdf_path}")
        except Exception as e:
            print(f"Error generating PDF report: {e}")

async def generate_batch_reports(input_file: str, output_dir: str = None):
    """Generate security reports for multiple tokens from input file"""
    if not output_dir:
        output_dir = os.getcwd()
        
    try:
        with open(input_file, 'r') as f:
            token_addresses = [line.strip() for line in f if line.strip()]
            
        print(f"\nProcessing {len(token_addresses)} tokens...")
        
        async with aiohttp.ClientSession() as session:
            results = await process_tokens_concurrently(token_addresses, session)
            
            # Generate timestamp for batch processing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save JSON results
            json_output = f"batch_results_{timestamp}.json"
            with open(os.path.join(output_dir, json_output), 'w') as f:
                json.dump(results, f, indent=2)
            
            # Generate PDF reports for each token
            for result in results:
                if result['status'] == 'success':
                    result_dict = result.copy()
                    result_dict['reviewer_name'] = 'SPL-AUTOMATION'
                    result_dict['confirmation_status'] = 'Confirmed'
                    try:
                        pdf_path = create_pdf(result_dict, output_dir)
                        print(f"Generated report: {pdf_path}")
                    except Exception as e:
                        print(f"Error generating PDF for {result['address']}: {e}")
                else:
                    print(f"Skipping PDF generation for {result['address']}: {result['error']}")
                    
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
    
    args = parser.parse_args()
    
    if args.batch:
        print(f"\nStarting batch processing from file: {args.input}")
        asyncio.run(generate_batch_reports(args.input, args.output))
    else:
        print(f"\nGenerating security report for token: {args.input}")
        asyncio.run(generate_single_report(args.input, args.output))

if __name__ == "__main__":
    main() 
