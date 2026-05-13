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


# ── Client ────────────────────────────────────────────────────

def _get_client() -> genai.Client:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=settings.gemini_api_key)


def _to_contents(messages: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])]
        )
        for m in messages
    ]


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

        contents = _to_contents(messages)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return response.text
    except GoogleAPIError as e:
        raise ValueError(f"Gemini API error: {str(e)}")


async def post_chat(messages: list[dict], post_title: str, post_content: str) -> str:
    try:
        client = _get_client()
        plain = re.sub(r"<[^>]+>", " ", post_content)
        plain = re.sub(r"\s+", " ", plain).strip()
        system = POST_SYSTEM_TEMPLATE.format(title=post_title, content=plain[:4000])

        contents = _to_contents(messages)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return response.text
    except GoogleAPIError as e:
        raise ValueError(f"Gemini API error: {str(e)}")


async def generate_comment_reply(comment_body: str, post_title: str) -> str:
    try:
        client = _get_client()
        system = COMMENT_REPLY_TEMPLATE.format(title=post_title)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=comment_body,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return response.text
    except GoogleAPIError as e:
        raise ValueError(f"Gemini API error: {str(e)}")