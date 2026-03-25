from typing import Dict, List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from page import save_to_csv, scrape

app = FastAPI(title="Vestiaire Scraper MVP")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": [],
            "message": "",
            "form": {
                "designer": "Balenciaga",
                "condition": "Very good condition",
                "max_pages": 1,
                "scroll_rounds": 6,
            },
        },
    )


@app.post("/run", response_class=HTMLResponse)
def run_scraper(
    request: Request,
    designer: str = Form("Balenciaga"),
    condition: str = Form("Very good condition"),
    scroll_rounds: int = Form(6),
) -> HTMLResponse:
    safe_max_pages = 1
    safe_scroll_rounds = max(1, min(scroll_rounds, 20))

    results: List[Dict[str, str]] = scrape(
        designer=designer.strip(),
        condition=condition.strip(),
        max_pages=safe_max_pages,
        scroll_rounds=safe_scroll_rounds,
        per_page_item_limit=60,
        headless=False,
    )
    save_to_csv(results, "items.csv")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": results,
            "message": f"Scrape complete: {len(results)} items saved to items.csv",
            "form": {
                "designer": designer,
                "condition": condition,
                "max_pages": safe_max_pages,
                "scroll_rounds": safe_scroll_rounds,
            },
        },
    )
