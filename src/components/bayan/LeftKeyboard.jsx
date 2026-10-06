import React, { useMemo } from 'react';
import { STRADELLA_ORDER, NOTE_COLORS, normalizeNoteName } from './constants';

// Левая клавиатура баяна - система Stradella
// 6 рядов × 12 кнопок (кварто-квинтовый круг)
// Ряды: Вспом.бас | Бас | Мажор | Минор | Септ | Умен.

const ROW_LABELS = ['', '', 'М', 'm', '7', 'у'];
const ROW_TYPES = ['counter-bass', 'bass', 'major', 'minor', 'seventh', 'dim'];

export default function LeftKeyboard({ activeButtons = [], visibleBasses = null }) {
  // visibleBasses - массив басов для отображения (фильтр октав)
  // Если null - показываем все
  const basses = visibleBasses || STRADELLA_ORDER;

  // Парсим activeButtons которые приходят в формате "Am-chord", "C-bass", "G7-chord", "Ddim-chord"
  // и матчим на кнопки клавиатуры по root ноте и типу ряда
  const activeSet = useMemo(() => {
    // Returns set of "rowType:bassName" keys
    const set = new Set();
    activeButtons.forEach(raw => {
      if (typeof raw !== 'string') return;

      // Парсим формат: "C-bass", "Am-chord", "G7-chord", "Bbdim-chord", "F#m-chord"
      let root = null;
      let type = null;

      // bass
      const bassMatch = raw.match(/^([A-G][#b]?)-bass$/i);
      if (bassMatch) { root = bassMatch[1]; type = 'bass'; }

      // counter-bass (вспомогательный бас)
      const cbMatch = raw.match(/^([A-G][#b]?)-counter-?bass$/i);
      if (cbMatch) { root = cbMatch[1]; type = 'counter-bass'; }

      // chord variants: Am-chord, C-chord, G7-chord, Adim-chord, A°-chord
      if (!root) {
        const chordMatch = raw.match(/^([A-G][#b]?)(m|maj|7|dim|°|M)?-chord$/i);
        if (chordMatch) {
          root = chordMatch[1];
          const suffix = (chordMatch[2] || '').toLowerCase();
          if (suffix === 'm') type = 'minor';
          else if (suffix === '7') type = 'seventh';
          else if (suffix === 'dim' || suffix === '°') type = 'dim';
          else type = 'major'; // '' or 'maj'
        }
      }

      // Also handle "G7-chord" where root=G type=seventh
      if (!root) {
        const seventhMatch = raw.match(/^([A-G][#b]?)7-chord$/i);
        if (seventhMatch) { root = seventhMatch[1]; type = 'seventh'; }
      }

      if (root && type) {
        // Normalize flats to what STRADELLA_ORDER uses (Eb, Bb, etc.)
        set.add(`${type}:${normalizeNoteName(root)}`);
      }
    });
    return set;
  }, [activeButtons]);

  return (
    <div className="flex flex-row gap-[3px] items-start h-full">
      {/* 6 рядов, от внешнего (умен.) к внутреннему (вспом. бас) */}
      {ROW_TYPES.slice().reverse().map((type, dispIdx) => {
        const rowIdx = 5 - dispIdx;
        return (
          <div key={type} className="flex flex-col gap-[3px]" style={{ marginTop: dispIdx % 2 === 1 ? 14 : 0 }}>
            {basses.map((bass, colIdx) => {
              const normalBass = normalizeNoteName(bass);
              const label = rowIdx <= 1 ? bass : `${bass}${ROW_LABELS[rowIdx]}`;
              const buttonId = `${type}:${bass}`;
              // Also check normalized variants (Bb == Bb, Eb == Eb, etc.)
              const normalizedBass = normalizeNoteName(bass);
              const isActive = activeSet.has(buttonId) || activeSet.has(`${type}:${normalizedBass}`);
              const color = NOTE_COLORS[normalBass] || '#64748b';
              
              // Визуальное разделение типов
              const isBassRow = rowIdx <= 1;
              
              return (
                <button
                  key={buttonId}
                  className={`
                    w-9 h-9 rounded-full flex items-center justify-center text-[9px] font-medium
                    transition-all duration-100 border-2 shrink-0
                    ${isActive 
                      ? 'scale-110 shadow-lg z-10' 
                      : 'hover:scale-105'
                    }
                  `}
                  style={{
                    backgroundColor: isActive ? color : (isBassRow ? '#f1f5f9' : '#ffffff'),
                    borderColor: isActive ? color : (isBassRow ? '#94a3b8' : '#d1d5db'),
                    color: isActive ? '#fff' : '#475569',
                    boxShadow: isActive ? `0 0 12px ${color}60` : 'none',
                  }}
                  title={label}
                >
                  <span className="leading-none truncate px-0.5">{label}</span>
                </button>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
