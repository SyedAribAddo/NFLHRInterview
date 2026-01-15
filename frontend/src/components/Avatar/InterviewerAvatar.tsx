import React, { useEffect, useState, useRef } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { VRMLoaderPlugin, VRMUtils, VRM } from '@pixiv/three-vrm';
import * as THREE from 'three';
import { useAudioLipSync } from './useAudioLipSync';

function AvatarModel({ audioRef }: { audioRef: React.RefObject<HTMLAudioElement> }) {
    const [vrm, setVrm] = useState<VRM | null>(null);
    const volumeRef = useAudioLipSync({ audioRef });

    // Load VRM
    const gltf = useLoader(GLTFLoader, '/avatars/interviewer_male.vrm', (loader) => {
        loader.register((parser) => {
            return new VRMLoaderPlugin(parser);
        });
    });

    useEffect(() => {
        if (!gltf) return;
        const vrm = gltf.userData.vrm;
        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        VRMUtils.combineSkeletons(gltf.scene);

        // Rotate to face camera if needed
        vrm.scene.rotation.y = Math.PI; // 180 deg

        setVrm(vrm);
        console.log("Avatar Loaded");
    }, [gltf]);

    // Animation Loop
    useFrame((state, delta) => {
        if (!vrm) return;

        // Update VRM Physics/Expressions
        vrm.update(delta);

        // Lip Sync
        if (vrm.expressionManager) {
            const vol = volumeRef.current; // 0..1
            // Map to 'aa' or 'ih'
            vrm.expressionManager.setValue('aa', vol * 1.5); // Boost slightly
            vrm.expressionManager.setValue('ih', vol * 0.5);
            vrm.expressionManager.update();
        }

        // Idle Animation (Blink)
        // Simple blink logic using Math.sin or random
        const time = state.clock.elapsedTime;
        if (vrm.expressionManager) {
            const blink = Math.sin(time * 0.5) > 0.99 ? 1 : 0; // Occasional blink
            vrm.expressionManager.setValue('blink', blink);
        }

        // Idle Breathing
        const breath = Math.sin(time) * 0.05;
        vrm.scene.position.y = -1.5 + breath; // Base position ajustment
    });

    return vrm ? <primitive object={vrm.scene} position={[0, -1.5, 0]} /> : null;
}

// Ensure Default Export
export default function InterviewerAvatar({ audioRef }: { audioRef: React.RefObject<HTMLAudioElement> }) {
    const [hasError, setHasError] = useState(false);

    if (hasError) {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center bg-gray-800 text-gray-500 text-xs p-4 text-center">
                <p className="font-bold mb-2 text-red-400">Avatar Not Found</p>
                <p className="mb-2">Please drop a VRM file into:</p>
                <code className="bg-black/30 p-2 rounded block break-all font-mono text-[10px] text-gray-400">
                    /frontend/public/avatars/interviewer_male.vrm
                </code>
                <p className="mt-4 text-[10px] opacity-70">
                    (Automatic download failed due to network restrictions)
                </p>
            </div>
        );
    }

    return (
        <div className="w-full h-full min-h-[300px] bg-gradient-to-b from-gray-800 to-gray-900 overflow-hidden relative border-r border-gray-700">
            <div className="absolute top-2 left-2 z-10 text-white/50 text-xs font-mono tracking-widest uppercase">
                AI Interviewer
                <span className="ml-2 inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            </div>

            <Canvas camera={{ fov: 25, position: [0, 0.2, 2] }} shadows>
                <ambientLight intensity={0.6} />
                <spotLight position={[2, 2, 2]} intensity={1.5} angle={0.5} penumbra={1} castShadow />
                <pointLight position={[-2, 1, 1]} intensity={0.5} color="#blue" />

                <ErrorBoundary onError={() => setHasError(true)}>
                    <React.Suspense fallback={null}>
                        <AvatarModel audioRef={audioRef} />
                    </React.Suspense>
                </ErrorBoundary>
            </Canvas>
        </div>
    );
}

// Simple Error Boundary wrapper
class ErrorBoundary extends React.Component<{ onError: () => void, children: React.ReactNode }, { hasError: boolean }> {
    constructor(props: any) {
        super(props);
        this.state = { hasError: false };
    }
    static getDerivedStateFromError(error: any) {
        return { hasError: true };
    }
    componentDidCatch(error: any) {
        console.error("Avatar Error:", error);
        this.props.onError();
    }
    render() {
        if (this.state.hasError) return null;
        return this.props.children;
    }
}
