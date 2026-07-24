"""Chat engine using configurable AI providers with function calling for database search."""

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
from formula_intake import needs_formula_followup, formula_followup_response
from ai_config import get_active_ai_provider
from pinyin_utils import chinese_to_pinyin, looks_like_pinyin_query, pinyin_matches

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
            "description": "Search the Fuling textbook by article number, keyword, Songben secondary tag, or channel.",
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
            "description": "Get a specific Song edition (宋本) line by Songben line number. Use only when the user explicitly asks for 宋本/Songben/Song edition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article_num": {"type": "integer", "description": "Explicit Song edition article number (1-398)"}
                },
                "required": ["article_num"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fuling_article",
            "description": "Get a specific Shang Han Za Bing Lun line by its Fuling Ancient Edition line number (涪陵古本篇号). Use by default for bare chapter/article/line numbers such as 'chapter 10', 'line 73', or '条文73', unless the user explicitly asks for Songben.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article_num": {"type": "integer", "description": "Fuling Ancient Edition article number (1-396); default numbering for unspecific chapter/article/line requests"}
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
    formula_number_match = re.search(r"(?:方剂|方|formula)\s*#?\s*(\d{1,3})\b", query, re.IGNORECASE)
    for key, formula in FORMULAS.items():
        if formula_number_match and str(formula.get("formula_number", "")) == formula_number_match.group(1):
            results.append(_formula_tool_payload(key, formula))
            continue
        zh_values = [formula.get("formula_title", ""), formula["names"].get("zh", "")]
        zh_values.extend(c.get("herb", "") for c in formula["composition"])
        search_terms = [term for term in q.split() if len(term) >= 3 or term.isdigit()]
        haystack = " ".join([
            key.replace("_", " "),
            *(str(v) for v in formula["names"].values()),
            *(c.get("herb", "") + " " + c.get("pinyin", "") + " " + c.get("en", "") for c in formula["composition"]),
            *(chinese_to_pinyin(value) for value in zh_values),
        ]).lower()
        token_match = all(term in haystack for term in search_terms) if len(search_terms) > 1 else any(term in haystack for term in search_terms)
        if pinyin_matches(query, *zh_values) or (token_match and not looks_like_pinyin_query(query)):
            results.append(_formula_tool_payload(key, formula))
    if not results:
        return json.dumps({"message": "No matching formulas found."}, ensure_ascii=False)
    return json.dumps(results[:5], indent=2, ensure_ascii=False)


def _formula_tool_payload(key, formula):
    return {
        "key": key,
        "formula_number": formula.get("formula_number"),
        "formula_title": formula.get("formula_title"),
        "names": formula["names"],
        "composition": formula["composition"],
        "indications": formula["indications"],
        "functions": formula["functions"],
        "pattern": formula["pattern"],
        "yuanben_article_num": formula.get("yuanben_article_num"),
        "songben_article_num": formula.get("songben_article_num"),
        "yuanben_text": formula.get("yuanben_text"),
        "songben_text": formula.get("songben_text"),
        "source_text": formula.get("source_text"),
        "preparation_text": formula.get("preparation_text"),
    }


def tool_search_terminology(query):
    q = query.lower()
    results = []
    for term, info in TERMINOLOGY.items():
        if q in term.lower() or q in info.get("en", "").lower() or q in info.get("pinyin", "").lower() or pinyin_matches(query, term, info.get("pinyin", "")):
            results.append({"term": term, "pinyin": info.get("pinyin", ""), "en": info.get("en", "")})
    if not results:
        return json.dumps({"message": "No matching terminology found."}, ensure_ascii=False)
    return json.dumps(results[:10], indent=2, ensure_ascii=False)


def expand_formula_pinyin_query(query):
    """Add Chinese formula titles for pinyin searches like sinitang."""
    expanded = [str(query or "")]
    seen = {expanded[0]}
    for formula in FORMULAS.values():
        title = formula.get("formula_title") or formula.get("names", {}).get("zh", "")
        names = formula.get("names", {})
        candidates = [title, names.get("zh", ""), names.get("pinyin", "")]
        if title and pinyin_matches(query, *candidates):
            for value in (title, title.removesuffix("方")):
                if value and value not in seen:
                    expanded.append(value)
                    seen.add(value)
    return " ".join(expanded)


def tool_search_articles(query):
    fuling_results = db.search_fuling_articles(expand_formula_pinyin_query(query))
    if not fuling_results:
        return json.dumps({"message": "No matching original text found."}, ensure_ascii=False)
    out = {"fuling": []}
    for r in fuling_results[:20]:
        out["fuling"].append({
            "fuling_article_num": r["fuling_article_num"],
            "fuling_zh": r["fuling_zh"],
            "songben_article_num": r["song_article_num"],
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
    results = db.search_fuling_articles(expand_formula_pinyin_query(query))
    if not results:
        return json.dumps({"message": "No matching Fuling articles found."}, ensure_ascii=False)
    out = []
    for r in results[:20]:
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


# ── AI Client with function calling ───────────────────────────────

class DeepSeekClient:
    """AI API client with tool/function calling support."""

    def __init__(self, api_key=None):
        self.provider, provider_config = get_active_ai_provider()
        self.api_key = api_key or provider_config.get("api_key", "")
        self.base_url = provider_config.get("base_url", "").rstrip("/")
        self.model = provider_config.get("model", "")
        self.max_retries = 2
        self.timeout = 45
        chat_logger.info(f"AI client initialized | Provider: {self.provider} | Model: {self.model} | Timeout: {self.timeout}s")

    def chat_with_tools(self, messages, system_prompt=None, tools=None):
        """Send chat request with optional tool calling. Returns the final assistant message after resolving tool calls."""
        if not self.api_key:
            raise ValueError(f"{self.provider} API key not configured")
        if self.provider == "claude":
            return self._chat_with_claude_tools(messages, system_prompt, tools)
        return self._chat_with_openai_tools(messages, system_prompt, tools)

    def _chat_with_openai_tools(self, messages, system_prompt=None, tools=None):
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
        all_messages.append({
            "role": "user",
            "content": (
                "Stop searching now. Answer the user's original question from the context "
                "and tool results already provided. Keep it concise, cite the available "
                "numbered sources when useful, and do not mention tool use or search limits."
            )
        })
        try:
            payload = {
                "model": self.model,
                "messages": all_messages,
                "temperature": 0.5,
                "max_tokens": 1200
            }
            result = self._send_request(payload)
            return result["choices"][0]["message"].get("content", "")
        except Exception as e:
            chat_logger.warning(f"Final no-tool answer failed after max tool rounds: {e}")
            return "I found relevant material, but need a narrower question to answer accurately. Please ask about a specific formula, line number, symptom pattern, or term."

    def _claude_tools(self, tools):
        claude_tools = []
        for tool in tools or []:
            fn = tool.get("function", {})
            claude_tools.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return claude_tools

    def _message_text(self, content):
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(part.get("text", "") for part in content if part.get("type") == "text")
        return ""

    def _chat_with_claude_tools(self, messages, system_prompt=None, tools=None):
        claude_messages = [
            {"role": msg["role"], "content": msg.get("content", "")}
            for msg in messages
            if msg.get("role") in ["user", "assistant"]
        ]
        max_tool_rounds = 3
        seen_tool_calls = set()
        for _round in range(max_tool_rounds):
            payload = {
                "model": self.model,
                "messages": claude_messages,
                "max_tokens": 2000,
            }
            if system_prompt:
                payload["system"] = system_prompt
            claude_tools = self._claude_tools(tools)
            if claude_tools:
                payload["tools"] = claude_tools

            result = self._send_claude_request(payload)
            content = result.get("content", [])
            tool_uses = [part for part in content if part.get("type") == "tool_use"]
            if not tool_uses:
                return self._message_text(content)

            claude_messages.append({"role": "assistant", "content": content})
            tool_results = []
            for tool_use in tool_uses:
                fn_name = tool_use.get("name")
                fn_args = tool_use.get("input", {}) or {}
                chat_logger.info(f"Claude tool call: {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:100]})")
                tool_signature = (fn_name, json.dumps(fn_args, sort_keys=True, ensure_ascii=False))
                if tool_signature in seen_tool_calls:
                    result_text = json.dumps({"message": "This search was already run. Use the previous result to answer."}, ensure_ascii=False)
                else:
                    seen_tool_calls.add(tool_signature)
                    handler = TOOL_DISPATCH.get(fn_name)
                    if handler:
                        try:
                            result_text = handler(**fn_args)
                        except Exception as e:
                            result_text = json.dumps({"error": str(e)}, ensure_ascii=False)
                    else:
                        result_text = json.dumps({"error": f"Unknown tool: {fn_name}"}, ensure_ascii=False)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.get("id"),
                    "content": result_text,
                })
            claude_messages.append({"role": "user", "content": tool_results})

        chat_logger.warning("Max Claude tool rounds reached")
        claude_messages.append({
            "role": "user",
            "content": (
                "Stop searching now. Answer the user's original question from the context "
                "and tool results already provided. Keep it concise, cite the available "
                "numbered sources when useful, and do not mention tool use or search limits."
            )
        })
        try:
            payload = {
                "model": self.model,
                "messages": claude_messages,
                "max_tokens": 1200,
            }
            if system_prompt:
                payload["system"] = system_prompt
            result = self._send_claude_request(payload)
            return self._message_text(result.get("content", []))
        except Exception as e:
            chat_logger.warning(f"Final Claude no-tool answer failed after max tool rounds: {e}")
            return "I found relevant material, but need a narrower question to answer accurately. Please ask about a specific formula, line number, symptom pattern, or term."

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
                    raise Exception(f"Invalid API key - please check the {self.provider} token")
                elif response.status_code == 429:
                    wait = 2 ** attempt
                    chat_logger.warning(f"Rate limited, waiting {wait}s")
                    time.sleep(wait)
                    continue
                elif response.status_code != 200:
                    raise Exception(f"{self.provider} API error: {response.text[:200]}")

                result = response.json()
                chat_logger.info(f"API successful | {result.get('usage', {})}")
                return result

            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise Exception(f"{self.provider} API failed after {self.max_retries} attempts: {last_error}")

    def _send_claude_request(self, payload):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 401:
                    raise Exception("Invalid API key - please check the Claude token")
                elif response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                elif response.status_code != 200:
                    raise Exception(f"Claude API error: {response.text[:200]}")

                result = response.json()
                chat_logger.info(f"Claude API successful | {result.get('usage', {})}")
                return result

            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise Exception(f"Claude API failed after {self.max_retries} attempts: {last_error}")


# ── Context builder (lightweight initial pass, tools handle deep search) ──

def build_context(query):
    """Build relevant context from knowledge base and lessons database based on query."""
    chat_logger.debug(f"build_context called with query: {query[:100]}...")
    
    context_parts = []
    sources = []
    
    expanded_query = expand_formula_pinyin_query(query)
    query_lower = query.lower()
    wants_fuling = True
    query_words = set(re.findall(r'[a-z0-9]+', query_lower))
    formula_number_match = re.search(r"(?:方剂|方|formula)\s*#?\s*(\d{1,3})\b", query, re.IGNORECASE)
    lesson_number = re.search(r'(?:lecture|lesson|课(?:程)?|讲)\s*(\d{1,4})', query, re.IGNORECASE)
    
    for key, formula in FORMULAS.items():
        names = formula['names']
        name_values = [str(names.get('zh', '')).lower(), str(names.get('pinyin', '')).lower(), str(names.get('en', '')).lower()]
        matches_name = any(n and n in query_lower for n in name_values)
        pinyin_values = [formula.get("formula_title", ""), names.get("zh", "")]
        pinyin_values.extend(c.get("herb", "") for c in formula.get("composition", []))
        matches_pinyin = pinyin_matches(query, *pinyin_values)
        matches_number = bool(formula_number_match and str(formula.get("formula_number", "")) == formula_number_match.group(1))
        key_terms = key.replace('_', ' ').split()
        matches_key = len(key_terms) >= 2 and sum(1 for t in key_terms if t in query_words) >= 2
        if matches_key or matches_name or matches_number or matches_pinyin:
            context_text = format_formula_context(formula)
            context_parts.append(context_text)
            title_zh = formula_source_title(formula, "zh")
            title_en = formula_source_title(formula, "en")
            sources.append({
                "title": title_zh,
                "title_zh": title_zh,
                "title_en": title_en,
                "type": "formula",
                "key": key,
                "content": context_text
            })
    
    for term_cn, term_info in TERMINOLOGY.items():
        if term_cn.lower() in query_lower or term_info.get('en', '').lower() in query_lower or pinyin_matches(query, term_cn, term_info.get("pinyin", "")):
            context_text = f"Term: {term_cn} ({term_info.get('pinyin', '')}) - {term_info.get('en', '')}"
            context_parts.append(context_text)
            sources.append({
                "title": "Shang Han Za Bing Lun - Terminology",
                "type": "terminology",
                "key": term_cn,
                "content": context_text
            })
    
    for pattern_key, pattern in PATTERN_INFO.items():
        if pattern_key.replace('_', ' ') in query_lower or pattern['name'].get('en', '').lower() in query_lower:
            context_text = format_pattern_context(pattern, pattern_key)
            context_parts.append(context_text)
            sources.append({
                "title": f"Shang Han Za Bing Lun - {pattern['name']['en']} Pattern",
                "type": "pattern",
                "key": pattern_key,
                "content": context_text
            })
    
    # Search the canonical Fuling textbook. Songben numbers are secondary tags
    # stored on the same record, not independent sources.
    try:
        fuling_results = db.search_fuling_articles(expanded_query) if wants_fuling and not formula_number_match and not lesson_number else []
        if fuling_results:
            for r in fuling_results[:12]:
                fa_num = r["fuling_article_num"]
                # Avoid duplicating if already found via Song search
                if any(s.get("key") == f"fuling_{fa_num}" for s in sources):
                    continue
                songben_tag = f"（宋本 {r['song_article_num']}）" if r['song_article_num'] else ""
                text = f"【涪陵古本 {fa_num}{songben_tag}】{r['fuling_zh'][:200]}"
                title_zh = f"涪陵古本第 {fa_num} 条" + (f"（宋本第 {r['song_article_num']} 条）" if r['song_article_num'] else "")
                title_en = f"Fulingben line {fa_num}" + (f" (Songben line {r['song_article_num']})" if r['song_article_num'] else "")
                context_parts.append(text)
                sources.append({
                    "title": title_zh,
                    "title_zh": title_zh,
                    "title_en": title_en,
                    "type": "fuling_article",
                    "key": f"fuling_{fa_num}",
                    "content": text
                })
    except Exception as e:
        chat_logger.warning(f"Article search failed: {e}")

    # Lecture material is available to the AI and is represented in the numbered
    # source list, but its protected text must never be exposed in the UI popup.
    try:
        lesson_matches = []
        if lesson_number:
            lesson_id = f"lesson{int(lesson_number.group(1)):04d}"
            exact_lesson = db.get_lesson(lesson_id)
            if exact_lesson:
                lesson_matches.append(exact_lesson)

        if not lesson_matches:
            seen_lesson_ids = set()
            for result in db.search_lessons(expanded_query):
                if result["lesson_id"] not in seen_lesson_ids:
                    lesson_matches.append(result)
                    seen_lesson_ids.add(result["lesson_id"])

        for r in lesson_matches[:3]:
            lesson_id = r["lesson_id"]
            lecture_number = int(re.search(r'\d+', lesson_id).group())
            lecture_text = (r.get("content") or r.get("preview") or "").strip()
            if not lecture_text:
                continue
            context_parts.append(f"[Lecture {lecture_number}] {lecture_text}")
            title_zh = f"马寿椿医师第 {lecture_number} 讲"
            title_en = f"Dr. Ma lecture {lecture_number}"
            sources.append({
                "title": title_zh,
                "title_zh": title_zh,
                "title_en": title_en,
                "type": "lecture",
                "key": lesson_id,
                "hide_in_popup": True
            })
    except Exception as e:
        chat_logger.warning(f"Lecture search failed: {e}")

    if not context_parts:
        context_parts.append("General reference: The Shang Han Za Bing Lun contains 112 classical formulas organized by the Six Channel (六经辨证) pattern identification system.")
        sources.append({"title": "Shang Han Za Bing Lun - General Reference", "type": "general", "key": "", "content": context_parts[-1]})
    
    seen = set()
    unique_sources = []
    for s in sources:
        if s["title"] not in seen:
            seen.add(s["title"])
            unique_sources.append(s)
    if not formula_number_match:
        type_order = {
            "fuling_article": 0,
            "formula": 1,
            "terminology": 2,
            "pattern": 3,
            "lecture": 4,
            "general": 5,
        }
        unique_sources.sort(key=lambda source: type_order.get(source.get("type"), 9))
    
    return "\n\n".join(context_parts), unique_sources


def format_formula_context(formula):
    names = formula['names']
    comp = formula['composition']
    herbs = ", ".join([f"{c['herb']} ({c['pinyin']}, {c['dosage']})" for c in comp])
    roles = ", ".join([f"{c['herb']} as {c['role']}" for c in comp])
    title = formula.get("formula_title") or names["zh"]
    formula_number = formula.get("formula_number")
    source_text = formula.get("source_text")
    preparation_text = formula.get("preparation_text")
    formula_label = f"方 {formula_number}: {title}" if formula_number else f"Formula: {title}"
    if source_text:
        parts = [
            formula_label,
            f"Reference: {formula_source_title(formula, 'zh')}",
            f"Use/Textbook line: {formula.get('yuanben_text') or formula.get('indications') or ''}",
            source_text,
        ]
        if preparation_text:
            parts.append(f"Preparation:\n{preparation_text}")
        return "\n".join(parts)
    return f"""{formula_label} ({names['pinyin']}, {names['en']})
Reference: {formula_source_title(formula, "zh")}
Composition: {herbs}
Roles: {roles}
Indications: {formula['indications']}
Functions: {formula['functions']}
Pattern: {formula['pattern']}"""


def formula_source_title(formula, language="zh"):
    yuanben = formula.get("yuanben_article_num")
    comparison = formula.get("comparison_article_num") or formula.get("songben_article_num")
    comparison_book = formula.get("comparison_book") or "宋本"
    formula_number = formula.get("formula_number")
    name = formula.get("formula_title") or formula.get("names", {}).get("zh") or ""
    if language == "en":
        comparison_label = "Jingui" if comparison_book == "金匮" else "Songben"
        if yuanben and comparison:
            prefix = f"Fulingben line {yuanben} ({comparison_label} line {comparison})"
        elif yuanben:
            prefix = f"Fulingben line {yuanben}"
        elif comparison:
            prefix = f"{comparison_label} line {comparison}"
        else:
            prefix = "Shang Han Za Bing Lun"
        if formula_number:
            return f"{prefix} - Formula {formula_number}: {name}"
        return f"{prefix} - {name}".rstrip(" -")
    if yuanben and comparison:
        prefix = f"涪陵古本第 {yuanben} 条（{comparison_book}第 {comparison} 条）"
    elif yuanben:
        prefix = f"涪陵古本第 {yuanben} 条"
    elif comparison:
        prefix = f"{comparison_book}第 {comparison} 条"
    else:
        prefix = "Shang Han Za Bing Lun"
    if formula_number:
        return f"{prefix} - 方 {formula_number}: {name}"
    return f"{prefix} - {name}".rstrip(" -")


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
        zh = names.get("zh", "")
        pinyin = names.get("pinyin", "").lower()
        en = names.get("en", "").lower()
        if (zh and zh in text) or (pinyin and pinyin in text_lower) or (en and en in text_lower):
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
The Shang Han Za Bing Lun exists in two primary editions in this system:
1. **宋本 (Song Edition)** — the standard 宋本《伤寒论》, also referred to as "Song version"
2. **涪陵古本 (Fuling Ancient Edition)** — 《重编施注涪陵古本伤寒杂病论》, the primary lecture textbook

Default to 涪陵古本/Fuling Ancient Edition for article, chapter, line, or 条文 requests when the edition is not explicitly specified. Use Song edition tools only when the user explicitly says 宋本, Songben, or Song edition. If both versions are relevant, answer from Fuling first and mention the aligned Songben number as secondary context.

TOOLS AVAILABLE:
You have access to the following tools to look up information on demand:
- search_formulas(query) — Search the classical formula database
- search_terminology(query) — Look up TCM term definitions
- search_articles(query) — Search the Fuling Ancient Edition first by keyword, line number, Songben secondary tag, or channel
- get_article(article_num) — Get a specific Song edition article by its Songben number; use only for explicit 宋本/Songben requests
- get_fuling_article(article_num) — Get a specific Fuling Ancient Edition article (涪陵古本) by its number (default for bare chapter/article/line requests, e.g., 10)
- search_fuling_articles(query) — Search the Fuling Ancient Edition (涪陵古本) articles by keyword

Use at most one or two searches before answering. Do not repeat the same search. Context prefixed with [Lecture N] is lecture material: use it directly and cite its matching numbered source. Never reproduce long lecture passages verbatim."""


class ChatEngine:
    """Chat engine for Shang Han Za Bing Lun queries with function calling."""

    def __init__(self, api_key=None):
        self.client = DeepSeekClient(api_key)
        self.system_prompt = TOOL_SYSTEM_PROMPT
        chat_logger.info("ChatEngine initialized (tool-calling mode)")

    def process_query(self, query, conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        chat_logger.info(f"Processing query: {query[:100]}... | History: {len(conversation_history)} messages")

        if needs_formula_followup(query, conversation_history):
            chat_logger.info("Formula recommendation request needs intake follow-up before suggesting formulas")
            return formula_followup_response(query), [], "", []

        # Lightweight initial context (tools handle deeper search)
        context, sources = build_context(query)
        chat_logger.debug(f"Initial context: {len(context)} chars, {len(sources)} sources")
        source_list = "\n".join(
            f"[{idx}] {source.get('title') if isinstance(source, dict) else source}"
            for idx, source in enumerate(sources, start=1)
        )

        user_message = f"""Question: {query}

Relevant context from Shang Han Za Bing Lun:
{context}

Available numbered sources:
{source_list}

Instructions:
- Use the available tools only if the provided context is not enough. Do not repeat searches.
- Keep answers SHORT (2-4 sentences).
- Use **bold** for formula names and key terms.
- After each formula or key claim, add a source reference in brackets like [1], [2] etc.
- Only use citation numbers from the Available numbered sources list above. You may cite lecture sources by number, but do not quote long lecture passages.
- Use ## for sections.
- Before recommending a formula for a patient's symptoms, confirm the conversation includes enough pattern details: main symptoms/duration, fever-chills-sweating, thirst/appetite/stool/urine, tongue/pulse when known, and safety context such as pregnancy, medications, or major illness. If these are missing, ask follow-up questions instead of recommending a formula.
- If you recommend a specific formula after sufficient intake, include a [FORMULA] JSON block at the end.
- Focus on the most relevant information only."""

        try:
            messages = []
            for msg in conversation_history[-6:]:
                if msg.get('role') in ['user', 'assistant']:
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content'][:500]
                    })
            # Lecture documents are longer than the former 4k-character cap;
            # retain enough context for the model to read the retrieved lecture.
            messages.append({"role": "user", "content": user_message[:16000]})

            chat_logger.debug(f"Sending to API with {len(messages)} messages + tools")
            answer = self.client.chat_with_tools(messages, self.system_prompt, tools=SEARCH_TOOLS)
            chat_logger.info(f"Query processed successfully, answer length: {len(answer)} chars")

        except Exception as e:
            chat_logger.error(f"Error processing query: {e}")
            answer = f"I apologize, but I encountered an error processing your query: {str(e)}. Please ensure the active AI provider token is properly configured."

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
