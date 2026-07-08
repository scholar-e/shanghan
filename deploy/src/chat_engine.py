"""Chat engine using DeepSeek API with function calling for database search."""

import os
import sys
import json
import re
import time
import logging
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from logger import setup_logging, get_logger
from knowledge_base import (
    get_formula_info,
    get_all_formulas,
    get_terminology,
    get_pattern_info,
    SYSTEM_PROMPT,
    TERMINOLOGY,
    PATTERN_INFO,
    FORMULAS
)
import database as db

chat_logger = setup_logging("chat", level=logging.DEBUG)
chat_logger.info("Chat engine initialized")

# ── Tool definitions ──────────────────────────────────────────────

SEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_formulas",
            "description": "Search the classical formula knowledge base for formulas matching a query. Use when the user asks about specific formulas, herbs, or patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Formula name, herb name, pattern, or keyword in Chinese or English"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_terminology",
            "description": "Search TCM terminology definitions. Use when the user asks about the meaning of TCM terms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "TCM term in Chinese or English"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_articles",
            "description": "Search both Song edition (宋本) and Yuanben/Fuling ancient edition (原本/涪陵古本) original text by article number, keyword, or channel. Use when the user quotes or asks about specific 原文 text from the Shang Han Lun.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Article number, keyword in Chinese/English, or channel name (e.g., '73', '五苓散', 'tai yang')"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_article",
            "description": "Get a specific Shang Han Lun article by its Song edition article number (宋本). Use when the user references a specific article number like 'article 73' or '条文73'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article_num": {"type": "integer", "description": "Song edition article number (1-398)"}
                },
                "required": ["article_num"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fuling_article",
            "description": "Get a specific Shang Han Lun article by its Fuling Ancient Edition article number (涪陵古本篇号). Use when the user references a Fuling article number like '涪陵古本 73'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article_num": {"type": "integer", "description": "Fuling Ancient Edition article number (1-396)"}
                },
                "required": ["article_num"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_fuling_articles",
            "description": "Search the Fuling Ancient Edition (涪陵古本) articles by keyword or article number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword in Chinese/English, article number, or channel name"}
                },
                "required": ["query"]
            }
        }
    }
]

# ── Tool implementations ──────────────────────────────────────────

def tool_search_formulas(query):
    results = []
    q = query.lower()
    for key, formula in FORMULAS.items():
        names = " ".join(str(v) for v in formula["names"].values()).lower()
        comp = " ".join(c.get("herb", "") + " " + c.get("pinyin", "") + " " + c.get("en", "") for c in formula["composition"]).lower()
        if any(term in names or term in comp or term in key for term in q.split()):
            results.append({
                "key": key,
                "names": formula["names"],
                "composition": formula["composition"],
                "indications": formula["indications"],
                "functions": formula["functions"],
                "pattern": formula["pattern"]
            })
    if not results:
        return json.dumps({"message": "No matching formulas found."}, ensure_ascii=False)
    return json.dumps(results[:5], indent=2, ensure_ascii=False)


def tool_search_terminology(query):
    q = query.lower()
    results = []
    for term, info in TERMINOLOGY.items():
        if q in term.lower() or q in info.get("en", "").lower() or q in info.get("pinyin", "").lower():
            results.append({"term": term, "pinyin": info.get("pinyin", ""), "en": info.get("en", "")})
    if not results:
        return json.dumps({"message": "No matching terminology found."}, ensure_ascii=False)
    return json.dumps(results[:10], indent=2, ensure_ascii=False)


def tool_search_articles(query):
    song_results = db.search_articles(query)
    yuanben_results = db.search_fuling_articles(query)
    if not song_results and not yuanben_results:
        return json.dumps({"message": "No matching original text found."}, ensure_ascii=False)

    out = {
        "songben": [],
        "yuanben": [],
    }
    for r in song_results[:5]:
        out["songben"].append({
            "article_num": r["article_num"],
            "channel": r["channel"],
            "pattern": r["pattern"],
            "original_zh": r["original_zh"],
            "translation_en": r["translation_en"]
        })
    for r in yuanben_results[:5]:
        out["yuanben"].append({
            "article_num": r["fuling_article_num"],
            "original_zh": r["fuling_zh"],
            "song_article_num": r["song_article_num"],
            "song_zh": r["song_zh"],
            "channel": r["channel"],
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


def tool_get_article(article_num):
    r = db.get_article(article_num)
    if not r:
        return json.dumps({"error": f"Article {article_num} not found"}, ensure_ascii=False)
    return json.dumps(dict(r), indent=2, ensure_ascii=False)


def tool_get_fuling_article(article_num):
    r = db.get_fuling_article(article_num)
    if not r:
        return json.dumps({"error": f"Fuling article {article_num} not found"}, ensure_ascii=False)
    return json.dumps(dict(r), indent=2, ensure_ascii=False)


def tool_search_fuling_articles(query):
    results = db.search_fuling_articles(query)
    if not results:
        return json.dumps({"message": "No matching Fuling articles found."}, ensure_ascii=False)
    out = []
    for r in results[:5]:
        out.append({
            "fuling_article_num": r["fuling_article_num"],
            "fuling_zh": r["fuling_zh"],
            "song_article_num": r["song_article_num"],
            "song_zh": r["song_zh"],
            "channel": r["channel"],
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


TOOL_DISPATCH = {
    "search_formulas": tool_search_formulas,
    "search_terminology": tool_search_terminology,
    "search_articles": tool_search_articles,
    "get_article": tool_get_article,
    "get_fuling_article": tool_get_fuling_article,
    "search_fuling_articles": tool_search_fuling_articles,
}


# ── DeepSeek Client with function calling ─────────────────────────

class DeepSeekClient:
    """DeepSeek API client with tool/function calling support."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        self.max_retries = 2
        self.timeout = 45
        chat_logger.info(f"DeepSeekClient initialized | Model: {self.model} | Timeout: {self.timeout}s")

    def chat_with_tools(self, messages, system_prompt=None, tools=None):
        """Send chat request with optional tool calling. Returns the final assistant message after resolving tool calls."""
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        max_tool_rounds = 3
        seen_tool_calls = set()
        for _round in range(max_tool_rounds):
            payload = {
                "model": self.model,
                "messages": all_messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            if tools:
                payload["tools"] = tools

            chat_logger.debug(f"API round {_round + 1} | {len(all_messages)} messages")

            result = self._send_request(payload)
            choice = result['choices'][0]
            msg = choice['message']

            if not msg.get('tool_calls'):
                return msg.get('content', '')

            # Handle tool calls
            all_messages.append(msg)
            for tc in msg['tool_calls']:
                fn = tc['function']
                fn_name = fn['name']
                try:
                    fn_args = json.loads(fn['arguments'])
                except json.JSONDecodeError:
                    fn_args = {}

                chat_logger.info(f"Tool call: {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:100]})")
                tool_signature = (fn_name, json.dumps(fn_args, sort_keys=True, ensure_ascii=False))
                if tool_signature in seen_tool_calls:
                    result_text = json.dumps({"message": "This search was already run. Use the previous result to answer."}, ensure_ascii=False)
                    all_messages.append({
                        "role": "tool",
                        "tool_call_id": tc['id'],
                        "content": result_text
                    })
                    continue
                seen_tool_calls.add(tool_signature)

                handler = TOOL_DISPATCH.get(fn_name)
                if handler:
                    try:
                        result_text = handler(**fn_args)
                    except Exception as e:
                        result_text = json.dumps({"error": str(e)}, ensure_ascii=False)
                else:
                    result_text = json.dumps({"error": f"Unknown tool: {fn_name}"}, ensure_ascii=False)

                all_messages.append({
                    "role": "tool",
                    "tool_call_id": tc['id'],
                    "content": result_text
                })

        chat_logger.warning("Max tool rounds reached")
        return "I found search results, but the model kept requesting more searches. Please try a more specific question."

    def _send_request(self, payload):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                chat_logger.debug(f"API attempt {attempt + 1}/{self.max_retries}")
                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 401:
                    raise Exception("Invalid API key - please check DEEPSEEK_API_KEY")
                elif response.status_code == 429:
                    wait = 2 ** attempt
                    chat_logger.warning(f"Rate limited, waiting {wait}s")
                    time.sleep(wait)
                    continue
                elif response.status_code != 200:
                    raise Exception(f"DeepSeek API error: {response.text[:200]}")

                result = response.json()
                chat_logger.info(f"API successful | {result['usage']}")
                return result

            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise Exception(f"DeepSeek API failed after {self.max_retries} attempts: {last_error}")


# ── Context builder (lightweight initial pass, tools handle deep search) ──

def build_context(query):
    """Build relevant context from knowledge base and lessons database based on query."""
    chat_logger.debug(f"build_context called with query: {query[:100]}...")
    
    context_parts = []
    sources = []
    
    query_lower = query.lower()
    wants_fuling = True
    query_words = set(re.findall(r'[a-z0-9]+', query_lower))
    
    for key, formula in FORMULAS.items():
        names = formula['names']
        name_values = [str(names.get('zh', '')).lower(), str(names.get('pinyin', '')).lower(), str(names.get('en', '')).lower()]
        matches_name = any(n and n in query_lower for n in name_values)
        key_terms = key.replace('_', ' ').split()
        matches_key = len(key_terms) >= 2 and sum(1 for t in key_terms if t in query_words) >= 2
        if matches_key or matches_name:
            context_text = format_formula_context(formula)
            context_parts.append(context_text)
            sources.append({
                "title": f"Shang Han Lun - {formula['names']['pinyin']}",
                "type": "formula",
                "key": key,
                "content": context_text
            })
    
    for term_cn, term_info in TERMINOLOGY.items():
        if term_cn.lower() in query_lower or term_info.get('en', '').lower() in query_lower:
            context_text = f"Term: {term_cn} ({term_info.get('pinyin', '')}) - {term_info.get('en', '')}"
            context_parts.append(context_text)
            sources.append({
                "title": "Shang Han Lun - Terminology",
                "type": "terminology",
                "key": term_cn,
                "content": context_text
            })
    
    for pattern_key, pattern in PATTERN_INFO.items():
        if pattern_key.replace('_', ' ') in query_lower or pattern['name'].get('en', '').lower() in query_lower:
            context_text = format_pattern_context(pattern, pattern_key)
            context_parts.append(context_text)
            sources.append({
                "title": f"Shang Han Lun - {pattern['name']['en']} Pattern",
                "type": "pattern",
                "key": pattern_key,
                "content": context_text
            })
    
    # Search SHL articles by number or keyword — these are citeable sources
    try:
        m = re.search(r'(?:article|条文|条|art[\.\s]*)\s*(\d{1,3})', query, re.IGNORECASE)
        if m:
            num = int(m.group(1))
            article = db.get_article(num)
            if article:
                text = f"Article {num} [{article['channel']}]: {article['original_zh']}"
                context_parts.append(text)
                sources.append({
                    "title": f"Shang Han Lun Article {num}",
                    "type": "article",
                    "key": str(num),
                    "content": f"{article['original_zh']}\n{article['translation_en']}"
                })
        article_results = db.search_articles(query)
        if article_results:
            for r in article_results[:3]:
                num = r["article_num"]
                if not any(s.get("key") == str(num) and s.get("type") == "article" for s in sources):
                    text = f"Article {num} [{r['channel']}]: {r['original_zh'][:200]}"
                    context_parts.append(text)
                    sources.append({
                        "title": f"Shang Han Lun Article {num}",
                        "type": "article",
                        "key": str(num),
                        "content": f"{r['original_zh']}\n{r['translation_en']}"
                    })
        # Search Yuanben/Fuling in parallel with Songben; do not cross-reference.
        fuling_results = db.search_fuling_articles(query) if wants_fuling else []
        if fuling_results:
            for r in fuling_results[:3]:
                fa_num = r["fuling_article_num"]
                # Avoid duplicating if already found via Song search
                if any(s.get("key") == f"fuling_{fa_num}" for s in sources):
                    continue
                text = f"【涪陵古本 {fa_num}】{r['fuling_zh'][:200]}"
                context_parts.append(text)
                sources.append({
                    "title": f"Yuanben/Fuling Article {fa_num}",
                    "type": "fuling_article",
                    "key": f"fuling_{fa_num}",
                    "content": text
                })
    except Exception as e:
        chat_logger.warning(f"Article search failed: {e}")

    # Internal reference: lesson content informs the AI but is not cited
    try:
        internal = db.search_lessons(query)
        if internal:
            for r in internal[:3]:
                excerpt = r.get("preview", "").strip()
                if excerpt:
                    context_parts.append(f"[Reference: {r['lesson_id']}] {excerpt}")
    except Exception:
        pass

    if not context_parts:
        context_parts.append("General reference: The Shang Han Lun contains 112 classical formulas organized by the Six Channel (六经辨证) pattern identification system.")
        sources.append({"title": "Shang Han Lun - General Reference", "type": "general", "key": "", "content": context_parts[-1]})
    
    seen = set()
    unique_sources = []
    for s in sources:
        if s["title"] not in seen:
            seen.add(s["title"])
            unique_sources.append(s)
    
    return "\n\n".join(context_parts), unique_sources


def format_formula_context(formula):
    names = formula['names']
    comp = formula['composition']
    herbs = ", ".join([f"{c['herb']} ({c['pinyin']}, {c['dosage']})" for c in comp])
    roles = ", ".join([f"{c['herb']} as {c['role']}" for c in comp])
    return f"""Formula: {names['zh']} ({names['pinyin']}, {names['en']})
Composition: {herbs}
Roles: {roles}
Indications: {formula['indications']}
Functions: {formula['functions']}
Pattern: {formula['pattern']}"""


def format_pattern_context(pattern, pattern_key):
    return f"""Pattern: {pattern['name']['zh']} ({pattern['name']['en']})
Location: {pattern['location']}
Characteristics: {pattern['characteristics']}
Sub-patterns: {', '.join(pattern['sub_patterns'])}"""


def extract_formulas_from_text(text):
    text_lower = text.lower()
    found = []
    seen_keys = set()
    for key, formula in FORMULAS.items():
        names = formula["names"]
        if (names.get("zh", "") and names["zh"] in text) or (names.get("pinyin", "").lower() in text_lower) or (names.get("en", "").lower() in text_lower):
            if key not in seen_keys:
                found.append(formula)
                seen_keys.add(key)
    novel_pattern = re.findall(r'([\u4e00-\u9fff]{2,4}汤)\s*[（(]?\s*([A-Za-z\s]+?)\s*[）)]?\s*[Dd]ecoction', text)
    for zh_name, pinyin_name in novel_pattern:
        pinyin_clean = pinyin_name.strip()
        key = f"_ai_{zh_name}_{pinyin_clean}"
        if key not in seen_keys:
            found.append({"names": {"zh": zh_name, "pinyin": pinyin_clean, "en": f"{pinyin_clean} Decoction"}, "composition": [], "indications": "", "functions": "", "pattern": "", "_ai_generated": True})
            seen_keys.add(key)
    return found


def extract_structured_formula(text):
    blocks = re.findall(r'\[FORMULA\](.*?)\[/FORMULA\]', text, re.DOTALL)
    formulas = []
    for block in blocks:
        try:
            data = json.loads(block.strip())
            data["_ai_generated"] = True
            formulas.append(data)
        except json.JSONDecodeError:
            chat_logger.warning(f"Failed to parse FORMULA block: {block[:100]}")
    cleaned = re.sub(r'\s*\[FORMULA\].*?\[/FORMULA\]\s*', '', text, flags=re.DOTALL).strip()
    return formulas, cleaned


# ── ChatEngine with tool calling ──────────────────────────────────

TOOL_SYSTEM_PROMPT = SYSTEM_PROMPT + """

TEXTUAL EDITIONS:
The Shang Han Lun exists in two primary editions in this system:
1. **宋本 (Song Edition)** — the standard 宋本《伤寒论》, also referred to as "Song version"
2. **涪陵古本 (Fuling Ancient Edition)** — 《重编施注涪陵古本伤寒杂病论》, the primary lecture textbook

Search the edition the user asks about. Use Song edition tools for ordinary article references, and Fuling tools only when the user mentions 涪陵古本/Fuling or asks for that edition.

TOOLS AVAILABLE:
You have access to the following tools to look up information on demand:
- search_formulas(query) — Search the classical formula database
- search_terminology(query) — Look up TCM term definitions
- search_articles(query) — Search the original Shang Han Lun articles/条文 (宋本) by keyword, article number, or channel
- get_article(article_num) — Get a specific Song edition article by its number (e.g., 73)
- get_fuling_article(article_num) — Get a specific Fuling Ancient Edition article (涪陵古本) by its number (e.g., 10)
- search_fuling_articles(query) — Search the Fuling Ancient Edition (涪陵古本) articles by keyword

Use at most one or two searches before answering. Do not repeat the same search. Context prefixed with [Reference:] is internal lecture material — do not quote or cite it directly, but use it to inform your answers."""


class ChatEngine:
    """Chat engine for Shang Han Lun queries with function calling."""

    def __init__(self, api_key=None):
        self.client = DeepSeekClient(api_key)
        self.system_prompt = TOOL_SYSTEM_PROMPT
        chat_logger.info("ChatEngine initialized (tool-calling mode)")

    def process_query(self, query, conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        chat_logger.info(f"Processing query: {query[:100]}... | History: {len(conversation_history)} messages")

        # Lightweight initial context (tools handle deeper search)
        context, sources = build_context(query)
        chat_logger.debug(f"Initial context: {len(context)} chars, {len(sources)} sources")

        user_message = f"""Question: {query}

Relevant context from Shang Han Lun:
{context}

Instructions:
- Use the available tools only if the provided context is not enough. Do not repeat searches.
- Keep answers SHORT (2-4 sentences).
- Use **bold** for formula names and key terms.
- After each formula or key claim, add a source reference in brackets like [1], [2] etc.
- Use ## for sections.
- If you recommend or discuss specific formulas, include a [FORMULA] JSON block at the end.
- Focus on the most relevant information only."""

        try:
            messages = []
            for msg in conversation_history[-6:]:
                if msg.get('role') in ['user', 'assistant']:
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content'][:500]
                    })
            messages.append({"role": "user", "content": user_message[:4000]})

            chat_logger.debug(f"Sending to API with {len(messages)} messages + tools")
            answer = self.client.chat_with_tools(messages, self.system_prompt, tools=SEARCH_TOOLS)
            chat_logger.info(f"Query processed successfully, answer length: {len(answer)} chars")

        except Exception as e:
            chat_logger.error(f"Error processing query: {e}")
            answer = f"I apologize, but I encountered an error processing your query: {str(e)}. Please ensure the DeepSeek API key is properly configured."

        ai_formulas, cleaned_answer = extract_structured_formula(answer)
        answer = cleaned_answer
        if ai_formulas:
            chat_logger.info(f"Extracted {len(ai_formulas)} AI-generated formula(s) from response")

        text_formulas = extract_formulas_from_text(answer)
        known_zh = {a.get("name_zh", "") for a in ai_formulas}
        all_ai_formulas = ai_formulas + [f for f in text_formulas if f.get("names", {}).get("zh", "") not in known_zh]

        return answer, sources, context, all_ai_formulas


def process_query(query, conversation_history=None, api_key=None):
    engine = ChatEngine(api_key)
    return engine.process_query(query, conversation_history)


def test_connection(api_key):
    client = DeepSeekClient(api_key)
    try:
        response = client.chat_with_tools(
            [{"role": "user", "content": "What is Gui Zhi Tang?"}],
            "You are a helpful TCM assistant.",
            tools=SEARCH_TOOLS
        )
        return True, response
    except Exception as e:
        return False, str(e)
