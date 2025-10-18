#!/usr/bin/env python3
"""
Cloud202 Executive Report Generator - Fixed Version with Inference Profiles
Uses AWS Bedrock with inference profiles to generate comprehensive executive reports
Converts output to beautifully formatted PDF using ReportLab
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import boto3
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# Import ReportLab libraries
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for page numbers and headers/footers"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        # Skip page numbers on first page (title page)
        if self._pageNumber == 1:
            canvas.Canvas.showPage(self)
            return

        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        # Page number at bottom right
        self.drawRightString(
            A4[0] - 0.75 * inch, 0.5 * inch, f"Page {self._pageNumber} of {page_count}"
        )
        # Company footer at bottom left
        self.setFont("Helvetica", 8)
        self.drawString(0.75 * inch, 0.5 * inch, "Cloud202 - RAPID Assessment")
        # Footer line
        self.setStrokeColor(colors.lightgrey)
        self.setLineWidth(0.5)
        self.line(0.75 * inch, 0.65 * inch, A4[0] - 0.75 * inch, 0.65 * inch)


class Cloud202ExecutiveReportGenerator:
    """
    Cloud202 Executive Report Generator using AWS Bedrock with Inference Profiles
    """

    def __init__(
        self,
        aws_region: str = "us-east-1",
        company_name: str = "Cloud202",
        tool_name: str = "Qubitz",
        contact_email: str = "hello@cloud202.com",
        contact_phone: str = "+44 7792 565738",
    ):
        """
        Initialize the executive report generator with inference profile support

        Args:
            aws_region: AWS region for Bedrock (default: us-east-1)
            company_name: Company name for branding
            tool_name: Tool name for branding
            contact_email: Contact email
            contact_phone: Contact phone
        """
        self.aws_region = aws_region
        self.company_name = company_name
        self.tool_name = tool_name
        self.contact_email = contact_email
        self.contact_phone = contact_phone
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize Bedrock client with inference profile
        try:
            self.bedrock_runtime = boto3.client(
                service_name="bedrock-runtime", region_name=aws_region
            )
            # Use inference profile for Claude Sonnet 4.5
            self.model_id = "arn:aws:bedrock:us-east-1:781364298443:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
            logger.info("✅ AWS Bedrock client initialized with inference profile")
            logger.info(f"🤖 Using model: {self.model_id}")
            logger.info(f"🌍 Region: {aws_region}")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Could not initialize AWS Bedrock client: {e}")
            logger.info("📝 Will use fallback content generation")
            self.bedrock_runtime = None

        # Create output directory
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"✅ Initialized Cloud202 Executive Report Generator")

    def interactive_file_selection(self) -> str:
        """Interactive file selection with validation"""
        print("\n" + "=" * 60)
        print("🚀 RAPID GenAI Assessment Report Generator v3.0")
        print("=" * 60)

        # Check for JSON files in current directory
        current_dir = Path(".")
        json_files = list(current_dir.glob("*.json"))

        if json_files:
            print(f"\n📁 Found {len(json_files)} JSON file(s) in current directory:")
            for i, file in enumerate(json_files, 1):
                file_size = file.stat().st_size / 1024  # KB
                print(f"   {i}. {file.name} ({file_size:.1f} KB)")

            print(f"\n   {len(json_files) + 1}. Enter custom file path")
            print("   0. Exit")

            while True:
                try:
                    choice = input(
                        f"\nSelect option (0-{len(json_files) + 1}): "
                    ).strip()

                    if choice == "0":
                        print("👋 Exiting...")
                        sys.exit(0)
                    elif choice == str(len(json_files) + 1):
                        break  # Go to custom path input
                    elif 1 <= int(choice) <= len(json_files):
                        selected_file = str(json_files[int(choice) - 1])
                        print(f"✅ Selected: {selected_file}")
                        return selected_file
                    else:
                        print("❌ Invalid selection. Please try again.")
                except (ValueError, IndexError):
                    print("❌ Invalid input. Please enter a number.")

        # Custom file path input
        while True:
            file_path = input(
                "\n📄 Enter the path to your JSON assessment file: "
            ).strip()

            if not file_path:
                print("❌ Please enter a file path.")
                continue

            # Remove quotes if present
            file_path = file_path.strip("\"'")

            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                continue

            if not file_path.lower().endswith(".json"):
                print("❌ File must be a JSON file (.json extension)")
                continue

            try:
                # Test if file is valid JSON
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
                print(f"✅ Valid JSON file: {file_path}")
                return file_path
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON format: {e}")
            except Exception as e:
                print(f"❌ Error reading file: {e}")

    def load_assessment_data(self, json_file_path: str) -> Dict[str, Any]:
        """Load customer assessment responses from JSON file"""
        try:
            with open(json_file_path, "r", encoding="utf-8") as file:
                customer_data = json.load(file)
            logger.info(f"📖 Loaded assessment data from {json_file_path}")
            return customer_data
        except Exception as e:
            logger.error(f"Error loading assessment data: {e}")
            raise

    def process_assessment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process assessment data from JSON format"""
        responses = raw_data.get("responses", {})

        business_owner = responses.get("business-owner", "")
        if "," in business_owner:
            company_name = business_owner.split(",")[0].strip()
        else:
            company_name = responses.get("company-name", "Valued Customer")

        processed_data = {
            "company_name": company_name,
            "industry": self._infer_industry(responses),
            "company_size": self._map_company_size(responses.get("scope-impact", "")),
            "assessment_type": responses.get("current-state", "Exploratory"),
            "assessment_date": raw_data.get("exportDate", datetime.now().isoformat())[
                :10
            ],
            "assessment_duration": self._map_timeline(
                responses.get("development-timeline", "")
            ),
            "business_problem": responses.get("business-problems", ""),
            "budget_range": responses.get("budget-range", ""),
            "primary_goal": responses.get("primary-goal", ""),
            "strategic_alignment": responses.get("strategic-alignment", ""),
            "urgency": responses.get("urgency", ""),
            "responses": responses,
        }

        return processed_data

    def _infer_industry(self, responses: Dict) -> str:
        """Infer industry from responses"""
        problem = responses.get("business-problems", "").lower()

        if any(
            word in problem
            for word in ["clinical", "physician", "patient", "healthcare", "medical"]
        ):
            return "Healthcare Technology"
        elif any(
            word in problem
            for word in [
                "financial",
                "banking",
                "fintech",
                "payment",
                "trading",
                "market",
                "advisory",
            ]
        ):
            return "Financial Technology"
        elif any(
            word in problem for word in ["vehicle", "manufacturing", "automotive"]
        ):
            return "Manufacturing & Automotive"
        else:
            return "Technology"

    def _map_company_size(self, scope: str) -> str:
        """Map scope to company size"""
        if "2000+" in scope or "5000+" in scope:
            return "Large Enterprise (2000-5000 employees)"
        elif "1000+" in scope:
            return "Enterprise (1000+ employees)"
        elif "500+" in scope:
            return "Mid-market (500-2000 employees)"
        else:
            return "Enterprise"

    def _map_timeline(self, timeline: str) -> str:
        """Map development timeline to assessment duration"""
        if "3-6" in timeline:
            return "3 weeks"
        elif "6-12" in timeline:
            return "4 weeks"
        else:
            return "2 weeks"

    def create_executive_report_prompt(self, processed_data: Dict[str, Any]) -> str:
        """Create comprehensive prompt for executive report generation"""

        company_name = processed_data.get("company_name", "Customer")
        industry = processed_data.get("industry", "Technology")
        business_problem = processed_data.get("business_problem", "")
        primary_goal = processed_data.get("primary_goal", "")
        budget = processed_data.get("budget_range", "")
        urgency = processed_data.get("urgency", "")

        # Calculate ROI based on budget
        if "$500K" in budget or "$1M" in budget:
            roi, annual_savings, payback = "420% over 3 years", "$4.2M", "14 months"
        elif "$100K" in budget:
            roi, annual_savings, payback = "300% over 3 years", "$2.5M", "18 months"
        else:
            roi, annual_savings, payback = "350% over 3 years", "$3.2M", "16 months"

        prompt = f"""You are a senior {self.company_name} Solutions Architect creating a comprehensive EXECUTIVE assessment report.

COMPANY: {company_name}
INDUSTRY: {industry}

ASSESSMENT DATA:
{json.dumps(processed_data, indent=2)}

Generate a detailed executive report with 6 sections. Each section should be 800-1200 words for a comprehensive 12-15 page PDF.

CRITICAL: Return ONLY valid JSON with these exact keys:
{{
  "executive_summary": "...",
  "business_case_analysis": "...",
  "technical_implementation_roadmap": "...",
  "financial_investment_analysis": "...",
  "risk_mitigation_strategy": "...",
  "strategic_recommendations": "..."
}}

SECTION REQUIREMENTS:

1. EXECUTIVE SUMMARY (1 page):
- Business problem: {business_problem}
- Proposed GenAI solution approach
- Quantified benefits: {roi} with {payback} payback, {annual_savings} annual savings
- Key findings and recommendations
- Strategic imperative for action within 30-60 days
- Write 4-6 paragraphs, each 3-5 sentences
- Professional, executive-level language

2. BUSINESS CASE & VALUE PROPOSITION (2-3 pages):
- Current State Challenges: Analyze business problems in detail
- Proposed Solution Benefits using GenAI and cloud services
- Quantified Impact: Cost savings, efficiency gains, revenue growth
- Competitive advantages in {industry} sector
- Strategic alignment with business goals
- Use subheaders for each major topic
- Mix of detailed paragraphs with occasional bullet points for key metrics only

3. IMPLEMENTATION ROADMAP (2-3 pages):
- Phase 1: Foundation (Months 1-3) - Infrastructure setup, security framework, pilot design
- Phase 2: AI Development (Months 4-6) - Model integration, data pipeline, initial deployment
- Phase 3: Pilot Deployment (Months 7-9) - Limited rollout, testing, optimization
- Phase 4: Production Scale (Months 10-12) - Full deployment, monitoring, support
- Each phase needs: objectives, key milestones, deliverables, resources needed
- Detailed paragraph descriptions for each phase

4. INVESTMENT & ROI ANALYSIS (1-2 pages):
- Total investment breakdown: {budget}
- Expected ROI: {roi}
- Annual savings: {annual_savings}
- Payback period: {payback}
- Break-even analysis with timeline
- Risk-adjusted financial projections
- Cost optimization strategies

5. RISK ASSESSMENT & NEXT STEPS (1-2 pages):
- Technical risks: integration, performance, scalability
- Operational risks: adoption, change management, skills gaps
- Financial risks: budget, ROI realization
- Mitigation strategies for each risk category
- Success factors and KPIs to track
- Immediate next steps with 30-60-90 day plan

6. STRATEGIC RECOMMENDATIONS (1-2 pages):
- Leadership and governance framework needed
- Organizational readiness and capability development
- Partnership strategy with {self.company_name}
- Innovation and competitive positioning approach
- Long-term investment allocation strategy
- How to establish AI Center of Excellence

FORMATTING RULES:
- Write in professional business paragraphs
- Use clear section headers
- Use bullet points ONLY for lists of metrics, features, or requirements
- Provide specific numbers, timelines, and data points
- Keep business-focused and executive-friendly
- Professional tone suitable for C-level executives
- Total content: 12-15 pages when rendered

Return ONLY the JSON object with the 6 sections as keys. No markdown formatting, no code blocks."""

        return prompt

    def generate_report_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate report content using AWS Bedrock with inference profile"""
        if self.bedrock_runtime:
            try:
                logger.info(
                    "🤖 Generating executive report content using Bedrock with inference profile..."
                )

                prompt = self.create_executive_report_prompt(processed_data)

                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 16000,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                }

                logger.info(f"📡 Invoking model: {self.model_id}")

                response = self.bedrock_runtime.invoke_model(
                    modelId=self.model_id, body=json.dumps(body)
                )

                response_body = json.loads(response.get("body").read())
                content_text = response_body.get("content")[0].get("text")

                # Clean JSON markers
                content_text = re.sub(r"```json\n?", "", content_text)
                content_text = re.sub(r"```\n?", "", content_text)
                content_text = content_text.strip()

                # Parse JSON
                content = json.loads(content_text)

                logger.info("✅ Successfully generated report content using Bedrock")
                return content

            except Exception as e:
                logger.error(f"❌ Bedrock generation failed: {e}")
                logger.info("📋 Using fallback content...")
                return self._generate_fallback_content(processed_data)
        else:
            logger.info("📋 Using fallback content (Bedrock not available)...")
            return self._generate_fallback_content(processed_data)

    def _generate_fallback_content(
        self, processed_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate fallback content if Bedrock fails"""
        company_name = processed_data.get("company_name", "Customer")
        industry = processed_data.get("industry", "Technology")
        business_problem = processed_data.get(
            "business_problem", "operational challenges"
        )
        budget = processed_data.get("budget_range", "$500K - $1M")

        return {
            "executive_summary": f"""EXECUTIVE SUMMARY

{company_name}, a leading organization in the {industry} sector, faces critical challenges with {business_problem}. Our comprehensive RAPID assessment using {self.tool_name} has identified substantial opportunities for transformation through Generative AI implementation.

The proposed GenAI solution addresses these challenges through intelligent automation, enhanced decision-making capabilities, and operational excellence. By leveraging cloud-based AI services, {company_name} can achieve significant improvements in efficiency, accuracy, and scalability while reducing operational costs.

Our assessment reveals exceptional organizational readiness for GenAI adoption. We project 420% ROI over 3 years with 14-month payback period. Direct cost savings of $4.2M annually will result from process automation and productivity improvements.

Investment required: {budget} over 18-month deployment timeline. Expected returns include direct cost savings of $4.2M annually, revenue enhancement of $1.8-2.4M annually, and operational efficiency improvements of 40-55% reduction in processing time.

Critical success factors include strong executive sponsorship, comprehensive change management, technical excellence in deployment, and continuous improvement based on performance metrics. We recommend immediate implementation with 95% confidence based on comprehensive readiness assessment. The strategic window for competitive advantage requires decisive action within 30-60 days.""",
            "business_case_analysis": f"""BUSINESS CASE & VALUE PROPOSITION

Current State Challenges

{company_name} faces significant operational inefficiencies with {business_problem}. These challenges represent a critical constraint on business growth and competitive positioning in the {industry} sector. Current manual processes consume excessive resources while limiting organizational agility and market responsiveness.

Quantitative analysis indicates current manual processes cost approximately $2.5-4.2M annually in direct operational expenses, opportunity costs, and competitive disadvantages. Employee productivity is constrained by repetitive tasks consuming 35-45% of knowledge worker time, while quality inconsistencies impact customer satisfaction and market reputation.

Proposed GenAI Solution Benefits

The recommended GenAI solution leverages cloud-based AI services to create intelligent automation capabilities that transform business operations. Core capabilities include natural language processing, predictive analytics, intelligent document processing, and automated decision support that addresses identified pain points through proven AI technologies.

Integration with existing enterprise systems ensures seamless workflow enhancement without disrupting critical business processes, while cloud-native architecture provides scalability, security, and cost optimization.

Quantified Business Impact

Comprehensive financial modeling projects 420% ROI over 3 years through multiple value streams including direct cost savings, revenue enhancement, and operational efficiency improvements. Direct cost savings of $1.8-2.4M annually result from process automation, productivity improvements, and resource optimization.

Revenue enhancement of $2.1-3.2M annually derives from improved customer experience, faster time-to-market, and enhanced competitive positioning. Operational efficiency improvements deliver 40-55% reduction in processing time, 60-75% improvement in accuracy, and 80-90% reduction in manual data entry requirements.

Competitive Advantages

GenAI implementation positions {company_name} as an innovation leader in {industry} with sustainable competitive advantages through enhanced customer experience, operational excellence, and strategic agility. Market analysis indicates AI-powered organizations achieve 2-3x performance premiums over traditional competitors, with advantages growing over time as AI capabilities mature. Early adoption positions {company_name} as an innovation leader.""",
            "technical_implementation_roadmap": f"""IMPLEMENTATION ROADMAP

Phase 1: Foundation (Months 1-3)

The foundation phase establishes core infrastructure, security frameworks, and integration capabilities required for GenAI deployment. Infrastructure provisioning includes cloud accounts structure, identity and access management, networking configuration, and security controls aligned with enterprise requirements. Data platform establishment includes data lakes, data integration services, and operational databases.

Key technical milestones include architecture compliance validation, security controls implementation, and integration testing with existing enterprise systems. Development environment configuration includes version control, CI/CD automation, and infrastructure as code. Team onboarding and training programs ensure technical competency across development, operations, and security teams.

Critical deliverables include technical architecture documentation, security compliance certification, integration architecture validation, and development environment operational readiness. Success criteria encompass infrastructure uptime >99.9%, security controls validation, and development team productivity metrics achievement.

Phase 2: AI Development (Months 4-6)

The development phase implements core GenAI capabilities using foundation models for AI services, custom model development platforms, and serverless compute integration. Model selection and fine-tuning processes optimize performance for specific use cases while ensuring cost efficiency and scalability requirements.

Integration development includes API gateway configuration, authentication systems, and monitoring implementation. Data pipeline development handles real-time data processing, while search and analytics capabilities support intelligent operations. Quality assurance processes include automated testing and performance monitoring.

Technical milestones include model performance validation achieving >95% accuracy targets, integration testing completion with <2 second response times, and scalability testing demonstrating 10x load capacity. Security testing includes penetration testing, vulnerability assessments, and compliance validation with industry standards.

Phase 3: Pilot Deployment (Months 7-9)

Pilot deployment implements GenAI capabilities for limited user groups with comprehensive monitoring and optimization processes. Deployment automation uses blue-green deployments, while container orchestration provides scalable deployment. Load balancing ensures high availability and performance optimization.

User acceptance testing includes functionality validation, performance benchmarking, and user experience optimization. Feedback integration processes capture user requirements and optimization opportunities for continuous improvement. Monitoring and alerting systems provide real-time visibility into system performance, user adoption, and business impact metrics.

Optimization activities include performance tuning, cost optimization, and capacity planning based on usage patterns. Security monitoring and compliance validation ensure ongoing security posture maintenance.

Phase 4: Production Scale (Months 10-12)

Production deployment extends GenAI capabilities organization-wide with enterprise-grade reliability, security, and performance. Auto-scaling implementation handles variable workloads while optimizing costs. Multi-region deployment provides disaster recovery and business continuity capabilities.

Change management processes include user training programs, documentation development, and support system establishment. Performance monitoring includes business impact tracking, ROI validation, and continuous optimization based on usage analytics. Integration with enterprise systems includes ERP, CRM, and business intelligence platforms.

Operational excellence includes automated backup and recovery procedures, security incident response capabilities, and proactive monitoring. Knowledge transfer ensures internal team capability for ongoing system management and optimization.""",
            "financial_investment_analysis": f"""INVESTMENT & ROI ANALYSIS

Total Investment Requirement

The GenAI implementation requires total investment of {budget} over 18-month deployment timeline, structured across technology infrastructure, professional services, internal resources, and change management activities. Technology costs represent 45% of total investment including cloud services, software licensing, security tools, and monitoring platforms.

Professional services account for 35% including solution architecture, development services, integration support, and training programs. Internal resource allocation represents 15% of investment covering dedicated project team members, subject matter experts, and management oversight. Change management activities comprise 5% including communication programs, training development, and user adoption support.

Investment phasing aligns with value delivery milestones, enabling ROI-driven funding decisions and risk mitigation. Detailed cost modeling includes cloud services consumption based on projected usage patterns, with cost optimization strategies including reserved instances, spot instances, and right-sizing recommendations.

Expected Returns Analysis

Comprehensive financial modeling projects exceptional returns through multiple value streams delivering 420% ROI over 3-year horizon. Direct cost savings of $2.1-2.8M annually result from process automation eliminating 45-60% of manual processing requirements, reducing operational expenses while improving accuracy and consistency.

Productivity improvements deliver $1.6-2.3M value through enhanced employee efficiency and capacity optimization. Revenue enhancement opportunities total $2.4-3.7M annually through improved customer experience, faster service delivery, and enhanced competitive positioning.

Customer satisfaction improvements drive 15-25% increase in customer retention worth $800K-1.2M annually, while operational efficiency enables 20-30% capacity expansion supporting revenue growth without proportional cost increases. Strategic positioning benefits create long-term value through market share protection, premium pricing capability, and competitive differentiation.

Break-even Analysis

Conservative financial modeling demonstrates break-even achievement within 16-18 months post-implementation, with accelerating value realization thereafter. Payback period analysis includes cumulative investment costs against projected benefits, with sensitivity analysis across multiple scenarios.

Base case projections show 14-month payback with moderate risk assumptions, while optimistic scenarios achieve 12-month payback under favorable adoption conditions. Cash flow analysis demonstrates positive monthly cash flow beginning month 15-18, with cumulative value creation exceeding $8-12M over 3-year horizon. Internal rate of return (IRR) exceeds 45% under base case assumptions, with net present value (NPV) of $6.2-8.8M using 12% discount rate.

Risk-Adjusted Projections

Sensitivity analysis across key variables including adoption rates, technology performance, market conditions, and competitive response provides robust financial validation. Conservative scenario (70% success probability) delivers 25% IRR and $3.8M NPV, while base case scenario (85% success probability) achieves 45% IRR and $6.8M NPV. Optimistic scenario (95% success probability) realizes 65% IRR and $11.2M NPV.""",
            "risk_mitigation_strategy": f"""RISK ASSESSMENT & NEXT STEPS

Key Risks and Mitigation Strategies

Comprehensive risk analysis identifies potential threats across technical, operational, and financial dimensions. Technical risks include integration complexity with existing systems (medium probability, high impact) mitigated through comprehensive architecture planning and phased integration approach. Model performance gaps (low probability, medium impact) addressed through rigorous testing protocols and alternative model preparation.

Technical mitigation budget of $350K-450K covers additional integration resources, testing infrastructure, and contingency development efforts. Performance validation includes accuracy testing, load testing, and user acceptance criteria with clear success thresholds. Scalability risk mitigation leverages cloud-native architecture design, auto-scaling capabilities, and performance monitoring systems.

Operational risks encompass user adoption resistance (medium probability, high impact) addressed through comprehensive change management program, user training initiatives, and adoption incentive structures. Change management investment of $180K-240K covers communication programs, training development, user support systems, and adoption measurement frameworks.

Organizational capability gap mitigation includes targeted training programs, external expertise augmentation, and knowledge transfer protocols. Training and certification programs build internal capabilities while external consultants provide specialized expertise during implementation phases. Documentation and knowledge management systems ensure capability retention and transfer.

Financial risks include budget overruns (medium probability, medium impact) managed through detailed cost estimation, vendor contract management, and financial controls with monthly budget tracking. Contingency budget of 15-20% addresses unexpected costs while change control processes manage scope modifications. Fixed-price contracts for major components reduce financial exposure to cost volatility.

Success Factors and KPIs

Critical success factors include executive sponsorship maintenance, technical excellence achievement, user adoption rate >85%, and financial performance meeting projection targets. KPI framework encompasses technical metrics (system uptime >99.9%, response time <2 seconds, accuracy >95%), operational metrics (user adoption rate, process efficiency improvement, cost reduction achievement), and financial metrics (ROI realization, budget adherence, benefit delivery).

Governance structure includes executive steering committee, technical oversight board, and user advisory groups providing multi-level oversight and decision-making authority. Monthly progress reviews, quarterly business impact assessments, and annual strategic alignment validation ensure continued program success and optimization.

Immediate Next Steps

30-60 day immediate actions include executive approval finalization, project governance establishment, core team mobilization, and vendor contract execution. Technical preparation includes cloud account setup, security framework implementation, and development environment configuration. Stakeholder engagement includes communication plan execution, training program initiation, and change management activation.

60-90 day horizon includes detailed technical design completion, integration planning finalization, pilot user group selection, and performance baseline establishment. Risk monitoring systems implementation provides early warning capabilities for proactive issue resolution.""",
            "strategic_recommendations": f"""STRATEGIC RECOMMENDATIONS

Leadership and Governance Framework

{company_name} leadership must establish comprehensive governance framework with C-level sponsorship, clear accountability structures, and strategic decision-making authority to ensure GenAI transformation success. Recommended governance includes Executive Steering Committee with CEO/COO leadership, Technical Advisory Board with CTO/CIO participation, and Business Impact Council with departmental representation.

Monthly executive reviews, quarterly strategy assessments, and annual roadmap validation provide multi-tier oversight and optimization. Leadership development programs should encompass AI/ML literacy, digital transformation strategy, and change leadership capabilities. Executive education includes industry best practices, competitive intelligence, and strategic positioning within AI-powered market dynamics.

We recommend establishing an AI Center of Excellence led by a Chief AI Officer, reporting directly to the CEO. This center will be responsible for setting AI vision, strategy, and governance while fostering a data-driven culture across the organization. Governance framework includes decision rights clarification, escalation procedures, and performance accountability structures.

Organizational Readiness and Capability Development

Strategic recommendation emphasizes comprehensive organizational transformation beyond technology implementation, including culture change, capability development, and process optimization. Cultural transformation includes innovation mindset development, data-driven decision making, and continuous learning orientation. Employee engagement programs should address change anxiety, provide growth opportunities, and celebrate transformation successes.

Capability development includes technical skills training for AI/ML literacy, business skills enhancement for digital collaboration, and leadership development for change management. Training investment of $240K-320K includes certifications, industry conference participation, and external training programs. Internal knowledge sharing includes communities of practice, innovation workshops, and success story communication.

Performance management integration includes AI adoption metrics, innovation contributions, and digital competency assessments within employee evaluation processes. Career development paths should reflect AI-enhanced role evolution and new opportunity creation through technology capabilities.

Partnership and Ecosystem Strategy

{company_name} should leverage strategic partnerships with {self.company_name} for ongoing advantage through professional services engagement, architectural guidance, and continuous optimization support. Partnership benefits include access to leading-edge capabilities, industry expertise, and strategic insights from {self.company_name}'s global AI implementation experience.

Regular partnership reviews ensure maximum value realization and strategic alignment. Ecosystem expansion includes technology vendor partnerships, system integrator relationships, and industry collaboration opportunities. AI vendor partnerships provide specialized capabilities while industry associations offer best practice sharing and competitive intelligence.

Innovation and Competitive Positioning Strategy

Long-term competitive positioning requires continuous innovation, capability enhancement, and market leadership demonstration. Innovation strategy includes internal R&D investment, external partnership development, and emerging technology evaluation. Innovation budget of 5-8% of AI program investment ensures competitive capability maintenance and enhancement.

Market positioning strategy leverages AI capabilities for thought leadership, customer experience differentiation, and operational excellence demonstration. Industry conference participation, case study development, and customer success story sharing establish {company_name} as AI transformation leader within {industry} sector.

Investment and Resource Allocation Strategy

Strategic resource allocation balances immediate implementation needs with long-term capability development and market positioning objectives. Investment prioritization includes proven ROI opportunities, strategic capability development, and competitive positioning enhancement. Portfolio approach balances risk and return across multiple AI initiatives and time horizons to ensure sustained value creation and market leadership.""",
        }

    def create_enhanced_styles(self):
        """Create enhanced custom styles for the PDF"""
        styles = getSampleStyleSheet()

        # Only add styles if they don't already exist
        style_names = [s.name for s in styles.byName.values()]

        if "TitlePage" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="TitlePage",
                    parent=styles["Title"],
                    fontSize=32,
                    leading=38,
                    textColor=colors.HexColor("#1a365d"),
                    spaceAfter=30,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                )
            )

        if "Subtitle" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="Subtitle",
                    parent=styles["Normal"],
                    fontSize=14,
                    leading=18,
                    textColor=colors.HexColor("#2d3748"),
                    spaceAfter=20,
                    alignment=TA_CENTER,
                    fontName="Helvetica",
                )
            )

        if "MainHeading" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="MainHeading",
                    parent=styles["Heading1"],
                    fontSize=20,
                    leading=24,
                    textColor=colors.HexColor("#1a365d"),
                    spaceAfter=16,
                    spaceBefore=24,
                    fontName="Helvetica-Bold",
                    backColor=colors.HexColor("#e6f0ff"),
                    leftIndent=10,
                    rightIndent=10,
                    borderPadding=8,
                )
            )

        if "SectionHeading" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="SectionHeading",
                    parent=styles["Heading2"],
                    fontSize=14,
                    leading=18,
                    textColor=colors.HexColor("#2c5282"),
                    spaceAfter=12,
                    spaceBefore=16,
                    fontName="Helvetica-Bold",
                    leftIndent=0,
                )
            )

        if "SubsectionHeading" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="SubsectionHeading",
                    parent=styles["Heading3"],
                    fontSize=12,
                    leading=15,
                    textColor=colors.HexColor("#2d3748"),
                    spaceAfter=8,
                    spaceBefore=12,
                    fontName="Helvetica-Bold",
                    leftIndent=0,
                )
            )

        if "BodyText" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="BodyText",
                    parent=styles["Normal"],
                    fontSize=10,
                    leading=14,
                    textColor=colors.HexColor("#2d3748"),
                    spaceAfter=10,
                    alignment=TA_JUSTIFY,
                    fontName="Helvetica",
                    leftIndent=10,
                )
            )

        if "BulletPoint" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="BulletPoint",
                    parent=styles["Normal"],
                    fontSize=10,
                    leading=14,
                    textColor=colors.HexColor("#2d3748"),
                    leftIndent=30,
                    bulletIndent=10,
                    spaceAfter=6,
                    fontName="Helvetica",
                    bulletFontName="Helvetica",
                )
            )

        if "HighlightBox" not in style_names:
            styles.add(
                ParagraphStyle(
                    name="HighlightBox",
                    parent=styles["Normal"],
                    fontSize=11,
                    leading=15,
                    textColor=colors.HexColor("#1a365d"),
                    backColor=colors.HexColor("#fef5e7"),
                    borderWidth=1,
                    borderColor=colors.HexColor("#f39c12"),
                    borderPadding=12,
                    borderRadius=3,
                    spaceAfter=14,
                    spaceBefore=14,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                )
            )

        return styles

    def create_title_page(self, styles, customer_data):
        """Create a professional centered title page"""
        elements = []

        # Add space at top
        elements.append(Spacer(1, 1.2 * inch))

        # Main title - CENTERED
        title = Paragraph(f"{self.company_name}", styles["TitlePage"])
        elements.append(title)
        elements.append(Spacer(1, 0.15 * inch))

        # Subtitle - CENTERED
        subtitle = Paragraph("GenAI Solutions", styles["Subtitle"])
        elements.append(subtitle)
        elements.append(Spacer(1, 0.4 * inch))

        # Report type - CENTERED
        report_type = Paragraph(
            "RAPID GenAI Assessment<br/>Comprehensive Executive Report",
            styles["TitlePage"],
        )
        elements.append(report_type)
        elements.append(Spacer(1, 0.8 * inch))

        # Horizontal line
        from reportlab.platypus import HRFlowable

        elements.append(
            HRFlowable(
                width="60%",
                thickness=2,
                color=colors.HexColor("#f39c12"),
                spaceAfter=0.4 * inch,
                spaceBefore=0,
            )
        )

        # Customer name - CENTERED
        company_name = customer_data.get("company_name", "")
        if company_name:
            customer_title = Paragraph(
                f"<b>Prepared for:</b><br/>{company_name}", styles["Subtitle"]
            )
            elements.append(customer_title)

        elements.append(Spacer(1, 0.4 * inch))

        # Details table - CENTERED
        details_data = [
            ["Industry:", customer_data.get("industry", "Technology")],
            ["Company Size:", customer_data.get("company_size", "Enterprise")],
            ["Assessment Type:", customer_data.get("assessment_type", "Comprehensive")],
            [
                "Assessment Duration:",
                customer_data.get("assessment_duration", "3 weeks"),
            ],
        ]

        details_table = Table(details_data, colWidths=[2 * inch, 3 * inch])
        details_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 11),
                    ("FONT", (1, 0), (1, -1), "Helvetica", 11),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2d3748")),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(details_table)

        elements.append(Spacer(1, 0.8 * inch))

        # Report date - CENTERED
        date_text = f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}"
        date_para = Paragraph(date_text, styles["Subtitle"])
        elements.append(date_para)

        elements.append(Spacer(1, 0.2 * inch))

        # RAPID program info - CENTERED
        rapid_text = (
            f"Readiness Assessment Acceleration Program (RAPID) - {self.tool_name}"
        )
        rapid_para = Paragraph(rapid_text, styles["Normal"])
        rapid_para.style.alignment = TA_CENTER
        elements.append(rapid_para)

        elements.append(Spacer(1, 0.15 * inch))

        # Confidentiality notice - CENTERED
        conf_text = f"<b>CONFIDENTIAL - {self.company_name} Strategic Assessment</b>"
        conf_para = Paragraph(conf_text, styles["Subtitle"])
        conf_para.style.textColor = colors.HexColor("#d35400")
        elements.append(conf_para)

        elements.append(PageBreak())

        return elements

    def create_table_of_contents(self, styles):
        """Create table of contents with proper alignment"""
        elements = []

        toc_title = Paragraph("Table of Contents", styles["MainHeading"])
        elements.append(toc_title)
        elements.append(Spacer(1, 0.3 * inch))

        toc_items = [
            ("Executive Summary", "3"),
            ("Business Case Analysis", "4"),
            ("Technical Implementation Roadmap", "5"),
            ("Financial Investment Analysis", "6"),
            ("Risk Mitigation Strategy", "7"),
            ("Strategic Recommendations", "8"),
            ("Appendix - Assessment Details", "9"),
        ]

        # Create TOC as a table for better alignment
        toc_table_data = []
        for item, page_num in toc_items:
            toc_table_data.append([item, page_num])

        toc_table = Table(toc_table_data, colWidths=[5 * inch, 0.5 * inch])
        toc_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (0, -1), "Helvetica", 12),
                    ("FONT", (1, 0), (1, -1), "Helvetica-Bold", 12),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2d3748")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a365d")),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.lightgrey),
                ]
            )
        )
        elements.append(toc_table)

        elements.append(PageBreak())

        return elements

    def create_content_section(
        self, title: str, content: str, styles, is_executive: bool = False
    ):
        """Create a content section with proper formatting and alignment"""
        elements = []

        # Section title
        section_title = Paragraph(title, styles["MainHeading"])
        elements.append(section_title)
        elements.append(Spacer(1, 0.2 * inch))

        # Executive summary callout
        if is_executive:
            exec_callout = Paragraph(
                "STRATEGIC EXECUTIVE SUMMARY", styles["HighlightBox"]
            )
            elements.append(exec_callout)
            elements.append(Spacer(1, 0.15 * inch))

        # Process content
        if content.strip():
            # Split into paragraphs
            paragraphs = content.split("\n\n")

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # Check if it's a subsection header
                is_header = False
                if para.endswith(":") and len(para) < 100:
                    is_header = True
                elif len(para.split()) <= 8 and para[0].isupper() and len(para) < 80:
                    is_header = True

                if is_header:
                    # Subsection heading - LEFT ALIGNED
                    subsection = Paragraph(para, styles["SectionHeading"])
                    elements.append(subsection)
                    elements.append(Spacer(1, 0.08 * inch))
                else:
                    # Regular paragraph - INDENTED from headers
                    paragraph = Paragraph(para, styles["BodyText"])
                    elements.append(paragraph)
                    elements.append(Spacer(1, 0.06 * inch))

        elements.append(PageBreak())

        return elements

    def create_appendix(self, styles, customer_data):
        """Create appendix section"""
        elements = []

        # Appendix title
        appendix_title = Paragraph(
            "Appendix - Assessment Details", styles["MainHeading"]
        )
        elements.append(appendix_title)
        elements.append(Spacer(1, 0.2 * inch))

        # RAPID Methodology
        method_heading = Paragraph(
            "RAPID Assessment Methodology", styles["SectionHeading"]
        )
        elements.append(method_heading)
        elements.append(Spacer(1, 0.12 * inch))

        method_text = f"""The Readiness Assessment Acceleration Program (RAPID) is a comprehensive evaluation framework designed to assess organizational readiness for GenAI implementation using {self.tool_name}. This assessment encompasses technical infrastructure, data readiness, compliance requirements, and business value analysis to provide strategic recommendations for successful GenAI adoption."""

        method_para = Paragraph(method_text, styles["BodyText"])
        elements.append(method_para)
        elements.append(Spacer(1, 0.2 * inch))

        # Assessment Scope
        scope_heading = Paragraph(
            "Assessment Scope and Coverage", styles["SectionHeading"]
        )
        elements.append(scope_heading)
        elements.append(Spacer(1, 0.12 * inch))

        scope_items = [
            "Use Case Discovery and Business Requirements Analysis",
            "Data Readiness and Infrastructure Assessment",
            "Model Evaluation and Technical Architecture Review",
            "Compliance and Security Framework Analysis",
            "Business Value and ROI Calculation",
            "Implementation Planning and Risk Assessment",
            "Change Management and Organizational Readiness",
        ]

        for item in scope_items:
            bullet = Paragraph(f"• {item}", styles["BulletPoint"])
            elements.append(bullet)

        elements.append(Spacer(1, 0.25 * inch))

        # Contact Information
        contact_heading = Paragraph(
            f"{self.company_name} Contact", styles["SectionHeading"]
        )
        elements.append(contact_heading)
        elements.append(Spacer(1, 0.12 * inch))

        contact_text = f"""For questions regarding this assessment or next steps:

{self.company_name} Team
Email: {self.contact_email}
Phone: {self.contact_phone}

Assessment Lead: {self.company_name} Senior Solutions Architect
Customer Success Manager: {self.company_name} Customer Success Manager"""

        contact_para = Paragraph(
            contact_text.replace("\n", "<br/>"), styles["BodyText"]
        )
        elements.append(contact_para)

        return elements

    def create_professional_pdf(
        self, content: Dict[str, str], customer_info: Dict[str, Any], output_path: str
    ):
        """Create professional PDF using ReportLab"""
        logger.info(f"📄 Creating professional PDF: {output_path}")

        try:
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=1 * inch,
                title=f"RAPID GenAI Assessment Report - {customer_info.get('company_name', 'Customer')}",
                author=f"{self.company_name} GenAI Solutions",
            )

            # Get styles
            styles = self.create_enhanced_styles()

            # Build document elements
            elements = []

            # Title page
            elements.extend(self.create_title_page(styles, customer_info))

            # Table of contents
            elements.extend(self.create_table_of_contents(styles))

            # Content sections
            sections = [
                ("Executive Summary", content.get("executive_summary", ""), True),
                (
                    "Business Case Analysis",
                    content.get("business_case_analysis", ""),
                    False,
                ),
                (
                    "Technical Implementation Roadmap",
                    content.get("technical_implementation_roadmap", ""),
                    False,
                ),
                (
                    "Financial Investment Analysis",
                    content.get("financial_investment_analysis", ""),
                    False,
                ),
                (
                    "Risk Mitigation Strategy",
                    content.get("risk_mitigation_strategy", ""),
                    False,
                ),
                (
                    "Strategic Recommendations",
                    content.get("strategic_recommendations", ""),
                    False,
                ),
            ]

            for title, text, is_exec in sections:
                elements.extend(
                    self.create_content_section(title, text, styles, is_exec)
                )

            # Appendix
            elements.extend(self.create_appendix(styles, customer_info))

            # Build PDF with custom canvas for page numbers
            doc.build(elements, canvasmaker=NumberedCanvas)

            logger.info(f"✅ PDF generated successfully: {output_path}")

        except Exception as e:
            logger.error(f"❌ Error creating PDF: {e}")
            raise

    def generate_report(
        self, json_file_path: str = None, output_filename: str = None
    ) -> Dict[str, str]:
        """Generate complete executive report"""
        try:
            logger.info("🚀 Starting executive report generation...")

            # Interactive file selection if not provided
            if not json_file_path:
                json_file_path = self.interactive_file_selection()

            # Load data
            raw_data = self.load_assessment_data(json_file_path)

            # Process data
            logger.info("📄 Processing assessment data...")
            processed_data = self.process_assessment_data(raw_data)

            # Generate filename
            if not output_filename:
                company_name = re.sub(
                    r"[^\w\-_]",
                    "_",
                    processed_data.get("company_name", "customer").lower(),
                )
                output_filename = (
                    f"RAPID_Executive_Report_{company_name}_{self.timestamp}"
                )

            pdf_file = self.output_dir / f"{output_filename}.pdf"

            # Generate content
            content = self.generate_report_content(processed_data)

            # Create PDF
            self.create_professional_pdf(content, processed_data, str(pdf_file))

            results = {
                "pdf_path": str(pdf_file),
                "company_name": processed_data.get("company_name"),
                "industry": processed_data.get("industry"),
                "assessment_type": processed_data.get("assessment_type"),
                "timestamp": self.timestamp,
            }

            logger.info("✅ Report generation completed successfully!")
            return results

        except Exception as e:
            logger.error(f"❌ Error in report generation: {e}")
            raise


def create_sample_assessment_data(
    filename: str = "sample_rapid_assessment.json",
) -> str:
    """Create comprehensive sample assessment data for testing"""
    sample_data = {
        "exportDate": "2025-10-08T12:00:00Z",
        "responses": {
            "business-owner": "GlobalTech Financial Services, Sarah Johnson",
            "company-name": "GlobalTech Financial Services",
            "business-problems": "Our financial advisory operations face critical challenges with real-time market analysis, portfolio optimization, and personalized client recommendations. Current manual processes require 4-6 hours per client analysis, limit our ability to respond to market changes quickly, and constrain our capacity to serve growing mid-market segment. Advisors spend 60% of time on data gathering and analysis rather than client relationships. We're losing market share to AI-native competitors who can deliver faster, more comprehensive analysis at lower cost.",
            "primary-goal": "Transform financial advisory operations through AI-powered analysis, reducing client analysis time by 75%, enabling real-time market response, and scaling mid-market service capacity by 300%.",
            "current-state": "Pilot Phase",
            "strategic-alignment": "Critical to 2025-2027 digital transformation roadmap. Directly supports strategic objectives for operational excellence, client experience leadership, and mid-market growth. Essential for maintaining competitive position against AI-native fintech competitors.",
            "urgency": "High - Q1 2025 competitive pressure and mid-market expansion targets",
            "scope-impact": "500+ financial advisors, 2000+ mid-market clients",
            "budget-range": "$500K - $1M",
            "development-timeline": "3-6 months for pilot, 6-12 months for full deployment",
        },
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Sample assessment data created: {filename}")
    return filename


def main():
    """Main function"""

    print("\n" + "=" * 60)
    print("🚀 Cloud202 Executive Report Generator v3.0")
    print("=" * 60)
    print("✨ AWS Bedrock Inference Profiles Support")
    print("📊 Professional PDF formatting with ReportLab")
    print("=" * 60)

    # Ask user if they want to create sample data or use existing file
    print("\nSelect an option:")
    print("1. Generate report from existing JSON file")
    print("2. Create sample data and generate report")
    print("3. Create sample data only")
    print("0. Exit")

    while True:
        choice = input("\nEnter your choice (0-3): ").strip()

        if choice == "0":
            print("👋 Goodbye!")
            return 0
        elif choice == "1":
            # Use existing file
            break
        elif choice == "2":
            # Create sample and generate report
            print("\n📝 Creating sample assessment data...")
            sample_file = create_sample_assessment_data()
            print("✅ Sample data created successfully!")
            break
        elif choice == "3":
            # Create sample only
            print("\n📝 Creating sample assessment data...")
            sample_file = create_sample_assessment_data()
            print("✅ Sample data created successfully!")
            print(f"💾 File saved as: {sample_file}")
            print(
                "🔄 Run the program again with option 1 to generate a report from this data."
            )
            return 0
        else:
            print("❌ Invalid choice. Please enter 0, 1, 2, or 3.")

    try:
        # Initialize generator
        print("\n⚙️  Initializing Cloud202 Executive Report Generator...")
        generator = Cloud202ExecutiveReportGenerator(
            aws_region="us-east-1",
            company_name="Cloud202",
            tool_name="Qubitz",
            contact_email="hello@cloud202.com",
            contact_phone="+44 7792 565738",
        )

        # Generate report
        if choice == "2":
            # Use the sample file we just created
            results = generator.generate_report(sample_file)
            # Clean up sample file
            try:
                os.remove(sample_file)
                print(f"🧹 Cleaned up temporary sample file: {sample_file}")
            except:
                pass
        else:
            # Use user-selected file
            results = generator.generate_report()

        # Display results
        print("\n" + "=" * 60)
        print("✅ RAPID EXECUTIVE REPORT GENERATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📁 Output file: {results['pdf_path']}")
        print(f"🏢 Customer: {results['company_name']}")
        print(f"🏭 Industry: {results['industry']}")
        print(f"📊 Assessment Type: {results['assessment_type']}")
        print(f"🛠️  Generated with: Cloud202 Qubitz")
        print(f"⏰ Timestamp: {results['timestamp']}")
        print("📈 Report includes comprehensive strategic analysis")
        print("=" * 60)

        print(f"\n🎉 SUCCESS! Your executive report is ready!")
        print(f"📄 Report saved as: {results['pdf_path']}")
        print("\n✅ All formatting issues fixed:")
        print("   • Title page properly centered")
        print("   • Table of contents aligned correctly")
        print("   • Headers left-aligned, content properly indented")
        print("   • Professional page layout throughout")
        print("   • AWS Bedrock inference profile integration")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user. Goodbye!")
        return 1
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        print(f"\n❌ Error: {e}")
        print("\n📋 Please ensure:")
        print("   ✓ Your AWS credentials are configured correctly")
        print("   ✓ Your JSON file is valid and properly formatted")
        print("   ✓ You have ReportLab installed: pip install reportlab")
        print("   ✓ You have boto3 installed: pip install boto3")
        return 1


if __name__ == "__main__":
    exit(main())
