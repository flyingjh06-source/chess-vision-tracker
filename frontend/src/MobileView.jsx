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
      if (data.board_corners) {
        setBoardCorners(data.board_corners);
      }
    };

    socket.on('scan_error', (data) => {
      setStatus(`Error: ${data.error || data.message}`);
      handleScanResult(data);
    });

    socket.on('scan_no_change', (data) => {
      setStatus('No change detected.');
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
  }, []);

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
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    // Capture the entire video frame
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
    socket.emit('send_frame', { code, image: dataUrl });
    setStatus('Scanning...');
  };

  useEffect(() => {
    if (!gameStarted || mode !== 'auto') return;
    const interval = setInterval(captureFrame, 5000);
    return () => clearInterval(interval);
  }, [gameStarted, mode, code]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && gameStarted && mode === 'manual') {
        captureFrame();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameStarted, mode, code]);

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
      <div className="bg-gray-900 text-white p-4 flex justify-between items-center z-10 shadow-lg">
        <div className="text-sm font-semibold truncate max-w-xs">{status}</div>
        <select 
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="bg-gray-800 text-white text-sm p-2 rounded border border-gray-700 outline-none"
        >
          <option value="auto">Auto (5s)</option>
          <option value="manual">Manual (Space)</option>
        </select>
      </div>

      <div className="flex-1 relative overflow-hidden flex items-center justify-center">
        <video 
          ref={videoRef}
          autoPlay 
          playsInline 
          className="w-full h-full object-contain opacity-80"
        />
        
        {/* Dynamic Polygon showing automatically detected board */}
        {boardCorners && videoRef.current && (
          <svg 
            className="absolute inset-0 w-full h-full pointer-events-none" 
            viewBox={`0 0 ${videoRef.current.videoWidth} ${videoRef.current.videoHeight}`}
            preserveAspectRatio="xMidYMid meet"
          >
            <polygon 
              points={boardCorners.map(p => `${p[0]},${p[1]}`).join(' ')}
              fill="rgba(255, 255, 0, 0.2)" 
              stroke="yellow" 
              strokeWidth="4" 
              strokeDasharray="10 5"
            />
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
