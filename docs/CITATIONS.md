# Citations and Attribution

This document provides quick reference for all external resources, data sources, and libraries used in this project.

## Data Sources

### Seed Company Lists
- **Source**: Top AI and Fintech company lists on the internet
- **Files**: 
  - `data/seed/top_ai50_seed.json` - Top 50 AI companies
  - `data/seed/top_fintech50_seed.json` - Top 50 Fintech companies
- **Usage**: Used as seed data to identify companies for analysis. Contains company names, websites, and metadata.

### Company Websites
- **Source**: Publicly accessible company websites
- **Content**: Homepage, about, product, careers, and blog sections
- **Citation**: Individual company websites (URLs preserved in metadata)
- **Usage**: Scraped for research and analysis purposes only. Content is not redistributed.

## External Libraries

All libraries are used in accordance with their respective open-source licenses:

| Library | License | URL |
|---------|---------|-----|
| requests | Apache 2.0 | https://requests.readthedocs.io/ |
| beautifulsoup4 | MIT | https://www.crummy.com/software/BeautifulSoup/ |
| lxml | BSD | https://lxml.de/ |
| fastapi | MIT | https://fastapi.tiangolo.com/ |
| streamlit | Apache 2.0 | https://streamlit.io/ |
| openai | MIT | https://platform.openai.com/ |
| langchain | MIT | https://www.langchain.com/ |
| chromadb | Apache 2.0 | https://www.trychroma.com/ |
| pydantic | MIT | https://docs.pydantic.dev/ |

See `requirements.txt` for specific versions.

## Code Attribution

All code in this repository is original work created for this project, with the following exceptions:
- Standard library usage (Python built-in modules)
- External libraries listed above (used according to their licenses)
- Common patterns and best practices from open-source community

## Academic/Research Citation

If citing this project in academic work:

```
InvestIQ - Investment Intelligence Platform
Data Sources: Top AI and Fintech company lists, company websites
Web scraping and analysis tools for company intelligence
[Your Name/Institution], [Year]
```

## Questions?

For detailed ethical considerations, see [ETHICS.md](ETHICS.md).  
For project overview, see [README.md](README.md).

