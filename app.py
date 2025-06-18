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
/* Base styles and resets */
.main {
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
}

/* Title section */
.title-section {
    padding: 2rem 0;
    margin-bottom: 1rem;
}

.title-section h1 {
    color: #2D3748;
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.title-section h1 .icon {
    font-size: 2rem;
}

.title-section p {
    color: #4A5568;
    font-size: 1.1rem;
    margin: 1rem 0;
    font-weight: 400;
    max-width: 800px;
}

/* Tab styling */
.stTabs {
    margin-top: 1rem;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 2rem;
}

.stTabs [data-baseweb="tab"] {
    padding: 1rem 0;
    font-size: 1rem;
    font-weight: 500;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: #FF4B4B;
    height: 3px;
}

/* Input fields */
.stTextInput > div > div > input {
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 0.75rem;
    font-size: 0.95rem;
    transition: all 0.2s ease;
}

.stTextInput > div > div > input:focus {
    border-color: #7047EB;
    box-shadow: 0 0 0 2px rgba(112, 71, 235, 0.1);
}

/* Section headers */
.section-header {
    margin: 2rem 0 1rem 0;
    padding: 1rem;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.section-header h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 0.5rem;
}

.section-description {
    font-size: 1rem;
    color: #666;
    margin-bottom: 0;
}

/* Mitigation sections */
.mitigation-section {
    background-color: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    border: 1px solid #f0f0f0;
}

.mitigation-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 0.5rem;
}

.mitigation-description {
    font-size: 0.9rem;
    color: #666;
    margin-bottom: 1.5rem;
}

/* Status indicators */
.mitigation-status {
    display: inline-flex;
    align-items: center;
    padding: 0.75rem 1.25rem;
    border-radius: 999px;
    font-size: 0.9rem;
    font-weight: 500;
    margin: 0.5rem 0;
    transition: all 0.2s ease;
}

.status-applied {
    background-color: #e6f4ea;
    color: #1e4620;
    border: 1px solid #a8dab5;
}

.status-not-applied {
    background-color: #fef7e6;
    color: #8c6c1f;
    border: 1px solid #fbe7a8;
}

/* Input fields in mitigation */
.stTextArea > div > div > textarea {
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    padding: 0.75rem;
    font-size: 0.95rem;
    min-height: 120px;
    background-color: #f8f9fa;
    transition: all 0.2s ease;
}

.stTextArea > div > div > textarea:focus {
    border-color: #7047EB;
    box-shadow: 0 0 0 2px rgba(112, 71, 235, 0.1);
    background-color: white;
}

/* Token address section */
.token-address {
    background-color: #f8f9fa;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 2rem;
    border: 1px solid #e0e0e0;
}

/* Reviewer section */
.reviewer-section {
    display: flex;
    gap: 2rem;
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* Analyze button */
.stButton > button {
    width: 100%;
    background: linear-gradient(45deg, #7047EB, #9747FF);
    color: white;
    border: none;
    padding: 1rem;
    font-size: 1rem;
    font-weight: 600;
    border-radius: 12px;
    margin: 1rem 0;
    transition: all 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(112, 71, 235, 0.2);
    background: linear-gradient(45deg, #6037DB, #8637EF);
}

/* Metrics styling */
.metric-container {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    border: 1px solid #f0f0f0;
    height: 100%;
    transition: all 0.2s ease;
}

.metric-container:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.metric-container.status-failed {
    border-left: 4px solid #dc3545;
}

.metric-container.status-passed {
    border-left: 4px solid #28a745;
}

.metric-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.75rem;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1a1a1a;
    line-height: 1.2;
}

/* Authority addresses */
[data-testid="stMetricValue"] div {
    font-family: 'SF Mono', 'Roboto Mono', monospace;
    font-size: 0.85rem !important;
    background: #f8f9fa;
    padding: 0.5rem;
    border-radius: 6px;
    color: #444;
    word-break: break-all;
    line-height: 1.4;
}

/* Raw data viewer */
.streamlit-expanderHeader {
    background-color: white !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    padding: 1rem !important;
    margin: 0.5rem 0 !important;
    font-weight: 600 !important;
    color: #1a1a1a !important;
    transition: all 0.2s ease;
}

.streamlit-expanderHeader:hover {
    background-color: #f8f9fa !important;
}

.streamlit-expanderContent {
    border: 1px solid #e0e0e0 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 1.5rem !important;
}

/* Download buttons */
.stDownloadButton > button {
    background-color: white;
    color: #1a1a1a;
    border: 1px solid #e0e0e0;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.stDownloadButton > button:hover {
    background-color: #f8f9fa;
    border-color: #7047EB;
    color: #7047EB;
}

/* Radio buttons */
.stRadio > div {
    padding: 1rem;
    background: white;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}

/* Footer */
footer {
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #e0e0e0;
    text-align: center;
    color: #666;
}

footer a {
    color: #7047EB;
    text-decoration: none;
    font-weight: 500;
}

footer a:hover {
    text-decoration: underline;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main {
        padding: 1rem;
    }
    
    .metric-container {
        margin-bottom: 1rem;
    }
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

# Tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    # Token input and reviewer info
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
                                st.markdown(f"""
                                    <div class="mitigation-section">
                                        <div class="mitigation-header">{check.replace('_', ' ').title()} Mitigation</div>
                                        <p class="mitigation-description">Document and apply mitigation for this security check</p>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # Documentation input
                                st.markdown("##### Mitigation Documentation")
                                documentation = st.text_area(
                                    "",
                                    key=f"{check}_documentation",
                                    value=st.session_state.mitigations[check].get('documentation', ''),
                                    help="Enter the documentation for how this risk is mitigated",
                                    placeholder="Enter detailed documentation about how this risk is mitigated..."
                                )
                                
                                # Links input
                                st.markdown("##### Reference Links")
                                links_text = st.text_area(
                                    "",
                                    key=f"{check}_links",
                                    value='\n'.join(st.session_state.mitigations[check].get('links', [])),
                                    help="Enter reference links, one per line",
                                    placeholder="Enter reference links, one per line..."
                                )
                                
                                # Update session state with current input values
                                st.session_state.mitigations[check].update({
                                    'documentation': documentation,
                                    'links': [link for link in links_text.split('\n') if link.strip()]
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

                    # Display results if they exist
                    if st.session_state.analysis_results:
                        result_dict = st.session_state.analysis_results
                        # Add reviewer information to the result dictionary
                        result_dict['reviewer_name'] = reviewer_name
                        result_dict['confirmation_status'] = confirmation_status
                        
                        # Display key metrics in columns
                        col1, col2 = st.columns(2)
                        with col1:
                            if result_dict.get('security_review') == 'FAILED':
                                st.markdown("""
                                    <div class="metric-container status-failed">
                                        <div class="metric-label">Security Review</div>
                                        <div class="metric-value">FAILED</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown("""
                                    <div class="metric-container status-passed">
                                        <div class="metric-label">Security Review</div>
                                        <div class="metric-value">PASSED</div>
                                    </div>
                                """, unsafe_allow_html=True)
                        with col2:
                            st.markdown(f"""
                                <div class="metric-container">
                                    <div class="metric-label">Token Program</div>
                                    <div class="metric-value">{"Token-2022" if "Token 2022" in result_dict.get('owner_program', '') else "SPL Token"}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # Display authorities in columns
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Update Authority", result_dict.get('update_authority'))
                        with col2:
                            st.metric("Freeze Authority", result_dict.get('freeze_authority') or 'None')
                        
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
                        
                        # If token is Token-2022, display extension features
                        if "Token 2022" in result_dict.get('owner_program', ''):
                            st.subheader("Token-2022 Features")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Permanent Delegate", result_dict.get('permanent_delegate') or 'None')
                                st.metric("Transfer Hook", result_dict.get('transfer_hook') or 'None')
                            with col2:
                                st.metric("Transaction Fees", result_dict.get('transaction_fees') or 'None')
                                st.metric("Confidential Transfers", result_dict.get('confidential_transfers') or 'None')
                        
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
    st.markdown("Batch processing functionality coming soon...")

# Footer
st.markdown("""
<footer>
    <p>Made by <a href="https://github.com/noamasamreen" target="_blank">Noama Samreen</a> | <a href="https://github.com/noamasamreen/spl-token-custody-risk-analyzer" target="_blank">GitHub</a></p>
</footer>
""", unsafe_allow_html=True) 
