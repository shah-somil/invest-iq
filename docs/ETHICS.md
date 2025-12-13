# Ethical Guidelines and Considerations

This document outlines the ethical considerations, limitations, and responsible use practices for the InvestIQ project.

## Copyright and Intellectual Property

### Data Sources

1. **Seed Company Lists**
   - We use seed JSON files (`top_ai50_seed.json`, `top_fintech50_seed.json`) containing lists of top AI and Fintech companies
   - These files contain company names, websites, and metadata
   - Used to identify companies for further research and analysis

2. **Company Website Content**
   - We scrape publicly accessible pages (homepage, about, product, careers, blog) from company websites
   - Content is used for **analysis and research purposes only**
   - We do not redistribute scraped content commercially
   - All scraped HTML/text is stored locally for analysis

### Fair Use Considerations

- **Purpose**: Educational/research use for investment analysis
- **Nature**: Transformative use (analysis, not reproduction)
- **Amount**: Limited to necessary sections (homepage, about, product, careers, blog)
- **Effect**: No commercial redistribution of original content

### Attribution

- All data sources are documented in [README.md](README.md)
- Source URLs are preserved in metadata files (`metadata.json`, `pages.jsonl`)
- When presenting results, we acknowledge data sources

## Bias, Fairness, and Representation

### Potential Biases

1. **Source Bias**
   - **List Selection Bias**: Companies in our seed lists may have inherent biases toward:
     - Well-funded companies
     - US-based companies
     - Companies with strong PR/marketing
     - Companies in specific sectors or stages
   - **Mitigation**: We acknowledge this limitation and note that our dataset reflects the selection criteria of the source lists, not a comprehensive market view

2. **Geographic Bias**
   - Initial lists may over-represent certain regions (e.g., Silicon Valley)
   - **Mitigation**: We preserve geographic metadata (HQ city/country) to enable analysis of representation

3. **Language Bias**
   - Scraping primarily English-language content
   - Companies with non-English websites may be underrepresented
   - **Mitigation**: We attempt to handle multilingual content but acknowledge limitations

4. **Temporal Bias**
   - Lists are snapshots in time
   - Company information may become outdated
   - **Mitigation**: We timestamp all scraped data (`crawled_at` field)

5. **Selection Bias**
   - Only companies that appear in our seed lists are included
   - Smaller or less-publicized companies may be excluded
   - **Mitigation**: We document this limitation clearly

### Fairness Considerations

- We do not filter or exclude companies based on protected characteristics
- Analysis should consider that the dataset is not representative of all companies in these sectors
- Results should be interpreted in context of the source data limitations

## System Limitations

### Technical Limitations

1. **Scraping Limitations**
   - Cannot access authenticated/paywalled content
   - May miss dynamically loaded content (JavaScript-heavy sites)
   - Rate limiting (0.5s delay) means collection is slow
   - Some websites may block automated access

2. **Data Quality**
   - HTML parsing may miss some structured data
   - Text extraction may include navigation/boilerplate
   - Some company websites may be unavailable or change structure

3. **Coverage**
   - Only scrapes 5 sections per company (homepage, about, product, careers, blog)
   - May miss important information in other sections
   - Does not include social media, news articles, or third-party data

### Analytical Limitations

1. **Static Analysis**
   - Data is a snapshot at collection time
   - Does not capture real-time changes or trends
   - Historical context may be missing

2. **Context Loss**
   - Scraped text may lose formatting, images, and interactive elements
   - May miss visual or multimedia information

3. **Interpretation**
   - AI/LLM analysis may introduce its own biases
   - Results should be validated and interpreted critically

## Potential Misuse Scenarios

### What This System Should NOT Be Used For

1. **Commercial Redistribution**
   - ❌ Republishing scraped content for profit
   - ❌ Creating competing services using scraped data
   - ✅ Research and analysis for personal/educational use

2. **Harassment or Targeting**
   - ❌ Using company data to target individuals
   - ❌ Extracting personal information (emails, phone numbers)
   - ✅ Analyzing public company information only

3. **Market Manipulation**
   - ❌ Using scraped data to manipulate stock prices
   - ❌ Creating false narratives from partial data
   - ✅ Legitimate investment research and analysis

4. **Privacy Violations**
   - ❌ Scraping private or authenticated content
   - ❌ Collecting user data or personal information
   - ✅ Only public, company-level information

5. **Copyright Infringement**
   - ❌ Republishing substantial portions of copyrighted content
   - ❌ Using scraped content without attribution
   - ✅ Transformative use for analysis with proper citation

### Responsible Use Guidelines

- Use data for research and analysis purposes only
- Respect website terms of service where applicable
- Implement rate limiting to avoid overloading servers
- Attribute data sources appropriately
- Do not redistribute scraped content
- Consider privacy implications when analyzing data

## Privacy Considerations

### Data Collection

1. **No Personal Data**
   - We do not collect personal information (names, emails, phone numbers)
   - We only collect public company information
   - No user tracking or analytics

2. **Public Information Only**
   - All scraped content is publicly accessible
   - No authentication or login required
   - No private or restricted content

3. **Data Storage**
   - All data stored locally
   - No sharing with third parties
   - Data used only for analysis

### Privacy Protections

- We block certain hosts to avoid scraping subscription/paywall pages
- We do not scrape social media profiles or personal pages
- We focus on company-level, not individual-level, data

## Content Filtering

### Current Filtering

1. **Host Blocking**
   - Blocks certain hosts (e.g., `forbes.com`, `buysub.com`) to avoid subscription/paywall pages
   - Prevents scraping of paywalled content

2. **URL Filtering**
   - Filters out spam URLs (coupons, UTM parameters, referral links)
   - Focuses on main content sections

3. **Section Selection**
   - Only scrapes specific sections (homepage, about, product, careers, blog)
   - Avoids scraping irrelevant or sensitive pages

### Recommendations for Enhancement

- ✅ **robots.txt checking** - Now implemented! The scraper checks robots.txt before scraping any URL
- Add content classification to filter inappropriate material
- Implement duplicate content detection
- Add content quality scoring

## Compliance and Legal Considerations

### Terms of Service

- We acknowledge that some websites may prohibit scraping in their Terms of Service
- We use publicly accessible data and implement respectful scraping practices
- For production use, consider:
  - ✅ robots.txt files are now checked automatically
  - Obtaining explicit permission for large-scale scraping
  - Using official APIs where available

### Legal Disclaimer

This project is for **educational and research purposes**. Users are responsible for:
- Complying with applicable laws and regulations
- Respecting website terms of service
- Obtaining necessary permissions for commercial use
- Ensuring fair use compliance

## Recommendations for Future Improvements

1. ✅ **robots.txt checking** - Implemented! The scraper now checks robots.txt before scraping
2. **Implement explicit rate limiting** with backoff on errors
3. **Add data retention policies** (delete old data after X days)
4. **Create data usage logs** for audit trails
5. **Add content moderation** for inappropriate material
6. **Implement user consent** if collecting any user data
7. **Regular ethics reviews** as the system evolves

## Contact and Reporting

If you have concerns about ethical use of this system or discover misuse, please:
1. Review this document
2. Check the project's code of conduct (if applicable)
3. Report issues through appropriate channels

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0

