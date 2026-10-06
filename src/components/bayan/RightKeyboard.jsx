import React, { useMemo } from 'react';
import { NOTE_NAMES, NOTE_COLORS, normalizeNoteName } from './constants';
import { B_SYSTEM_ROWS_FROM_BELLOWS } from './bSystem';

// Правая клавиатура русского баяна тип B
// 3 основных ряда (+ 2 вспомогательных), хроматическая раскладка
// Кнопки расположены в шахматном порядке

export default function RightKeyboard({ activeNotes = [], octaveRange = [3, 6] }) {
  const [startOct, endOct] = octaveRange;
  
  const keyboard = useMemo(() => {
    // Тип B раскладка: 3 основных ряда
    // Каждый ряд содержит ноты через 3 полутона
    // Вид спереди, слева мех: внутренний ряд (3): C, D#, F#, A
    // Ряд 2 (средний): C#, E, G, A#  
    // Внешний ряд (1): D, F, G#, B
    
    const rowPatterns = B_SYSTEM_ROWS_FROM_BELLOWS;
    
    const rows = [];
    for (let r = 0; r < 3; r++) {
      const row = [];
      for (let oct = startOct; oct <= endOct; oct++) {
        for (const noteIdx of rowPatterns[r]) {
          const noteName = NOTE_NAMES[noteIdx];
          row.push({
            note: `${noteName}${oct}`,
            noteName,
            octave: oct,
            midi: (oct + 1) * 12 + noteIdx,
          });
        }
      }
      rows.push(row);
    }
    return rows;
  }, [startOct, endOct]);

  const activeSet = useMemo(() => {
    const set = new Set();
    activeNotes.forEach(n => {
      if (typeof n === 'string') set.add(n);
    });
    return set;
  }, [activeNotes]);

  return (
    <div className="flex flex-row gap-[3px] items-start h-full">
      {/* Слева направо: от меха к внешнему краю, B-гриф */}
      {keyboard.map((row, rowIdx) => (
        <div key={rowIdx} className="flex flex-col gap-[3px]" style={{ marginTop: rowIdx * 14 }}>
          {row.map((btn) => {
            const isActive = activeSet.has(btn.note);
            const baseNote = normalizeNoteName(btn.noteName);
            const color = NOTE_COLORS[baseNote] || '#64748b';
            const isBlack = btn.noteName.includes('#');
            
            return (
              <button
                key={btn.note}
                className={`
                  w-9 h-9 rounded-full flex items-center justify-center text-[10px] font-medium
                  transition-all duration-100 border-2 shrink-0
                  ${isActive 
                    ? 'scale-110 shadow-lg shadow-blue-500/40 z-10' 
                    : 'hover:scale-105'
                  }
                `}
                style={{
                  backgroundColor: isActive ? color : (isBlack ? '#1e293b' : '#f8fafc'),
                  borderColor: isActive ? color : (isBlack ? '#334155' : '#cbd5e8'),
                  color: isActive ? '#fff' : (isBlack ? '#94a3b8' : '#475569'),
                  boxShadow: isActive ? `0 0 12px ${color}60` : 'none',
                }}
                title={btn.note}
              >
                <span className="leading-none">
                  {btn.noteName}
                  <sub className="text-[7px] opacity-60">{btn.octave}</sub>
                </span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
