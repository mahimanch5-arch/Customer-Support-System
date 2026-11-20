import { useMemo } from 'react';
import type { Conversation } from '../types';
import { dateBucket } from '../lib/format';
import { PlusIcon, TrashIcon } from './Icons';

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
}

export function Sidebar({
  conversations,
  activeId,
  open,
  onNew,
  onSelect,
  onDelete,
  onRename,
}: Props) {
  // Group by recency; conversations arrive already sorted newest-first.
  const groups = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    for (const c of conversations) {
      const key = dateBucket(c.updatedAt);
      const list = map.get(key);
      if (list) list.push(c);
      else map.set(key, [c]);
    }
    return [...map.entries()];
  }, [conversations]);

  return (
    <aside className={`sidebar${open ? '' : ' sidebar--collapsed'}`} aria-label="Conversation history">
      <div className="sidebar__head">
        <button className="btn-new" onClick={onNew} type="button">
          <PlusIcon />
          New conversation
        </button>
      </div>

      <nav className="sidebar__list">
        {groups.length === 0 && <p className="sidebar__empty">No conversations yet.</p>}

        {groups.map(([label, items]) => (
          <section key={label} className="sidebar__group">
            <h2 className="sidebar__group-label">{label}</h2>
            <ul>
              {items.map((c) => (
                <li key={c.id}>
                  <div className={`conv${c.id === activeId ? ' conv--active' : ''}`}>
                    <button
                      className="conv__main"
                      type="button"
                      onClick={() => onSelect(c.id)}
                      onDoubleClick={() => {
                        const next = window.prompt('Rename conversation', c.title);
                        if (next !== null) onRename(c.id, next);
                      }}
                      title={`${c.title}\n${c.id} · ${c.turns.length} turn${c.turns.length === 1 ? '' : 's'}`}
                      aria-current={c.id === activeId ? 'page' : undefined}
                    >
                      <span className="conv__title">{c.title}</span>
                    </button>
                    <button
                      className="conv__delete"
                      type="button"
                      aria-label={`Delete conversation: ${c.title}`}
                      onClick={() => {
                        if (window.confirm(`Delete "${c.title}"?`)) onDelete(c.id);
                      }}
                    >
                      <TrashIcon />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </nav>

      <footer className="sidebar__foot">
        <span className="badge">Phase 1 · mock data</span>
      </footer>
    </aside>
  );
}
