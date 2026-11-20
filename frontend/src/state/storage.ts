import type { Conversation } from '../types';

const KEY = 'support-assistant.conversations.v1';

/** Best-effort persistence. Private windows and blocked storage must not break the app. */
export function loadConversations(): Conversation[] | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return parsed.filter(isConversation);
  } catch {
    return null;
  }
}

export function saveConversations(conversations: Conversation[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(conversations));
  } catch {
    /* quota, private mode, blocked site data — ignore */
  }
}

function isConversation(v: unknown): v is Conversation {
  const c = v as Conversation;
  return !!c && typeof c.id === 'string' && typeof c.title === 'string' && Array.isArray(c.turns);
}
