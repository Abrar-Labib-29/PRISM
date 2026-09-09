---
name: ollama-streaming-client
description: Ollama /api/chat streaming pattern with thread-safe queue.Queue handoff to CustomTkinter UI thread
---

# Ollama Streaming Client Pattern

## API Endpoint
Use `/api/chat` (NOT `/api/generate`) per §7.4:

```
POST http://127.0.0.1:11434/api/chat
Content-Type: application/json

{
  "model": "phi4-mini",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "stream": true,
  "options": {
    "num_ctx": 2048,
    "num_thread": 4
  }
}
```

## Streaming Token Reader (Worker Thread)

```python
import requests
import json
import threading
import queue

def stream_chat(messages, cancel_event, ui_queue, 
                host="http://127.0.0.1:11434", model="phi4-mini",
                timeout=180):
    """Streams tokens from Ollama and posts them to UI queue.
    Runs on background worker thread — NEVER on main UI thread."""
    
    full_text = []
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{host}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {"num_ctx": 2048, "num_thread": 4}
            },
            stream=True,
            timeout=(5, timeout)  # (connect_timeout, read_timeout)
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            # Check cancellation between every chunk
            if cancel_event.is_set():
                ui_queue.put({"type": "ANALYSIS_CANCELLED"})
                return
            
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Generation exceeded {timeout}s")
            
            if line:
                chunk = json.loads(line)
                if chunk.get("done"):
                    break
                
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_text.append(token)
                    ui_queue.put({"type": "STREAM_TOKEN", "token": token})
        
        completed_text = "".join(full_text)
        ui_queue.put({"type": "STREAM_COMPLETE", "full_text": completed_text})
    
    except requests.ConnectionError:
        ui_queue.put({
            "type": "ANALYSIS_ERROR",
            "error_type": "NETWORK",
            "message": "Ollama connection lost during inference."
        })
    except TimeoutError:
        ui_queue.put({
            "type": "ANALYSIS_ERROR",
            "error_type": "TIMEOUT",
            "message": f"Generation exceeded {timeout} seconds."
        })
    except Exception as e:
        ui_queue.put({
            "type": "ANALYSIS_ERROR",
            "error_type": "NETWORK",
            "message": str(e)
        })
```

## UI Queue Consumer (Main Thread)

```python
class PRISMApp(customtkinter.CTk):
    def _process_queue(self):
        """Called every 50ms via app.after(). Drains queue safely."""
        try:
            while True:
                msg = self._ui_queue.get_nowait()
                
                if msg["type"] == "STATUS_STEP":
                    self.stream_box.set_step(msg["step"], msg["label"])
                
                elif msg["type"] == "STREAM_TOKEN":
                    self.stream_box.append_token(msg["token"])
                
                elif msg["type"] == "STREAM_COMPLETE":
                    pass  # Wait for ANALYSIS_SUCCESS with validated payload
                
                elif msg["type"] == "ANALYSIS_SUCCESS":
                    self._show_results(msg["payload"])
                
                elif msg["type"] == "ANALYSIS_ERROR":
                    self._show_error(msg["error_type"], msg["message"])
                
                elif msg["type"] == "ANALYSIS_CANCELLED":
                    self._reset_ui()
                    self.toast.show("Analysis cancelled.", variant="info")
                    
        except queue.Empty:
            pass
        
        # Re-schedule
        self.after(50, self._process_queue)
```

## Queue Message Protocol (§9.10 item 4)

| Type | Payload | Direction |
|---|---|---|
| `STATUS_STEP` | `step: 1\|2\|3`, `label: str` | Worker → UI |
| `STREAM_TOKEN` | `token: str` | Worker → UI |
| `STREAM_COMPLETE` | `full_text: str` | Worker → UI |
| `ANALYSIS_SUCCESS` | `payload: AnalyzeResponse` | Worker → UI |
| `ANALYSIS_ERROR` | `error_type`, `message` | Worker → UI |
| `ANALYSIS_CANCELLED` | (none) | Worker → UI |

## Critical Rules
1. **NEVER call Tkinter widgets from the worker thread** — always post to queue.
2. **Always check `cancel_event.is_set()` between chunks** — user may cancel mid-stream.
3. **Use `daemon=True` for worker threads** — ensures clean process exit.
4. **Wrap entire worker in global `try/except`** — per §10.6, never let exceptions silently kill the thread.
5. **Model tag is `"phi4-mini"`** — canonical tag, resolves to `phi4-mini:3.8b-instruct-q4_K_M`.

## Ollama Service Discovery (§9.11)

Check order:
1. HTTP ping `GET /api/tags` (1s timeout)
2. `shutil.which("ollama")`
3. `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`
4. `%ProgramFiles%\Ollama\ollama.exe`
5. Config file override

Auto-start: `subprocess.Popen([path, "serve"], creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS)`
Poll `/api/tags` every 1.5s for up to 15s.
