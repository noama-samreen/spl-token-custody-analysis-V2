import os
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageTemplate
from reportlab.pdfgen import canvas
from typing import Dict
import re

class TokenReportStyles:
    """Container for all report styles"""
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_styles()
    
    def _create_styles(self):
        """Create all custom styles for the report"""
        self.title = self._create_title_style()
        self.cell = self._create_cell_style()
        self.context = self._create_context_style()
        self.header = self._create_header_style()
        self.risk_header = self._create_risk_header_style()
        self.risk_subheader = self._create_risk_subheader_style()
        self.risk_body = self._create_risk_body_style()
        self.conflicts = self._create_conflicts_style()
        self.security = self._create_security_style()
    
    def _create_title_style(self):
        return ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
    
    def _create_cell_style(self):
        return ParagraphStyle(
            'CustomCell',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            fontName='Helvetica',
            leading=14
        )
    
    def _create_context_style(self):
        return ParagraphStyle(
            'CustomContext',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            leading=16,
            alignment=4,
            fontName='Helvetica'
        )
    
    def _create_header_style(self):
        return ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=0
        )
    
    def _create_risk_header_style(self):
        return ParagraphStyle(
            'RiskHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=15,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            alignment=0,
            leading=20
        )
    
    def _create_risk_subheader_style(self):
        return ParagraphStyle(
            'RiskSubHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            alignment=0,
            leading=18
        )
    
    def _create_risk_body_style(self):
        return ParagraphStyle(
            'RiskBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leading=14,
            alignment=0,
            fontName='Helvetica',
            linkUnderline=True,
            textColor=colors.black,
            linkColor=colors.blue
        )
    
    def _create_conflicts_style(self):
        return ParagraphStyle(
            'Conflicts',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            leading=14,
            alignment=4,
            fontName='Helvetica'
        )
    
    def _create_security_style(self):
        return lambda status: ParagraphStyle(
            'SecurityCell',
            parent=self.cell,
            textColor=colors.HexColor('#006400') if status == 'PASSED'
                     else colors.red if status == 'FAILED'
                     else colors.black,
            fontName='Helvetica-Bold'
        )

class TokenReportGenerator:
    """Handles generation of token security assessment reports"""
    def __init__(self, token_data, output_dir):
        self.token_data = token_data
        self.output_dir = output_dir
        self.styles = TokenReportStyles()
        self.elements = []
        
        # Initialize token metadata
        self.token_name = self._get_valid_value(token_data.get('name'), 'Unknown')
        self.token_symbol = self._get_valid_value(token_data.get('symbol'), 'UNKNOWN')
        self.security_review = self._get_valid_value(token_data.get('security_review'), 'UNKNOWN')
        self.is_token_2022 = "Token 2022" in token_data.get('owner_program', '')
    
    @staticmethod
    def _get_valid_value(value, default):
        """Return valid value or default if value is invalid"""
        return default if value in ['N/A', None, ''] else value
    
    def _create_document(self):
        """Create and configure the PDF document"""
        filename = f"{self.token_name} ({self.token_symbol}) Security Memo.pdf"
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '(', ')', '.'))
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            leftMargin=72,
            rightMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
        template = PageTemplate(id='main', frames=frame, onPage=self._create_header)
        doc.addPageTemplates([template])
        
        return doc, filepath
    
    @staticmethod
    def _create_header(canvas, doc):
        """Add header to each page"""
        canvas.saveState()
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(72, letter[1] - 50, 
            "Confidential treatment requested under NY Banking Law § 36.10 and NY Pub. Off. Law § 87.2(d).")
        canvas.restoreState()
    
    def _add_title(self):
        """Add report title"""
        title = Paragraph(
            f"Solana Token Security Assessment:<br/>{self.token_name} ({self.token_symbol})", 
            self.styles.title
        )
        self.elements.extend([title, Spacer(1, 20)])
    
    def _create_basic_table(self, data):
        """Create and style the basic information table"""
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
    
    def _create_additional_table(self, data):
        """Create and style the additional fields table"""
        table = Table(data, colWidths=[2.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('PADDING', (0,0), (-1,-1), 12),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f9f9f9')]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f8f8f8')),
        ]))
        return table
    
    def _add_metadata(self):
        """Add basic metadata table"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        profile = "SPL Token 2022 Standard" if self.is_token_2022 else "SPL Token Standard"
        
        metadata = [
            ["Reviewer", self.token_data.get('reviewer_name', 'Noama Samreen')],
            ["Profile", profile],
            ["Review Date", current_date],
            ["Network", "Solana"],
            ["Address", self.token_data['address']]
        ]
        
        metadata_data = [[Paragraph(k, self.styles.cell), Paragraph(v, self.styles.cell)] 
                        for k, v in metadata]
        
        self.elements.extend([
            self._create_basic_table(metadata_data),
            Spacer(1, 20)
        ])
    
    def _add_conflicts_certification(self):
        """Add conflicts certification section"""
        conflicts_text = """<b>Conflicts Certification:</b> To the best of your knowledge, please confirm that you and your immediate family: (1) have not invested more than $10,000 in the asset or its issuer, (2) do not own more than 1% of the asset outstanding, and (3) do not have a personal relationship with the issuer's management, governing body, or owners. For wrapped assets, the underlying asset must be considered for the purpose of this conflict certification, unless: 1) the asset is a stablecoin; or 2) has a market cap of over $100 billion dollars. For multi-chain assets every version of the multi-chain asset must be counted together for the purpose of this conflict certification."""
        
        reviewer_confirmation = [[
            Paragraph("Reviewer:", self.styles.cell),
            Paragraph(self.token_data.get('reviewer_name', 'Noama Samreen'), self.styles.cell),
            Paragraph("Status:", self.styles.cell),
            Paragraph(self.token_data.get('confirmation_status', 'Confirmed'), self.styles.cell)
        ]]
        
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
        
        self.elements.extend([
            Paragraph(conflicts_text, self.styles.conflicts),
            Spacer(1, 10),
            reviewer_table,
            Spacer(1, 30)
        ])
    
    def _add_context(self):
        """Add context section"""
        context_text = """<b>Solana SPL Token Review Context:</b> Solana tokens do not possess customizable code per 
asset. Rather, a single "program" generates boiler template tokens with distinct states for each 
newly created token. Therefore, examining the base program configurations is adequate for 
reviewing all other tokens associated with it. The 'Token Program' adheres to standard 
practices, undergoing thorough review and auditing procedures. Therefore, within this review 
process, the focus remains on validating token configurations specific to tokens managed by the 
trusted Token Program"""
        
        self.elements.extend([
            Paragraph(context_text, self.styles.context),
            Spacer(1, 25)
        ])
    
    def _add_recommendation(self):
        """Add recommendation section with risk scores"""
        mitigations = self.token_data.get('mitigations', {})
        all_mitigations_applied = all(
            m.get('applied', False) 
            for m in mitigations.values()
        )
        
        # Calculate risk score based on the highest risk level
        risk_score = 1  # Default to lowest risk
        
        # Check for freeze authority
        if self.token_data.get('freeze_authority'):
            if mitigations.get('freeze_authority', {}).get('applied', False):
                risk_score = max(risk_score, 4)  # Mitigated
            else:
                risk_score = 5  # Failed
        
        # Check Token 2022 specific features
        if self.is_token_2022:
            for feature in ['permanent_delegate', 'transfer_hook', 'confidential_transfers', 'transaction_fees']:
                value = getattr(self.token_data.get('extensions', {}), feature, None)
                if value not in [None, 0, 'None']:
                    if mitigations.get(feature, {}).get('applied', False):
                        risk_score = max(risk_score, 4)  # Mitigated
                    else:
                        risk_score = 5  # Failed
                        break
        
        recommendation = (
            f"<b>{self.token_name} ({self.token_symbol}) "
            f"is {'recommended' if self.security_review == 'PASSED' else 'not recommended'} for listing.</b>"
        )
        
        self.elements.extend([
            Paragraph(recommendation, ParagraphStyle(
                'CustomRecommendation',
                parent=self.styles.context,
                fontSize=12,
                textColor=colors.HexColor('#006400') if risk_score < 5 else colors.red
            )),
            Spacer(1, 15),
            Paragraph(f"<b>Residual Security Risk Score:</b> {risk_score}", self.styles.risk_body),
            Paragraph(f"<b>Inherent Security Risk Score:</b> {risk_score}", self.styles.risk_body),
            Spacer(1, 25)
        ])
    
    def _add_token_details(self):
        """Add token details table"""
        field_order = ['owner_program', 'freeze_authority']
        
        if self.is_token_2022:
            field_order.extend([
                'update_authority',
                'permanent_delegate',
                'transaction_fees',
                'transfer_hook',
                'confidential_transfers'
            ])
        
        data = [["Field", "Value"]]
        for field in field_order:
            value = self._get_valid_value(self.token_data.get(field), 'None')
            if isinstance(value, bool):
                value = str(value)
            display_name = field.replace('_', ' ').title()
            data.append([
                Paragraph(display_name, self.styles.cell),
                Paragraph(str(value), self.styles.cell)
            ])
        
        data.append([
            Paragraph("Security Review", self.styles.cell),
            Paragraph(self.security_review, self.styles.security(self.security_review))
        ])
        
        self.elements.extend([
            self._create_additional_table(data),
            Spacer(1, 30)
        ])
    
    def _add_risk_findings(self):
        """Add risk findings section"""
        self.elements.append(Paragraph("Risk Findings", self.styles.risk_header))
        
        # Add standard checks
        self._add_standard_spl_check()
        self._add_freeze_authority_check()
        
        # Add Token 2022 specific checks
        if self.is_token_2022:
            self._add_token_2022_checks()
    
    def _add_standard_spl_check(self):
        """Add standard SPL token check"""
        is_valid = "Token Program" in self.token_data.get('owner_program', '') or self.is_token_2022
        score = '1' if is_valid else '5'
        status = 'Pass' if is_valid else 'Fail'
        
        self.elements.extend([
            Paragraph(f"{score} | Standard Solana SPL Token - {status}", 
                     self.styles.risk_subheader),
            Paragraph(
                "The token must be a standard Solana SPL Token (i.e. owned by the Token Program or Token 2022 Program) to be eligible for umbrella approval.",
                self.styles.risk_body
            ),
            Spacer(1, 8),
            Paragraph("<b>Assessment:</b>", self.styles.risk_body),
            Paragraph(
                f"As token metadata indicates, the token owner is the {self.token_data['owner_program']}.",
                self.styles.risk_body
            ),
            Spacer(1, 8)
        ])
    
    def _add_check_section(self, title, value, description, field_name):
        """Add a generic check section"""
        has_no_value = value in [None, 'None', '', '0', 0]
        mitigation_applied = self.token_data.get('mitigations', {}).get(field_name, {}).get('applied', False)
        
        if has_no_value:
            status = 'Pass'
            score = '1'
        elif mitigation_applied:
            status = 'Mitigated'
            score = '4'
        else:
            status = 'Fail'
            score = '5'
        
        self.elements.extend([
            Paragraph(f"{score} | {title} - {status}", self.styles.risk_subheader),
            Paragraph(description, self.styles.risk_body),
            Paragraph("<b>Assessment:</b>", self.styles.risk_body),
            Paragraph(f"As token metadata indicates, the {field_name.replace('_', ' ')} is: {value}.",
                     self.styles.risk_body),
            Spacer(1, 8),
            Paragraph("<b>Mitigations:</b>", self.styles.risk_body)
        ])
        
        if not has_no_value and field_name in self.token_data.get('mitigations', {}):
            mitigation = self.token_data['mitigations'][field_name]
            if mitigation['applied']:
                # Convert markdown links to ReportLab link format
                doc_text = mitigation['documentation']
                # Replace markdown links with ReportLab link format
                doc_text = re.sub(
                    r'\[(.*?)\]\((https?://[^\s\)]+)\)',
                    r'<a href="\2" color="blue"><u>\1</u></a>',
                    doc_text
                )
                self.elements.append(Paragraph(doc_text, self.styles.risk_body))
        else:
            self.elements.append(Paragraph("N/A", self.styles.risk_body))
    
    def _add_freeze_authority_check(self):
        """Add freeze authority check section"""
        self._add_check_section(
            "No Freeze Authority",
            self.token_data.get('freeze_authority'),
            "A missing freeze authority means that it is set to null and therefore a permanently revoked privilege. This means that account blacklisting is not possible.",
            'freeze_authority'
        )
    
    def _add_token_2022_checks(self):
        """Add Token-2022 specific checks"""
        checks = [
            ("No Permanent Delegate",
             self.token_data.get('permanent_delegate'),
             "A missing Permanent Delegate means that it is set to null and therefore no delegate can burn or transfer any amount of tokens.",
             'permanent_delegate'),
            
            ("No Transfer Hook",
             self.token_data.get('transfer_hook'),
             "A missing TransferHook means that it is set to null and therefore does not communicate with a custom program whenever this token is transferred.",
             'transfer_hook'),
            
            ("No Confidential Transfers",
             self.token_data.get('confidential_transfers'),
             "The confidential transfer is a non-anonymous, non-private transfer that publicly shares the source, destination, and token type, but uses zero-knowledge proofs to encrypt the amount of the transfer.",
             'confidential_transfers'),
            
            ("No Transaction Fees",
             self.token_data.get('transaction_fees'),
             "Transaction fees are set to 0 and therefore no transaction fees are possible and send/receive token amounts are the same as expected.",
             'transfer_fees')
        ]
        
        for title, value, description, field_name in checks:
            self._add_check_section(title, value, description, field_name)
    
    def generate(self):
        """Generate the complete PDF report"""
        doc, filepath = self._create_document()
        
        # Build report structure
        self._add_title()
        self._add_metadata()
        self._add_conflicts_certification()
        self._add_context()
        self._add_recommendation()
        self._add_token_details()
        self._add_risk_findings()
        
        # Build PDF
        doc.build(self.elements)
        return filepath

def create_pdf(token_data, output_dir):
    """Create a PDF report for the given token data"""
    generator = TokenReportGenerator(token_data, output_dir)
    return generator.generate()

# Export the function
__all__ = ['create_pdf']

if __name__ == '__main__':
    pdf_path = create_pdf(token_data, output_dir)

def to_dict(self) -> Dict:
    result = {
        'name': self.token_name,
        'symbol': self.token_symbol,
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
    
    # Calculate security review status based on risk score
    risk_score = 1  # Default to lowest risk
    
    # Check for freeze authority
    if self.freeze_authority:
        if self.mitigations.get('freeze_authority', {}).get('applied', False):
            risk_score = max(risk_score, 4)  # Mitigated
        else:
            risk_score = 5  # Failed
    
    # Check Token 2022 specific features if present
    if self.extensions:
        for feature, value in {
            'permanent_delegate': self.extensions.permanent_delegate,
            'transfer_hook': self.extensions.transfer_hook_authority,
            'confidential_transfers': self.extensions.confidential_transfers_authority,
            'transfer_fees': self.extensions.transfer_fee
        }.items():
            if value not in [None, 0, 'None']:
                if self.mitigations.get(feature, {}).get('applied', False):
                    risk_score = max(risk_score, 4)  # Mitigated
                else:
                    risk_score = 5  # Failed
                    break
    
    result['security_review'] = 'PASSED' if risk_score < 5 else 'FAILED'
    return result
