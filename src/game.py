"""
Main Game class with game loop, state machine, and input handling.
"""

import time
from enum import Enum, auto
from typing import List, Optional
import pygame

from .entities.player import Player, PlayerRole
from .entities.ball import Ball
from .entities.team import Team
from .pitch import Pitch
from .physics import PhysicsEngine
from .ai import AIController, TeammateAIController
from .renderer import Renderer
from .constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, FIXED_TIMESTEP, MAX_FRAME_TIME,
    MATCH_DURATION, GOAL_CELEBRATION_TIME, KICKOFF_DELAY,
    COLOR_TEAM_HOME, COLOR_TEAM_HOME_SECONDARY,
    COLOR_TEAM_AWAY, COLOR_TEAM_AWAY_SECONDARY,
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_SHOOT, KEY_PASS, KEY_SWITCH_PLAYER, KEY_RESET, KEY_CELEBRATE, KEY_QUIT
)


class GameState(Enum):
    """All possible game states."""
    KICKOFF = auto()
    PLAYING = auto()
    GOAL_SCORED = auto()
    MATCH_END = auto()


class Game:
    """Main game class orchestrating all systems."""

    def __init__(self):
        # Initialize pygame
        pygame.init()
        pygame.display.set_caption("European Football - 4v4")

        # Create display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Create pitch
        self.pitch = Pitch()

        # Create ball at center
        self.ball = Ball(self.pitch.center.copy())

        # Create teams
        self.teams: List[Team] = []
        self._create_teams()

        # Create physics engine
        self.physics = PhysicsEngine(self.pitch)

        # Create AI controller for away team
        self.ai_controller = AIController(
            self.teams[1],  # Away team (AI)
            self.teams[0],  # Home team (player)
            self.ball,
            self.pitch
        )

        # Create AI controller for player's teammates (non-selected players)
        self.teammate_ai = TeammateAIController(
            self.teams[0],  # Home team (player's teammates)
            self.teams[1],  # Away team (opponents)
            self.ball,
            self.pitch
        )

        # Create renderer
        self.renderer = Renderer(self.screen, self.pitch)

        # Game state
        self.state = GameState.KICKOFF
        self.state_timer = 0.0
        self.kickoff_team = 0  # 0 = home, 1 = away

        # Score
        self.score = {'home': 0, 'away': 0}

        # Match timer
        self.match_timer = MATCH_DURATION

        # Message to display
        self.message: Optional[str] = None

        # Running flag
        self.running = True

        # Last goal scorer
        self.last_scorer: Optional[Player] = None

    def _create_teams(self) -> None:
        """Create both teams with players."""
        # Home team (player-controlled, attacks right)
        home_team = Team(
            name="Red",
            color=COLOR_TEAM_HOME,
            secondary_color=COLOR_TEAM_HOME_SECONDARY,
            attacking_direction=1,
            is_player_controlled=True
        )
        home_team.create_players()
        self.teams.append(home_team)

        # Away team (AI-controlled, attacks left)
        away_team = Team(
            name="Blue",
            color=COLOR_TEAM_AWAY,
            secondary_color=COLOR_TEAM_AWAY_SECONDARY,
            attacking_direction=-1,
            is_player_controlled=False
        )
        away_team.create_players()
        self.teams.append(away_team)

    def run(self) -> None:
        """Main game loop with fixed timestep."""
        current_time = time.perf_counter()
        accumulator = 0.0

        while self.running:
            new_time = time.perf_counter()
            frame_time = new_time - current_time
            current_time = new_time

            # Cap frame time to prevent spiral of death
            if frame_time > MAX_FRAME_TIME:
                frame_time = MAX_FRAME_TIME

            accumulator += frame_time

            # Handle events (once per frame)
            self._handle_events()

            # Fixed timestep updates
            while accumulator >= FIXED_TIMESTEP:
                self._update(FIXED_TIMESTEP)
                accumulator -= FIXED_TIMESTEP

            # Render
            self._render()

            # Cap frame rate
            self.clock.tick(FPS)

        pygame.quit()

    def _handle_events(self) -> None:
        """Process pygame events and user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_key_down(event.key)

            if event.type == pygame.KEYUP:
                self._handle_key_up(event.key)

    def _handle_key_down(self, key: int) -> None:
        """Handle key press."""
        if key == KEY_QUIT:
            self.running = False
            return

        if key == KEY_RESET:
            if self.state == GameState.MATCH_END:
                self._restart_match()
            else:
                self._setup_kickoff()
            return

        # In-game controls (only during PLAYING state)
        if self.state == GameState.PLAYING:
            if key == KEY_SWITCH_PLAYER:
                self._switch_player()

            elif key == KEY_SHOOT:
                player = self.teams[0].selected_player
                if player and player.has_ball:
                    player.start_charging_shot()

            elif key == KEY_PASS:
                self._execute_pass()

            elif key == KEY_CELEBRATE:
                player = self.teams[0].selected_player
                if player:
                    player.celebrate()

    def _handle_key_up(self, key: int) -> None:
        """Handle key release."""
        if key == KEY_SHOOT:
            player = self.teams[0].selected_player
            if player and player.is_charging_shot:
                # Calculate shot target (toward opponent goal)
                goal_center = self.pitch.get_goal_center('right')
                player.release_shot(self.ball, goal_center)

    def _handle_player_input(self, dt: float) -> None:
        """Handle continuous player input (movement)."""
        if self.state != GameState.PLAYING:
            return

        player = self.teams[0].selected_player
        if not player:
            return

        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)

        if keys[KEY_MOVE_UP]:
            direction.y -= 1
        if keys[KEY_MOVE_DOWN]:
            direction.y += 1
        if keys[KEY_MOVE_LEFT]:
            direction.x -= 1
        if keys[KEY_MOVE_RIGHT]:
            direction.x += 1

        if direction.length() > 0:
            player.move(direction)

    def _switch_player(self) -> None:
        """Switch to next best player."""
        home_team = self.teams[0]
        home_team.cycle_selection(self.ball.position)

    def _execute_pass(self) -> None:
        """Execute pass to nearest teammate and auto-switch to receiver."""
        player = self.teams[0].selected_player
        if not player or not player.has_ball:
            return

        # Find best open teammate
        teammate = self.teams[0].get_open_teammate(player, self.teams[1].players)
        if not teammate:
            # Just pass to closest if no one is open
            teammates = self.teams[0].get_teammates(player)
            if teammates:
                teammate = min(teammates, key=lambda t: (t.position - player.position).length())

        if teammate:
            player.pass_ball(self.ball, teammate)
            # Auto-switch to the pass receiver
            self.teams[0].select_player(teammate)

    def _update(self, dt: float) -> None:
        """Update game logic."""
        # Update state timer
        self.state_timer += dt

        # State-specific updates
        if self.state == GameState.KICKOFF:
            self._update_kickoff(dt)

        elif self.state == GameState.PLAYING:
            self._update_playing(dt)

        elif self.state == GameState.GOAL_SCORED:
            self._update_goal_scored(dt)

        elif self.state == GameState.MATCH_END:
            pass  # Wait for restart

    def _update_kickoff(self, dt: float) -> None:
        """Update during kickoff state."""
        self.message = "KICK OFF!"

        # Auto-transition after delay
        if self.state_timer >= KICKOFF_DELAY:
            self._transition_to(GameState.PLAYING)

    def _update_playing(self, dt: float) -> None:
        """Update during normal gameplay."""
        self.message = None

        # Update match timer
        self.match_timer -= dt
        if self.match_timer <= 0:
            self.match_timer = 0
            self._transition_to(GameState.MATCH_END)
            return

        # Handle player input
        self._handle_player_input(dt)

        # Update AI for opponent team
        self.ai_controller.update(dt)

        # Update AI for player's teammates (non-selected players move intelligently)
        self.teammate_ai.update(dt)

        # Get all players
        all_players = self._get_all_players()

        # Update physics
        self.physics.update(dt, self.ball, all_players)

        # Check for auto-tackle (when player gets close to opponent with ball)
        self._check_auto_tackle()

        # Check for goal
        goal_side = self.pitch.check_goal(self.ball.position)
        if goal_side:
            self._handle_goal(goal_side)

    def _update_goal_scored(self, dt: float) -> None:
        """Update during goal celebration."""
        self.message = "GOAL!"

        # Trigger celebration for scorer
        if self.last_scorer and not self.last_scorer.is_celebrating:
            self.last_scorer.celebrate()

        # Auto-transition after celebration
        if self.state_timer >= GOAL_CELEBRATION_TIME:
            self._setup_kickoff()
            self._transition_to(GameState.KICKOFF)

    def _handle_goal(self, goal_side: str) -> None:
        """Handle goal scored."""
        # Determine who scored
        # Ball went into left goal = away team scores (if attacking left) or home scores (if attacking right)
        if goal_side == 'left':
            # Left goal = home team's goal (they attack right)
            self.score['away'] += 1
            self.kickoff_team = 0  # Home restarts
        else:
            # Right goal = away team's goal
            self.score['home'] += 1
            self.kickoff_team = 1  # Away restarts

        # Track last scorer
        self.last_scorer = self.ball.last_owner

        self._transition_to(GameState.GOAL_SCORED)

    def _check_auto_tackle(self) -> None:
        """Check if player team should auto-tackle."""
        # Find if any player team member is close to ball carrier
        ball_carrier = self.teams[1].get_player_with_ball()  # AI ball carrier
        if not ball_carrier:
            return

        for player in self.teams[0].players:
            if player.is_selected:  # Only selected player can tackle
                dist = (player.position - ball_carrier.position).length()
                if dist < 35:  # Close enough for auto-tackle
                    player.attempt_tackle(ball_carrier, self.ball)
                    break

    def _setup_kickoff(self) -> None:
        """Setup positions for kickoff."""
        # Reset ball to center
        self.ball.reset(self.pitch.center.copy())

        # Reset all players
        for team in self.teams:
            team.reset_formation()

        # Select appropriate player for kickoff
        kicking_team = self.teams[self.kickoff_team]
        if kicking_team.is_player_controlled:
            # Select striker for kickoff
            for player in kicking_team.players:
                if player.role == PlayerRole.STRIKER:
                    kicking_team.select_player(player)
                    break

        self.last_scorer = None

    def _restart_match(self) -> None:
        """Restart entire match."""
        self.score = {'home': 0, 'away': 0}
        self.match_timer = MATCH_DURATION
        self.kickoff_team = 0
        self._setup_kickoff()
        self._transition_to(GameState.KICKOFF)

    def _transition_to(self, new_state: GameState) -> None:
        """Transition to new game state."""
        self.state = new_state
        self.state_timer = 0.0

    def _get_all_players(self) -> List[Player]:
        """Get list of all players from both teams."""
        return self.teams[0].players + self.teams[1].players

    def _render(self) -> None:
        """Render current frame."""
        if self.state == GameState.MATCH_END:
            # First render normal frame, then overlay
            self.renderer.render(
                self.ball, self.teams, self.score,
                self.match_timer, self.state.name, None
            )
            self.renderer.draw_winner_screen(self.score, self.teams)
        else:
            self.renderer.render(
                self.ball, self.teams, self.score,
                self.match_timer, self.state.name, self.message
            )
