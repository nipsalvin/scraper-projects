# scraper-projects

Monorepo for multiple independent Python web scrapers. Shared dependencies live at the repo root; each scraper has its own folder and entry point.

## Project layout

```
scraper-projects/
├── requirements.txt          # shared dependencies for all scrapers
├── e-commerce_scraper/       # product listings scraper
│   └── main.py
├── cbk-rate_scraper/         # Central Bank of Kenya rates scraper
│   └── main.py
└── <new_scraper>/            # add more scrapers the same way
    └── main.py
```

Each scraper is self-contained under its own directory. Prefer one folder per target site or data source, with `main.py` as the runnable entry point.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ recommended.

## Scrapers

| Folder | Target | Run |
|--------|--------|-----|
| `e-commerce_scraper` | [livebetterwithbetty.com](https://livebetterwithbetty.com/) shop | `python e-commerce_scraper/main.py` |
| `cbk-rate_scraper` | [cbk.go.ke](https://www.cbk.go.ke/) rates | `python cbk-rate_scraper/main.py` |

Activate the venv first, then run any scraper’s `main.py` from the repo root.

## Adding a scraper

1. Create a new directory (e.g. `my_scraper/`).
2. Add `main.py` (and any helpers) inside it.
3. Install any new packages into the shared env and update `requirements.txt`.
4. Document the scraper in the table above.

## Shared stack

- [requests](https://requests.readthedocs.io/) — HTTP
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) — HTML parsing
- [Selenium](https://www.selenium.dev/) — browser automation when needed
- [pandas](https://pandas.pydata.org/) — tabular data

## License

MIT — see [LICENSE](LICENSE).
