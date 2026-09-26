import React, { useState, useEffect } from 'react';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import { io } from 'socket.io-client';

const socket = io(); // Connect to the same host

export default function PCView() {
  const [game, setGame] = useState(new Chess());
  const [roomCode, setRoomCode] = useState(null);
  const [mobileConnected, setMobileConnected] = useState(false);
  const [gameStarted, setGameStarted] = useState(false);
  const [history, setHistory] = useState([]);
  
  // Post-game review states
  const [isGameOver, setIsGameOver] = useState(false);
  const [reviewIndex, setReviewIndex] = useState(-1);
  const [customArrows, setCustomArrows] = useState([]);

  useEffect(() => {
    // 소켓이 이미 연결된 상태라면 즉시 방을 만듭니다.
    if (socket.connected) {
      socket.emit('create_room');
    }
    
    socket.on('connect', () => {
      socket.emit('create_room');
    });

    socket.on('room_created', (data) => {
      setRoomCode(data.code);
    });

    socket.on('mobile_connected', () => {
      setMobileConnected(true);
    });

    socket.on('move_detected', (data) => {
      const newGame = new Chess(data.fen);
      setGame(newGame);
      setHistory(newGame.history({ verbose: true }));
      if (data.is_game_over) {
        setIsGameOver(true);
        // Optionally request engine analysis here
      }
    });

    socket.on('partner_disconnected', () => {
      setMobileConnected(false);
      alert('Mobile disconnected!');
    });

    return () => {
      socket.off('connect');
      socket.off('room_created');
      socket.off('mobile_connected');
      socket.off('move_detected');
      socket.off('partner_disconnected');
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && mobileConnected && !gameStarted) {
        setGameStarted(true);
        socket.emit('start_game', { code: roomCode });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileConnected, gameStarted, roomCode]);

  const handleReviewMove = (index) => {
    if (!isGameOver) return;
    setReviewIndex(index);
    
    // Reconstruct board up to this move
    const reviewGame = new Chess();
    for (let i = 0; i <= index; i++) {
      reviewGame.move(history[i]);
    }
    
    // Set arrow for the move (yellow color)
    const move = history[index];
    setCustomArrows([[move.from, move.to, 'rgb(255, 255, 0)']]);
    
    setGame(reviewGame);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left side - Board */}
      <div className="w-2/3 p-8 flex flex-col items-center justify-center">
        {!mobileConnected ? (
          <div className="text-center p-12 bg-white rounded-lg shadow-xl">
            <h2 className="text-3xl font-bold mb-4 text-gray-800">Pair your phone</h2>
            <p className="text-xl mb-6 text-gray-600">Enter this code on your mobile device:</p>
            <div className="text-6xl font-mono tracking-widest font-bold text-blue-600 bg-blue-50 p-6 rounded-lg border-2 border-blue-200">
              {roomCode || '...'}
            </div>
          </div>
        ) : !gameStarted ? (
          <div className="text-center p-12 bg-white rounded-lg shadow-xl">
            <h2 className="text-3xl font-bold mb-4 text-green-600">Mobile Connected!</h2>
            <p className="text-xl text-gray-600 mb-6">Press <kbd className="bg-gray-100 p-2 rounded shadow border text-gray-800">Space</kbd> to start the game.</p>
          </div>
        ) : (
          <div className="w-full max-w-2xl bg-white p-6 rounded-xl shadow-lg border border-gray-100 relative">
             {isGameOver && <div className="absolute top-2 left-2 bg-red-500 text-white px-3 py-1 rounded font-bold z-10 animate-pulse">Game Over - Review Mode</div>}
             <Chessboard 
                position={game.fen()} 
                arePiecesDraggable={false}
                customArrows={customArrows}
             />
          </div>
        )}
      </div>

      {/* Right side - Notation */}
      <div className="w-1/3 bg-white border-l shadow-2xl flex flex-col">
        <div className="bg-gray-800 text-white p-4">
          <h2 className="text-2xl font-bold">Move History {isGameOver && '(Review)'}</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-4">
            {history.reduce((result, move, index) => {
              if (index % 2 === 0) {
                result.push([{...move, index}]);
              } else {
                result[result.length - 1].push({...move, index});
              }
              return result;
            }, []).map((pair, idx) => (
              <React.Fragment key={idx}>
                <div 
                  onClick={() => handleReviewMove(pair[0].index)}
                  className={`p-3 rounded shadow-sm border border-gray-100 font-mono flex items-center cursor-pointer transition-colors ${reviewIndex === pair[0].index ? 'bg-yellow-100 border-yellow-400' : 'bg-gray-50 hover:bg-gray-200'}`}
                >
                  <span className="text-gray-400 w-6">{idx + 1}.</span> {pair[0].san}
                  {/* Mock Engine Icon */}
                  {isGameOver && <span className="ml-auto text-xs bg-green-200 text-green-800 px-1 rounded" title="Great Move">★</span>}
                </div>
                {pair[1] ? (
                  <div 
                    onClick={() => handleReviewMove(pair[1].index)}
                    className={`p-3 rounded shadow-sm border border-gray-100 font-mono cursor-pointer transition-colors flex items-center ${reviewIndex === pair[1].index ? 'bg-yellow-100 border-yellow-400' : 'bg-gray-50 hover:bg-gray-200'}`}
                  >
                    {pair[1].san}
                    {isGameOver && <span className="ml-auto text-xs bg-red-200 text-red-800 px-1 rounded" title="Blunder">??</span>}
                  </div>
                ) : <div />}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
