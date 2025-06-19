# Import required libraries
import streamlit as st
import json
import aiohttp
import asyncio
import os
import tempfile
import zipfile
from datetime import datetime
from spl_token_analysis import get_token_details_async
from spl_report_generator import create_pdf

# Initialize session state if not already done
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = None
if 'token_address' not in st.session_state:
    st.session_state.token_address = None
if 'reviewer_name' not in st.session_state:
    st.session_state.reviewer_name = None
if 'confirmation_status' not in st.session_state:
    st.session_state.confirmation_status = None
if 'mitigations' not in st.session_state:
    st.session_state.mitigations = {}

# Page config
st.set_page_config(
    page_title="Solana Token Security Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
/* Base styles */
.main {
    padding: 0;
    max-width: 1200px;
    margin: 0 auto;
}

/* Security review container */
.security-review-container {
    background-color: white;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    border-left: 4px solid;
    height: 100%;
}

.security-review-container.failed {
    border-left-color: #dc3545;
}

.security-review-container.passed {
    border-left-color: #28a745;
}

.security-review-label {
    color: #6B7280;
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.125rem;
}

.security-review-value {
    color: #111827;
    font-size: 2.25rem;
    font-weight: 700;
    line-height: 1;
}

.security-review-value.failed {
    color: #dc3545;
}

.security-review-value.passed {
    color: #28a745;
}

/* Metric adjustments */
[data-testid="stMetricValue"] {
    font-size: 1.2rem !important;
    line-height: 1.2 !important;
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.875rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 !important;
    padding: 0 !important;
}

/* Remove default padding and margins */
[data-testid="metric-container"] {
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stVerticalBlock"] > div {
    padding: 0 !important;
    margin: 0 !important;
}

/* Address display */
.address-display {
    font-family: 'Courier New', monospace;
    font-size: 0.75rem !important;
    word-break: break-all;
    background: #f8f9fa;
    padding: 0.375rem;
    border-radius: 6px;
    margin: 0.125rem 0 0.5rem 0;
}

/* Authority section */
.authority-section {
    margin-bottom: 0.25rem;
}

/* Security checks section */
.section-header {
    margin: 1rem 0 0.5rem 0;
}

.section-header h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0;
}

.section-description {
    color: #666;
    margin: 0.25rem 0 0 0;
}

/* Column spacing */
[data-testid="column"] {
    padding: 0 !important;
    gap: 0.5rem !important;
}

/* Streamlit element overrides */
.element-container {
    margin: 0 !important;
    padding: 0 !important;
}

.stMarkdown {
    margin: 0 !important;
    padding: 0 !important;
}

/* Title section adjustments */
.title-section {
    padding: 0.5rem 0;
    margin-bottom: 0.5rem;
}

/* Tab adjustments */
.stTabs [data-baseweb="tab-list"] {
    gap: 1rem !important;
    margin-bottom: 0.5rem !important;
}

/* Input field adjustments */
.stTextInput > div {
    margin-bottom: 0.5rem !important;
}

/* Remove extra spacing from block containers */
[data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# Page layout
st.markdown("""
    <div class="title-section">
        <h1><span class="icon">🔍</span> Solana Token Security Analyzer</h1>
        <p>Analyze details of SPL tokens and Token-2022 assets on the Solana blockchain, including tokens from pump.fun.</p>
    </div>
""", unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    # Single token analysis UI
    token_address = st.text_input("Token Address", value=st.session_state.token_address if st.session_state.token_address else "", placeholder="Enter SPL token address...")

    col1, col2 = st.columns(2)
    with col1:
        reviewer_name = st.text_input("Reviewer Name", value=st.session_state.reviewer_name if st.session_state.reviewer_name else "", placeholder="Enter your name...")
    with col2:
        confirmation_status = st.radio("Conflicts Certification Status", ["Confirmed", "Denied"], index=0 if st.session_state.confirmation_status == "Confirmed" else 1)

    # Store current values in session state
    st.session_state.token_address = token_address
    st.session_state.reviewer_name = reviewer_name
    st.session_state.confirmation_status = confirmation_status

    if st.button("Analyze Token", use_container_width=True) or st.session_state.analysis_results:
        if not token_address:
            st.error("Please enter a token address")
        else:
            try:
                # Only run analysis if we don't have results or if this is a new token
                if not st.session_state.analysis_results or st.session_state.token_address != token_address:
                    with st.spinner("Analyzing token..."):
                        # Define async function for token analysis
                        async def get_token():
                            async with aiohttp.ClientSession() as session:
                                details, _ = await get_token_details_async(token_address, session)
                                return details
                        
                        # Run the async function
                        result = asyncio.run(get_token())
                        
                        if isinstance(result, str):  # Error message
                            st.error(result)
                            st.session_state.analysis_results = None
                        else:
                            st.session_state.analysis_results = result.to_dict()
                
                # If we have valid results, display them
                if st.session_state.analysis_results:
                    result_dict = st.session_state.analysis_results
                    
                    # Add reviewer information to the result dictionary
                    result_dict['reviewer_name'] = reviewer_name
                    result_dict['confirmation_status'] = confirmation_status
                    
                    # Check for failing conditions
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
                    
                    # Initialize mitigations for each failing check
                    for check in failing_checks:
                        if check not in st.session_state.mitigations:
                            st.session_state.mitigations[check] = {
                                'documentation': '',
                                'links': [],
                                'applied': False
                            }

                    # Display results if they exist
                    if st.session_state.analysis_results:
                        result_dict = st.session_state.analysis_results
                        
                        # Add reviewer information to the result dictionary
                        result_dict['reviewer_name'] = reviewer_name
                        result_dict['confirmation_status'] = confirmation_status
                        
                        # Create two columns with different widths (40:60 ratio)
                        col1, col2 = st.columns([4, 6])
                        
                        with col1:
                            # Large security review section
                            security_review = result_dict.get('security_review', 'UNKNOWN')
                            st.markdown(f"""
                                <div class="security-review-container {'failed' if security_review == 'FAILED' else 'passed'}">
                                    <div class="security-review-label">SECURITY REVIEW</div>
                                    <div class="security-review-value {'failed' if security_review == 'FAILED' else 'passed'}">{security_review}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            # Token Program (thin)
                            st.metric(
                                "TOKEN PROGRAM",
                                "Token-2022" if "Token 2022" in result_dict.get('owner_program', '') else "SPL Token"
                            )
                            
                            # Freeze Authority (thin)
                            st.markdown('<div class="authority-section">', unsafe_allow_html=True)
                            freeze_auth = result_dict.get('freeze_authority', 'None')
                            st.metric("FREEZE AUTHORITY", "None" if not freeze_auth or freeze_auth == 'None' else "")
                            st.markdown(f'<div class="address-display">{freeze_auth}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Update Authority (thin)
                            st.markdown('<div class="authority-section">', unsafe_allow_html=True)
                            update_auth = result_dict.get('update_authority', 'None')
                            st.metric("UPDATE AUTHORITY", "None" if not update_auth or update_auth == 'None' else "")
                            st.markdown(f'<div class="address-display">{update_auth}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

                            # If token is Token-2022, display extension features
                            if "Token 2022" in result_dict.get('owner_program', ''):
                                # Permanent Delegate
                                st.markdown('<div class="authority-section">', unsafe_allow_html=True)
                                delegate = result_dict.get('permanent_delegate', 'None')
                                st.metric("PERMANENT DELEGATE", "None" if not delegate or delegate == 'None' else "")
                                st.markdown(f'<div class="address-display">{delegate}</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                                # Transfer Hook
                                st.markdown('<div class="authority-section">', unsafe_allow_html=True)
                                hook = result_dict.get('transfer_hook', 'None')
                                st.metric("TRANSFER HOOK", "None" if not hook or hook == 'None' else "")
                                st.markdown(f'<div class="address-display">{hook}</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                                # Confidential Transfers
                                st.markdown('<div class="authority-section">', unsafe_allow_html=True)
                                confidential = result_dict.get('confidential_transfers', 'None')
                                st.metric("CONFIDENTIAL TRANSFERS", "None" if not confidential or confidential == 'None' else "")
                                st.markdown(f'<div class="address-display">{confidential}</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                                # Transaction Fees
                                st.markdown('<div class="authority-section">', unsafe_allow_html=True)
                                fees = result_dict.get('transaction_fees', 'None')
                                st.metric("TRANSACTION FEES", "None" if not fees or fees in ['None', 0] else str(fees))
                                st.markdown(f'<div class="address-display">{fees}</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Add spacing between sections
                        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
                        
                        # Display failing checks and mitigation UI
                        if failing_checks:
                            st.markdown("""
                                <div class="section-header">
                                    <h2>Security Checks & Mitigations</h2>
                                    <p class="section-description">Review and apply mitigations for each failing security check below</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # Display each failing check
                            for check in failing_checks:
                                with st.expander(f"{check.replace('_', ' ').title()} Check - Failed"):
                                    # Documentation input with concise instructions and example
                                    st.markdown("##### Mitigation Documentation")
                                    st.markdown("""
                                        <p style='color: #666; font-size: 0.9rem;'>To add links, include the full URL (http:// or https://) in your text.</p>
                                        <div style='color: #666; font-size: 0.9rem; background-color: #f8f9fa; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.75rem;'>
                                            Example: Asset Issuer's Response: (https://example.com/response)
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    documentation = st.text_area(
                                        "",
                                        key=f"{check}_documentation",
                                        value=st.session_state.mitigations[check].get('documentation', ''),
                                        placeholder="Enter mitigation documentation with any relevant URLs..."
                                    )
                                    
                                    # Update session state with current input values
                                    st.session_state.mitigations[check].update({
                                        'documentation': documentation,
                                        'links': [url for url in documentation.split() if url.startswith(('http://', 'https://'))]
                                    })
                                    
                                    # Status and action section
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        if st.session_state.mitigations[check].get('applied', False):
                                            st.markdown("""
                                                <div class="mitigation-status status-applied">
                                                    ✅ Mitigation Applied
                                                </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.markdown("""
                                                <div class="mitigation-status status-not-applied">
                                                    ❌ Mitigation Not Applied
                                                </div>
                                            """, unsafe_allow_html=True)
                                    
                                    with col2:
                                        if not st.session_state.mitigations[check].get('applied', False):
                                            if st.button("Apply Mitigation", key=f"apply_{check}", use_container_width=True):
                                                if not documentation.strip():
                                                    st.error("Please provide mitigation documentation before applying.")
                                                else:
                                                    st.session_state.mitigations[check]['applied'] = True
                                                    
                                                    # Update the result dictionary with the mitigation details
                                                    if 'mitigations' not in result_dict:
                                                        result_dict['mitigations'] = {}
                                                    result_dict['mitigations'][check] = st.session_state.mitigations[check]
                                                    
                                                    # Recalculate security review status
                                                    has_unmitigated_risks = False
                                                    for c in failing_checks:
                                                        if not st.session_state.mitigations[c].get('applied', False):
                                                            has_unmitigated_risks = True
                                                            break
                                                    
                                                    st.session_state.analysis_results['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
                                                    st.success("✅ Mitigation applied successfully!")
                                                    st.rerun()

                        # Display pump.fun specific metrics if applicable
                        if "Pump.Fun Mint Authority" in str(result_dict.get('update_authority', '')):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Genuine Pump Fun Token", "Yes" if result_dict.get('is_genuine_pump_fun_token', False) else "No")
                            with col2:
                                st.metric("Graduated to Raydium", "Yes" if result_dict.get('token_graduated_to_raydium', False) else "No")
                                
                                if result_dict.get('interacted_with'):
                                    st.metric("Interaction Type", result_dict.get('interacted_with'))
                                    
                                    if result_dict.get('interacting_account'):
                                        with st.expander("Interaction Details"):
                                            st.text("Interacting Account")
                                            st.code(result_dict.get('interacting_account'))
                                            if result_dict.get('interaction_signature'):
                                                st.text("Transaction Signature")
                                                st.code(result_dict.get('interaction_signature'))
                        
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
            except Exception as e:
                st.error(f"Error analyzing token: {str(e)}")

with tab2:
    # Batch processing UI
    st.markdown("### Batch Token Analysis")
    st.markdown("Upload a file containing multiple token addresses to analyze them in batch.")
    
    # Reviewer information
    col1, col2 = st.columns(2)
    with col1:
        batch_reviewer_name = st.text_input("Reviewer Name", value="Noama Samreen", key="batch_reviewer_name")
    with col2:
        batch_confirmation_status = st.radio(
            "Conflicts Certification Status",
            options=["Confirmed", "Denied"],
            horizontal=True,
            key="batch_confirmation_status"
        )

    # File upload
    uploaded_file = st.file_uploader(
        "Upload a text file with token addresses",
        type="txt",
        help="File should contain one Solana token address per line"
    )

    if uploaded_file:
        # Read addresses from file
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")

        if st.button("Process Batch", use_container_width=True):
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
                    if isinstance(result, dict) and result.get('status') == 'success':
                        result['reviewer_name'] = batch_reviewer_name
                        result['confirmation_status'] = batch_confirmation_status
                st.session_state.batch_results = results
                st.success(f"Successfully processed {len(results)} tokens")

                # Display results
                if st.session_state.batch_results:
                    # Download options
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # JSON download
                        st.download_button(
                            "Download JSON",
                            data=json.dumps(results, indent=2),
                            file_name="token_analysis_results.json",
                            mime="application/json"
                        )
                    
                    with col2:
                        # CSV download
                        csv_data = "address,name,symbol,owner_program,update_authority,freeze_authority,security_review\n"
                        for r in results:
                            if isinstance(r, dict) and r.get('status') == 'success':
                                csv_data += f"{r.get('address', '')},{r.get('name', 'N/A')},{r.get('symbol', 'N/A')},"
                                csv_data += f"{r.get('owner_program', 'N/A')},{r.get('update_authority', 'None')},"
                                csv_data += f"{r.get('freeze_authority', 'None')},{r.get('security_review', 'N/A')}\n"
                        
                        st.download_button(
                            "Download CSV",
                            data=csv_data,
                            file_name="token_analysis_results.csv",
                            mime="text/csv"
                        )
                    
                    with col3:
                        # PDF download
                        with tempfile.TemporaryDirectory() as temp_dir:
                            zip_path = os.path.join(temp_dir, "token_analysis_pdfs.zip")
                            with zipfile.ZipFile(zip_path, 'w') as zipf:
                                for result in results:
                                    if isinstance(result, dict) and result.get('status') == 'success':
                                        pdf_path = create_pdf(result, temp_dir)
                                        zipf.write(pdf_path, os.path.basename(pdf_path))
                            
                            with open(zip_path, "rb") as zip_file:
                                st.download_button(
                                    "Download PDFs",
                                    data=zip_file.read(),
                                    file_name="token_analysis_pdfs.zip",
                                    mime="application/zip"
                                )
                    
                    # Display results in expandable sections
                    st.markdown("### Analysis Results")
                    for i, result in enumerate(results):
                        if isinstance(result, dict):
                            with st.expander(f"Token {i+1}: {result.get('address', 'Unknown')}"):
                                st.json(result)

            except Exception as e:
                st.error(f"Error during batch processing: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Made by <a href="https://github.com/noamasamreen" target="_blank">Noama Samreen</a> | 
    <a href="https://github.com/noamasamreen/spl-token-custody-risk-analyzer" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True) 
