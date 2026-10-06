import React from 'react';
import { Play, Pause, SkipBack, SkipForward, Minus, Plus } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

export default function PlaybackControls({ 
  isPlaying, 
  onPlayPause, 
  onStop, 
  tempo, 
  onTempoChange,
  currentBeat,
  totalBeats,
  onSeek
}) {
  const formatTime = (beats) => {
    if (!beats || !tempo) return '0:00';
    const seconds = (beats / tempo) * 60;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center gap-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-2xl px-5 py-3 shadow-sm">
      {/* Transport */}
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500" aria-label="Стоп" onClick={onStop}>
          <SkipBack className="h-4 w-4" />
        </Button>
        <Button 
          variant="default" 
          size="icon" 
          className="h-10 w-10 rounded-full bg-slate-800 hover:bg-slate-700 text-white shadow-md"
          aria-label={isPlaying ? "Пауза" : "Воспроизвести"}
          onClick={onPlayPause}
        >
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500" 
          aria-label="Вперёд на четыре доли" onClick={() => onSeek(Math.min(currentBeat + 4, totalBeats))}>
          <SkipForward className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Progress */}
      <div className="flex-1 flex items-center gap-3 min-w-0">
        <span className="text-xs text-slate-400 w-10 text-right font-mono">{formatTime(currentBeat)}</span>
        <Slider
          value={[currentBeat]}
          max={totalBeats || 100}
          step={0.25}
          onValueChange={(v) => onSeek(v[0])}
          className="flex-1"
        />
        <span className="text-xs text-slate-400 w-10 font-mono">{formatTime(totalBeats)}</span>
      </div>
      
      {/* Tempo */}
      <div className="flex items-center gap-2 pl-3 border-l border-slate-200">
        <Button variant="ghost" size="icon" className="h-7 w-7" 
          onClick={() => onTempoChange(Math.max(40, tempo - 10))}>
          <Minus className="h-3 w-3" />
        </Button>
        <div className="text-center min-w-[60px]">
          <div className="text-sm font-semibold text-slate-700">{tempo}</div>
          <div className="text-[9px] text-slate-400 -mt-0.5">BPM</div>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7"
          onClick={() => onTempoChange(Math.min(300, tempo + 10))}>
          <Plus className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}