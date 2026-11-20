/**
 * Core conversation data model.
 *
 * Shape is deliberately the one the agent harness (Phase 3) will receive:
 *   Conversation -> ordered Turn[] -> { human: Message, ai: Message | null }
 *
 * Every Conversation and every Message carries its own id so a turn can be
 * referenced, retried or cited later (e.g. tool traces, feedback, ticket links).
 */

export type Role = 'human' | 'ai';

export interface Message {
  /** Unique Message ID, e.g. "msg_9f2c1a4b". */
  id: string;
  role: Role;
  content: string;
  /** ISO-8601 UTC timestamp. */
  createdAt: string;
  /** Populated by the agent later (tool calls, KB citations, confidence...). */
  meta?: MessageMeta;
}

export interface MessageMeta {
  /** Names of tool APIs the agent called to produce this answer. */
  tools?: string[];
  /** KB article paths the answer was grounded in. */
  citations?: string[];
  /** True when the agent wants a human to take over. */
  escalated?: boolean;
}

export type TurnStatus = 'pending' | 'complete' | 'error';

export interface Turn {
  /** Unique Turn ID, e.g. "turn_3b81de02". */
  id: string;
  human: Message;
  /** null while the agent is still answering, or when the turn errored. */
  ai: Message | null;
  status: TurnStatus;
  /** Human-readable reason when status === 'error'. */
  error?: string;
}

export interface Conversation {
  /** Unique Conversation ID, e.g. "conv_7d4e0f11". */
  id: string;
  /** Auto-generated from the user's first question. */
  title: string;
  createdAt: string;
  updatedAt: string;
  /** Ordered oldest -> newest. */
  turns: Turn[];
}

/* ---------- The payload handed to the agent (Phase 3 contract) ---------- */

export interface AgentContextMessage {
  role: Role;
  content: string;
  messageId: string;
}

export interface AgentRequest {
  conversationId: string;
  /** The new question being asked now. */
  question: string;
  messageId: string;
  /** Prior turns, flattened oldest -> newest. Excludes the new question. */
  history: AgentContextMessage[];
}
