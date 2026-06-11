import re
from google import genai
from google.genai import types
from google.api_core.exceptions import GoogleAPIError

from app.core.config import get_settings

settings = get_settings()


# ── System prompts ────────────────────────────────────────────

BLOG_SYSTEM = """You are a helpful AI assistant embedded in Ashwani Kumar's developer blog.
Ashwani is a Full-Stack Developer specialising in Django, FastAPI, PostgreSQL, and AI/RAG pipelines, based in New Delhi, India, studying at IIT Mandi.
Answer questions based on the blog posts provided. Be concise, technical, and practical.
Keep responses under 150 words unless explaining a complex topic."""

POST_SYSTEM_TEMPLATE = """You are an AI assistant for the blog post titled "{title}" by Ashwani Kumar.
Post content: {content}
Answer questions about this specific post. Be concise and technical. Maximum 120 words."""

COMMENT_REPLY_TEMPLATE = """You are Ashwani Kumar, a Full-Stack Django developer.
Reply to a comment on your blog post titled "{title}".
Be friendly, helpful, and technical. Keep it under 60 words."""

POST_GENERATE_SYSTEM = """You are a technical blog writer for Ashwani Kumar's developer portfolio.
Ashwani is a Full-Stack Developer from New Delhi specialising in Django, FastAPI, PostgreSQL, Docker, and AWS. Currently studying at IIT Mandi.
Write production-quality technical blog posts in his voice: direct, code-first, with real numbers and real examples.
Always return ONLY valid JSON with no markdown fences, no preamble, no trailing explanation."""


# ── Client singleton ──────────────────────────────────────────
# FIX: was recreated on every call. Now a module-level singleton so the
# underlying HTTP session is reused across requests.

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ── Shared helpers ────────────────────────────────────────────

def _to_contents(messages: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])]
        )
        for m in messages
    ]


def _user_content(text: str) -> list[types.Content]:
    """Wrap a plain string as a single-user-turn Content list."""
    return [types.Content(role="user", parts=[types.Part(text=text)])]


def build_blog_context(posts: list) -> str:
    return "\n\n".join(
        f'POST: "{p.title}"\nSummary: {p.excerpt}'
        for p in posts
    )


# ── Public functions ──────────────────────────────────────────

async def blog_chat(messages: list[dict], posts: list) -> str:
    try:
        client = _get_client()
        blog_ctx = build_blog_context(posts)
        system = BLOG_SYSTEM + f"\n\nBlog posts:\n{blog_ctx}"

        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=_to_contents(messages),
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return response.text
    except GoogleAPIError as e:
        # FIX: raise ... from e preserves original traceback in logs
        raise ValueError(f"Gemini API error: {str(e)}") from e


async def post_chat(messages: list[dict], post_title: str, post_content: str) -> str:
    try:
        client = _get_client()
        plain = re.sub(r"<[^>]+>", " ", post_content)
        plain = re.sub(r"\s+", " ", plain).strip()
        system = POST_SYSTEM_TEMPLATE.format(title=post_title, content=plain[:4000])

        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=_to_contents(messages),
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return response.text
    except GoogleAPIError as e:
        raise ValueError(f"Gemini API error: {str(e)}") from e


async def generate_comment_reply(comment_body: str, post_title: str) -> str:
    try:
        client = _get_client()
        system = COMMENT_REPLY_TEMPLATE.format(title=post_title)

        # FIX: was passing raw string — now uses proper Content list, consistent
        # with blog_chat and post_chat
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=_user_content(comment_body),
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return response.text
    except GoogleAPIError as e:
        raise ValueError(f"Gemini API error: {str(e)}") from e


async def generate_post(
    topic: str,
    cat: str,
    tone: str,
    length: str,
    key_points: str = "",
) -> dict:
    """
    NEW: Gemini-powered post generation.
    Returns a parsed dict with keys:
      title, slug, excerpt, read_time, tags, toc, body
    Raises ValueError if Gemini returns unparseable JSON.
    """
    import json

    points_block = f"- Key points to cover:\n{key_points}" if key_points else ""

    prompt = f"""Write a complete technical blog post with these specs:
- Topic: {topic}
- Category: {cat}
- Tone: {tone}
- Length: {length}
{points_block}

Return ONLY a raw JSON object (no markdown fences, no extra text):
{{
  "title": "Full post title",
  "slug": "url-friendly-slug-max-60-chars",
  "excerpt": "2-3 sentence compelling excerpt describing what the reader learns",
  "read_time": "X min read",
  "tags": ["Tag1", "Tag2", "Tag3", "Tag4"],
  "toc": [
    {{"title": "Section Heading", "anchor": "section-heading", "level": 2}}
  ],
  "body": "Full HTML body. Use <h2> for main sections. Use <pre><code> for all code blocks. Use <div class=\\"callout\\"><div class=\\"callout-icon\\">⚠️</div><div class=\\"callout-text\\">note</div></div> for warnings. Include real production-quality code. Minimum 800 words."
}}"""

    try:
        client = _get_client()
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=_user_content(prompt),
            config=types.GenerateContentConfig(system_instruction=POST_GENERATE_SYSTEM),
        )
        raw = response.text or ""

        # Strip any accidental markdown fences
        clean = re.sub(r"^```json\s*", "", raw.strip())
        clean = re.sub(r"^```\s*", "", clean)
        clean = re.sub(r"```\s*$", "", clean).strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Fallback: extract first {...} block
            m = re.search(r"\{[\s\S]*\}", clean)
            if m:
                return json.loads(m.group(0))
            raise ValueError("Gemini returned non-JSON output. Try again.") from None

    except GoogleAPIError as e:
        raise ValueError(f"Gemini API error: {str(e)}") from e