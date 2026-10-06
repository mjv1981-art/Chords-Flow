const waves = new WeakMap();
export default function ReedVoice(ctx, output, frequency, duration, volume, when, voices) {
  if (!waves.has(ctx)) {
    const real = new Float32Array(25), imag = new Float32Array(25);
    [1,.68,.43,.3,.21,.16,.12,.09,.065,.05,.035,.025].forEach((v,i) => { imag[i+1] = v; });
    waves.set(ctx, ctx.createPeriodicWave(real,imag));
  }
  const envelope = ctx.createGain(), filter = ctx.createBiquadFilter();
  filter.type = 'lowpass'; filter.Q.value = .45;
  filter.frequency.setValueAtTime(Math.min(8500,frequency*12+1300),when);
  envelope.connect(filter); filter.connect(output);
  const attack = Math.min(.026,duration*.2), release = Math.min(.065,duration*.22);
  envelope.gain.setValueAtTime(0,when);
  envelope.gain.linearRampToValueAtTime(volume,when+attack);
  envelope.gain.linearRampToValueAtTime(volume*.91,when+duration*.6);
  envelope.gain.setValueAtTime(volume*.88,when+duration-release);
  envelope.gain.linearRampToValueAtTime(0,when+duration);
  // Dry reed registration: fundamental plus quieter octave reed, no musette beating.
  const oscillators = [1,.5].map((ratio,i) => {
    const osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.setPeriodicWave(waves.get(ctx)); osc.frequency.value = frequency*ratio;
    gain.gain.value = i === 0 ? .82 : .18;
    osc.connect(gain); gain.connect(envelope);
    osc.start(when); osc.stop(when+duration+.01);
    osc.onended = () => { osc.disconnect(); gain.disconnect(); };
    return osc;
  });
  const voice = {stop:() => {
    envelope.gain.cancelScheduledValues(ctx.currentTime);
    envelope.gain.setTargetAtTime(0,ctx.currentTime,.006);
    oscillators.forEach(osc => osc.stop(ctx.currentTime+.025));
  }};
  voices.add(voice);
  oscillators[0].onended = () => {
    oscillators[0].disconnect();
    envelope.disconnect(); filter.disconnect(); voices.delete(voice);
  };
}