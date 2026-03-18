import React, { useEffect, useState } from 'react';

const IntroAnimation = ({ onComplete }) => {
    const [showFullLogo, setShowFullLogo] = useState(false);

    useEffect(() => {
        // Sequence:
        // 0s: Start writing "GGS"
        // 2s: Writing done, fill color
        // 3s: Move to header position / reveal full text "Information Services"
        // 4s: Signal completion to parent to show main UI (but keep header)

        const timer1 = setTimeout(() => {
            setShowFullLogo(true);
        }, 1200);

        const timer2 = setTimeout(() => {
            onComplete();
        }, 1800);

        return () => {
            clearTimeout(timer1);
            clearTimeout(timer2);
        };
    }, [onComplete]);

    return (
        <div className={`fixed inset-0 z-50 flex items-center justify-center bg-white transition-all duration-1000 ${showFullLogo ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
            <div className="relative">
                <svg
                    viewBox="0 0 300 100"
                    className="w-64 h-auto md:w-96"
                >
                    {/* GGS Text Path Approximation or Text Element */}
                    <text
                        x="50%"
                        y="50%"
                        dominantBaseline="middle"
                        textAnchor="middle"
                        className="text-6xl font-bold stroke-black fill-transparent animate-stroke-write"
                        style={{
                            fontFamily: 'Inter, sans-serif',
                            strokeWidth: '2px',
                            strokeDasharray: '400',
                            strokeDashoffset: '400',
                            animation: 'write 2s ease-out forwards, fill 0.5s ease-out 2s forwards'
                        }}
                    >
                        GGS
                    </text>
                </svg>

                {/* Full Text that fades in - This might overlap or rely on the main header taking over */}
            </div>

            <style>{`
        @keyframes write {
          to {
            stroke-dashoffset: 0;
          }
        }
        @keyframes fill {
          to {
            fill: #1a1a1a;
            stroke: transparent;
          }
        }
      `}</style>
        </div>
    );
};

export default IntroAnimation;
