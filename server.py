import os
import subprocess
import json
from dotenv import load_dotenv
from flask import Flask, send_file, jsonify, request
import httpx

load_dotenv()

app = Flask(__name__)
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = "38115b64-5f2e-8009-8e54-c3ba397dcbcc"
NOTION_BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

video_cache = {}


def extract_video_url(ig_url):
    if not ig_url:
        return None
    if ig_url in video_cache:
        return video_cache[ig_url]
    try:
        clean = ig_url.split("?")[0]
        result = subprocess.run(
            ["python3", "-m", "yt_dlp", "--dump-json", "--no-download", clean],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            url = data.get("url")
            if url:
                video_cache[ig_url] = url
                return url
    except Exception:
        pass
    return None


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/posts")
def get_posts():
    resp = httpx.post(
        f"{NOTION_BASE}/databases/{DATABASE_ID}/query",
        headers=HEADERS,
        json={
            "filter": {
                "and": [
                    {"property": "Archive", "checkbox": {"equals": False}},
                    {"property": "Tested", "checkbox": {"equals": False}},
                    {"property": "Test Later", "checkbox": {"equals": False}},
                    {"property": "Signed", "checkbox": {"equals": False}},
                ]
            }
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    posts = []
    for page in data["results"]:
        props = page["properties"]
        title_parts = props.get("Instagram", {}).get("title", [])
        instagram = title_parts[0]["plain_text"] if title_parts else ""

        artist_parts = props.get("Artist Name(s)", {}).get("rich_text", [])
        artist = artist_parts[0]["plain_text"] if artist_parts else ""

        song_parts = props.get("Song name", {}).get("rich_text", [])
        song = song_parts[0]["plain_text"] if song_parts else ""

        link1 = props.get("Post link 1", {}).get("url")
        link2 = props.get("Post link 2", {}).get("url")

        posts.append({
            "id": page["id"],
            "instagram": instagram,
            "artistName": artist,
            "songName": song,
            "postLink1": link1,
            "postLink2": link2,
            "approved": props.get("Approve", {}).get("checkbox", False),
        })

    return jsonify(posts)


@app.route("/api/video")
def get_video():
    ig_url = request.args.get("url")
    if not ig_url:
        return jsonify({"error": "Missing url param"}), 400
    video_url = extract_video_url(ig_url)
    return jsonify({"videoUrl": video_url})


@app.route("/api/approve/<page_id>", methods=["POST"])
def approve(page_id):
    body = request.get_json()
    resp = httpx.patch(
        f"{NOTION_BASE}/pages/{page_id}",
        headers=HEADERS,
        json={"properties": {"Approve": {"checkbox": body["approved"]}}},
        timeout=30,
    )
    resp.raise_for_status()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
