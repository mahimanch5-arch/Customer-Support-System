import type { AgentRequest, MessageMeta } from '../types';
import { replyFor } from './replies';

export interface AgentChunk {
  /** Text appended to the answer so far. */
  delta?: string;
  /** Sent once, on the final chunk. */
  meta?: MessageMeta;
}

/**
 * The ONE seam between the UI and the agent.
 *
 * Phase 3 replaces the body of `askAgent` with a fetch against the harness
 * (`POST /api/v1/agent/chat`, SSE or chunked) and yields its chunks instead.
 * Nothing else in the app needs to change: the UI already consumes an async
 * iterable of deltas and already builds the full `AgentRequest` (including the
 * prior turns as history).
 */
export async function* askAgent(
  req: AgentRequest,
  signal?: AbortSignal,
): AsyncGenerator<AgentChunk> {
  const { content, meta } = replyFor(req.question);

  // Simulated "thinking" latency before the first token.
  await sleep(450 + Math.random() * 400, signal);

  // Stream in word-ish chunks so the typing feel matches a real token stream.
  const tokens = content.match(/\S+\s*/g) ?? [content];
  for (let i = 0; i < tokens.length; i += 3) {
    throwIfAborted(signal);
    yield { delta: tokens.slice(i, i + 3).join('') };
    await sleep(14 + Math.random() * 22, signal);
  }

  yield { meta };
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(abortError());
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(t);
        reject(abortError());
      },
      { once: true },
    );
  });
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw abortError();
}

function abortError(): Error {
  const e = new Error('Aborted');
  e.name = 'AbortError';
  return e;
}
