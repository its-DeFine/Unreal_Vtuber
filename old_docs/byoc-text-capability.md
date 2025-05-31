# Livepeer BYOC – Migrating from Voice-Clone to Text-Echo Capability

> **Goal**  
> Accept a JSON request `{ "text": "..." }` and return `{ "echo": "...a" }` (or any other trivial text response) through the same Orchestrator/Gateway pipeline, re-using the on-chain payment & capability negotiation already proven by the voice-clone sample.

---

## 1  Reference: current voice-clone request-flow

1. **Worker start-up** – `server.py` registers capability `voice-clone` at `ORCH_URL/capability/register`.
2. **Front-end** – user connects wallet → JS obtains signer.
3. **GET /process/token**  
   `Livepeer-Job-Eth-Address` (base64 of `{addr,sig}`)  +  `Livepeer-Job-Capability: voice-clone` → returns `{ticket_params, price, …}`.
4. **POST /process/request/voice-clone**  
   headers:
   - `Livepeer-Job`             (base64 of signed **jobRequest** JSON)
   - `Livepeer-Job-Payment`    (base64 of **paymentTicket** JSON)
   body: `multipart/form-data` with `audio`, `text` → orchestrator forwards unchanged to worker.
5. **Worker** does TTS and streams `audio/wav` back – orchestrator pipes to browser.

> All security / payment validation happens in the orchestrator based on the two headers.

---

## 2  Design for **text-echo** capability

| Component | Change | Details |
|-----------|--------|---------|
| Worker container | new route `/v1/echo` (or simply `/`) & capability `text-echo` | Accepts JSON `{text:"foo"}` → responds `{echo:"fooa"}`.  Can be implemented inside existing `server_adapter.py`. |
| Orchestrator | **No change** | Capability registration + ticket validation already generic. |
| Front-end webapp | Replace voice-clone service with `text-echo` service | Re-use token logic 100 %; change `processJob()` so: <br>• `CAPABILITY = "text-echo"` <br>• body = `JSON.stringify({text: prompt})`; `Content-Type: application/json` <br>• fetch URL `/process/request/text-echo` <br>• Expect `application/json` in response. |
| UI component | Remove microphone / audio controls | Simple `<textarea>` + "Send" button; show response JSON. |

### 2.1   Environment variables for worker
```
CAPABILITY_NAME=text-echo
CAPABILITY_DESCRIPTION="simple echo"
CAPABILITY_URL=http://<container>:9876
CAPABILITY_PRICE_PER_UNIT=1
```

### 2.2   Minimal FastAPI handler (pseudo-diff)
```diff
@@
-from fastapi import FastAPI, Request, HTTPException
+# keep imports …

 @app.post("/")
 async def echo_root(req: Request):
     body = await req.json()
-    text = body.get("text", "")
-    return {"echo": text, "received_at": time.time()}
+    text = body.get("text", "")
+    # trivial transform so client sees change
+    return {"echo": f"{text}a"}
```

### 2.3   Frontend service snippet (TypeScript)
```ts
// src/services/textEcho.ts
import { getProcessToken } from "./api"; // reuse token util
const CAPABILITY = "text-echo";
export async function sendText(baseUrl: string, ethAddr: string, signerFn: SignFn, prompt: string) {
  const token = await getProcessToken(baseUrl, ethAddr, signerFn);

  // Build jobRequest & paymentTicket exactly like voice-clone but without FormData
  // … identical logic, just change CAPABILITY and body.

  const resp = await fetch(`${baseUrl}/process/request/text-echo`, {
    method: "POST",
    headers: {
      "Livepeer-Job": jobHeader,
      "Livepeer-Job-Payment": paymentHeader,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: prompt }),
  });
  return resp.json();
}
```

---

## 3  Step-by-step migration checklist

1. **Backend**
   1. Add/modify FastAPI route as above.
   2. Ensure registration env-vars use `text-echo`.
   3. Re-build Docker image → compose file unchanged except variable update.
2. **Frontend**
   1. Duplicate `voice-clone/webapp` into new webapp (already in repo).
   2. Delete audio-capture & waveform rendering components.
   3. Add `textEcho.ts` service; wire to simple React component.
3. **Testing locally**
   1. `docker-compose.byoc.yml` – point Caddy to new dist folder if name differs.
   2. `curl -X GET https://orchestrator:9995/process/token` with proper headers → verify ticket_params arrive.
   3. `curl -X POST https://orchestrator:9995/process/request/text-echo -d '{"text":"hi"}' …` → expect `{"echo":"hia"}`.
4. **Production notes**
   * Payment off-chain (`-network=offchain`) acceptable; switch flags for on-chain.
   * Keep `expiration_check` interval (12 s) – still valid.

---

## 4  Open items / TODO

- [ ] Contract schema for `expected_price` when payload is not time-based (voice used seconds). Keep as 1 for now.
- [ ] Decide on SSE vs plain JSON for future streaming text.
- [ ] Unit tests in `neurosync-worker/tests/` to validate schema & 200-OK path.

---

Happy hacking – this doc should give you a precise map from the working voice-clone demo to a minimal text-echo capability that still exercises all Livepeer BYOC payment & routing primitives. 