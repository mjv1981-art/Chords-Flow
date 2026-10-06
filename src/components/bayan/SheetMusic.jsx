import React, { useRef, useEffect, useMemo } from 'react';

// Нотный стан с двумя строками (скрипичный и басовый ключ)
// Рисуем на canvas для производительности

const STAFF_LINE_GAP = 10;
const NOTE_SPACING = 40;
const MARGIN_LEFT = 70;
const MARGIN_TOP = 30;
const TREBLE_TOP = MARGIN_TOP;
const BASS_TOP = MARGIN_TOP + 90;

// Позиция ноты на нотном стане (от C4 = middle C)
function noteToStaffPosition(noteStr, clef = 'treble') {
  const match = noteStr.match(/^([A-G][#b]?)(\d+)$/);
  if (!match) return 0;
  
  const noteName = match[1].replace('#', '').replace('b', '');
  const octave = parseInt(match[2]);
  
  const notePositions = { 'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6 };
  const pos = notePositions[noteName] + (octave - 4) * 7;
  
  if (clef === 'treble') {
    // Middle C (pos=0) находится на первой добавочной линейке снизу = позиция -1
    return -pos;
  } else {
    // В басовом ключе: A2 (pos=-12) на средней линейке
    return -pos - 2;
  }
}

function getAccidental(noteStr) {
  if (noteStr.includes('#')) return '♯';
  if (noteStr.includes('b')) return '♭';
  return '';
}

export default function SheetMusic({
  title = '',
  rightHand = [],
  leftHand = [],
  currentTime = 0,
  beatsPerMeasure = 4,
  totalBeats = 0,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  
  const totalWidth = useMemo(() => {
    const maxTime = Math.max(
      ...rightHand.map(n => (n.time || 0) + (n.duration || 1)),
      ...leftHand.map(n => (n.time || 0) + (n.duration || 1)),
      totalBeats || 16
    );
    return MARGIN_LEFT + maxTime * NOTE_SPACING + 100;
  }, [rightHand, leftHand, totalBeats]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const height = 220;
    // Keep the same scrolling score, but only rasterize a viewport. A full-song
    // canvas can exceed browser width limits (especially on Retina displays).
    const renderWidth = Math.min(totalWidth, Math.max(container.clientWidth * 2, 2048));
    const cursorX = MARGIN_LEFT + currentTime * NOTE_SPACING;
    const renderLeft = Math.max(0, Math.min(totalWidth - renderWidth,
      Math.floor(Math.max(0, cursorX - container.clientWidth / 3) / 1024) * 1024));
    
    canvas.width = renderWidth * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${renderWidth}px`;
    canvas.style.height = `${height}px`;
    canvas.style.left = `${renderLeft}px`;
    ctx.scale(dpr, dpr);
    ctx.translate(-renderLeft, 0);
    
    ctx.clearRect(0, 0, totalWidth, height);
    ctx.fillStyle = '#fefefe';
    ctx.fillRect(0, 0, totalWidth, height);
    
    // Рисуем линейки нотного стана
    ctx.strokeStyle = '#c4c9d4';
    ctx.lineWidth = 1;
    
    // Скрипичный ключ (5 линеек)
    for (let i = 0; i < 5; i++) {
      const y = TREBLE_TOP + i * STAFF_LINE_GAP;
      ctx.beginPath();
      ctx.moveTo(MARGIN_LEFT - 30, y);
      ctx.lineTo(totalWidth - 20, y);
      ctx.stroke();
    }
    
    // Басовый ключ (5 линеек)  
    for (let i = 0; i < 5; i++) {
      const y = BASS_TOP + i * STAFF_LINE_GAP;
      ctx.beginPath();
      ctx.moveTo(MARGIN_LEFT - 30, y);
      ctx.lineTo(totalWidth - 20, y);
      ctx.stroke();
    }
    
    // Ключевые знаки
    ctx.font = '32px serif';
    ctx.fillStyle = '#1e293b';
    ctx.fillText('𝄞', MARGIN_LEFT - 28, TREBLE_TOP + 32);
    ctx.font = '26px serif';
    ctx.fillText('𝄢', MARGIN_LEFT - 25, BASS_TOP + 30);
    
    // Тактовые линии
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1;
    if (beatsPerMeasure > 0) {
      const maxBeat = Math.max(totalBeats || 16, 
        ...rightHand.map(n => (n.time || 0) + (n.duration || 1)),
        ...leftHand.map(n => (n.time || 0) + (n.duration || 1))
      );
      for (let beat = beatsPerMeasure; beat <= maxBeat; beat += beatsPerMeasure) {
        const x = MARGIN_LEFT + beat * NOTE_SPACING;
        ctx.beginPath();
        ctx.moveTo(x, TREBLE_TOP - 5);
        ctx.lineTo(x, TREBLE_TOP + 4 * STAFF_LINE_GAP + 5);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, BASS_TOP - 5);
        ctx.lineTo(x, BASS_TOP + 4 * STAFF_LINE_GAP + 5);
        ctx.stroke();
      }
    }
    
    // Текущая позиция (курсор)
    ctx.fillStyle = 'rgba(59, 130, 246, 0.15)';
    ctx.fillRect(cursorX - 2, TREBLE_TOP - 10, 4 + NOTE_SPACING * 0.5, BASS_TOP + 4 * STAFF_LINE_GAP - TREBLE_TOP + 20);
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(cursorX - 1, TREBLE_TOP - 10, 2, BASS_TOP + 4 * STAFF_LINE_GAP - TREBLE_TOP + 20);
    
    // Рисуем ноты правой руки (скрипичный ключ)
    rightHand.forEach(noteData => {
      if (!noteData.note) return;
      const x = MARGIN_LEFT + (noteData.time || 0) * NOTE_SPACING + NOTE_SPACING / 2;
      if (x < renderLeft - 30 || x > renderLeft + renderWidth + 30) return;
      const staffPos = noteToStaffPosition(noteData.note, 'treble');
      const y = TREBLE_TOP + 2 * STAFF_LINE_GAP + staffPos * (STAFF_LINE_GAP / 2);
      
      const isCurrentNote = currentTime >= (noteData.time || 0) && 
                            currentTime < (noteData.time || 0) + (noteData.duration || 1);
      
      // Добавочные линейки
      ctx.strokeStyle = '#94a3b8';
      ctx.lineWidth = 1;
      if (y > TREBLE_TOP + 4 * STAFF_LINE_GAP) {
        for (let ly = TREBLE_TOP + 5 * STAFF_LINE_GAP; ly <= y + 2; ly += STAFF_LINE_GAP) {
          ctx.beginPath();
          ctx.moveTo(x - 8, ly);
          ctx.lineTo(x + 8, ly);
          ctx.stroke();
        }
      }
      if (y < TREBLE_TOP) {
        for (let ly = TREBLE_TOP - STAFF_LINE_GAP; ly >= y - 2; ly -= STAFF_LINE_GAP) {
          ctx.beginPath();
          ctx.moveTo(x - 8, ly);
          ctx.lineTo(x + 8, ly);
          ctx.stroke();
        }
      }
      
      // Головка ноты
      ctx.fillStyle = isCurrentNote ? '#3b82f6' : '#1e293b';
      ctx.beginPath();
      ctx.ellipse(x, y, 5, 4, -0.2, 0, Math.PI * 2);
      ctx.fill();
      
      // Штиль
      if ((noteData.duration || 1) < 4) {
        ctx.strokeStyle = isCurrentNote ? '#3b82f6' : '#1e293b';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        if (staffPos > 0) {
          ctx.moveTo(x - 5, y);
          ctx.lineTo(x - 5, y + 30);
        } else {
          ctx.moveTo(x + 5, y);
          ctx.lineTo(x + 5, y - 30);
        }
        ctx.stroke();
      }
      
      // Знак альтерации
      const acc = getAccidental(noteData.note);
      if (acc) {
        ctx.font = '12px serif';
        ctx.fillStyle = isCurrentNote ? '#3b82f6' : '#475569';
        ctx.fillText(acc, x - 14, y + 4);
      }
    });
    
    // Рисуем ноты левой руки (басовый ключ)
    leftHand.forEach(noteData => {
      if (!noteData.note) return;
      const x = MARGIN_LEFT + (noteData.time || 0) * NOTE_SPACING + NOTE_SPACING / 2;
      if (x < renderLeft - 30 || x > renderLeft + renderWidth + 30) return;
      
      const isCurrentNote = currentTime >= (noteData.time || 0) && 
                            currentTime < (noteData.time || 0) + (noteData.duration || 1);
      
      // Для левой руки показываем текст аккорда/баса
      const isChord = noteData.note.includes('-');
      
      if (isChord) {
        // Аккорд - показываем как текст над басовым ключом
        ctx.font = isCurrentNote ? 'bold 11px Inter, sans-serif' : '11px Inter, sans-serif';
        ctx.fillStyle = isCurrentNote ? '#3b82f6' : '#64748b';
        ctx.fillText(noteData.note.replace('-chord', '').replace('-bass', ''), x - 8, BASS_TOP - 8);
        
        // Блок-аккорд (закрашенный прямоугольник)
        ctx.fillStyle = isCurrentNote ? 'rgba(59, 130, 246, 0.5)' : 'rgba(30, 41, 59, 0.6)';
        ctx.fillRect(x - 5, BASS_TOP + STAFF_LINE_GAP, 10, 2 * STAFF_LINE_GAP);
      } else {
        // Бас - как обычная нота
        const staffPos = noteToStaffPosition(noteData.note, 'bass');
        const y = BASS_TOP + 2 * STAFF_LINE_GAP + staffPos * (STAFF_LINE_GAP / 2);
        
        ctx.fillStyle = isCurrentNote ? '#3b82f6' : '#1e293b';
        ctx.beginPath();
        ctx.ellipse(x, y, 5, 4, -0.2, 0, Math.PI * 2);
        ctx.fill();
        
        if ((noteData.duration || 1) < 4) {
          ctx.strokeStyle = isCurrentNote ? '#3b82f6' : '#1e293b';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(x - 5, y);
          ctx.lineTo(x - 5, y + 30);
          ctx.stroke();
        }
      }
    });
    
    // Автоскролл
    if (container) {
      const scrollTarget = cursorX - container.clientWidth / 3;
      container.scrollLeft = Math.max(0, scrollTarget);
    }
    
  }, [rightHand, leftHand, currentTime, beatsPerMeasure, totalBeats, totalWidth]);

  return (
    <div className="flex flex-col w-full">
      {title && (
        <div className="text-center mb-2">
          <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        </div>
      )}
      <div 
        ref={containerRef}
        className="overflow-x-auto overflow-y-hidden border border-slate-200 rounded-xl bg-white"
        style={{ scrollBehavior: 'smooth' }}
      >
        <div style={{ width: totalWidth, height: 220, position: 'relative' }}>
          <canvas ref={canvasRef} style={{ position: 'absolute', top: 0 }} />
        </div>
      </div>
    </div>
  );
}
