import asyncio
from stockfish import Stockfish

async def analyze_moves(move_list):
    # Initialize Stockfish. Adjust path if necessary.
    try:
        # Stockfish binary must be available in PATH or provide absolute path
        # In a real setup you'd point to the downloaded executable.
        stockfish = Stockfish()
        stockfish.set_depth(15) # Quick analysis
    except Exception as e:
        print("Stockfish not available:", e)
        return []

    evaluations = []
    
    for i in range(len(move_list)):
        # Provide history up to this move
        stockfish.set_position(move_list[:i])
        eval_before = stockfish.get_evaluation()
        
        # Make the move
        stockfish.set_position(move_list[:i+1])
        eval_after = stockfish.get_evaluation()
        
        # Calculate diff (very simplified logic for move classification)
        # You'd typically look at cp (centipawns)
        classification = "Good"
        
        # Just a mock classification logic based on eval_after type for demonstration
        if eval_after.get("type") == "mate":
            classification = "Brilliant"
        else:
            val = eval_after.get("value", 0)
            if val > 300: classification = "Best Move"
            elif val < -300: classification = "Blunder"
            else: classification = "Good"

        evaluations.append({
            "move_index": i,
            "classification": classification,
            "eval": eval_after
        })
        
    return evaluations
