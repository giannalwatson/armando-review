import os
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
        spotify = props.get("Spotify link", {}).get("url")

        approved1 = props.get("Approve link 1", {}).get("checkbox", False)
        approved2 = props.get("Approve link 2", {}).get("checkbox", False)

        posts.append({
            "id": page["id"],
            "instagram": instagram,
            "artistName": artist,
            "songName": song,
            "postLink1": link1,
            "postLink2": link2,
            "spotifyLink": spotify,
            "approved1": approved1,
            "approved2": approved2,
        })

    return jsonify(posts)


@app.route("/api/approve/<page_id>", methods=["POST"])
def approve(page_id):
    body = request.get_json()
    props = {}
    if "approved1" in body:
        props["Approve link 1"] = {"checkbox": body["approved1"]}
    if "approved2" in body:
        props["Approve link 2"] = {"checkbox": body["approved2"]}
    resp = httpx.patch(
        f"{NOTION_BASE}/pages/{page_id}",
        headers=HEADERS,
        json={"properties": props},
        timeout=30,
    )
    resp.raise_for_status()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
