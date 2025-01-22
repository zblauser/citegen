from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
from datetime import datetime
import re

app = Flask(__name__)

# Format date function
def format_date(date_str):
    try:
        return datetime.strptime(re.sub(r"T.*|Z$", "", date_str), "%Y-%m-%d").strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return "n.d."

# Fetch metadata for YouTube links
def fetch_youtube_metadata(soup):
    return {
        "title": soup.find("meta", {"property": "og:title"})["content"] if soup.find("meta", {"property": "og:title"}) else "Unknown Video Title",
        "author": soup.find("link", {"itemprop": "name"})["content"] if soup.find("link", {"itemprop": "name"}) else "YouTube",
        "date": format_date(soup.find("meta", {"itemprop": "uploadDate"})["content"]) if soup.find("meta", {"itemprop": "uploadDate"}) else "n.d.",
    }

# Fetch metadata for general links
def fetch_metadata(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        if "youtube.com" in urlparse(url).netloc or "youtu.be" in urlparse(url).netloc:
            return fetch_youtube_metadata(soup)

        title = soup.title.string.strip() if soup.title else "No title available"
        author, date = "Unknown", "n.d."

        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    author = data.get("author", {}).get("name", author)
                    date = data.get("datePublished", date)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item.get("author"), dict):
                            author = item["author"].get("name", author)
                        date = item.get("datePublished", date)
            except json.JSONDecodeError:
                pass
        date = format_date(date)

        return {"title": title, "author": author, "date": date}
    except Exception:
        return {"title": "Error fetching title", "author": "Error", "date": "Error"}

# Generate citation
def generate_citation(link, style="APA"):
    metadata = fetch_metadata(link)
    author, date, title = metadata["author"], metadata["date"], metadata["title"]
    if style == "APA":
        return f"{author} ({date}). {title}. Retrieved from {link}"
    elif style == "MLA":
        site_name = urlparse(link).netloc.replace("www.", "")
        return f"{author}. \"{title}.\" {site_name}, {date}. Accessed <{link}>."
    else:
        return f"Citation for {link} not available in '{style}' style."

# Flask routes
@app.route("/", methods=["GET", "POST"])
def index():
    citation = None
    if request.method == "POST":
        link = request.form.get("link")
        style = request.form.get("style")
        if link:
            citation = generate_citation(link, style)
    return render_template("index.html", citation=citation)

if __name__ == "__main__":
    app.run(debug=True)
