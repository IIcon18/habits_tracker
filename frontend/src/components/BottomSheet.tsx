import { useEffect, useId, type ReactNode } from 'react';
import './BottomSheet.css';

interface BottomSheetProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/** Нижний лист: затемнение закрывает, Esc тоже. MainButton на время листа экран скрывает сам. */
export function BottomSheet({ title, onClose, children }: BottomSheetProps) {
  const titleId = useId();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="sheet-layer">
      <div className="sheet-layer__scrim" onClick={onClose} aria-hidden="true" />
      <section className="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <i className="sheet__grab" aria-hidden="true" />
        <h2 id={titleId} className="sheet__title">
          {title}
        </h2>
        {children}
      </section>
    </div>
  );
}
