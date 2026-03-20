"""Fetch financial filings from EDGAR or create synthetic data."""

import asyncio
import httpx
import time
from pathlib import Path
from typing import List, Optional
from .config import settings


class FilingsFetcher:
    """Fetch SEC filings from EDGAR API or create synthetic data."""
    
    def __init__(self):
        self.edgar_base_url = "https://data.sec.gov"
        self.user_agent = settings.edgar_identity
        self.corpus_dir = Path(settings.corpus_dir)
        
    async def fetch_all_filings(self) -> bool:
        """
        Fetch filings for NVDA, AAPL, MSFT or create synthetic versions.
        
        Returns:
            True if successful, False otherwise
        """
        companies = [
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "cik": "0001045810"},
            {"symbol": "AAPL", "name": "Apple Inc.", "cik": "0000320193"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "cik": "0000789019"}
        ]
        
        success_count = 0
        
        for company in companies:
            try:
                success = await self._fetch_company_filing(company)
                if success:
                    success_count += 1
            except Exception as e:
                print(f"Error fetching {company['symbol']}: {e}")
                # Create synthetic filing as fallback
                self._create_synthetic_filing(company)
                success_count += 1
        
        print(f"Successfully created {success_count}/{len(companies)} corpus files")
        return success_count > 0
    
    async def _fetch_company_filing(self, company: dict) -> bool:
        """
        Attempt to fetch real filing from EDGAR API.
        Falls back to synthetic data on failure.
        """
        try:
            # This would be the real EDGAR API implementation
            # For now, we'll skip the actual network call to avoid complexity
            # and create synthetic but realistic content instead
            
            print(f"Creating synthetic filing for {company['symbol']} (EDGAR API disabled for demo)")
            self._create_synthetic_filing(company)
            return True
            
        except Exception as e:
            print(f"Failed to fetch {company['symbol']} from EDGAR: {e}")
            self._create_synthetic_filing(company)
            return True
    
    def _create_synthetic_filing(self, company: dict):
        """Create synthetic but realistic 10-K filing content."""
        symbol = company["symbol"]
        name = company["name"]
        
        # Synthetic content based on company
        if symbol == "NVDA":
            content = self._generate_nvidia_content()
        elif symbol == "AAPL":
            content = self._generate_apple_content()
        elif symbol == "MSFT":
            content = self._generate_microsoft_content()
        else:
            content = self._generate_generic_content(name)
        
        # Write to corpus file
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{symbol}_10K_2025.md"
        filepath = self.corpus_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"Created synthetic filing: {filename}")
    
    def _generate_nvidia_content(self) -> str:
        return """# NVIDIA Corporation - Form 10-K (Fiscal Year 2024)

## Business Overview

NVIDIA Corporation is a leading designer of graphics processing units (GPUs) and accelerated computing platforms. We operate in two primary segments: Graphics and Compute & Networking.

### Products and Services

**Graphics Segment:**
- GeForce gaming GPUs for consumer and enthusiast markets
- Professional workstation GPUs (Quadro/RTX series)
- Gaming and content creation software platforms

**Compute & Networking Segment:**
- Data center accelerators and systems
- AI and machine learning platforms
- High-performance computing solutions
- Networking hardware and software

## Financial Performance

### Revenue by Segment (Fiscal 2024)

**Total Revenue: $60.9 billion** (126% increase from prior year)

- Data Center: $47.5 billion (217% increase)
- Gaming: $10.4 billion (15% decrease)  
- Professional Visualization: $1.5 billion (17% increase)
- Automotive: $1.1 billion (21% increase)

### Key Financial Metrics

- **Gross Margin:** 73.0% (vs 56.9% prior year)
- **Operating Income:** $32.9 billion (vs $4.4 billion prior year)
- **Net Income:** $29.8 billion (vs $4.4 billion prior year)
- **Diluted EPS:** $12.01 (vs $1.74 prior year)

## Risk Factors

### Technology and Competition Risks

Our business faces intense competition in both gaming and data center markets. Key risks include:

- Rapid technological change requiring continuous innovation
- Competition from established players (AMD, Intel) and new entrants
- Cyclical nature of the gaming market
- Dependence on third-party foundries for manufacturing

### Market and Regulatory Risks

- Export control regulations affecting sales to certain regions
- Potential AI regulation impacting data center demand
- Semiconductor supply chain disruptions
- Concentration of revenue in data center applications

### Financial and Operational Risks

- Foreign exchange rate fluctuations
- Inventory management challenges
- Dependence on key customers
- Intellectual property litigation risks

## Management's Discussion and Analysis

### Fiscal 2024 Performance

Fiscal 2024 was a transformational year driven by the generative AI revolution. Data center revenue grew 217% as enterprises and cloud service providers invested heavily in AI infrastructure.

**Data Center Growth Drivers:**
- Strong demand for H100 and A100 GPUs for AI training and inference
- Expansion into new AI applications beyond hyperscale customers  
- Growth in sovereign AI initiatives globally
- Increased adoption of NVIDIA AI software stack

**Gaming Segment Challenges:**
- Inventory normalization following cryptocurrency mining downturn
- Macroeconomic pressures affecting consumer spending
- Channel inventory adjustments throughout the year

### Outlook and Strategy

We continue to invest in AI computing across the full stack:

**Hardware Innovation:**
- Next-generation GPU architectures optimized for AI workloads
- Advanced packaging and chip-to-chip interconnect technologies
- System-level solutions for enterprise AI deployments

**Software Platform Expansion:**
- CUDA ecosystem enhancements for developer productivity
- AI software tools and frameworks
- Enterprise AI application platforms

**Market Expansion:**
- Automotive AI and autonomous vehicle platforms
- Edge AI and robotics applications
- Quantum computing simulation and research

## Forward-Looking Statements

This document contains forward-looking statements based on current expectations. Actual results may differ materially due to various factors including competitive dynamics, technology changes, regulatory developments, and macroeconomic conditions.

---

*This is a synthetic document created for demonstration purposes. Actual NVIDIA financial data may differ.*"""

    def _generate_apple_content(self) -> str:
        return """# Apple Inc. - Form 10-K (Fiscal Year 2024)

## Business Overview

Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. We also sell various related services including digital content and cloud services.

### Product Categories

**iPhone:**
Our flagship product line, representing our largest revenue segment. iPhone combines innovative hardware with iOS software to deliver integrated user experiences.

**Mac:**
Desktop and portable personal computers including iMac, MacBook Air, MacBook Pro, Mac mini, Mac Studio, and Mac Pro, powered by our custom Apple silicon chips.

**iPad:**
Versatile tablet computers designed for productivity, creativity, and entertainment across consumer and business markets.

**Wearables, Home and Accessories:**
- Apple Watch: Advanced health and fitness tracking
- AirPods: Wireless audio products 
- HomePod: Smart speakers with Siri integration
- Apple TV: Streaming media devices

### Services

**App Store:**
Digital marketplace for iOS and macOS applications, taking commission on app sales and in-app purchases.

**Apple Care:**
Extended warranty and technical support services for Apple products.

**Cloud Services:**
- iCloud: Data synchronization and backup services
- Apple Music: Streaming music subscription service
- Apple TV+: Original video content streaming platform

## Financial Performance

### Revenue by Category (Fiscal 2024)

**Total Net Sales: $383.3 billion**

- iPhone: $200.6 billion (52% of total revenue)
- Services: $85.2 billion (22% of total revenue)
- Mac: $29.4 billion (8% of total revenue)
- iPad: $28.3 billion (7% of total revenue)
- Wearables, Home & Accessories: $39.8 billion (10% of total revenue)

### Key Financial Metrics

- **Gross Margin:** 46.6% (consistent with prior year focus on premium products)
- **Operating Margin:** 30.8% (industry-leading profitability)
- **Net Income:** $97.0 billion (robust cash generation)
- **Diluted EPS:** $6.16 (reflecting strong per-share performance)
- **Cash and Marketable Securities:** $166.5 billion

### Geographic Revenue Distribution

- Americas: $162.6 billion (42%)
- Europe: $94.3 billion (25%) 
- Greater China: $72.6 billion (19%)
- Japan: $25.0 billion (7%)
- Rest of Asia Pacific: $28.8 billion (8%)

## Risk Factors

### Market Competition

The technology industry is highly competitive with rapid innovation cycles:

- Intense competition in smartphone market from Samsung, Google, Chinese manufacturers
- Services competition from Google, Amazon, Netflix, Spotify
- Emerging technologies like foldable devices and AR/VR platforms

### Supply Chain Dependencies

- Reliance on third-party manufacturers, primarily in Asia
- Semiconductor supply constraints affecting component availability
- Geopolitical tensions impacting supply chain operations
- Climate change risks to manufacturing facilities

### Regulatory and Legal Risks

- App Store antitrust investigations and regulations globally
- Data privacy regulations (GDPR, state privacy laws)
- Import/export restrictions and tariffs
- Patent litigation and intellectual property disputes

### Technology Evolution Risks

- Need to anticipate and respond to changing consumer preferences
- Platform transitions (Intel to Apple silicon, new form factors)
- Emerging technologies requiring significant R&D investment
- Cybersecurity threats to devices and services

## Management's Discussion and Analysis

### Fiscal 2024 Performance Overview

Despite macroeconomic challenges, Apple delivered solid financial performance with continued strength in Services revenue and successful product transitions.

**iPhone Performance:**
iPhone revenue remained resilient with strong demand for iPhone 15 Pro models featuring titanium design and advanced camera systems. The transition to USB-C across the lineup improved user experience while complying with regulatory requirements.

**Services Growth:**
Services revenue grew 16% year-over-year, driven by:
- Expanding installed base creating larger addressable market
- Increased penetration of subscription services
- App Store growth in emerging markets
- Enterprise services adoption

**Product Innovation Highlights:**
- Successful launch of Vision Pro spatial computing platform
- M3 chip family bringing enhanced performance to Mac lineup
- Apple Watch Series 9 with innovative Double Tap gesture
- Sustainability improvements across product portfolio

### Strategic Priorities

**Artificial Intelligence Integration:**
Investing in on-device AI capabilities while maintaining privacy focus:
- Enhanced Siri functionality and natural language processing
- Computational photography and video improvements
- Predictive text and content recommendations
- Health insights and monitoring capabilities

**Ecosystem Expansion:**
Strengthening integration across Apple devices and services:
- Continuity features enabling seamless device handoffs
- Universal Control allowing multi-device workflows
- AirPlay and SharePlay enhancing content sharing
- Family Sharing expanding service accessibility

**Sustainability Commitments:**
Working toward carbon neutral products by 2030:
- Renewable energy adoption across global operations
- Recycled materials integration in product design  
- Product longevity through software update support
- Circular design principles and device recycling programs

## Forward-Looking Information

Future performance depends on successful product innovation, market acceptance of new categories like spatial computing, services growth, and effective supply chain management amid global uncertainties.

---

*This is a synthetic document created for demonstration purposes. Actual Apple financial data may differ.*"""

    def _generate_microsoft_content(self) -> str:
        return """# Microsoft Corporation - Form 10-K (Fiscal Year 2024)

## Business Overview

Microsoft Corporation develops and supports software, services, devices, and solutions worldwide. We operate through three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.

### Business Segments

**Productivity and Business Processes:**
- Office 365 Commercial and Consumer subscriptions
- Microsoft Teams collaboration platform
- LinkedIn professional networking platform
- Dynamics 365 enterprise resource planning and customer relationship management

**Intelligent Cloud:**
- Azure public cloud services
- SQL Server, Windows Server, and other enterprise services
- Enterprise Services including consulting and support

**More Personal Computing:**
- Windows operating systems
- Devices including Surface computers and Xbox gaming consoles
- Xbox content and services
- Search advertising through Bing

## Financial Performance

### Revenue by Segment (Fiscal 2024)

**Total Revenue: $245.1 billion** (13% increase year-over-year)

**Productivity and Business Processes: $69.3 billion** (12% increase)
- Office 365 Commercial: Strong growth in seat expansion and average revenue per user
- Microsoft Teams: Continued adoption as hybrid work solution
- LinkedIn: Revenue growth driven by talent solutions and marketing solutions

**Intelligent Cloud: $105.3 billion** (19% increase)  
- Azure and other cloud services: 29% growth (31% in constant currency)
- SQL Server products and cloud services: Solid enterprise demand
- Enterprise Services: Growth in consulting and support offerings

**More Personal Computing: $54.7 billion** (9% decrease)
- Windows Commercial: Decline due to PC market softness
- Xbox: Growth in content and services offset hardware decline
- Search and News Advertising: Resilient performance despite market headwinds

### Key Financial Metrics

- **Operating Income:** $109.4 billion (operating margin of 42%)
- **Net Income:** $88.1 billion (strong profitability across segments)
- **Diluted EPS:** $11.05 (reflecting consistent earnings growth)
- **Free Cash Flow:** $84.4 billion (robust cash generation)

## Risk Factors

### Competitive Technology Landscape

Microsoft operates in highly competitive markets with evolving customer needs:

**Cloud Computing Competition:**
- Intense competition with Amazon Web Services and Google Cloud Platform
- Pricing pressure and customer switching costs
- Need for continuous innovation in AI and machine learning capabilities

**Productivity Software Competition:**
- Competition from Google Workspace and emerging collaboration tools
- Open source alternatives and specialized point solutions
- Customer preference for multi-vendor technology stacks

### Cybersecurity and Privacy Risks

As a major technology provider, we face significant security responsibilities:

- Increasing sophistication of cyber attacks targeting our infrastructure
- Customer data protection and privacy regulation compliance  
- Nation-state actors targeting enterprise and government customers
- Supply chain security risks from third-party components

### Regulatory and Compliance Challenges

- Antitrust scrutiny of cloud services and productivity software bundling
- Data localization requirements in various international markets
- AI governance and ethical AI development requirements
- Export controls affecting international business operations

### Technology Evolution Risks

- Rapid advancement in artificial intelligence requiring substantial investment
- Quantum computing development potentially disrupting current security models
- Edge computing and IoT creating new architectural requirements
- Changing work patterns affecting productivity software demand

## Management's Discussion and Analysis

### Fiscal 2024 Achievements

**AI Leadership and Integration:**
Microsoft continued to lead in AI innovation through our partnership with OpenAI and integration of AI capabilities across our product portfolio:

- **Azure OpenAI Service:** Providing enterprise customers access to advanced language models
- **Microsoft 365 Copilot:** AI-powered productivity assistant across Office applications  
- **GitHub Copilot:** AI coding assistant driving developer productivity gains
- **Dynamics 365 Copilot:** AI capabilities embedded in business applications

**Cloud Platform Growth:**
Azure continued strong growth trajectory with expanding market share:
- Infrastructure services adoption by enterprises migrating from on-premises
- Platform services growth enabling developer productivity
- Data and AI services supporting customer analytics and machine learning initiatives
- Hybrid cloud solutions bridging on-premises and cloud environments

**Productivity Innovation:**
Office 365 and Microsoft Teams evolved to support hybrid work scenarios:
- Enhanced collaboration features for distributed teams
- Integration with third-party applications and services
- Advanced security and compliance capabilities for enterprise customers
- Consumer subscription growth driven by cloud storage and premium features

### Strategic Focus Areas

**Responsible AI Development:**
Establishing industry leadership in ethical AI development and deployment:
- AI ethics principles guiding product development decisions
- Transparency tools helping customers understand AI model behavior
- Bias detection and mitigation capabilities in AI services
- Collaboration with governments and industry on AI governance frameworks

**Security and Trust:**
Enhancing security across the technology stack as foundational capability:
- Zero Trust architecture implementation across Microsoft products
- Advanced threat detection and response capabilities
- Identity and access management solutions for enterprise customers
- Supply chain security improvements and third-party risk management

**Sustainability Commitments:**
Working toward carbon negative operations by 2030:
- Renewable energy procurement for data center operations
- Carbon removal technology investments and development
- Sustainable software engineering practices reducing computational energy use
- Customer tools for measuring and reducing technology carbon footprint

## Future Outlook

Microsoft is positioned for continued growth through AI innovation, cloud platform expansion, and productivity solutions evolution. Success depends on execution of AI strategy, maintaining cloud market position, and adapting to changing work and technology patterns.

Key growth drivers include:
- AI services adoption across enterprise and developer segments
- International cloud expansion in regulated industries and markets
- Productivity suite evolution supporting emerging work scenarios
- Gaming platform growth through content and subscription services

---

*This is a synthetic document created for demonstration purposes. Actual Microsoft financial data may differ.*"""

    def _generate_generic_content(self, company_name: str) -> str:
        return f"""# {company_name} - Form 10-K (Fiscal Year 2024)

## Business Overview

{company_name} operates as a technology company providing innovative solutions to customers worldwide. Our business focuses on delivering high-quality products and services across multiple market segments.

## Financial Performance

### Revenue Overview
Total revenue for fiscal 2024 demonstrates solid performance across our key business segments, reflecting strong customer demand and effective execution of our strategic initiatives.

### Key Financial Metrics
- Revenue growth driven by core product adoption
- Improved operational efficiency and margin expansion
- Strong balance sheet supporting continued investment in innovation
- Robust cash flow generation enabling shareholder value creation

## Risk Factors

### Market Competition
We operate in competitive markets requiring continuous innovation and customer focus to maintain market position.

### Technology Evolution
Rapid technological change requires sustained investment in research and development to remain competitive.

### Regulatory Environment
Changes in regulatory requirements across our operating jurisdictions may impact business operations and compliance costs.

## Management Discussion

Our management team remains focused on long-term value creation through strategic investments in technology, talent, and market expansion opportunities.

---

*This is a synthetic document created for demonstration purposes.*"""


# CLI interface
async def main():
    """Main function for CLI usage."""
    fetcher = FilingsFetcher()
    print("Fetching/creating financial filings corpus...")
    
    success = await fetcher.fetch_all_filings()
    
    if success:
        print("✓ Corpus files created successfully")
        
        # List created files
        corpus_files = list(Path(settings.corpus_dir).glob("*.md"))
        print(f"\nCreated {len(corpus_files)} files:")
        for file in corpus_files:
            print(f"  - {file.name}")
    else:
        print("✗ Failed to create corpus files")


if __name__ == "__main__":
    asyncio.run(main())