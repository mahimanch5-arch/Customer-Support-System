import type { AgentContextMessage, Conversation, MessageMeta, Turn } from '../types';
import { newConversationId, newMessageId, newTurnId } from '../lib/ids';
import { titleFromQuestion } from '../lib/title';

export interface ChatState {
  conversations: Conversation[];
  /** null = the "new conversation" screen. */
  activeId: string | null;
}

export type Action =
  | { type: 'newConversation' }
  | { type: 'selectConversation'; id: string }
  | { type: 'deleteConversation'; id: string }
  | { type: 'renameConversation'; id: string; title: string }
  /** Starts a turn; creates the conversation first if there isn't one. */
  | { type: 'askQuestion'; conversationId: string | null; question: string; turnId: string; conversationIdOverride: string }
  | { type: 'appendDelta'; conversationId: string; turnId: string; delta: string }
  | { type: 'completeTurn'; conversationId: string; turnId: string; meta?: MessageMeta }
  | { type: 'failTurn'; conversationId: string; turnId: string; error: string }
  | { type: 'dropTurn'; conversationId: string; turnId: string };

export const initialState = (conversations: Conversation[]): ChatState => ({
  conversations,
  activeId: null,
});

export function reducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case 'newConversation':
      return { ...state, activeId: null };

    case 'selectConversation':
      return { ...state, activeId: action.id };

    case 'deleteConversation': {
      const conversations = state.conversations.filter((c) => c.id !== action.id);
      return {
        conversations,
        activeId: state.activeId === action.id ? null : state.activeId,
      };
    }

    case 'renameConversation':
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.id ? { ...c, title: action.title.trim() || c.title } : c,
        ),
      };

    case 'askQuestion': {
      const now = new Date().toISOString();
      const turn: Turn = {
        id: action.turnId,
        status: 'pending',
        human: {
          id: newMessageId(),
          role: 'human',
          content: action.question,
          createdAt: now,
        },
        ai: null,
      };

      // Existing conversation: append the turn.
      if (action.conversationId) {
        return {
          ...state,
          activeId: action.conversationId,
          conversations: state.conversations.map((c) =>
            c.id === action.conversationId
              ? { ...c, updatedAt: now, turns: [...c.turns, turn] }
              : c,
          ),
        };
      }

      // First question: the conversation is born, titled from that question.
      const created: Conversation = {
        id: action.conversationIdOverride,
        title: titleFromQuestion(action.question),
        createdAt: now,
        updatedAt: now,
        turns: [turn],
      };
      return {
        conversations: [created, ...state.conversations],
        activeId: created.id,
      };
    }

    case 'appendDelta':
      return mapTurn(state, action.conversationId, action.turnId, (turn) => ({
        ...turn,
        ai: turn.ai
          ? { ...turn.ai, content: turn.ai.content + action.delta }
          : {
              id: newMessageId(),
              role: 'ai',
              content: action.delta,
              createdAt: new Date().toISOString(),
            },
      }));

    case 'completeTurn':
      return mapTurn(state, action.conversationId, action.turnId, (turn) => ({
        ...turn,
        status: 'complete',
        error: undefined,
        ai: turn.ai
          ? { ...turn.ai, meta: action.meta ?? turn.ai.meta }
          : {
              id: newMessageId(),
              role: 'ai',
              content: '',
              createdAt: new Date().toISOString(),
              meta: action.meta,
            },
      }));

    case 'failTurn':
      return mapTurn(state, action.conversationId, action.turnId, (turn) => ({
        ...turn,
        status: 'error',
        error: action.error,
      }));

    case 'dropTurn':
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.conversationId
            ? { ...c, turns: c.turns.filter((t) => t.id !== action.turnId) }
            : c,
        ),
      };

    default:
      return state;
  }
}

function mapTurn(
  state: ChatState,
  conversationId: string,
  turnId: string,
  fn: (turn: Turn) => Turn,
): ChatState {
  return {
    ...state,
    conversations: state.conversations.map((c) =>
      c.id === conversationId
        ? {
            ...c,
            updatedAt: new Date().toISOString(),
            turns: c.turns.map((t) => (t.id === turnId ? fn(t) : t)),
          }
        : c,
    ),
  };
}

/* ---------------------------------- helpers --------------------------------- */

export const makeTurnId = newTurnId;
export const makeConversationId = newConversationId;

/**
 * Flatten completed prior turns into the history the agent receives.
 * Pending/errored turns are skipped — a half-finished answer is not context.
 */
export function buildHistory(conversation: Conversation | undefined): AgentContextMessage[] {
  if (!conversation) return [];
  const history: AgentContextMessage[] = [];
  for (const turn of conversation.turns) {
    if (turn.status !== 'complete' || !turn.ai) continue;
    history.push({ role: 'human', content: turn.human.content, messageId: turn.human.id });
    history.push({ role: 'ai', content: turn.ai.content, messageId: turn.ai.id });
  }
  return history;
}

export const findConversation = (state: ChatState, id: string | null) =>
  state.conversations.find((c) => c.id === id);
