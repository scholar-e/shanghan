"""Chat engine using DeepSeek API."""

import os
import sys
import json
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

chat_logger = setup_logging("chat", level=logging.DEBUG)
chat_logger.info("Chat engine initialized")


class DeepSeekClient:
    """DeepSeek API client."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        self.max_retries = 3
        self.timeout = 60
        chat_logger.info(f"DeepSeekClient initialized | Model: {self.model} | Timeout: {self.timeout}s")
    
    def chat(self, messages, system_prompt=None):
        """Send chat request to DeepSeek API with retry logic."""
        chat_logger.debug(f"DeepSeekClient.chat called with {len(messages)} messages")
        
        if not self.api_key:
            chat_logger.error("DeepSeek API key not configured")
            raise ValueError("DeepSeek API key not configured")
        
        chat_logger.debug(f"Using API key: {self.api_key[:8]}...{self.api_key[-4:]}")  # Log partial for security
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",  # Full key for request
            "Content-Type": "application/json"
        }
        
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt[:100] + "..."})
        all_messages.extend(messages)
        
        payload = {
            "model": self.model,
            "messages": all_messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        chat_logger.info(f"Sending request to DeepSeek API | Attempt 1/{self.max_retries}")
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                chat_logger.debug(f"API attempt {attempt + 1}/{self.max_retries}")
                
                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 401:
                    chat_logger.error("API authentication failed - invalid key")
                    raise Exception("Invalid API key - please check DEEPSEEK_API_KEY")
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    chat_logger.warning(f"Rate limited (429), waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                elif response.status_code != 200:
                    error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
                    chat_logger.error(error_msg)
                    raise Exception(f"DeepSeek API error: {response.text}")
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                chat_logger.info(f"API request successful | Response length: {len(content)} chars")
                return content
                
            except requests.exceptions.Timeout as e:
                last_error = e
                chat_logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    chat_logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
        
        raise Exception(f"DeepSeek API timeout after {self.max_retries} attempts: {last_error}")


def build_context(query):
    """Build relevant context from knowledge base based on query."""
    chat_logger.debug(f"build_context called with query: {query[:100]}...")
    
    context_parts = []
    sources = []
    
    query_lower = query.lower()
    
    for key, formula in FORMULAS.items():
        formula_names = ' '.join([
            str(formula['names'].get('zh', '')),
            str(formula['names'].get('pinyin', '')),
            str(formula['names'].get('en', ''))
        ]).lower()
        
        if any(term in query_lower for term in key.replace('_', ' ').split()):
            context_parts.append(format_formula_context(formula))
            sources.append(f"Shang Han Lun - {formula['names']['pinyin']}")
    
    for term_cn, term_info in TERMINOLOGY.items():
        if term_cn.lower() in query_lower or term_info.get('en', '').lower() in query_lower:
            context_parts.append(f"Term: {term_cn} ({term_info.get('pinyin', '')}) - {term_info.get('en', '')}")
            sources.append("Shang Han Lun - Terminology")
    
    for pattern_key, pattern in PATTERN_INFO.items():
        pattern_names = ' '.join([
            str(pattern['name'].get('zh', '')),
            str(pattern['name'].get('en', ''))
        ]).lower()
        
        if pattern_key.replace('_', ' ') in query_lower or pattern['name'].get('en', '').lower() in query_lower:
            context_parts.append(format_pattern_context(pattern, pattern_key))
            sources.append(f"Shang Han Lun - {pattern['name']['en']} Pattern")
    
    herbs = ['ma huang', 'gui zhi', 'chai hu', 'shi gao', 'huang qin', 'ban xia', 
             'fu ling', 'dang gui', 'sheng di', 'wu wei zi', 'hou po', 'zhi shi',
             '麻黄', '桂枝', '柴胡', '石膏', '黄芩', '半夏', '茯苓', '当归', '生地']
    
    for herb in herbs:
        if herb in query_lower:
            context_parts.append(f"Note: Query mentions herb '{herb}' - refer to relevant formulas for usage context")
            break
    
    if not context_parts:
        context_parts.append("General reference: The Shang Han Lun contains 112 classical formulas organized by the Six Channel (六经辨证) pattern identification system.")
        sources.append("Shang Han Lun - General Reference")
    
    return "\n\n".join(context_parts), list(set(sources))


def format_formula_context(formula):
    """Format formula information as context."""
    names = formula['names']
    comp = formula['composition']
    indications = formula['indications']
    functions = formula['functions']
    pattern = formula['pattern']
    
    herbs = ", ".join([f"{c['herb']} ({c['pinyin']}, {c['dosage']})" for c in comp])
    roles = ", ".join([f"{c['herb']} as {c['role']}" for c in comp])
    
    return f"""Formula: {names['zh']} ({names['pinyin']}, {names['en']})
Composition: {herbs}
Roles: {roles}
Indications: {indications}
Functions: {functions}
Pattern: {pattern}"""


def format_pattern_context(pattern, pattern_key):
    """Format pattern information as context."""
    name = pattern['name']
    location = pattern['location']
    characteristics = pattern['characteristics']
    sub_patterns = ", ".join(pattern['sub_patterns'])
    
    return f"""Pattern: {name['zh']} ({name['en']})
Location: {location}
Characteristics: {characteristics}
Sub-patterns: {sub_patterns}"""


class ChatEngine:
    """Chat engine for Shang Han Lun queries."""
    
    def __init__(self, api_key=None):
        self.client = DeepSeekClient(api_key)
        self.system_prompt = SYSTEM_PROMPT
        chat_logger.info("ChatEngine initialized")
    
    def process_query(self, query, conversation_history=None):
        """Process user query with conversation history and return answer with sources."""
        if conversation_history is None:
            conversation_history = []
        
        chat_logger.info(f"Processing query: {query[:100]}... | History: {len(conversation_history)} messages")
        
        context, sources = build_context(query)
        chat_logger.debug(f"Built context with {len(context)} chars, sources: {sources}")
        
        user_message = f"""Context from Shang Han Lun:

{context}

Question: {query}

Instructions:
- Keep answer SHORT (2-4 sentences)
- Use **bold** for formula names
- Use ## for sections
- Include key dosages and indications
- Focus on most relevant information only"""
        
        try:
            messages = []
            
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                if msg.get('role') in ['user', 'assistant']:
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content'][:500]  # Truncate old messages
                    })
            
            messages.append({"role": "user", "content": user_message[:4000]})
            
            chat_logger.debug(f"Sending {len(messages)} messages to DeepSeek")
            answer = self.client.chat(messages, self.system_prompt)
            chat_logger.info(f"Query processed successfully, answer length: {len(answer)} chars")
        except Exception as e:
            chat_logger.error(f"Error processing query: {e}")
            answer = f"I apologize, but I encountered an error processing your query: {str(e)}. Please ensure the DeepSeek API key is properly configured."
            sources = ["Error"]
        
        return answer, sources


def process_query(query, conversation_history=None, api_key=None):
    """Convenience function to process a query."""
    engine = ChatEngine(api_key)
    return engine.process_query(query, conversation_history)


def test_connection(api_key):
    """Test DeepSeek API connection."""
    client = DeepSeekClient(api_key)
    try:
        response = client.chat([
            {"role": "user", "content": "What is Gui Zhi Tang?"}
        ], "You are a helpful TCM assistant.")
        return True, response
    except Exception as e:
        return False, str(e)
