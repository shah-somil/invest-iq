# InvestIQ

An investment intelligence platform for analyzing AI and Fintech companies using web-scraped data and AI-powered analysis.

## Overview

InvestIQ collects and analyzes publicly available information about top AI and Fintech companies and their official websites to provide investment insights and company intelligence.

## Data Sources

### Primary Data Sources

1. **Seed Company Lists**
   - **Top AI 50**: `data/seed/top_ai50_seed.json` - List of top 50 AI companies
   - **Top Fintech 50**: `data/seed/top_fintech50_seed.json` - List of top 50 Fintech companies
   - These seed files contain company names, websites, and metadata
   - Used to identify companies for analysis

2. **Company Websites**
   - Publicly accessible company websites (homepage, about, product, careers, blog sections)
   - Data is collected for research and analysis purposes only
   - All scraped content is stored locally and used for analysis, not redistribution

### Data Collection Methods

- Web scraping using Python `requests` library
- HTML parsing using `BeautifulSoup4`
- **robots.txt checking**: Respects website crawling policies before scraping
- Rate limiting: 0.5 second delay between requests to minimize server load
- Only public, non-authenticated pages are accessed
- Respects blocked hosts to avoid paywalled or inappropriate content

## External Libraries and Dependencies

This project uses the following open-source libraries (see `requirements.txt` for versions):

- **requests** (https://requests.readthedocs.io/) - HTTP library for web scraping
- **beautifulsoup4** (https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
- **lxml** (https://lxml.de/) - XML/HTML parser (optional, fallback to html.parser)
- **fastapi** (https://fastapi.tiangolo.com/) - Web framework
- **streamlit** (https://streamlit.io/) - Dashboard framework
- **openai** (https://platform.openai.com/) - AI/LLM integration
- **langchain** (https://www.langchain.com/) - LLM application framework
- **chromadb** (https://www.trychroma.com/) - Vector database
- **pydantic** (https://docs.pydantic.dev/) - Data validation

All libraries are used in accordance with their respective licenses (primarily MIT, Apache 2.0, or BSD).

## Project Structure

```
invest-iq/
├── data/
│   ├── seed/          # Seed JSON files (top_ai50_seed.json, top_fintech50_seed.json)
│   ├── raw/           # Scraped HTML and text files
│   └── logs/          # Ingestion logs and summaries
├── src/
│   ├── tools/         # Data collection scripts
│   └── scripts/       # Processing and analysis scripts
└── requirements.txt   # Python dependencies
```

## Ethical Considerations

See [ETHICS.md](ETHICS.md) for detailed documentation on:
- Copyright and intellectual property considerations
- Bias, fairness, and representation
- System limitations
- Potential misuse scenarios
- Privacy considerations
- Content filtering

## Usage

### Setting Up

```bash
pip install -r requirements.txt
```

### Running Full Ingestion

```bash
python src/scripts/run_full_ingest.py
```

## License

See [LICENSE](LICENSE) file for details.

## Citation

If you use this project or its data, please cite:

```
InvestIQ - Investment Intelligence Platform
Data sources: Top AI and Fintech company lists
Web scraping and analysis tools for company intelligence
```

## Disclaimer

This project is for educational and research purposes. All data is collected from publicly available sources. The authors do not claim ownership of scraped content and use it under fair use principles for research and analysis.

