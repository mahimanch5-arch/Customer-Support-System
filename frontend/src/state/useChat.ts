import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { askAgent } from '../mock/agentClient';
import { seedConversations } from '../mock/seed';
import type { AgentRequest, Conversation } from '../types';
import {
  buildHistory,
  findConversation,
  initialState,
  makeConversationId,
  makeTurnId,
  reducer,
} from './reducer';
import { loadConversations, saveConversations } from './storage';

export interface UseChat {
  conversations: Conversation[];
  activeConversation: Conversation | undefined;
  activeId: string | null;
  /** A turn is streaming right now. */
  isStreaming: boolean;
  send: (question: string) => void;
  stop: () => void;
  retry: (turnId: string) => void;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
}

export function useChat(): UseChat {
  const [state, dispatch] = useReducer(
    reducer,
    undefined,
    () => initialState(loadConversations() ?? seedConversations()),
  );
  const [isStreaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    saveConversations(state.conversations);
  }, [state.conversations]);

  // Abandon any in-flight stream when the app unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback(async (req: AgentRequest, turnId: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);

    try {
      for await (const chunk of askAgent(req, controller.signal)) {
        if (chunk.delta) {
          dispatch({
            type: 'appendDelta',
            conversationId: req.conversationId,
            turnId,
            delta: chunk.delta,
          });
        }
        if (chunk.meta) {
          dispatch({
            type: 'completeTurn',
            conversationId: req.conversationId,
            turnId,
            meta: chunk.meta,
          });
        }
      }
      dispatch({ type: 'completeTurn', conversationId: req.conversationId, turnId });
    } catch (err) {
      const aborted = err instanceof Error && err.name === 'AbortError';
      dispatch({
        type: 'failTurn',
        conversationId: req.conversationId,
        turnId,
        error: aborted ? 'Stopped.' : 'Something went wrong reaching the assistant.',
      });
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setStreaming(false);
      }
    }
  }, []);

  const send = useCallback(
    (raw: string) => {
      const question = raw.trim();
      if (!question || isStreaming) return;

      const conversationId = state.activeId ?? makeConversationId();
      const turnId = makeTurnId();
      const existing = findConversation(state, state.activeId);

      dispatch({
        type: 'askQuestion',
        conversationId: state.activeId,
        conversationIdOverride: conversationId,
        question,
        turnId,
      });

      // Prior turns go to the agent as context; the new question goes separately.
      void run(
        {
          conversationId,
          question,
          messageId: turnId,
          history: buildHistory(existing),
        },
        turnId,
      );
    },
    [isStreaming, run, state],
  );

  const retry = useCallback(
    (turnId: string) => {
      const conversation = findConversation(state, state.activeId);
      if (!conversation || isStreaming) return;
      const turn = conversation.turns.find((t) => t.id === turnId);
      if (!turn) return;

      const priorTurns = conversation.turns.slice(0, conversation.turns.indexOf(turn));
      dispatch({ type: 'dropTurn', conversationId: conversation.id, turnId });
      dispatch({
        type: 'askQuestion',
        conversationId: conversation.id,
        conversationIdOverride: conversation.id,
        question: turn.human.content,
        turnId,
      });

      void run(
        {
          conversationId: conversation.id,
          question: turn.human.content,
          messageId: turnId,
          history: buildHistory({ ...conversation, turns: priorTurns }),
        },
        turnId,
      );
    },
    [isStreaming, run, state],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const sorted = useMemo(
    () =>
      [...state.conversations].sort(
        (a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt),
      ),
    [state.conversations],
  );

  return {
    conversations: sorted,
    activeConversation: findConversation(state, state.activeId),
    activeId: state.activeId,
    isStreaming,
    send,
    stop,
    retry,
    newConversation: useCallback(() => {
      abortRef.current?.abort();
      dispatch({ type: 'newConversation' });
    }, []),
    selectConversation: useCallback((id: string) => {
      abortRef.current?.abort();
      dispatch({ type: 'selectConversation', id });
    }, []),
    deleteConversation: useCallback((id: string) => dispatch({ type: 'deleteConversation', id }), []),
    renameConversation: useCallback(
      (id: string, title: string) => dispatch({ type: 'renameConversation', id, title }),
      [],
    ),
  };
}
