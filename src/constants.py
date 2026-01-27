"""
All game constants and tuning parameters.
Modify these values to adjust game feel and balance.
"""

import pygame

# =============================================================================
# DISPLAY
# =============================================================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
FIXED_TIMESTEP = 1.0 / 60.0  # Physics update rate (60 Hz)
MAX_FRAME_TIME = 0.25  # Cap to prevent spiral of death

# =============================================================================
# PITCH DIMENSIONS
# =============================================================================
PITCH_WIDTH = 1200
PITCH_HEIGHT = 650
PITCH_MARGIN_X = (SCREEN_WIDTH - PITCH_WIDTH) // 2
PITCH_MARGIN_Y = (SCREEN_HEIGHT - PITCH_HEIGHT) // 2

GOAL_WIDTH = 120  # Height of goal opening (vertical)
GOAL_DEPTH = 30   # How deep the net extends behind goal line
GOAL_POST_RADIUS = 5

CENTER_CIRCLE_RADIUS = 70
PENALTY_AREA_WIDTH = 120
PENALTY_AREA_HEIGHT = 250

# =============================================================================
# PLAYER PHYSICS
# =============================================================================
PLAYER_RADIUS = 15
PLAYER_MAX_SPEED = 280.0        # pixels/second
PLAYER_ACCELERATION = 900.0     # pixels/second^2
PLAYER_FRICTION = 600.0         # deceleration when not moving
PLAYER_TURN_SPEED = 10.0        # how fast player can change direction

# =============================================================================
# BALL PHYSICS
# =============================================================================
BALL_RADIUS = 8
BALL_MAX_SPEED = 650.0          # pixels/second
BALL_FRICTION = 180.0           # ground friction (deceleration)
BALL_BOUNCE_DAMPING = 0.7       # energy retained on bounce (0-1)
BALL_MIN_SPEED = 5.0            # below this, ball stops

# =============================================================================
# POSSESSION
# =============================================================================
POSSESSION_DISTANCE = 28        # max distance to "own" ball
POSSESSION_SPEED = 180.0        # max ball speed to gain possession
POSSESSION_OFFSET = 22          # ball offset in front of player when owned

# =============================================================================
# SHOOTING / PASSING
# =============================================================================
SHOT_POWER_MIN = 250.0          # minimum shot speed
SHOT_POWER_MAX = 650.0          # maximum shot speed
SHOT_CHARGE_RATE = 1.8          # power per second (0-1 scale)
SHOT_CHARGE_MAX = 1.0           # max charge level
SHOT_INACCURACY = 0.15          # shot direction randomness (radians)

PASS_SPEED = 320.0              # base pass speed
PASS_LEAD_FACTOR = 0.2          # lead pass toward teammate's velocity

# =============================================================================
# TACKLING
# =============================================================================
TACKLE_RANGE = 32               # distance to attempt tackle
TACKLE_SUCCESS_CHANCE = 0.55    # base success probability
TACKLE_COOLDOWN = 0.7           # seconds between tackles
TACKLE_STUN_TIME = 0.25         # brief stun on failed tackle
TACKLE_KNOCKBACK = 80.0         # ball knockback on successful tackle

# =============================================================================
# MATCH
# =============================================================================
MATCH_DURATION = 180.0          # 3 minutes in seconds
GOAL_CELEBRATION_TIME = 4.0     # pause after goal (more time to celebrate!)
KICKOFF_DELAY = 1.0             # countdown before kickoff starts

# =============================================================================
# AI PARAMETERS
# =============================================================================
AI_DECISION_COOLDOWN = 0.18     # seconds between major decisions (faster reactions)
AI_REACTION_DELAY = 0.05        # slight delay for human-like feel
AI_SMOOTHING_FACTOR = 0.12      # movement smoothing (0 = instant, 1 = no change)

AI_CHASE_BALL_DISTANCE = 350    # how far to chase loose ball (more aggressive)
AI_PASS_PREFERENCE = 0.45       # tendency to pass vs dribble (0-1)
AI_SHOT_DISTANCE = 380          # max distance to attempt shot (longer range)
AI_SHOT_ANGLE_MAX = 0.6         # max angle to goal center (radians) - wider shots allowed

AI_ZONE_DEFENSE_RADIUS = 180    # defender zone radius
AI_STRIKER_PUSH_UP = 180        # how far striker pushes forward (more aggressive)
AI_MIDFIELDER_SUPPORT = 120     # midfielder offset for support

AI_GOALKEEPER_RANGE_X = 80      # how far GK ventures from goal line
AI_GOALKEEPER_RANGE_Y = 100     # vertical movement range

AI_PRESSURE_DISTANCE = 120      # distance to consider "under pressure"
AI_OPEN_SPACE_THRESHOLD = 60    # min distance from defenders to be "open"

# Advanced AI parameters
AI_DRIBBLE_SPEED = 100          # how far ahead to target when dribbling
AI_THROUGH_BALL_CHANCE = 0.3    # chance to attempt through ball
AI_ONE_TWO_CHANCE = 0.25        # chance to attempt one-two passing play

# =============================================================================
# COLORS
# =============================================================================
COLOR_PITCH_GREEN = (34, 139, 34)
COLOR_PITCH_LIGHT = (46, 155, 46)  # lighter stripes
COLOR_PITCH_LINES = (255, 255, 255)

COLOR_BALL = (255, 255, 255)
COLOR_BALL_PATTERN = (40, 40, 40)
COLOR_BALL_SHADOW = (0, 0, 0)

COLOR_TEAM_HOME = (220, 50, 50)        # Red team (player)
COLOR_TEAM_HOME_SECONDARY = (150, 30, 30)
COLOR_TEAM_AWAY = (50, 100, 220)       # Blue team (AI)
COLOR_TEAM_AWAY_SECONDARY = (30, 60, 150)

COLOR_SELECTED = (255, 230, 0)         # Yellow highlight for selected player
COLOR_POSSESSION = (255, 200, 0)       # Gold for possession indicator

COLOR_GOAL_POST = (255, 255, 255)
COLOR_GOAL_NET = (180, 180, 180)

COLOR_HUD_TEXT = (255, 255, 255)
COLOR_HUD_SHADOW = (0, 0, 0)
COLOR_HUD_BACKGROUND = (20, 20, 20)

COLOR_POWER_BAR_BG = (60, 60, 60)
COLOR_POWER_BAR_LOW = (100, 255, 100)
COLOR_POWER_BAR_MED = (255, 255, 100)
COLOR_POWER_BAR_HIGH = (255, 100, 100)

COLOR_CELEBRATION = (255, 215, 0)  # Gold

# =============================================================================
# FORMATIONS (4v4: 1 GK, 1 DEF, 1 MID, 1 STR)
# =============================================================================
# Positions as (x_fraction, y_fraction) of half-field from own goal
# x: 0 = goal line, 1 = center line
# y: 0 = top, 1 = bottom
FORMATION_4V4 = {
    'GOALKEEPER': (0.06, 0.5),
    'DEFENDER': (0.28, 0.5),
    'MIDFIELDER': (0.52, 0.5),
    'STRIKER': (0.78, 0.5),
}

# Vertical offsets for variety (applied alternately)
FORMATION_Y_OFFSETS = {
    'GOALKEEPER': 0.0,
    'DEFENDER': 0.0,
    'MIDFIELDER': 0.0,
    'STRIKER': 0.0,
}

# =============================================================================
# CONTROLS (pygame key constants)
# =============================================================================
KEY_MOVE_UP = pygame.K_UP
KEY_MOVE_DOWN = pygame.K_DOWN
KEY_MOVE_LEFT = pygame.K_LEFT
KEY_MOVE_RIGHT = pygame.K_RIGHT
KEY_SHOOT = pygame.K_SPACE
KEY_PASS = pygame.K_s
KEY_SWITCH_PLAYER = pygame.K_TAB
KEY_RESET = pygame.K_r
KEY_CELEBRATE = pygame.K_k
KEY_QUIT = pygame.K_ESCAPE

# =============================================================================
# RANDOM SEED (for reproducible AI behavior during testing)
# =============================================================================
RANDOM_SEED = 42
