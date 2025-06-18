import os
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageTemplate
from reportlab.pdfgen import canvas

def create_styles():
    styles = getSampleStyleSheet()
    
    # Title style with better spacing and alignment
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Cell style with better formatting
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10,
        fontName='Helvetica',
        leading=14  # Line spacing
    )
    
    # Context style with better readability
    context_style = ParagraphStyle(
        'CustomContext',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=16,  # Increased line spacing
        alignment=4,  # Justified text
        fontName='Helvetica',
        leftIndent=0,  # No left indent
        rightIndent=0  # No right indent
    )
    
    # Header style for table headers
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.black,
        alignment=0  # Left alignment
    )
    
    # Risk Findings styles
    risk_header_style = ParagraphStyle(
        'RiskHeader',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=15,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        alignment=0,  # Left alignment
        leading=20
    )
    
    risk_subheader_style = ParagraphStyle(
        'RiskSubHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        alignment=0,  # Left alignment
        leading=18
    )
    
    risk_body_style = ParagraphStyle(
        'RiskBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leading=14,
        alignment=0,  # Changed from 4 (justified) to 0 (left)
        fontName='Helvetica',
        leftIndent=0
    )

    return styles, title_style, cell_style, context_style, header_style, risk_header_style, risk_subheader_style, risk_body_style

def create_basic_table(data, cell_style):
    """Create and style the basic information table"""
    # Reduced table width (adjusted from 6 inches to 5 inches total)
    table = Table(data, colWidths=[1.2*inch, 3.8*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return table

def create_additional_table(data, cell_style):
    """Create and style the additional fields table"""
    table = Table(data, colWidths=[2.5*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),  # Bold header row
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),  # Light gray header
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f9f9f9')]),  # Alternating rows
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f8f8f8')),  # Slight emphasis on last row
    ]))
    return table

def create_header(canvas, doc):
    canvas.saveState()
    # Set up the style for confidentiality notice
    canvas.setFont('Helvetica-Oblique', 8)
    canvas.setFillColor(colors.grey)
    # Position the text at the top of the page (72 is the default margin)
    canvas.drawString(72, letter[1] - 50, 
        "Confidential treatment requested under NY Banking Law § 36.10 and NY Pub. Off. Law § 87.2(d).")
    canvas.restoreState()

def create_pdf(token_data, output_dir):
    """Generate PDF for a single token"""
    # Handle missing or invalid name/symbol
    token_name = token_data.get('name', 'Unknown')
    if token_name in ['N/A', None, '']:
        token_name = 'Unknown'
    
    token_symbol = token_data.get('symbol', 'UNKNOWN')
    if token_symbol in ['N/A', None, '']:
        token_symbol = 'UNKNOWN'
    
    filename = f"{token_name} ({token_symbol}) Security Memo.pdf"
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '(', ')', '.'))
    filepath = os.path.join(output_dir, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Add page template with header
    frame = Frame(
        doc.leftMargin, 
        doc.bottomMargin, 
        doc.width, 
        doc.height,
        id='normal'
    )
    template = PageTemplate(
        id='main',
        frames=frame,
        onPage=create_header
    )
    doc.addPageTemplates([template])
    
    styles, title_style, cell_style, context_style, header_style, risk_header_style, risk_subheader_style, risk_body_style = create_styles()
    elements = []
    
    # Title first
    title = Paragraph(
        f"Solana Token Security Assessment:<br/>{token_name} ({token_symbol})", 
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Basic information table (reviewer, profile, date, etc.)
    current_date = datetime.now().strftime("%Y-%m-%d")
    profile = "SPL Token 2022 Standard" if "Token 2022" in token_data['owner_program'] else "SPL Token Standard"
    
    metadata_data = [
        [Paragraph("Reviewer", cell_style), Paragraph(token_data.get('reviewer_name', 'Noama Samreen'), cell_style)],
        [Paragraph("Profile", cell_style), Paragraph(profile, cell_style)],
        [Paragraph("Review Date", cell_style), Paragraph(current_date, cell_style)],
        [Paragraph("Network", cell_style), Paragraph("Solana", cell_style)],
        [Paragraph("Address", cell_style), Paragraph(token_data['address'], cell_style)]
    ]
    
    elements.append(create_basic_table(metadata_data, cell_style))
    elements.append(Spacer(1, 20))
    
    # Add conflicts certification
    conflicts_style = ParagraphStyle(
        'Conflicts',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=14,
        alignment=4,
        fontName='Helvetica'
    )
    conflicts_text = """<b>Conflicts Certification:</b> To the best of your knowledge, please confirm that you and your immediate family: (1) have not invested more than $10,000 in the asset or its issuer, (2) do not own more than 1% of the asset outstanding, and (3) do not have a personal relationship with the issuer's management, governing body, or owners. For wrapped assets, the underlying asset must be considered for the purpose of this conflict certification, unless: 1) the asset is a stablecoin; or 2) has a market cap of over $100 billion dollars. For multi-chain assets every version of the multi-chain asset must be counted together for the purpose of this conflict certification."""
    elements.append(Paragraph(conflicts_text, conflicts_style))
    elements.append(Spacer(1, 10))
    
    # Add reviewer confirmation (single row table)
    reviewer_confirmation = [[
        Paragraph("Reviewer:", cell_style), 
        Paragraph(token_data.get('reviewer_name', 'Noama Samreen'), cell_style),
        Paragraph("Status:", cell_style),
        Paragraph(token_data.get('confirmation_status', 'Confirmed'), cell_style)
    ]]
    
    # Create table with 4 columns for single-row layout
    reviewer_table = Table(reviewer_confirmation, colWidths=[1*inch, 2*inch, 1*inch, 2*inch])
    reviewer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (0,0), colors.lightgrey),
        ('BACKGROUND', (2,0), (2,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(reviewer_table)
    elements.append(Spacer(1, 30))
    
    # Context text
    context_text = """<b>Solana SPL Token Review Context:</b> Solana tokens do not possess customizable code per 
asset. Rather, a single "program" generates boiler template tokens with distinct states for each 
newly created token. Therefore, examining the base program configurations is adequate for 
reviewing all other tokens associated with it. The 'Token Program' adheres to standard 
practices, undergoing thorough review and auditing procedures. Therefore, within this review 
process, the focus remains on validating token configurations specific to tokens managed by the 
trusted Token Program"""
    
    elements.append(Paragraph(context_text, context_style))
    elements.append(Spacer(1, 25))
    
    # Recommendation with error handling and risk scores
    security_review = token_data.get('security_review', 'UNKNOWN')
    if security_review in ['N/A', None, '']:
        security_review = 'UNKNOWN'
    
    # Determine risk scores based on security review
    risk_score = 1 if security_review == 'PASSED' else 5
    
    recommendation = (
        f"<b>{token_name} ({token_symbol}) "
        f"{'is' if security_review == 'PASSED' else 'is not'} recommended for listing.</b>"
    )
    elements.append(Paragraph(recommendation, ParagraphStyle(
        'CustomRecommendation',
        parent=context_style,
        fontSize=12,
        textColor=colors.HexColor('#006400') if security_review == 'PASSED' else colors.red
    )))
    elements.append(Spacer(1, 15))
    
    # Add risk scores
    risk_style = ParagraphStyle(
        'RiskScore',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leading=14,
        fontName='Helvetica'
    )
    
    elements.append(Paragraph(
        f"<b>Residual Security Risk Score:</b> {risk_score}",
        risk_style
    ))
    elements.append(Paragraph(
        f"<b>Inherent Security Risk Score:</b> {risk_score}",
        risk_style
    ))
    elements.append(Spacer(1, 25))
    
    # Additional details table
    additional_data = [["Field", "Value"]]
    
    # Base fields for all tokens
    field_order = [
        'owner_program',
        'freeze_authority'
    ]
    
    # Add Token 2022 specific fields if applicable
    if "Token 2022" in token_data.get('owner_program', ''):
        field_order.extend([
            'update_authority',
            'permanent_delegate',
            'transaction_fees',
            'transfer_hook',
            'confidential_transfers'
        ])
    
    # Add pump.fun specific fields if applicable
   # if "Pump.Fun Mint Authority" in str(token_data.get('update_authority', '')):
    #    field_order.extend([
    #        'is_genuine_pump_fun_token',
    #        'interacted_with',
    #        'token_graduated_to_raydium'
    #    ])
    #    if token_data.get('interacting_account') or token_data.get('interaction_signature'):
    #        field_order.extend([
    #            'interacting_account',
    #            'interaction_signature'
    #        ])
    
    # Add fields in specified order
    for field in field_order:
        value = token_data.get(field, 'None')
        if value in ['N/A', None, '']:
            value = 'None'
        if isinstance(value, bool):
            value = str(value)
        display_name = str(field).replace('_', ' ').title()
        additional_data.append([
            Paragraph(display_name, cell_style),
            Paragraph(str(value), cell_style)
        ])
    
    # Add security review as the last row
    security_style = ParagraphStyle(
        'SecurityCell',
        parent=cell_style,
        textColor=colors.HexColor('#006400') if security_review == 'PASSED' 
                 else colors.red if security_review == 'FAILED'
                 else colors.black,
        fontName='Helvetica-Bold'
    )
    
    additional_data.append([
        Paragraph("Security Review", cell_style),
        Paragraph(security_review, security_style)
    ])
    
    elements.append(create_additional_table(additional_data, cell_style))
    
    # After the details table, add Risk Findings section
    elements.append(Spacer(1, 30))
    
    # Risk Findings Header
    elements.append(Paragraph("Risk Findings", risk_header_style))
    
    # Standard SPL Token Check
    is_valid_token_program = "Token Program" in token_data.get('owner_program', '') or "Token 2022" in token_data.get('owner_program', '')
    spl_header = f"""{'1' if is_valid_token_program else '5'} | Standard Solana SPL Token {'- Pass' if is_valid_token_program else '- Fail'}"""
    
    elements.append(Paragraph(spl_header, risk_subheader_style))
    
    spl_description = """The token must be a standard Solana SPL Token (i.e. owned by the Token Program or Token
2022 Program) to be eligible for umbrella approval."""
    elements.append(Paragraph(spl_description, risk_body_style))
    elements.append(Spacer(1, 8))
    
    # Assessment
    elements.append(Paragraph("<b>Assessment:</b>", risk_body_style))
    owner_assessment = f"""As token metadata indicates, the token owner is the {token_data['owner_program']}."""
    elements.append(Paragraph(owner_assessment, risk_body_style))
    elements.append(Spacer(1, 8))
    
    # Freeze Authority Check
    freeze_value = token_data.get('freeze_authority', 'None')
    has_no_freeze = freeze_value == 'None' or freeze_value is None or freeze_value == ''
    freeze_header = f"""{'1' if has_no_freeze else '5'} | No Freeze Authority {'- Pass' if has_no_freeze else '- Fail'}"""
    elements.append(Paragraph(freeze_header, risk_subheader_style))
    
    freeze_description = """A missing freeze authority means that it is set to null and therefore a permanently revoked privilege. This means that account blacklisting is not possible."""
    elements.append(Paragraph(freeze_description, risk_body_style))
    elements.append(Spacer(1, 8))
    
    # Assessment
    elements.append(Paragraph("<b>Assessment:</b>", risk_body_style))
    elements.append(Paragraph(
        f"""As token metadata indicates, the freeze authority is: {freeze_value}.""",
        risk_body_style
    ))
    elements.append(Spacer(1, 8))
    
    # Mitigations for Freeze Authority
    elements.append(Paragraph("<b>Mitigations:</b>", risk_body_style))
    if not has_no_freeze and token_data.get('mitigations', {}).get('freeze_authority'):
        mitigation = token_data['mitigations']['freeze_authority']
        if mitigation['applied']:
            # Create hyperlinked text
            doc_text = mitigation['documentation']
            for link in mitigation.get('links', []):
                if link in doc_text:
                    doc_text = doc_text.replace(link, f'<link href="{link}">{link}</link>')
            elements.append(Paragraph(doc_text, risk_body_style))
    else:
        elements.append(Paragraph("N/A", risk_body_style))
    
    # Add Token 2022 specific checks if applicable
    if "Token 2022" in token_data.get('owner_program', ''):
        # Permanent Delegate Check
        delegate_value = token_data.get('permanent_delegate', 'None')
        has_no_delegate = delegate_value == 'None' or delegate_value is None or delegate_value == ''
        delegate_header = f"""{'1' if has_no_delegate else '5'} | No Permanent Delegate {'- Pass' if has_no_delegate else '- Fail'}"""
        elements.append(Paragraph(delegate_header, risk_subheader_style))
        
        delegate_description = """A missing Permanent Delegate means that it is set to null and therefore no delegate can burn or transfer any amount of tokens."""
        elements.append(Paragraph(delegate_description, risk_body_style))
        elements.append(Paragraph("<b>Assessment:</b>", risk_body_style))
        elements.append(Paragraph(
            f"""As token metadata indicates, the permanent delegate is: {delegate_value}.""",
            risk_body_style
        ))
        elements.append(Spacer(1, 8))
        
        # Mitigations for Permanent Delegate
        elements.append(Paragraph("<b>Mitigations:</b>", risk_body_style))
        if not has_no_delegate and token_data.get('mitigations', {}).get('permanent_delegate'):
            mitigation = token_data['mitigations']['permanent_delegate']
            if mitigation['applied']:
                doc_text = mitigation['documentation']
                for link in mitigation.get('links', []):
                    if link in doc_text:
                        doc_text = doc_text.replace(link, f'<link href="{link}">{link}</link>')
                elements.append(Paragraph(doc_text, risk_body_style))
        else:
            elements.append(Paragraph("N/A", risk_body_style))
        
        # Transfer Hook Check
        hook_value = token_data.get('transfer_hook', 'None')
        has_no_hook = hook_value == 'None' or hook_value is None or hook_value == ''
        hook_header = f"""{'1' if has_no_hook else '5'} | No Transfer Hook {'- Pass' if has_no_hook else '- Fail'}"""
        elements.append(Paragraph(hook_header, risk_subheader_style))
        
        transfer_hook_description = """A missing TransferHook means that it is set to null and therefore does not communicate with a custom program whenever this token is transferred."""
        elements.append(Paragraph(transfer_hook_description, risk_body_style))
        elements.append(Paragraph("<b>Assessment:</b>", risk_body_style))
        elements.append(Paragraph(
            f"""As token metadata indicates, the transfer hook is: {hook_value}.""",
            risk_body_style
        ))
        elements.append(Spacer(1, 8))
        
        # Mitigations for Transfer Hook
        elements.append(Paragraph("<b>Mitigations:</b>", risk_body_style))
        if not has_no_hook and token_data.get('mitigations', {}).get('transfer_hook'):
            mitigation = token_data['mitigations']['transfer_hook']
            if mitigation['applied']:
                doc_text = mitigation['documentation']
                for link in mitigation.get('links', []):
                    if link in doc_text:
                        doc_text = doc_text.replace(link, f'<link href="{link}">{link}</link>')
                elements.append(Paragraph(doc_text, risk_body_style))
        else:
            elements.append(Paragraph("N/A", risk_body_style))
        
        # Confidential Transfers Check
        confidential_value = token_data.get('confidential_transfers', 'None')
        has_no_confidential = confidential_value == 'None' or confidential_value is None or confidential_value == ''
        confidential_header = f"""{'1' if has_no_confidential else '5'} | No Confidential Transfers {'- Pass' if has_no_confidential else '- Fail'}"""
        elements.append(Paragraph(confidential_header, risk_subheader_style))
        
        confidential_description = """The confidential transfer is a non-anonymous, non-private transfer that publicly shares the source, destination, and token type, but uses zero-knowledge proofs to encrypt the amount of the transfer."""
        elements.append(Paragraph(confidential_description, risk_body_style))
        elements.append(Paragraph("<b>Assessment:</b>", risk_body_style))
        elements.append(Paragraph(
            f"""As token metadata indicates, the confidential transfers are: {confidential_value}.""",
            risk_body_style
        ))
        elements.append(Spacer(1, 8))
        
        # Mitigations for Confidential Transfers
        elements.append(Paragraph("<b>Mitigations:</b>", risk_body_style))
        if not has_no_confidential and token_data.get('mitigations', {}).get('confidential_transfers'):
            mitigation = token_data['mitigations']['confidential_transfers']
            if mitigation['applied']:
                doc_text = mitigation['documentation']
                for link in mitigation.get('links', []):
                    if link in doc_text:
                        doc_text = doc_text.replace(link, f'<link href="{link}">{link}</link>')
                elements.append(Paragraph(doc_text, risk_body_style))
        else:
            elements.append(Paragraph("N/A", risk_body_style))
        
        # Transaction Fees Check
        fees_value = token_data.get('transaction_fees', 'None')
        has_no_fees = (fees_value == 'None' or fees_value is None or fees_value == '' 
                      or fees_value == '0' or fees_value == 0)
        fees_header = f"""{'1' if has_no_fees else '5'} | No Transaction Fees {'- Pass' if has_no_fees else '- Fail'}"""
        elements.append(Paragraph(fees_header, risk_subheader_style))
        
        fees_description = """Transaction fees are set to 0 and therefore no transaction fees are possible and send/receive token amounts are the same as expected."""
        elements.append(Paragraph(fees_description, risk_body_style))
        elements.append(Paragraph("<b>Assessment:</b>", risk_body_style))
        elements.append(Paragraph(
            f"""As token metadata indicates, the transaction fees are: {fees_value}.""",
            risk_body_style
        ))
        elements.append(Spacer(1, 8))
        
        # Mitigations for Transaction Fees
        elements.append(Paragraph("<b>Mitigations:</b>", risk_body_style))
        if not has_no_fees and token_data.get('mitigations', {}).get('transfer_fees'):
            mitigation = token_data['mitigations']['transfer_fees']
            if mitigation['applied']:
                doc_text = mitigation['documentation']
                for link in mitigation.get('links', []):
                    if link in doc_text:
                        doc_text = doc_text.replace(link, f'<link href="{link}">{link}</link>')
                elements.append(Paragraph(doc_text, risk_body_style))
        else:
            elements.append(Paragraph("N/A", risk_body_style))
    
    # Build PDF
    doc.build(elements)
    return filepath

# Export the function
__all__ = ['create_pdf']

if __name__ == '__main__':
    pdf_path = create_pdf(token_data, output_dir)