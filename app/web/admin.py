"""Admin-only news credential forms."""
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app import config
from app.collection import news_keys

basic = HTTPBasic(auto_error=False)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def require_admin(credentials: HTTPBasicCredentials | None = Depends(basic)):
    if not config.ADMIN_PASSWORD:
        raise HTTPException(503, "Set ADMIN_PASSWORD on the server to enable admin access.")
    if (credentials is None or credentials.username != "admin" or
            not secrets.compare_digest(credentials.password.encode(), config.ADMIN_PASSWORD.encode())):
        raise HTTPException(401, "Admin sign-in required.", headers={"WWW-Authenticate": 'Basic realm="Daily Brief"'})


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def key_page(request, *, saved=None, error=None, status=200):
    return templates.TemplateResponse(request, "admin.html", {
        "providers": news_keys.PROVIDERS, "configured": news_keys.configured_providers(),
        "saved": saved, "error": error,
    }, status_code=status, headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY"})


@router.get("", response_class=HTMLResponse)
def admin_page(request: Request, saved: str = ""):
    return key_page(request, saved=saved if saved in news_keys.PROVIDERS else None)


@router.post("/keys/{provider}")
def update_key(request: Request, provider: str, api_key: str = Form("")):
    # Browsers supply Origin on form POST. Reject missing and cross-origin submissions.
    origin = f"{request.url.scheme}://{request.url.netloc}"
    if request.headers.get("origin") != origin:
        raise HTTPException(403, "Submit the form from the admin page.")
    if provider not in news_keys.PROVIDERS:
        raise HTTPException(404, "Unknown news provider.")
    try:
        news_keys.save_news_key(provider, api_key)
    except (OSError, TimeoutError) as exc:
        raise HTTPException(503, "Could not update the server configuration file.") from exc
    except ValueError as exc:
        return key_page(request, error=f"{provider}: {exc}", status=400)
    return RedirectResponse(f"/admin?saved={provider}", status_code=303)
