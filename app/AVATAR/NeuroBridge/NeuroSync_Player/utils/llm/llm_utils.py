# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

import requests
from threading import Thread
from queue import Queue
from openai import OpenAI
import json

from utils.llm.sentence_builder import SentenceBuilder
from utils.scb import scb_store, BridgeCache  # NEW
from utils.scb.color_text import ColorText # ADDED


def warm_up_llm_connection(config):
    """
    Perform a lightweight dummy request to warm up the LLM connection.
    This avoids the initial delay when the user sends the first real request.
    """
    provider = config.get("LLM_PROVIDER", "openai")
    
    if provider == "ollama":
        try:
            # Test Ollama connection
            ollama_endpoint = config["OLLAMA_API_ENDPOINT"]
            test_url = f"{ollama_endpoint}/api/tags"  # List available models
            response = requests.get(test_url, timeout=3)
            if response.ok:
                print(f"🦙 Ollama connection successful. Available models: {len(response.json().get('models', []))}")
            else:
                print(f"⚠️ Ollama connection test failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠️ Ollama connection warm-up failed: {e}")
    elif provider == "custom_local" or config["USE_LOCAL_LLM"]:
        try:
            # For local LLM, use a dummy ping request with a short timeout.
            requests.post(config["LLM_STREAM_URL"], json={"dummy": "ping"}, timeout=1)
            print("🔧 Custom Local LLM connection warmed up.")
        except Exception as e:
            print(f"⚠️ Custom Local LLM connection warm-up failed: {e}")
    else:  # OpenAI
        try:
            # For OpenAI API, send a lightweight ping message.
            client = OpenAI(api_key=config["OPENAI_API_KEY"])
            client.chat.completions.create(
                model=config.get("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "system", "content": "ping"}],
                max_tokens=1,
                stream=False
            )
            print("🎯 OpenAI API connection warmed up.")
        except Exception as e:
            print(f"⚠️ OpenAI API connection warm-up failed: {e}")


def update_ui(token: str):
    """
    Immediately update the UI with the token.
    This version checks for newline characters and prints them so that
    line breaks and paragraphs are preserved.
    """
    # Replace Windows-style newlines with Unix-style
    token = token.replace('\r\n', '\n')
    # If the token contains newline(s), split and print accordingly.
    if '\n' in token:
        parts = token.split('\n')
        for i, part in enumerate(parts):
            print(part, end='', flush=True)
            if i < len(parts) - 1:
                print()
    else:
        print(token, end='', flush=True)


def build_llm_payload(user_input, chat_history, config):
    """
    Build the conversation messages and payload from the user input,
    chat history, and configuration.  (SCB-enhanced)
    """
    system_message = config.get(
        "system_message",
        "You are Mai, speak naturally and like a human might with humour and dryness."
    )
    messages = [{"role": "system", "content": system_message}]

    # ----- SCB context injection -----
    try:
        summary = scb_store.get_summary()
        if summary:
            messages.append({"role": "system", "content": f"Current summary:\n{summary}"})
        recent_chat = scb_store.get_recent_chat(3)
        if recent_chat:
            messages.append({"role": "system", "content": f"Recent chat:\n{recent_chat}"})
        bridge_txt = BridgeCache.read()
        if bridge_txt:
            messages.append({"role": "system", "content": bridge_txt})
    except Exception as scb_err:
        # Fail gracefully – continue without SCB context
        print(f"[LLM] Warning: SCB context unavailable ({scb_err}). Proceeding without it.")
    # ---------------------------------

    # Preserve existing rolling history inclusion
    for entry in chat_history:
        messages.append({"role": "user", "content": entry["input"]})
        messages.append({"role": "assistant", "content": entry["response"]})

    # Finally the current user turn
    messages.append({"role": "user", "content": user_input})

    # ---- PRINT FULL PROMPT FOR DEBUGGING ----
    try:
        full_prompt_text_for_log = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        print(f"\n{ColorText.PURPLE}--- LLM PROMPT START ---\n{full_prompt_text_for_log}\n--- LLM PROMPT END ---{ColorText.RESET}\n")
    except Exception as e:
        print(f"{ColorText.YELLOW}[LLM PROMPT LOGGING ERROR] Could not print full prompt: {e}{ColorText.RESET}")
    # -----------------------------------------

    # Build payload based on provider
    provider = config.get("LLM_PROVIDER", "openai")
    
    if provider == "ollama":
        # Ollama API format
        payload = {
            "model": config.get("OLLAMA_MODEL", "llama3.2:3b"),
            "messages": messages,
            "stream": config.get("OLLAMA_STREAMING", True),
            "options": {
                "temperature": 0.8,
                "top_p": 0.9,
                "num_predict": 4000,
            }
        }
    else:
        # OpenAI/Custom format
        payload = {
            "messages": messages,
            "max_new_tokens": 4000,
            "temperature": 1,
            "top_p": 0.9
        }
    
    return payload


def ollama_streaming(user_input, chat_history, chunk_queue, config):
    """
    Streams tokens from Ollama using the streaming API.
    """
    payload = build_llm_payload(user_input, chat_history, config)
    full_response = ""
    max_chunk_length = config.get("max_chunk_length", 500)
    flush_token_count = config.get("flush_token_count", 10)
    
    # Create the SentenceBuilder and a dedicated token_queue.
    sentence_builder = SentenceBuilder(chunk_queue, max_chunk_length, flush_token_count)
    token_queue = Queue()  
    sb_thread = Thread(target=sentence_builder.run, args=(token_queue,))
    sb_thread.start()
    
    try:
        ollama_endpoint = config["OLLAMA_API_ENDPOINT"]
        url = f"{ollama_endpoint}/api/chat"
        
        print(f"\n{ColorText.GREEN}🦙 Ollama Streaming Response:{ColorText.RESET}\n", flush=True)
        
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        
                        # Extract token from Ollama response
                        if 'message' in data and 'content' in data['message']:
                            token = data['message']['content']
                            if token:
                                full_response += token
                                update_ui(token)
                                token_queue.put(token)
                        
                        # Check if this is the final message
                        if data.get('done', False):
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"[Ollama] JSON decode error: {e}")
                        continue
        
        token_queue.put(None)
        sb_thread.join()
        return full_response.strip()
        
    except Exception as e:
        print(f"\n{ColorText.RED}Error during Ollama streaming: {e}{ColorText.RESET}")
        return "Error: Ollama streaming call failed."


def ollama_non_streaming(user_input, chat_history, chunk_queue, config):
    """
    Calls Ollama non-streaming endpoint and processes the entire response.
    """
    payload = build_llm_payload(user_input, chat_history, config)
    payload["stream"] = False  # Ensure non-streaming
    
    full_response = ""
    max_chunk_length = config.get("max_chunk_length", 500)
    flush_token_count = config.get("flush_token_count", 10)
    
    # Set up the SentenceBuilder.
    sentence_builder = SentenceBuilder(chunk_queue, max_chunk_length, flush_token_count)
    token_queue = Queue()
    sb_thread = Thread(target=sentence_builder.run, args=(token_queue,))
    sb_thread.start()
    
    try:
        ollama_endpoint = config["OLLAMA_API_ENDPOINT"]
        url = f"{ollama_endpoint}/api/chat"
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if 'message' in result and 'content' in result['message']:
            text = result['message']['content']
            print(f"\n{ColorText.GREEN}🦙 Ollama Response:{ColorText.RESET}\n", flush=True)
            
            # Process text word by word for natural display
            tokens = text.split(' ')
            for token in tokens:
                token_with_space = token + " "
                full_response += token_with_space
                update_ui(token_with_space)
                token_queue.put(token_with_space)
        else:
            print(f"{ColorText.RED}Unexpected Ollama response format{ColorText.RESET}")
            return "Error: Unexpected response format from Ollama."
        
        token_queue.put(None)
        sb_thread.join()
        return full_response.strip()
        
    except Exception as e:
        print(f"{ColorText.RED}Error calling Ollama: {e}{ColorText.RESET}")
        return "Error: Ollama call failed."


def local_llm_streaming(user_input, chat_history, chunk_queue, config):
    """
    Streams tokens from a local LLM using streaming.
    """
    payload = build_llm_payload(user_input, chat_history, config)
    full_response = ""
    max_chunk_length = config.get("max_chunk_length", 500)
    flush_token_count = config.get("flush_token_count", 10)
    
    # Create the SentenceBuilder and a dedicated token_queue.
    sentence_builder = SentenceBuilder(chunk_queue, max_chunk_length, flush_token_count)
    token_queue = Queue()  
    sb_thread = Thread(target=sentence_builder.run, args=(token_queue,))
    sb_thread.start()
    
    try:
        session = requests.Session()
        with session.post(config["LLM_STREAM_URL"], json=payload, stream=True) as response:
            response.raise_for_status()
            print(f"\n{ColorText.CYAN}🔧 Custom Local LLM Streaming Response:{ColorText.RESET}\n", flush=True)
            for token in response.iter_content(chunk_size=1, decode_unicode=True):
                if not token:
                    continue
                full_response += token
                update_ui(token)
                token_queue.put(token)
        session.close()
        
        token_queue.put(None)
        sb_thread.join()
        return full_response.strip()
    
    except Exception as e:
        print(f"\n{ColorText.RED}Error during streaming local LLM call: {e}{ColorText.RESET}")
        return "Error: Streaming LLM call failed."

def local_llm_non_streaming(user_input, chat_history, chunk_queue, config):
    """
    Calls a local LLM non-streaming endpoint and processes the entire response.
    """
    payload = build_llm_payload(user_input, chat_history, config)
    full_response = ""
    max_chunk_length = config.get("max_chunk_length", 500)
    flush_token_count = config.get("flush_token_count", 10)
    
    # Set up the SentenceBuilder.
    sentence_builder = SentenceBuilder(chunk_queue, max_chunk_length, flush_token_count)
    token_queue = Queue()
    sb_thread = Thread(target=sentence_builder.run, args=(token_queue,))
    sb_thread.start()
    
    try:
        session = requests.Session()
        response = session.post(config["LLM_API_URL"], json=payload)
        session.close()
        if response.ok:
            result = response.json()
            text = result.get('assistant', {}).get('content', "Error: No response.")
            print(f"{ColorText.CYAN}🔧 Custom Local LLM Response:{ColorText.RESET}\n", flush=True)
            tokens = text.split(' ')
            for token in tokens:
                token_with_space = token + " "
                full_response += token_with_space
                update_ui(token_with_space)
                token_queue.put(token_with_space)
            
            token_queue.put(None)
            sb_thread.join()
            return full_response.strip()
        else:
            print(f"{ColorText.RED}LLM call failed: HTTP {response.status_code}{ColorText.RESET}")
            return "Error: LLM call failed."
    
    except Exception as e:
        print(f"{ColorText.RED}Error calling local LLM: {e}{ColorText.RESET}")
        return "Error: Exception occurred."


def openai_llm_streaming(user_input, chat_history, chunk_queue, config):
    """
    Streams tokens from the OpenAI API.
    """
    payload = build_llm_payload(user_input, chat_history, config)
    full_response = ""
    max_chunk_length = config.get("max_chunk_length", 500)
    flush_token_count = config.get("flush_token_count", 10)
    
    # Set up the SentenceBuilder.
    sentence_builder = SentenceBuilder(chunk_queue, max_chunk_length, flush_token_count)
    token_queue = Queue()
    sb_thread = Thread(target=sentence_builder.run, args=(token_queue,))
    sb_thread.start()
    
    try:
        client = OpenAI(api_key=config["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=config.get("OPENAI_MODEL", "gpt-4o"),
            messages=payload["messages"],
            max_tokens=4000,
            temperature=1,
            top_p=0.9,
            stream=True
        )
        print(f"{ColorText.BLUE}🎯 OpenAI Streaming Response:{ColorText.RESET}\n", flush=True)
        for chunk in response:
            token = chunk.choices[0].delta.content if chunk.choices[0].delta else ""
            if not token:
                continue
            full_response += token
            update_ui(token)
            token_queue.put(token)
        
        token_queue.put(None)
        sb_thread.join()
        return full_response.strip()
    
    except Exception as e:
        print(f"{ColorText.RED}Error calling OpenAI API (streaming): {e}{ColorText.RESET}")
        return "Error: OpenAI API call failed."


def openai_llm_non_streaming(user_input, chat_history, chunk_queue, config):
    """
    Calls the OpenAI API without streaming.
    """
    payload = build_llm_payload(user_input, chat_history, config)
    full_response = ""
    max_chunk_length = config.get("max_chunk_length", 500)
    flush_token_count = config.get("flush_token_count", 10)
    
    # Set up the SentenceBuilder.
    sentence_builder = SentenceBuilder(chunk_queue, max_chunk_length, flush_token_count)
    token_queue = Queue()
    sb_thread = Thread(target=sentence_builder.run, args=(token_queue,))
    sb_thread.start()
    
    try:
        client = OpenAI(api_key=config["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=config.get("OPENAI_MODEL", "gpt-4o"),
            messages=payload["messages"],
            max_tokens=4000,
            temperature=1,
            top_p=0.9
        )
        text = response.choices[0].message.content
        
        print(f"{ColorText.BLUE}🎯 OpenAI Response:{ColorText.RESET}\n", flush=True)
        tokens = text.split(' ')
        for token in tokens:
            token_with_space = token + " "
            full_response += token_with_space
            update_ui(token_with_space)
            token_queue.put(token_with_space)
        
        token_queue.put(None)
        sb_thread.join()
        return full_response.strip()
    
    except Exception as e:
        print(f"{ColorText.RED}Error calling OpenAI API (non-streaming): {e}{ColorText.RESET}")
        return "Error: OpenAI API call failed."


def stream_llm_chunks(user_input, chat_history, chunk_queue, config):
    """
    Dispatches the LLM call to the proper variant based on the configuration.
    Enhanced with Ollama support and improved provider selection.
    """
    provider = config.get("LLM_PROVIDER", "openai")
    use_streaming = config.get("USE_STREAMING", True)
    
    print(f"{ColorText.MAGENTA}[LLM] Using provider: {provider}, streaming: {use_streaming}{ColorText.RESET}")
    
    if provider == "ollama":
        if use_streaming and config.get("OLLAMA_STREAMING", True):
            return ollama_streaming(user_input, chat_history, chunk_queue, config)
        else:
            return ollama_non_streaming(user_input, chat_history, chunk_queue, config)
    elif provider == "custom_local" or config.get("USE_LOCAL_LLM", False):
        if use_streaming:
            return local_llm_streaming(user_input, chat_history, chunk_queue, config)
        else:
            return local_llm_non_streaming(user_input, chat_history, chunk_queue, config)
    else:  # Default to OpenAI
        if use_streaming:
            return openai_llm_streaming(user_input, chat_history, chunk_queue, config)
        else:
            return openai_llm_non_streaming(user_input, chat_history, chunk_queue, config)

