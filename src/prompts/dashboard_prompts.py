"""
Dashboard Generation Prompts
Implements structured prompt engineering for investment analysis dashboard generation.
"""

from typing import List, Dict


def get_dashboard_system_prompt() -> str:
    """
    Generate the system prompt for dashboard generation.
    
    Follows prompt engineering best practices:
    - Clear role definition
    - Explicit constraints and guidelines
    - Structured output format specification
    - Quality standards
    """
    return """You are an expert investment analyst specializing in private AI and Fintech startups. Your role is to generate comprehensive, investor-facing diligence dashboards that provide actionable insights for investment decision-making.

## Your Expertise
- Deep understanding of startup valuation, funding dynamics, and market analysis
- Ability to synthesize information from multiple sources into coherent insights
- Strong analytical skills for identifying risks, opportunities, and market positioning
- Knowledge of investor information needs and due diligence requirements

## Task
Generate a structured investment analysis dashboard for a private AI/Fintech startup using ONLY the provided context data. The dashboard must be professional, accurate, and suitable for investor review.

## Output Format Requirements

You MUST generate exactly 8 sections in the following order, using the exact section headers:

### 1. ## Company Overview
Provide a concise summary of:
- Company name and core mission
- Primary business focus and value proposition
- Key differentiators and market positioning
- Founding story or background (if available)

### 2. ## Business Model and GTM
Analyze and present:
- Revenue model and monetization strategy
- Target customer segments
- Go-to-market approach and distribution channels
- Pricing strategy (if disclosed)
- Key partnerships or strategic relationships

### 3. ## Funding & Investor Profile
Document:
- Funding history (rounds, amounts, dates if available)
- Current investors and their profiles
- Valuation information (if disclosed)
- Use of funds or strategic direction indicated by funding

### 4. ## Growth Momentum
Assess:
- Hiring trends and team expansion
- Product development milestones
- Market traction indicators
- Customer growth signals
- Geographic expansion or market entry

### 5. ## Visibility & Market Sentiment
Evaluate:
- Media coverage and press mentions
- Industry recognition and awards
- Public perception and brand visibility
- Thought leadership activities
- Community engagement

### 6. ## Risks and Challenges
Identify:
- Competitive landscape and market risks
- Operational challenges
- Regulatory or compliance considerations
- Technology or product risks
- Market timing or adoption risks

### 7. ## Outlook
Provide forward-looking analysis:
- Strategic direction and future plans
- Market opportunities
- Growth potential
- Competitive positioning
- Key success factors

### 8. ## Disclosure Gaps
List specific information that is:
- Not available in the provided context
- Critical for investment decision-making
- Would require additional research or direct inquiry

## Critical Guidelines

1. **Data Fidelity**: Use ONLY information from the provided context. Do not infer, assume, or add information not explicitly stated.

2. **Missing Information**: If information is not available in the context, explicitly state "Not disclosed." Do not use placeholder text, estimates, or generic statements.

3. **Accuracy**: Ensure all facts, figures, and claims are directly supported by the provided context. Cite specific sources when possible.

4. **Professional Tone**: Maintain a professional, objective, and analytical tone suitable for investor review. Avoid speculation or unsubstantiated claims.

5. **Completeness**: Every section must contain substantive content. If a section has limited data, explain what is known and what is missing.

6. **Structure**: Use clear markdown formatting with proper headers, bullet points, and paragraphs for readability.

7. **Context Awareness**: Synthesize information across multiple sources to provide comprehensive insights, but always ground conclusions in the provided data.

8. **Bias Avoidance**: Present balanced analysis including both strengths and weaknesses. Do not overstate positive aspects or ignore risks.

## Quality Standards

- Each section should be 2-5 paragraphs or equivalent bullet points
- Use specific details, numbers, and examples when available
- Connect insights across sections to show a cohesive narrative
- Highlight the most important and actionable information prominently
- Ensure the dashboard tells a complete story about the company's investment profile

Remember: Your goal is to provide investors with a clear, accurate, and comprehensive view of the company that enables informed decision-making."""


def format_context_for_prompt(company_name: str, chunks: List[Dict]) -> str:
    """
    Format retrieved chunks into a well-structured context for the LLM.
    
    This function implements best practices for RAG context formatting:
    - Clear section headers
    - Source attribution
    - Chunk ordering
    - Metadata preservation
    
    Args:
        company_name: Name of the company being analyzed
        chunks: List of chunk dictionaries with 'text', 'source_type', 'source_url', etc.
    
    Returns:
        Formatted context string ready for inclusion in user prompt
    """
    if not chunks:
        return f"# Company Data: {company_name}\n\n**Status**: No data available in the knowledge base.\n\nAll sections should indicate 'Not disclosed.'"
    
    # Group chunks by source type for better organization
    by_source = {}
    for chunk in chunks:
        source = chunk.get('source_type', 'unknown')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(chunk)
    
    # Build formatted context
    context_parts = [
        f"# Company Data: {company_name}",
        f"",
        f"**Total Context Chunks**: {len(chunks)}",
        f"**Source Types**: {', '.join(sorted(by_source.keys()))}",
        f"",
        f"---",
        f"",
        f"## Context Information",
        f"",
        f"The following information has been retrieved from the company's public sources. Use this information to generate the investment analysis dashboard.",
        f"",
    ]
    
    # Add chunks grouped by source type
    for source_type in sorted(by_source.keys()):
        source_chunks = sorted(by_source[source_type], key=lambda x: x.get('chunk_index', 0))
        
        context_parts.append(f"### Source: {source_type.upper()}")
        context_parts.append(f"")
        
        for idx, chunk in enumerate(source_chunks, 1):
            chunk_text = chunk.get('text', '').strip()
            if not chunk_text:
                continue
                
            chunk_index = chunk.get('chunk_index', idx - 1)
            source_url = chunk.get('source_url', 'N/A')
            
            context_parts.append(f"**Chunk {chunk_index + 1}** (from {source_type}):")
            context_parts.append(f"Source URL: {source_url}")
            context_parts.append(f"")
            context_parts.append(chunk_text)
            context_parts.append(f"")
        
        context_parts.append("---")
        context_parts.append("")
    
    context_parts.append("## Instructions")
    context_parts.append("")
    context_parts.append("Using the context above, generate a comprehensive investment analysis dashboard following the specified format.")
    context_parts.append("Remember to:")
    context_parts.append("- Use only information from the context provided")
    context_parts.append("- State 'Not disclosed.' for any missing information")
    context_parts.append("- Provide specific details and examples when available")
    context_parts.append("- Maintain professional, analytical tone")
    
    return "\n".join(context_parts)


def get_dashboard_user_prompt(company_name: str, context: str) -> str:
    """
    Generate the user prompt for dashboard generation.
    
    Implements prompt engineering best practices:
    - Clear task specification
    - Context integration
    - Output requirements
    - Chain of thought guidance
    
    Args:
        company_name: Name of the company to analyze
        context: Formatted context string from format_context_for_prompt()
    
    Returns:
        Complete user prompt ready for LLM
    """
    return f"""Generate a comprehensive investment analysis dashboard for **{company_name}**.

## Your Task

Analyze the provided context data and create an 8-section investment diligence dashboard that provides investors with a complete view of the company's investment profile.

## Context Data

{context}

## Output Requirements

1. Generate all 8 required sections in the exact order specified
2. Use the exact section headers: ## Company Overview, ## Business Model and GTM, etc.
3. Base all content strictly on the provided context
4. For any missing information, explicitly state "Not disclosed."
5. Provide specific details, numbers, and examples when available
6. Maintain professional, analytical tone throughout
7. Ensure each section contains substantive content (2-5 paragraphs or equivalent)

## Analysis Approach

1. **Synthesize**: Combine information from multiple sources to build a complete picture
2. **Prioritize**: Highlight the most important and actionable insights
3. **Balance**: Present both strengths and areas of concern
4. **Ground**: Ensure all claims are supported by the provided context
5. **Complete**: Address all aspects of each section, noting gaps where information is missing

Begin generating the dashboard now."""


# ========== CHAT INTERFACE PROMPTS ==========

def get_chat_system_prompt() -> str:
    """System prompt for the chat interface."""
    return """You are an expert investment analyst assistant specializing in private AI and Fintech startups. You help users understand companies in the InvestIQ database by answering questions and providing insights.

## Your Capabilities

1. **General Knowledge**: You can answer general questions about startups, investment analysis, and business concepts using your training data.

2. **Company-Specific Data**: When users ask about specific companies, you can retrieve relevant information from the InvestIQ knowledge base. The system will automatically retrieve relevant chunks when needed.

3. **Analysis**: You can synthesize information, provide insights, and help users understand investment opportunities and risks.

## Guidelines

- Be conversational, helpful, and professional
- When discussing companies, base your answers on retrieved context when available
- If you don't have specific information, say so clearly
- Cite sources when referencing retrieved data
- Help users understand complex investment concepts
- Ask clarifying questions if needed

## Available Companies

The system has data on 50+ AI and Fintech startups. When users mention a company name, the system will retrieve relevant information automatically."""


def format_chat_context(company_name: str, chunks: List[Dict]) -> str:
    """Format retrieved chunks for chat context."""
    if not chunks:
        return f"**No data available** for {company_name} in the knowledge base."
    
    context_parts = [
        f"## Retrieved Information for {company_name}",
        f"**{len(chunks)} relevant chunks found:**",
        f"",
    ]
    
    for idx, chunk in enumerate(chunks[:10], 1):
        source_type = chunk.get('source_type', 'unknown')
        source_url = chunk.get('source_url', 'N/A')
        text = chunk.get('text', '').strip()
        
        if text:
            context_parts.append(f"### Chunk {idx} ({source_type})")
            context_parts.append(f"Source: {source_url}")
            context_parts.append("")
            if len(text) > 500:
                text = text[:500] + "..."
            context_parts.append(text)
            context_parts.append("")
    
    if len(chunks) > 10:
        context_parts.append(f"*... and {len(chunks) - 10} more chunks*")
    
    return "\n".join(context_parts)


def get_retrieval_decision_prompt(user_message: str, conversation_history: List[Dict], available_companies: List[str]) -> str:
    """Prompt for LLM to decide if retrieval is needed."""
    companies_str = ", ".join(available_companies[:20])
    
    return f"""Analyze this question to determine if it needs company-specific data from the knowledge base.

Available Companies: {companies_str}{f" ... and {len(available_companies) - 20} more" if len(available_companies) > 20 else ""}

User Question: {user_message}

Conversation History:
{_format_conversation_history(conversation_history[-5:]) if conversation_history else "No previous messages"}

Respond in JSON format:
{{
    "needs_retrieval": true/false,
    "company_name": "company-name" or null,
    "search_query": "query string" or null,
    "reasoning": "brief explanation"
}}

Guidelines:
- Set needs_retrieval=true if asking about specific company details (funding, business model, products, team, etc.)
- Set needs_retrieval=false for general knowledge questions
- If needs_retrieval=true, extract company name (lowercase with hyphens) and create a search query (3-10 words)

Respond ONLY with valid JSON."""


def _format_conversation_history(history: List[Dict]) -> str:
    """Format conversation history for prompts."""
    if not history:
        return ""
    formatted = []
    for msg in history:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        formatted.append(f"{role.upper()}: {content}")
    return "\n".join(formatted)

