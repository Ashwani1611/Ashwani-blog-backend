import google.generativeai as genai
import re
from app.core.config import get_settings

settings = get_settings()

# Configure Gemini once
genai.configure(api_key=settings.gemini_api_key)

# System prompts
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


def _build_model(system_instruction: str) -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system_instruction,
    )


def build_blog_context(posts: list) -> str:
    return "\n\n".join(
        f'POST: "{p.title}" [{p.cat}]\nSummary: {p.content}'
        for p in posts
    )


async def blog_chat(messages: list[dict], posts: list) -> str:
    blog_ctx = build_blog_context(posts)
    system = BLOG_SYSTEM + f"\n\nBlog posts:\n{blog_ctx}"
    model = _build_model(system)

    history = []
    for m in messages[:-1]:
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})

    chat = model.start_chat(history=history)
    response = chat.send_message(messages[-1]["content"])
    return response.text


async def post_chat(messages: list[dict], post_title: str, post_body: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", post_body)
    plain = re.sub(r"\s+", " ", plain).strip()

    system = POST_SYSTEM_TEMPLATE.format(title=post_title, content=plain[:4000])
    model = _build_model(system)

    history = []
    for m in messages[:-1]:
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})

    chat = model.start_chat(history=history)
    response = chat.send_message(messages[-1]["content"])
    return response.text


async def generate_comment_reply(comment_body: str, post_title: str) -> str:
    system = COMMENT_REPLY_TEMPLATE.format(title=post_title)
    model = _build_model(system)
    response = model.generate_content(comment_body)
    return response.text