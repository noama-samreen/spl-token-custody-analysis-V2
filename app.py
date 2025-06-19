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

# Initialize session state
def init_session_state():
    """Initialize all session state variables if they don't exist."""
    defaults = {
        'analysis_results': None,
        'batch_results': None,
        'token_address': None,
        'reviewer_name': None,
        'confirmation_status': None,
        'mitigations': {}
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# UI Components
def render_custom_styles():
    """Render custom CSS styles for the application."""
    st.markdown("""
    <style>
    /* Base styles */
    .main { padding: 0; max-width: 1200px; margin: 0 auto; }

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
    .security-review-container.failed { border-left-color: #dc3545; }
    .security-review-container.passed { border-left-color: #28a745; }

    /* Security review components */
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
    .security-review-value.failed { color: #dc3545; }
    .security-review-value.passed { color: #28a745; }

    /* Metric adjustments */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stMetricLabel"] {
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="metric-container"] { padding: 0 !important; margin: 0 !important; }

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

    /* Layout adjustments */
    .authority-section { margin-bottom: 0.25rem; }
    .section-header { margin: 1rem 0 0.5rem 0; }
    .section-header h2 {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0;
    }
    .section-description { color: #666; margin: 0.25rem 0 0 0; }
    [data-testid="column"] { padding: 0 !important; gap: 0.5rem !important; }
    .element-container, .stMarkdown { margin: 0 !important; padding: 0 !important; }
    .title-section { padding: 0.5rem 0; margin-bottom: 0.5rem; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    .stTextInput > div { margin-bottom: 0.5rem !important; }
    [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

    /* Mitigation expander styles */
    [data-testid="stExpander"] {
        border: none !important;
        box-shadow: none !important;
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stExpander"] > div:first-child {
        border-radius: 4px !important;
        border: 1px solid #e5e7eb !important;
        background-color: #f8f9fa !important;
    }
    [data-testid="stExpanderContent"] {
        border: 1px solid #e5e7eb !important;
        border-top: none !important;
        border-radius: 0 0 4px 4px !important;
        padding: 0.75rem !important;
    }
    .stTextArea > div > textarea {
        min-height: 100px !important;
        font-size: 0.875rem !important;
    }
    [data-testid="stTextArea"] label {
        font-size: 0.875rem !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    """Render the application header."""
    st.markdown("""
    <div class="title-section">
        <h1><span class="icon">🔍</span> Solana Token Security Analyzer</h1>
        <p>Analyze details of SPL tokens and Token-2022 assets on the Solana blockchain, including tokens from pump.fun.</p>
    </div>
    """, unsafe_allow_html=True)

def render_metric_with_value(label, value, container_class="authority-section", check_name=None):
    """Render a metric with a value and mitigation controls if applicable."""
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    st.metric(label, "")
    st.markdown(f'<div class="address-display">{value}</div>', unsafe_allow_html=True)
    
    # Add mitigation controls if this is a failing check
    if check_name and value not in [None, 'None', '', '0', 0]:
        with st.expander(f"{label.title()} Check - Failed", expanded=False):
            # Initialize mitigation state if needed
            if check_name not in st.session_state.mitigations:
                st.session_state.mitigations[check_name] = {
                    'documentation': '',
                    'links': [],
                    'applied': False
                }
            
            # Mitigation documentation input
            documentation = st.text_area(
                "Mitigation Documentation",
                value=st.session_state.mitigations[check_name].get('documentation', ''),
                placeholder="Enter mitigation documentation with any relevant URLs...",
                key=f"{check_name}_documentation",
                help="To add links, include the full URL (http:// or https://) in your text."
            )
            
            # Update mitigation state
            st.session_state.mitigations[check_name].update({
                'documentation': documentation,
                'links': [url for url in documentation.split() if url.startswith(('http://', 'https://'))]
            })
            
            # Status and apply button in columns
            col1, col2 = st.columns([3, 1])
            with col1:
                status_html = """
                    <div style="color: #28a745; font-weight: bold;">✅ Mitigation Applied</div>
                """ if st.session_state.mitigations[check_name].get('applied', False) else """
                    <div style="color: #dc3545; font-weight: bold;">❌ Mitigation Not Applied</div>
                """
                st.markdown(status_html, unsafe_allow_html=True)
            
            with col2:
                if not st.session_state.mitigations[check_name].get('applied', False):
                    if st.button("Apply", key=f"apply_{check_name}", use_container_width=True):
                        if documentation.strip():
                            st.session_state.mitigations[check_name]['applied'] = True
                            
                            # Update the result dict in session state
                            if 'analysis_results' in st.session_state:
                                if 'mitigations' not in st.session_state.analysis_results:
                                    st.session_state.analysis_results['mitigations'] = {}
                                st.session_state.analysis_results['mitigations'][check_name] = {
                                    'documentation': documentation,
                                    'applied': True
                                }
                                
                                # Calculate new security review status
                                has_unmitigated_risks = False
                                
                                # Check freeze authority
                                if st.session_state.analysis_results.get('freeze_authority'):
                                    if not st.session_state.mitigations.get('freeze_authority', {}).get('applied', False):
                                        has_unmitigated_risks = True
                                
                                # Check Token 2022 features if present
                                if "Token 2022" in st.session_state.analysis_results.get('owner_program', ''):
                                    for feature in ['permanent_delegate', 'transfer_hook', 'confidential_transfers', 'transaction_fees']:
                                        value = st.session_state.analysis_results.get(feature)
                                        if value not in [None, 0, 'None']:
                                            if not st.session_state.mitigations.get(feature, {}).get('applied', False):
                                                has_unmitigated_risks = True
                                                break
                                
                                st.session_state.analysis_results['security_review'] = 'FAILED' if has_unmitigated_risks else 'PASSED'
                            
                            st.rerun()
                        else:
                            st.error("Please provide mitigation documentation before applying.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_security_review(status):
    """Render the security review status container."""
    st.markdown(f"""
        <div class="security-review-container {'failed' if status == 'FAILED' else 'passed'}">
            <div class="security-review-label">SECURITY REVIEW</div>
            <div class="security-review-value {'failed' if status == 'FAILED' else 'passed'}">{status}</div>
        </div>
    """, unsafe_allow_html=True)

def render_token_2022_features(result_dict):
    """Render Token-2022 specific features."""
    if "Token 2022" in result_dict.get('owner_program', ''):
        features = {
            'PERMANENT DELEGATE': result_dict.get('permanent_delegate', 'None'),
            'TRANSFER HOOK': result_dict.get('transfer_hook', 'None'),
            'CONFIDENTIAL TRANSFERS': result_dict.get('confidential_transfers', 'None'),
            'TRANSACTION FEES': result_dict.get('transaction_fees', 'None')
        }
        for label, value in features.items():
            render_metric_with_value(label, value)

def render_pump_fun_metrics(result_dict):
    """Render pump.fun specific metrics if applicable."""
    if "Pump.Fun Mint Authority" in str(result_dict.get('update_authority', '')):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Genuine Pump Fun Token", 
                     "Yes" if result_dict.get('is_genuine_pump_fun_token', False) else "No")
        with col2:
            st.metric("Graduated to Raydium", 
                     "Yes" if result_dict.get('token_graduated_to_raydium', False) else "No")
            
            if result_dict.get('interacted_with'):
                st.metric("Interaction Type", result_dict.get('interacted_with'))
                if result_dict.get('interacting_account'):
                    with st.expander("Interaction Details"):
                        st.text("Interacting Account")
                        st.code(result_dict.get('interacting_account'))
                        if result_dict.get('interaction_signature'):
                            st.text("Transaction Signature")
                            st.code(result_dict.get('interaction_signature'))

async def analyze_token(token_address):
    """Analyze a single token address."""
    async with aiohttp.ClientSession() as session:
        details, _ = await get_token_details_async(token_address, session)
        return details

async def process_tokens_concurrently(addresses, session):
    """Process multiple token addresses concurrently."""
    tasks = [get_token_details_async(addr, session) for addr in addresses]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r[0] if not isinstance(r, Exception) else {'status': 'error', 'error': str(r)} for r in results]

def render_download_buttons(result_dict, token_address):
    """Render JSON and PDF download buttons."""
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

def render_batch_download_buttons(results):
    """Render batch analysis download buttons."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            "Download JSON",
            data=json.dumps(results, indent=2),
            file_name="token_analysis_results.json",
            mime="application/json"
        )
    
    with col2:
        csv_data = generate_csv_data(results)
        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name="token_analysis_results.csv",
            mime="text/csv"
        )
    
    with col3:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = create_pdf_zip(results, temp_dir)
            with open(zip_path, "rb") as zip_file:
                st.download_button(
                    "Download PDFs",
                    data=zip_file.read(),
                    file_name="token_analysis_pdfs.zip",
                    mime="application/zip"
                )

def generate_csv_data(results):
    """Generate CSV data from analysis results."""
    csv_data = "address,name,symbol,owner_program,update_authority,freeze_authority,security_review\n"
    for r in results:
        if isinstance(r, dict) and r.get('status') == 'success':
            csv_data += f"{r.get('address', '')},{r.get('name', 'N/A')},{r.get('symbol', 'N/A')},"
            csv_data += f"{r.get('owner_program', 'N/A')},{r.get('update_authority', 'None')},"
            csv_data += f"{r.get('freeze_authority', 'None')},{r.get('security_review', 'N/A')}\n"
    return csv_data

def create_pdf_zip(results, temp_dir):
    """Create a ZIP file containing PDFs for all analysis results."""
    zip_path = os.path.join(temp_dir, "token_analysis_pdfs.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for result in results:
            if isinstance(result, dict) and result.get('status') == 'success':
                pdf_path = create_pdf(result, temp_dir)
                zipf.write(pdf_path, os.path.basename(pdf_path))
    return zip_path

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Solana Token Security Analyzer",
        page_icon="🔍",
        layout="wide"
    )
    
    init_session_state()
    render_custom_styles()
    render_header()
    
    tab1, tab2 = st.tabs(["Single Token", "Batch Process"])
    
    with tab1:
        render_single_token_analysis()
    
    with tab2:
        render_batch_analysis()
    
    render_footer()

def render_single_token_analysis():
    """Render the single token analysis interface."""
    token_address = st.text_input(
        "Token Address",
        value=st.session_state.token_address or "",
        placeholder="Enter SPL token address..."
    )

    col1, col2 = st.columns(2)
    with col1:
        reviewer_name = st.text_input(
            "Reviewer Name",
            value=st.session_state.reviewer_name or "",
            placeholder="Enter your name..."
        )
    with col2:
        confirmation_status = st.radio(
            "Conflicts Certification Status",
            ["Confirmed", "Denied"],
            index=0 if st.session_state.confirmation_status == "Confirmed" else 1
        )

    update_session_state(token_address, reviewer_name, confirmation_status)
    
    if st.button("Analyze Token", use_container_width=True) or st.session_state.analysis_results:
        process_single_token_analysis(token_address)

def update_session_state(token_address, reviewer_name, confirmation_status):
    """Update session state with current values."""
    st.session_state.token_address = token_address
    st.session_state.reviewer_name = reviewer_name
    st.session_state.confirmation_status = confirmation_status

def process_single_token_analysis(token_address):
    """Process the analysis of a single token."""
    if not token_address:
        st.error("Please enter a token address")
        return

    try:
        if not st.session_state.analysis_results or st.session_state.token_address != token_address:
            with st.spinner("Analyzing token..."):
                result = asyncio.run(analyze_token(token_address))
                
                if isinstance(result, str):
                    st.error(result)
                    st.session_state.analysis_results = None
                    return
                
                st.session_state.analysis_results = result.to_dict()
        
        if st.session_state.analysis_results:
            display_analysis_results(st.session_state.analysis_results)
    
    except Exception as e:
        st.error(f"Error analyzing token: {str(e)}")

def display_analysis_results(result_dict):
    """Display the analysis results."""
    result_dict.update({
        'reviewer_name': st.session_state.reviewer_name,
        'confirmation_status': st.session_state.confirmation_status
    })
    
    col1, col2 = st.columns([4, 6])
    with col1:
        render_security_review(result_dict.get('security_review', 'UNKNOWN'))
    
    with col2:
        render_metric_with_value("TOKEN PROGRAM",
            "Token-2022" if "Token 2022" in result_dict.get('owner_program', '') else "SPL Token")
        render_metric_with_value("FREEZE AUTHORITY",
            result_dict.get('freeze_authority', 'None'),
            check_name='freeze_authority')
        render_metric_with_value("UPDATE AUTHORITY",
            result_dict.get('update_authority', 'None'))
        
        # Render Token-2022 specific features with mitigation controls
        if "Token 2022" in result_dict.get('owner_program', ''):
            features = {
                'PERMANENT DELEGATE': ('permanent_delegate', result_dict.get('permanent_delegate', 'None')),
                'TRANSFER HOOK': ('transfer_hook', result_dict.get('transfer_hook', 'None')),
                'CONFIDENTIAL TRANSFERS': ('confidential_transfers', result_dict.get('confidential_transfers', 'None')),
                'TRANSACTION FEES': ('transaction_fees', result_dict.get('transaction_fees', 'None'))
            }
            for label, (check_name, value) in features.items():
                render_metric_with_value(label, value, check_name=check_name)
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    render_pump_fun_metrics(result_dict)
    
    with st.expander("View Raw Data"):
        st.json(result_dict)
    
    render_download_buttons(result_dict, st.session_state.token_address)

def render_batch_analysis():
    """Render the batch analysis interface."""
    st.markdown("### Batch Token Analysis")
    st.markdown("Upload a file containing multiple token addresses to analyze them in batch.")
    
    batch_reviewer_name = st.text_input("Reviewer Name", value="Noama Samreen", key="batch_reviewer_name")
    batch_confirmation_status = st.radio(
        "Conflicts Certification Status",
        options=["Confirmed", "Denied"],
        horizontal=True,
        key="batch_confirmation_status"
    )
    
    uploaded_file = st.file_uploader(
        "Upload a text file with token addresses",
        type="txt",
        help="File should contain one Solana token address per line"
    )
    
    if uploaded_file:
        process_batch_upload(uploaded_file, batch_reviewer_name, batch_confirmation_status)

def process_batch_upload(uploaded_file, batch_reviewer_name, batch_confirmation_status):
    """Process a batch upload of token addresses."""
    addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
    st.info(f"Found {len(addresses)} addresses in file")
    
    if st.button("Process Batch", use_container_width=True):
        process_batch_analysis(addresses, batch_reviewer_name, batch_confirmation_status)

def process_batch_analysis(addresses, batch_reviewer_name, batch_confirmation_status):
    """Process batch analysis of multiple tokens."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        results = asyncio.run(process_batch_tokens(
            addresses, progress_bar, status_text,
            batch_reviewer_name, batch_confirmation_status
        ))
        
        st.session_state.batch_results = results
        st.success(f"Successfully processed {len(results)} tokens")
        
        if st.session_state.batch_results:
            render_batch_results(results)
    
    except Exception as e:
        st.error(f"Error during batch processing: {str(e)}")

async def process_batch_tokens(addresses, progress_bar, status_text,
                             batch_reviewer_name, batch_confirmation_status):
    """Process multiple tokens concurrently with progress updates."""
    async with aiohttp.ClientSession() as session:
        results = []
        for i, address in enumerate(addresses, 1):
            result = await get_token_details_async(address, session)
            if isinstance(result[0], dict):
                result[0].update({
                    'reviewer_name': batch_reviewer_name,
                    'confirmation_status': batch_confirmation_status
                })
            results.append(result[0])
            
            progress = i / len(addresses)
            progress_bar.progress(progress)
            status_text.text(f"Processed {i}/{len(addresses)} tokens")
        
        return results

def render_batch_results(results):
    """Render the batch analysis results."""
    render_batch_download_buttons(results)
    
    st.markdown("### Analysis Results")
    for i, result in enumerate(results):
        if isinstance(result, dict):
            with st.expander(f"Token {i+1}: {result.get('address', 'Unknown')}"):
                st.json(result)

def render_footer():
    """Render the application footer."""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        Made by <a href="https://github.com/noamasamreen" target="_blank">Noama Samreen</a> | 
        <a href="https://github.com/noamasamreen/spl-token-custody-risk-analyzer" target="_blank">GitHub</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 
