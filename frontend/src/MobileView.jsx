import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';

const socket = io(); // Connect to the same host

export default function MobileView() {
  const [code, setCode] = useState('');
  const [connected, setConnected] = useState(false);
  const [gameStarted, setGameStarted] = useState(false);
  const [mode, setMode] = useState('auto'); // auto or manual
  const [status, setStatus] = useState('Waiting for PC to start game...');
  const [boardCorners, setBoardCorners] = useState(null);
  const [manualCorners, setManualCorners] = useState([]);
  const [isManualSelecting, setIsManualSelecting] = useState(false);
  const [orientation, setOrientation] = useState('auto');
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    socket.on('room_joined', (data) => {
      if (data.success) {
        setConnected(true);
      } else {
        alert(data.message);
      }
    });

    socket.on('game_started', () => {
      setGameStarted(true);
      setStatus('Game started! Scanning...');
    });

    const handleScanResult = (data) => {
      if (data.board_corners && !isManualSelecting) {
        setBoardCorners(data.board_corners);
      }
      if (data.orientation && orientation === 'auto') {
        const textMap = {'0': 'White at Bottom', '180': 'Black at Bottom', '90': 'White on Right', '270': 'White on Left'};
        setStatus(`Auto-oriented: ${textMap[data.orientation] || data.orientation}`);
      }
    };

    socket.on('scan_error', (data) => {
      setStatus(`Error: ${data.error || data.message}`);
      handleScanResult(data);
    });

    socket.on('scan_no_change', (data) => {
      // Don't overwrite status if we just want to show no change, but we want to show auto-orientation.
      handleScanResult(data);
    });

    socket.on('scan_success', (data) => {
      setStatus(`Move detected: ${data.move}`);
      handleScanResult(data);
    });

    return () => {
      socket.off('room_joined');
      socket.off('game_started');
      socket.off('scan_error');
      socket.off('scan_no_change');
      socket.off('scan_success');
    };
  }, [isManualSelecting, orientation]);

  useEffect(() => {
    if (connected) {
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(stream => {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        })
        .catch(err => console.error('Error accessing camera:', err));
    }
  }, [connected]);

  const captureFrame = () => {
    if (!videoRef.current || !canvasRef.current || isManualSelecting) return;
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    // Capture the entire video frame
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
    socket.emit('send_frame', { code, image: dataUrl, orientation });
  };

  useEffect(() => {
    if (!gameStarted || mode !== 'auto' || isManualSelecting) return;
    const interval = setInterval(captureFrame, 5000);
    return () => clearInterval(interval);
  }, [gameStarted, mode, code, isManualSelecting, orientation]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && gameStarted && mode === 'manual' && !isManualSelecting) {
        captureFrame();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameStarted, mode, code, isManualSelecting, orientation]);

  const handleSvgClick = (e) => {
    if (!isManualSelecting) return;
    
    const svg = e.currentTarget;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
    
    const newCorners = [...manualCorners, [svgP.x, svgP.y]];
    setManualCorners(newCorners);
    
    if (newCorners.length === 4) {
       socket.emit('set_corners', { code, corners: newCorners });
       setBoardCorners(newCorners);
       setIsManualSelecting(false);
       setStatus('Manual corners set. Resuming scan...');
    } else {
       setStatus(`Tap corner ${newCorners.length + 1} of 4 (Top-Left, Top-Right, Bottom-Right, Bottom-Left)`);
    }
  };

  const startManualSelection = () => {
    setIsManualSelecting(true);
    setManualCorners([]);
    setBoardCorners(null);
    setStatus('Tap corner 1 of 4 (A8, or Top-Left)');
  };

  if (!connected) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
        <div className="bg-white p-8 rounded-xl shadow-xl w-full max-w-sm">
          <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Connect to PC</h2>
          <input 
            type="text" 
            placeholder="4-digit code" 
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full text-center text-3xl tracking-widest font-mono p-4 border-2 border-gray-300 rounded-lg mb-6"
            maxLength={4}
          />
          <button 
            onClick={() => socket.emit('join_room', { code })}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-lg"
          >
            Connect
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-black flex flex-col relative">
      <div className="bg-gray-900 text-white p-4 flex flex-wrap gap-2 justify-between items-center z-10 shadow-lg">
        <div className="text-sm font-semibold truncate w-full mb-1">{status}</div>
        <div className="flex gap-2 w-full justify-between">
            {!isManualSelecting && (
                <button onClick={startManualSelection} className="bg-blue-600 text-white text-xs px-2 py-1 rounded shrink-0">
                  Manual Select
                </button>
            )}
            <select 
              value={orientation}
              onChange={(e) => { setOrientation(e.target.value); setStatus('Orientation changed. Scanning...'); captureFrame(); }}
              className="bg-gray-800 text-white text-xs p-1 rounded border border-gray-700 outline-none shrink-0"
            >
              <option value="auto">Auto-Detect</option>
              <option value="0">Behind White</option>
              <option value="90">Left of White</option>
              <option value="180">Behind Black</option>
              <option value="270">Right of White</option>
            </select>
            <select 
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="bg-gray-800 text-white text-xs p-1 rounded border border-gray-700 outline-none shrink-0"
            >
              <option value="auto">Auto (5s)</option>
              <option value="manual">Manual</option>
            </select>
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden flex items-center justify-center">
        <video 
          ref={videoRef}
          autoPlay 
          playsInline 
          className="w-full h-full object-contain opacity-80"
        />
        
        {/* Dynamic Polygon showing detected or manual board */}
        {videoRef.current && (
          <svg 
            className={`absolute inset-0 w-full h-full ${isManualSelecting ? 'cursor-crosshair pointer-events-auto' : 'pointer-events-none'}`} 
            viewBox={`0 0 ${videoRef.current.videoWidth} ${videoRef.current.videoHeight}`}
            preserveAspectRatio="xMidYMid meet"
            onClick={handleSvgClick}
            style={{ zIndex: 20 }}
          >
            {/* Draw confirmed corners */}
            {boardCorners && (
                <polygon 
                  points={boardCorners.map(p => `${p[0]},${p[1]}`).join(' ')}
                  fill="rgba(255, 255, 0, 0.2)" 
                  stroke="yellow" 
                  strokeWidth="4" 
                  strokeDasharray="10 5"
                />
            )}
            
            {/* Draw dots for manual selection */}
            {isManualSelecting && manualCorners.map((p, i) => (
                <circle key={i} cx={p[0]} cy={p[1]} r="10" fill="red" />
            ))}
          </svg>
        )}
        
        {!boardCorners && (
           <p className="absolute text-yellow-400 font-bold bg-black bg-opacity-50 p-2 rounded">
             Auto-detecting board...
           </p>
        )}
        
        <canvas ref={canvasRef} className="hidden" />
      </div>

      {mode === 'manual' && gameStarted && (
        <div className="absolute bottom-8 left-0 right-0 flex justify-center z-10">
          <button 
            onClick={captureFrame}
            className="w-20 h-20 bg-white rounded-full border-4 border-gray-300 active:bg-gray-200 shadow-xl"
          ></button>
        </div>
      )}
    </div>
  );
}
