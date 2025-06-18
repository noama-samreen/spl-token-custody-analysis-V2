import streamlit as st
import asyncio
import aiohttp
import json
from spl_token_analysis import get_token_details_async, process_tokens_concurrently
from spl_report_generator import create_pdf
import tempfile
import os
import zipfile

# Initialize session state if not already done
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = None

# Page config
st.set_page_config(
    page_title="Solana Token Security Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.main {
    padding: 2rem;
}
.stButton>button {
    width: 100%;
    background-color: #7047EB;
    color: white;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    margin: 1rem 0;
}
.stButton>button:hover {
    background-color: #5835c4;
}
.json-output {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    font-family: monospace;
    white-space: pre-wrap;
    font-size: 0.85rem;
}
.output-container {
    margin: 2rem 0;
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
}
.header-container {
    text-align: center;
    padding: 2rem 0;
}
.stProgress > div > div > div {
    background-color: #7047EB;
}
.metric-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
}

/* New styles for metrics */
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 600;
}
[data-testid="stMetricLabel"] {
    font-size: 1rem !important;
    font-weight: 500;
    color: #555;
}
[data-testid="stMetricDelta"] {
    font-size: 0.9rem !important;
}

/* Style for long addresses */
[data-testid="stMetricValue"] div {
    font-family: 'Courier New', monospace;
    font-size: 0.85rem !important;
    word-break: break-all;
    line-height: 1.2;
}

/* Adjust overall container padding */
.element-container {
    padding: 0.5rem 0;
}

/* Style JSON display */
.stJson {
    font-size: 0.85rem !important;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)

# Header
st.title("🔍 Solana Token Security Analyzer")
st.markdown("Analyze details of SPL tokens and Token-2022 assets on the Solana blockchain, including tokens from pump.fun.")

# Create tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    # Token address input first
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        token_address = st.text_input("Enter token address", placeholder="Enter Solana token address...")

    # Reviewer information below address
    reviewer_col1, reviewer_col2 = st.columns(2)
    with reviewer_col1:
        reviewer_name = st.text_input("Reviewer Name", value="Noama Samreen", key="reviewer_name")
    with reviewer_col2:
        confirmation_status = st.radio(
            "Conflicts Certification Status",
            options=["Confirmed", "Denied"],
            horizontal=True,
            key="confirmation_status"
        )
    
    # Analyze button at the bottom
    analyze_button = st.button("Analyze Token", key="single_analyze", use_container_width=True)
    
    if analyze_button and token_address:
        with st.spinner("Analyzing token..."):
            async def get_token():
                async with aiohttp.ClientSession() as session:
                    details, _ = await get_token_details_async(token_address, session)
                    return details
            
            try:
                result = asyncio.run(get_token())
                if isinstance(result, str):  # Error message
                    st.error(result)
                else:
                    st.session_state.analysis_results = result.to_dict()
                    
                    # Initialize mitigations in session state if not exists
                    if 'mitigations' not in st.session_state:
                        st.session_state.mitigations = {}
                    
                    # Add a reanalyze button after mitigation inputs
                    if st.button("Apply Mitigations and Reanalyze", key="reanalyze_single"):
                        # Update the token details with mitigation information
                        for check, mitigation in st.session_state.mitigations.items():
                            if 'mitigations' not in st.session_state.analysis_results:
                                st.session_state.analysis_results['mitigations'] = {}
                            st.session_state.analysis_results['mitigations'][check] = {
                                'documentation': mitigation['documentation'],
                                'applied': mitigation['applied'],
                                'links': mitigation['links']
                            }
                        
                        # Recalculate security review status
                        has_unmitigated_risks = False
                        if st.session_state.analysis_results.get('freeze_authority'):
                            check = 'freeze_authority'
                            if check not in st.session_state.mitigations or not st.session_state.mitigations[check]['applied']:
                                has_unmitigated_risks = True
                        
                        if "Token 2022" in st.session_state.analysis_results.get('owner_program', ''):
                            if (st.session_state.analysis_results.get('permanent_delegate') and 
                                ('permanent_delegate' not in st.session_state.mitigations or 
                                not st.session_state.mitigations['permanent_delegate']['applied'])):
                                has_unmitigated_risks = True
                            
                            if (st.session_state.analysis_results.get('transfer_hook') and 
                                ('transfer_hook' not in st.session_state.mitigations or 
                                not st.session_state.mitigations['transfer_hook']['applied'])):
                                has_unmitigated_risks = True
                            
                            if (st.session_state.analysis_results.get('confidential_transfers') and 
                                ('confidential_transfers' not in st.session_state.mitigations or 
                                not st.session_state.mitigations['confidential_transfers']['applied'])):
                                has_unmitigated_risks = True
                            
                            if (st.session_state.analysis_results.get('transaction_fees') not in [None, 0] and 
                                ('transfer_fees' not in st.session_state.mitigations or 
                                not st.session_state.mitigations['transfer_fees']['applied'])):
                                has_unmitigated_risks = True
                        
                        st.session_state.analysis_results['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
                        st.rerun()
            except Exception as e:
                st.error(f"Error analyzing token: {str(e)}")
    
    # Display results if they exist
    if st.session_state.analysis_results:
        result_dict = st.session_state.analysis_results
        # Add reviewer information to the result dictionary
        result_dict['reviewer_name'] = reviewer_name
        result_dict['confirmation_status'] = confirmation_status
        
        # Display key metrics in columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Security Review", result_dict.get('security_review', 'N/A'))
        with col2:
            st.metric("Token Program", "Token-2022" if "Token 2022" in result_dict.get('owner_program', '') else "SPL Token")
        
        # Add mitigation inputs for failing checks
        st.subheader("Security Checks & Mitigations")
        
        # Check for failing conditions and display mitigation inputs
        failing_checks = []
        
        # Check freeze authority
        if result_dict.get('freeze_authority'):
            failing_checks.append('freeze_authority')
            
        # Check Token-2022 specific features
        if "Token 2022" in result_dict.get('owner_program', ''):
            if result_dict.get('permanent_delegate'):
                failing_checks.append('permanent_delegate')
            if result_dict.get('transfer_hook'):
                failing_checks.append('transfer_hook')
            if result_dict.get('confidential_transfers'):
                failing_checks.append('confidential_transfers')
            if result_dict.get('transaction_fees') not in [None, 0]:
                failing_checks.append('transfer_fees')
        
        # Display mitigation inputs for each failing check
        for check in failing_checks:
            with st.expander(f"{check.replace('_', ' ').title()} Check - Failed"):
                # Documentation input
                st.text_area(
                    "Mitigation Documentation",
                    key=f"{check}_documentation",
                    value=st.session_state.mitigations[check]['documentation'],
                    help="Enter the documentation for how this risk is mitigated"
                )
                
                # Mitigation applied checkbox
                st.checkbox(
                    "Mitigation Applied",
                    key=f"{check}_applied",
                    value=st.session_state.mitigations[check]['applied'],
                    help="Check if the mitigation has been applied"
                )
                
                # Links input (one per line)
                st.text_area(
                    "Reference Links (one per line)",
                    key=f"{check}_links",
                    value='\n'.join(st.session_state.mitigations[check]['links']),
                    help="Enter reference links, one per line"
                )
                
                # Update session state when inputs change
                st.session_state.mitigations[check] = {
                    'documentation': st.session_state[f"{check}_documentation"],
                    'applied': st.session_state[f"{check}_applied"],
                    'links': [link for link in st.session_state[f"{check}_links"].split('\n') if link.strip()]
                }
                
                # Update the result dictionary with the mitigation details
                if 'mitigations' not in result_dict:
                    result_dict['mitigations'] = {}
                result_dict['mitigations'][check] = st.session_state.mitigations[check]
        
        # Display authorities in columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Update Authority", result_dict.get('update_authority', 'None'))
        with col2:
            st.metric("Freeze Authority", result_dict.get('freeze_authority', 'None'))
        
        # Display pump.fun specific metrics if applicable
        if "Pump.Fun Mint Authority" in str(result_dict.get('update_authority', '')):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Genuine Pump Fun Token", "Yes" if result_dict.get('is_genuine_pump_fun_token', False) else "No")
            with col2:
                st.metric("Graduated to Raydium", "Yes" if result_dict.get('token_graduated_to_raydium', False) else "No")
            
            if result_dict.get('interacted_with'):
                st.metric("Interaction Type", result_dict.get('interacted_with', 'None'))
                
                if result_dict.get('interacting_account'):
                    with st.expander("Interaction Details"):
                        st.text("Interacting Account")
                        st.code(result_dict.get('interacting_account'))
                        if result_dict.get('interaction_signature'):
                            st.text("Transaction Signature")
                            st.code(result_dict.get('interaction_signature'))
        
        # If token is Token-2022, display extension features
        if "Token 2022" in result_dict.get('owner_program', ''):
            st.subheader("Token-2022 Features")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Permanent Delegate", result_dict.get('permanent_delegate', 'None'))
                st.metric("Transfer Hook", result_dict.get('transfer_hook', 'None'))
            with col2:
                st.metric("Transaction Fees", result_dict.get('transaction_fees', 'None'))
                st.metric("Confidential Transfers", result_dict.get('confidential_transfers', 'None'))
        
        # Display full results
        with st.expander("View Raw Data"):
            st.json(result_dict)
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download JSON",
                data=json.dumps(result_dict, indent=2),
                file_name=f"token_analysis_{token_address}.json",
                mime="application/json"
            )
        
        with col2:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = create_pdf(result_dict, temp_dir)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        "Download PDF",
                        data=pdf_file.read(),
                        file_name=f"token_analysis_{token_address}.pdf",
                        mime="application/pdf"
                    )

with tab2:
    # Reviewer information first
    reviewer_col1, reviewer_col2 = st.columns(2)
    with reviewer_col1:
        reviewer_name = st.text_input("Reviewer Name", value="Noama Samreen", key="batch_reviewer_name")
    with reviewer_col2:
        confirmation_status = st.radio(
            "Conflicts Certification Status",
            options=["Confirmed", "Denied"],
            horizontal=True,
            key="batch_confirmation_status"
        )

    # File upload section
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a text file with one token address per line",
            type="txt",
            help="File should contain one Solana token address per line"
        )
    
    if uploaded_file:
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")
        
        if st.button("Process Batch", key="batch_process", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            async def process_batch():
                async with aiohttp.ClientSession() as session:
                    results = await process_tokens_concurrently(addresses, session)
                    for i, _ in enumerate(results, 1):
                        progress = i / len(addresses)
                        progress_bar.progress(progress)
                        status_text.text(f"Processed {i}/{len(addresses)} tokens")
                    return results
            
            try:
                results = asyncio.run(process_batch())
                # Add reviewer information to each result
                for result in results:
                    result['reviewer_name'] = reviewer_name
                    result['confirmation_status'] = confirmation_status
                st.session_state.batch_results = results
                st.success(f"Successfully processed {len(results)} tokens")
            except Exception as e:
                st.error(f"Error during batch processing: {str(e)}")

    # Display batch results if they exist
    if st.session_state.batch_results:
        results = st.session_state.batch_results
        
        # Display results in a more organized way
        for i, result in enumerate(results):
            with st.expander(f"Token {i+1}: {result.get('name', 'Unknown')} ({result.get('symbol', 'UNKNOWN')})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Security Review", result.get('security_review', 'N/A'))
                    st.metric("Token Program", "Token-2022" if "Token 2022" in result.get('owner_program', '') else "SPL Token")
                with col2:
                    st.metric("Address", result.get('address', 'N/A'))
                    st.metric("Update Authority", result.get('update_authority', 'None'))
                
                # Initialize session state for batch mitigations if not exists
                if 'batch_mitigations' not in st.session_state:
                    st.session_state.batch_mitigations = {}
                if i not in st.session_state.batch_mitigations:
                    st.session_state.batch_mitigations[i] = {}
                
                # Check for failing conditions and display mitigation inputs
                failing_checks = []
                
                # Check freeze authority
                if result.get('freeze_authority'):
                    failing_checks.append('freeze_authority')
                    
                # Check Token-2022 specific features
                if "Token 2022" in result.get('owner_program', ''):
                    if result.get('permanent_delegate'):
                        failing_checks.append('permanent_delegate')
                    if result.get('transfer_hook'):
                        failing_checks.append('transfer_hook')
                    if result.get('confidential_transfers'):
                        failing_checks.append('confidential_transfers')
                    if result.get('transaction_fees') not in [None, 0]:
                        failing_checks.append('transfer_fees')
                
                if failing_checks:
                    st.subheader("Security Checks & Mitigations")
                    # Display mitigation inputs for each failing check
                    for check in failing_checks:
                        with st.expander(f"{check.replace('_', ' ').title()} Check - Failed"):
                            # Documentation input
                            st.text_area(
                                "Mitigation Documentation",
                                key=f"batch_{i}_{check}_documentation",
                                value=st.session_state.batch_mitigations[i].get(check, {}).get('documentation', ''),
                                help="Enter the documentation for how this risk is mitigated"
                            )
                            
                            # Mitigation applied checkbox
                            st.checkbox(
                                "Mitigation Applied",
                                key=f"batch_{i}_{check}_applied",
                                value=st.session_state.batch_mitigations[i].get(check, {}).get('applied', False),
                                help="Check if the mitigation has been applied"
                            )
                            
                            # Links input (one per line)
                            st.text_area(
                                "Reference Links (one per line)",
                                key=f"batch_{i}_{check}_links",
                                value='\n'.join(st.session_state.batch_mitigations[i].get(check, {}).get('links', [])),
                                help="Enter reference links, one per line"
                            )
                            
                            # Update session state when inputs change
                            st.session_state.batch_mitigations[i][check] = {
                                'documentation': st.session_state[f"batch_{i}_{check}_documentation"],
                                'applied': st.session_state[f"batch_{i}_{check}_applied"],
                                'links': [link for link in st.session_state[f"batch_{i}_{check}_links"].split('\n') if link.strip()]
                            }
                        
                        # Add reanalyze button for this token
                        if st.button("Apply Mitigations and Reanalyze", key=f"reanalyze_batch_{i}"):
                            # Update the token details with mitigation information
                            if 'mitigations' not in result:
                                result['mitigations'] = {}
                            
                            for check in failing_checks:
                                result['mitigations'][check] = st.session_state.batch_mitigations[i][check]
                            
                            # Recalculate security review status
                            has_unmitigated_risks = False
                            if result.get('freeze_authority'):
                                check = 'freeze_authority'
                                if check not in st.session_state.batch_mitigations[i] or not st.session_state.batch_mitigations[i][check]['applied']:
                                    has_unmitigated_risks = True
                            
                            if "Token 2022" in result.get('owner_program', ''):
                                if (result.get('permanent_delegate') and 
                                    ('permanent_delegate' not in st.session_state.batch_mitigations[i] or 
                                    not st.session_state.batch_mitigations[i]['permanent_delegate']['applied'])):
                                    has_unmitigated_risks = True
                                
                                if (result.get('transfer_hook') and 
                                    ('transfer_hook' not in st.session_state.batch_mitigations[i] or 
                                    not st.session_state.batch_mitigations[i]['transfer_hook']['applied'])):
                                    has_unmitigated_risks = True
                                
                                if (result.get('confidential_transfers') and 
                                    ('confidential_transfers' not in st.session_state.batch_mitigations[i] or 
                                    not st.session_state.batch_mitigations[i]['confidential_transfers']['applied'])):
                                    has_unmitigated_risks = True
                                
                                if (result.get('transaction_fees') not in [None, 0] and 
                                    ('transfer_fees' not in st.session_state.batch_mitigations[i] or 
                                    not st.session_state.batch_mitigations[i]['transfer_fees']['applied'])):
                                    has_unmitigated_risks = True
                            
                            result['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
                            st.rerun()
                
                # Display Token-2022 features if applicable
                if "Token 2022" in result.get('owner_program', ''):
                    st.subheader("Token-2022 Features")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Permanent Delegate", result.get('permanent_delegate', 'None'))
                        st.metric("Transfer Hook", result.get('transfer_hook', 'None'))
                    with col2:
                        st.metric("Transaction Fees", result.get('transaction_fees', 'None'))
                        st.metric("Confidential Transfers", result.get('confidential_transfers', 'None'))
                
                # Display pump.fun specific metrics if applicable
                if "Pump.Fun Mint Authority" in str(result.get('update_authority', '')):
                    st.subheader("Pump.Fun Details")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Genuine Pump Fun Token", "Yes" if result.get('is_genuine_pump_fun_token', False) else "No")
                    with col2:
                        st.metric("Graduated to Raydium", "Yes" if result.get('token_graduated_to_raydium', False) else "No")
                    
                    if result.get('interacted_with'):
                        st.metric("Interaction Type", result.get('interacted_with', 'None'))
                        if result.get('interacting_account'):
                            with st.expander("Interaction Details"):
                                st.text("Interacting Account")
                                st.code(result.get('interacting_account'))
                                if result.get('interaction_signature'):
                                    st.text("Transaction Signature")
                                    st.code(result.get('interaction_signature'))
        
        # Raw data and download buttons
        with st.expander("View Raw Data"):
            st.json(results)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "Download JSON",
                data=json.dumps(results, indent=2),
                file_name="batch_token_analysis.json",
                mime="application/json"
            )
        
        with col2:
            # Create CSV with update authority
            csv_data = "address,name,symbol,owner_program,update_authority,freeze_authority,security_review\n"
            for r in results:
                if r['status'] == 'success':
                    csv_data += f"{r['address']},{r.get('name', 'N/A')},{r.get('symbol', 'N/A')},"
                    csv_data += f"{r.get('owner_program', 'N/A')},{r.get('update_authority', 'None')},"
                    csv_data += f"{r.get('freeze_authority', 'None')},{r.get('security_review', 'N/A')}\n"
            
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="token_analysis_results.csv",
                mime="text/csv"
            )
        
        with col3:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a ZIP file containing PDFs for each token
                zip_path = os.path.join(temp_dir, "batch_token_analysis.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for result in results:
                        pdf_path = create_pdf(result, temp_dir)
                        zipf.write(pdf_path, os.path.basename(pdf_path))
                
                with open(zip_path, "rb") as zip_file:
                    st.download_button(
                        "Download PDFs",
                        data=zip_file.read(),
                        file_name="batch_token_analysis.zip",
                        mime="application/zip"
                    )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Noama Samreen | 
    <a href='https://github.com/noama-samreen/spl-token-custody-analysis' target='_blank'>GitHub</a>
</div>
""", unsafe_allow_html=True) 
