#!/usr/bin/env python
"""Smart router: serves Gradio if available, falls back to HTML if not."""
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
def root():
    try:
        r = requests.get("http://gradio:7860/config", timeout=2)
        if r.status_code == 200:
            return HTMLResponse('<script>window.location.href="http://localhost:7861"</script>')
    except Exception:
        pass
    html_path = "/app/web/dashboard.html"
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return "<h1>NEXUS Enhanced</h1><p>UI loading...</p>"

@app.get("/fallback/html", response_class=HTMLResponse)
def fallback_html():
    html_path = "/app/web/dashboard.html"
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return "<h1>Error: HTML not found</h1>"

@app.get("/health")
def health():
    return {"status": "healthy", "mode": "router"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
