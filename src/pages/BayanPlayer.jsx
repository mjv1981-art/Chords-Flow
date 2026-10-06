import React, { useState, useEffect } from 'react';
import { Music, Save, FolderOpen, ChevronLeft } from 'lucide-react';
import { Button } from "@/components/ui/button";
import RightKeyboard from '../components/bayan/RightKeyboard';
import LeftKeyboard from '../components/bayan/LeftKeyboard';
import SheetMusic from '../components/bayan/SheetMusic';
import PlaybackControls from '../components/bayan/PlaybackControls';
import SongInput from '../components/bayan/SongInput';
import { getAudioContext, stopAll } from '@/components/bayan/AudioEngine';
import useBayanPlayback from '@/components/bayan/useBayanPlayback';
import KaraokeLyrics from '@/components/bayan/KaraokeLyrics';
import { transposeToAm } from "@/components/bayan/transposeSong";
import { Switch } from "@/components/ui/switch";

export default function BayanPlayer() {
  const [view, setView] = useState('input'); // 'input' | 'player'
  const [isLoading, setIsLoading] = useState(false);
  const [originalSong, setOriginalSong] = useState(null);
  const [inAm, setInAm] = useState(false);
  const [saveNotice, setSaveNotice] = useState('');
  const song = React.useMemo(() => originalSong && inAm ? transposeToAm(originalSong) : originalSong, [originalSong, inAm]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentBeat, setCurrentBeat] = useState(0);
  const [tempo, setTempo] = useState(120);
  const [activeRightNotes, setActiveRightNotes] = useState([]);
  const [activeLeftButtons, setActiveLeftButtons] = useState([]);
  
  const [seekVersion, setSeekVersion] = useState(0);
  
  // Октавный диапазон из текущей песни
  const octaveRange = React.useMemo(() => {
    if (!song?.right_hand?.length) return [3, 6];
    let min = 8, max = 0;
    song.right_hand.forEach(n => {
      const match = n.note?.match(/(\d+)$/);
      if (match) {
        const oct = parseInt(match[1]);
        min = Math.min(min, oct);
        max = Math.max(max, oct);
      }
    });
    return [Math.max(1, min - 1), Math.min(7, max + 1)];
  }, [song]);
  
  // Общее количество долей
  const totalBeats = React.useMemo(() => {
    if (!song) return 0;
    const rMax = Math.max(0, ...((song.right_hand || []).map(n => (n.time || 0) + (n.duration || 1))));
    const lMax = Math.max(0, ...((song.left_hand || []).map(n => (n.time || 0) + (n.duration || 1))));
    return Math.max(rMax, lMax);
  }, [song]);
  
  const beatsPerMeasure = React.useMemo(() => {
    if (!song?.time_signature) return 4;
    const parts = song.time_signature.split('/');
    return (Number(parts[0]) || 4) * 4 / (Number(parts[1]) || 4);
  }, [song]);

  useBayanPlayback(song,isPlaying,tempo,currentBeat,seekVersion,totalBeats,setCurrentBeat,setIsPlaying);
  useEffect(() => {
    const active = notes => (notes || []).filter(n=>currentBeat>=n.time && currentBeat<n.time+n.duration).map(n=>n.note);
    setActiveRightNotes(isPlaying ? active(song?.right_hand) : []);
    setActiveLeftButtons(isPlaying ? active(song?.left_hand) : []);
  },[song,currentBeat,isPlaying]);

  const handleSongReady = (songData) => {
    stopAll();
    setOriginalSong(songData);
    setInAm(false);
    setSaveNotice('');
    setTempo(songData.tempo || 120);
    setCurrentBeat(0);
    setIsPlaying(Boolean(songData.autoPlay));
    setView('player');
  };
  const handlePlayPause = () => {
    if (!isPlaying) {
      getAudioContext();
      if (currentBeat>=totalBeats) setCurrentBeat(0);
    } else stopAll();
    setIsPlaying(!isPlaying);
  };
  const handleStop = () => {
    setIsPlaying(false); setCurrentBeat(0);
    setActiveRightNotes([]); setActiveLeftButtons([]); stopAll();
  };
  const handleSeek = beat => {
    stopAll(); setCurrentBeat(beat); setSeekVersion(v=>v+1);
  };

  const handleSave = () => {
    if (!originalSong) return;
    try {
      const saved = JSON.parse(localStorage.getItem('bayanflow-songs') || '[]');
      const id = originalSong.source_url || originalSong.title;
      localStorage.setItem('bayanflow-songs', JSON.stringify([
        {...originalSong, tempo, id}, ...saved.filter(s => s.id !== id)
      ].slice(0, 10)));
      setSaveNotice('Сохранено в этом браузере');
    } catch { setSaveNotice('Не удалось сохранить: хранилище браузера недоступно'); }
  };

  // Страница ввода
  if (view === 'input') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20">
        <div className="max-w-4xl mx-auto px-4 py-12">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-600 shadow-xl mb-6">
              <Music className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-slate-900 tracking-tight">Баян Плеер</h1>
            <p className="text-slate-500 mt-3 text-lg max-w-md mx-auto">
              Мелодия и аккорды из YouTube · русский баян, B-гриф
            </p>
          </div>
          
          {/* Input */}
          <SongInput 
            onSongReady={handleSongReady} 
            isLoading={isLoading} 
            setIsLoading={setIsLoading} 
          />
          
          {/* Saved songs */}
          <SavedSongs onSelect={handleSongReady} />
        </div>
      </div>
    );
  }

  // Страница плеера
  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => { handleStop(); setView('input'); }}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-base font-semibold text-slate-800">{song?.title || 'Без названия'}</h1>
            {song?.composer && <p className="text-xs text-slate-400">{song.composer}</p>}
            <p className="text-xs text-slate-500">{song?.key} · B-гриф{song?.mode_adapted ? ' · Мажорная мелодия адаптирована в минор' : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <Switch aria-label="Транспонировать в ля минор" checked={inAm} onCheckedChange={value => { handleStop(); setInAm(value); }} />
            Am
          </label>
          {saveNotice && <span role="status" className="text-xs text-slate-500">{saveNotice}</span>}
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleSave}>
            <Save className="h-3.5 w-3.5" /> Сохранить
          </Button>
        </div>
      </div>
      
      {/* Main content: Left keyboard | Sheet music | Right keyboard */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Левая клавиатура */}
        <div className="w-[220px] shrink-0 border-r border-slate-200 bg-gradient-to-b from-slate-100 to-slate-50 overflow-y-auto p-3 flex items-start justify-center">
          <LeftKeyboard activeButtons={activeLeftButtons} />
        </div>
        
        {/* Центр - нотный стан */}
        <div className="flex-1 flex flex-col min-w-0 px-4 py-3 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-hidden">
            <SheetMusic
              title=""
              rightHand={song?.right_hand || []}
              leftHand={song?.left_hand || []}
              currentTime={currentBeat}
              beatsPerMeasure={beatsPerMeasure}
              totalBeats={totalBeats}
            />
          </div>
          
          <KaraokeLyrics song={song} beat={currentBeat} onSeek={handleSeek} />
          {/* Playback controls */}
          <div className="mt-3 shrink-0">
            <PlaybackControls
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
              onStop={handleStop}
              tempo={tempo}
              onTempoChange={setTempo}
              currentBeat={currentBeat}
              totalBeats={totalBeats}
              onSeek={handleSeek}
            />
          </div>
        </div>
        
        {/* Правая клавиатура */}
        <div className="w-[160px] shrink-0 border-l border-slate-200 bg-gradient-to-b from-slate-100 to-slate-50 overflow-y-auto p-3 flex items-start justify-center">
          <RightKeyboard activeNotes={activeRightNotes} octaveRange={octaveRange} />
        </div>
      </div>
    </div>
  );
}

// Компонент списка сохранённых песен
function SavedSongs({ onSelect }) {
  const [songs, setSongs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    try { setSongs(JSON.parse(localStorage.getItem('bayanflow-songs') || '[]')); }
    catch { setSongs([]); }
    setLoading(false);
  }, []);

  if (loading || songs.length === 0) return null;

  return (
    <div className="mt-12">
      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
        <FolderOpen className="h-4 w-4" /> Сохранённые песни
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {songs.map(s => (
          <button
            key={s.id}
            onClick={() => onSelect(s)}
            className="text-left p-4 bg-white rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-slate-200 transition-colors">
                <Music className="h-5 w-5 text-slate-500" />
              </div>
              <div className="min-w-0">
                <p className="font-medium text-slate-800 truncate">{s.title}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {s.composer && `${s.composer} · `}{s.tempo} BPM
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}