# European Football - 2D Top-Down Soccer Game

A simple 4v4 top-down football (soccer) game built with Python and pygame-ce.

## Requirements

- Python 3.11+
- macOS (Apple Silicon compatible)

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Game

```bash
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys | Move the selected player |
| Space | Shoot/Kick (hold to charge power, release to shoot) |
| S | Pass to nearest teammate |
| Tab | Switch control to teammate closest to ball |
| R | Reset to kickoff (also auto-resets after goals) |
| K | Celebrate (dance after scoring) |
| Esc | Quit the game |

## Gameplay

- **Teams**: You control the red team (left side), AI controls the blue team (right side)
- **Objective**: Score more goals than the opponent in 3 minutes
- **Possession**: Get close to the ball when it's slow to gain control
- **Shooting**: Hold Space to charge, release to shoot - longer hold = more power
- **Passing**: Press S to pass to your nearest open teammate
- **Tackling**: Get close to an opponent with the ball to attempt a steal

## Game Features

- 4v4 players (1 GK, 1 Defender, 1 Midfielder, 1 Striker per team)
- Physics-based ball movement with friction and bouncing
- AI opponents with role-based behaviors
- 3-minute match timer
- Goal celebrations
- Scoreboard and match timer HUD
