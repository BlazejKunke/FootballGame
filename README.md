# European Football - 2D Top-Down Soccer Game

A 4v4 top-down football (soccer) game built with Python and pygame-ce. Features intelligent AI opponents and a 3-mode passing system.

## Quick Start

### Requirements
- **Python 3.8+** (tested on 3.10.2)
- **macOS** (or any OS running Python + pygame-ce)

### Installation & Running

**Step 1: Open Terminal**
Navigate to the project directory:
```bash
cd "/Users/blazejkunke/Documents/CODE Projects/European Football"
```

**Step 2: Activate Virtual Environment** (first time only)
```bash
python3 -m venv venv
source venv/bin/activate
```

(Subsequent times, just run the activation command without creating venv again)

**Step 3: Install Dependencies** (first time only)
```bash
pip install -r requirements.txt
```

**Step 4: Run the Game**
```bash
python3 main.py
```

The game window should open immediately. If you get an error, make sure you're in the correct directory and venv is activated.

---

## Game Controls

### Movement & Basic Actions
| Key | Action |
|-----|--------|
| **Arrow Keys ↑↓←→** | Move the selected player |
| **D** | Shoot (hold to charge power, release to shoot) |
| **Tab** | Switch to teammate closest to ball |
| **R** | Reset to kickoff |
| **K** | Celebrate (dance after scoring) |
| **Esc** | Quit the game |

### Passing System (3 Modes)

#### Mode 1: Short Pass (Direct to Teammate)
- **Hold S + Press Arrow Key + Release S**
- Passes the ball directly to the teammate in that direction
- Fast, direct ground pass
- Use when you know where your teammate is

#### Mode 2: Through Ball (Forward Pass)
- **Press W**
- Passes the ball to open space ahead of your running teammate
- Faster and longer-ranged than short pass
- Perfect for creating scoring opportunities

#### Mode 3: Lobbed Pass (Over Defenders)
- **Press A**
- Aerial pass that goes over defenders
- Ball cannot be intercepted while it's in the air (high enough)
- Use to avoid blockers or pass to distant teammates

---

## Gameplay Guide

### Your Team (Red)
- You control the **red team** (attacks toward the right goal)
- AI controls your non-selected teammates (they move intelligently)
- Your striker and midfielders make runs to receive passes

### Opponent Team (Blue)
- Fully AI-controlled blue team (attacks toward the left goal)
- Improved AI that shoots, passes, and scores goals
- Watch out for their striker making aggressive runs

### Objectives
- **Win**: Score more goals than the opponent in 3 minutes
- **Key Skills**: Passing, shooting, switching players, defending
- **Timing**: Goal celebrations pause the game - use this time to catch your breath!

### Tips & Tricks

**Shooting Tips:**
- Hold D and watch the power bar fill (darker red = more power)
- Release at max power for long-distance shots
- Aim for the corners - the AI goalkeeper can't cover everything
- Get close to the goal for easier scoring

**Passing Tips:**
- Use **S + Arrow** to pass to specific teammates
- Use **W** when your striker is making a forward run
- Use **A** when defenders are blocking your direct pass
- The AI will automatically choose the best pass type

**Defensive Tips:**
- Get close to the opponent with the ball to tackle
- Switch players to position defenders
- Block shooting lanes - don't let strikers have space

**AI Behavior:**
- AI opponents shoot from medium range
- They make forward runs looking for through balls
- They pass instead of always dribbling
- They use lobbed passes to get past defenders

---

## Game Features

✅ **4v4 Realistic Soccer**
- 1 Goalkeeper, 1 Defender, 1 Midfielder, 1 Striker per team
- Intelligent AI with role-based behaviors

✅ **3-Mode Passing System**
- Short pass (direct to teammate in direction)
- Through ball (fast pass to space ahead)
- Lobbed pass (aerial over defenders)

✅ **Physics-Based Gameplay**
- Ball friction and bounce physics
- Player acceleration and momentum
- Realistic possession mechanics

✅ **Match Management**
- 3-minute matches with countdown timer
- Automatic goal detection and scoring
- Celebrations after goals
- Final score display with restart option

✅ **Visual Feedback**
- Score and timer HUD
- Selected player highlight
- Power bar for shooting
- Ball shadow (larger when ball is in air)
- Control hints at bottom of screen

---

## Troubleshooting

### "Command not found: python3"
- Install Python from https://www.python.org/downloads/
- Use `python --version` to verify installation

### "ModuleNotFoundError: No module named 'pygame'"
- Make sure virtual environment is activated: `source venv/bin/activate`
- Reinstall requirements: `pip install -r requirements.txt`

### "pygame.error: No available video device"
- This shouldn't happen on macOS with a display, but try:
  ```bash
  pip uninstall pygame-ce
  pip install pygame-ce
  ```

### Game runs but is very slow
- Make sure no other heavy applications are running
- Close the Terminal window and try again
- Check your Mac's Activity Monitor for resource usage

---

## File Structure

```
European Football/
├── main.py                 # Entry point - run this file
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── src/
    ├── constants.py       # Game parameters (speeds, physics, etc.)
    ├── game.py           # Main game loop and logic
    ├── physics.py        # Physics engine
    ├── renderer.py       # Drawing and visualization
    ├── pitch.py          # Soccer field definition
    ├── ai.py             # AI controller and behaviors
    └── entities/
        ├── player.py     # Player class
        ├── ball.py       # Ball physics and mechanics
        └── team.py       # Team management
```

---

## Game Version

**Current Version**: 3.0
- ✨ New: 3-mode passing system (short, through, lob)
- ✨ New: Aerial ball physics with interception prevention
- ✨ Improved: AI uses intelligent pass selection
- ✨ Updated: Shoot key changed from Space to D
- ✨ Enhanced: Visual feedback for aerial passes

---

## Have Fun!

This is a fully playable soccer game. Try different strategies:
- Quick short passes for possession
- Long through balls to catch defenders off-guard
- Lobbed passes over crowded defenses
- Mix up your style to keep the AI guessing!

Good luck, and enjoy the match! ⚽
