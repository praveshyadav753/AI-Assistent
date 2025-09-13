// AnimatedWave.jsx
import React from 'react';

const AnimatedWave = () => {
  return (
    <div className="wave-container">
      <svg
        className="waves"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 24 150 28"
        preserveAspectRatio="none"
        shapeRendering="auto"
      >
        <defs>
          <path
            id="gentle-wave"
            d="M-160 44c30 0 58-18 88-18s 58 18 88 18 58-18 88-18 58 18 88 18 v44h-352z"
          />
          {/* NEW: Gradient Definitions */}
          <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'rgba(77, 192, 242, 0.8)' }} />
            <stop offset="100%" style={{ stopColor: 'rgba(77, 192, 242, 0)' }} />
          </linearGradient>
          <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'rgba(88, 122, 245, 0.7)' }} />
            <stop offset="100%" style={{ stopColor: 'rgba(88, 122, 245, 0)' }} />
          </linearGradient>
           <linearGradient id="grad3" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'rgba(137, 94, 255, 0.6)' }} />
            <stop offset="100%" style={{ stopColor: 'rgba(137, 94, 255, 0)' }} />
          </linearGradient>
        </defs>

        <g className="parallax">
          {/* UPDATED: Applying gradients with url(#id) */}
          <use href="#gentle-wave" x="48" y="0" fill="url(#grad1)" />
          <use href="#gentle-wave" x="48" y="3" fill="url(#grad2)" />
          <use href="#gentle-wave" x="48" y="5" fill="url(#grad3)" />
          <use href="#gentle-wave" x="48" y="7" fill="rgba(88, 122, 245, 0.7)" />
        </g>
      </svg>

      {/* --- Styling and Animation (No changes needed here) --- */}
      <style jsx>{`
        .wave-container {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          overflow: hidden;
          line-height: 0;
        }

        .waves {
          position: relative;
          width: 100%;
          height: 25vh;
          min-height: 100px;
          max-height: 150px;
        }

        .parallax > use {
          animation: move-forever 25s cubic-bezier(0.55, 0.5, 0.45, 0.5) infinite;
        }
        
        .parallax > use:nth-child(1) {
          animation-delay: -2s;
          animation-duration: 7s;
        }
        .parallax > use:nth-child(2) {
          animation-delay: -3s;
          animation-duration: 10s;
        }
        .parallax > use:nth-child(3) {
          animation-delay: -4s;
          animation-duration: 13s;
        }
        .parallax > use:nth-child(4) {
          animation-delay: -5s;
          animation-duration: 20s;
        }

        @keyframes move-forever {
          0% {
            transform: translate3d(-90px, 0, 0);
          }
          100% {
            transform: translate3d(85px, 0, 0);
          }
        }
      `}</style>
    </div>
  );
};

export default AnimatedWave;