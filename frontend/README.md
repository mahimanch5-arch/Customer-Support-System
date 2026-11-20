# Frontend — Phase 1 (UI only, mock data)

ChatGPT-style chat UI for the Agentic Customer Support System. **No backend
calls**: every answer comes from a local mock that fakes latency and token
streaming. Phase 2 adds the remaining APIs; Phase 3 adds the agent harness.

React 18 + TypeScript + Vite. Plain CSS, no UI framework, no state library —
one reducer and one hook.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # typecheck + production bundle into dist/
npm run typecheck
```

## What's implemented

| Requirement | Where |
|---|---|
| Sidebar with conversation history, grouped by recency | `src/components/Sidebar.tsx` |
| Prompt bar (Enter sends, Shift+Enter newline, auto-grow, stop button) | `src/components/PromptBar.tsx` |
| Multi-turn chat window, follows the stream unless you scroll up | `src/components/ChatWindow.tsx` |
| Unique Conversation ID / Turn ID / Message ID | `src/lib/ids.ts` |
| Title auto-generated from the first question | `src/lib/title.ts` |
| Prior turns retained and shaped for the agent | `buildHistory` in `src/state/reducer.ts` |
| Mock agent with streaming, abort and retry | `src/mock/agentClient.ts` |

Also: new/select/rename (double-click a sidebar item)/delete conversation,
per-turn error + retry, light & dark themes, mobile layout, history persisted
to `localStorage` (best-effort — the app works fine without it).

Out of scope by design: **document/file uploads**.

## Data model

```
Conversation { id, title, createdAt, updatedAt, turns[] }
  └─ Turn { id, status: pending|complete|error, human: Message, ai: Message|null }
       └─ Message { id, role: human|ai, content, createdAt, meta? }
```

`Turn.ai` is `null` while the agent is answering, which is what drives the
typing indicator. `Message.meta` carries what the agent used — tool APIs
called, KB articles cited, whether it escalated — rendered as chips under the
answer. The mock populates it so the real agent has somewhere to put it.

## Wiring up Phases 2 and 3

There is exactly one seam: **`askAgent` in `src/mock/agentClient.ts`**. It takes
an `AgentRequest` and yields `{ delta?, meta? }` chunks. Replace its body with a
fetch against the harness and nothing else in the app changes — the UI already
builds the full request, including prior turns as `history`:

```ts
// src/types.ts
interface AgentRequest {
  conversationId: string;
  question: string;        // the new question
  messageId: string;
  history: { role, content, messageId }[];  // prior completed turns, oldest -> newest
}
```

Notes for whoever does that swap:

- Only **completed** turns enter `history`; a pending or errored turn is not context.
- The UI already handles abort (`AbortSignal` is passed through), per-chunk
  appends, and a final chunk carrying `meta` — map SSE/chunked events onto those.
- `vite.config.ts` proxies `/api` to `http://127.0.0.1:8000`, so calls to
  `/api/v1/...` reach the FastAPI app in dev with no CORS setup.
- Server-generated ids should win: when the backend returns real conversation
  and message ids, use them instead of the client-side ones from `src/lib/ids.ts`.
