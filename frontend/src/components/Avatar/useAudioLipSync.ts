import { useRef, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';

export function useAudioLipSync({ audioRef }: { audioRef: React.RefObject<HTMLAudioElement> }) {
    const analyserRef = useRef<AnalyserNode | null>(null);
    const dataArrayRef = useRef<Uint8Array | null>(null);
    const volumeRef = useRef(0);

    useEffect(() => {
        if (!audioRef.current) return;

        const audio = audioRef.current;
        let audioContext: AudioContext;
        let source: MediaElementAudioSourceNode;

        const initAudio = () => {
            if (analyserRef.current) return; // Already init

            audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            analyserRef.current = audioContext.createAnalyser();
            analyserRef.current.fftSize = 256;

            // Connect audio element source
            try {
                source = audioContext.createMediaElementSource(audio);
                source.connect(analyserRef.current);
                analyserRef.current.connect(audioContext.destination);

                const bufferLength = analyserRef.current.frequencyBinCount;
                dataArrayRef.current = new Uint8Array(bufferLength);
            } catch (e) {
                console.error("Audio Context Error:", e);
            }
        };

        // Initialize on play to avoid autoplay policy issues? 
        // Or just init immediately if user already interacted (which they did in landing page).
        // Safest is to try init immediately, but handle errors.
        // Actually, for MediaElementSource, we need to be careful not to hijack the destination?
        // We connected source -> analyser -> destination, so audio should still play.

        // Listen for play event to ensure context is resumed
        const handlePlay = () => {
            if (!analyserRef.current) initAudio();
            if (audioContext && audioContext.state === 'suspended') audioContext.resume();
        };

        audio.addEventListener('play', handlePlay);

        return () => {
            audio.removeEventListener('play', handlePlay);
            // Don't close context if shared? But here it's local.
            // if (audioContext) audioContext.close(); 
        };
    }, [audioRef]);

    useFrame(() => {
        if (analyserRef.current && dataArrayRef.current) {
            // @ts-ignore
            analyserRef.current.getByteFrequencyData(dataArrayRef.current);
            const sum = dataArrayRef.current.reduce((a, b) => a + b, 0);
            const avg = sum / dataArrayRef.current.length;
            // Normalize 0-255 to 0-1
            // Apply smoothing
            const target = Math.min(1, avg / 50); // Sensitivity
            volumeRef.current += (target - volumeRef.current) * 0.2; // Lerp
        } else {
            volumeRef.current = 0;
        }
    });

    return volumeRef;
}
