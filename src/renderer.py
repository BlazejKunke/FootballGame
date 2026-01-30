"""
Renderer for drawing pitch, players, ball, and HUD.
"""

import math
from typing import List, Optional, Tuple
import pygame

from .entities.player import Player
from .entities.ball import Ball
from .entities.team import Team
from .pitch import Pitch
from .constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    PITCH_WIDTH, PITCH_HEIGHT, PITCH_MARGIN_X, PITCH_MARGIN_Y,
    CENTER_CIRCLE_RADIUS, GOAL_WIDTH, GOAL_DEPTH, GOAL_POST_RADIUS,
    PLAYER_RADIUS, BALL_RADIUS,
    COLOR_PITCH_GREEN, COLOR_PITCH_LIGHT, COLOR_PITCH_LINES,
    COLOR_BALL, COLOR_BALL_PATTERN, COLOR_BALL_SHADOW,
    COLOR_GOAL_POST, COLOR_GOAL_NET,
    COLOR_SELECTED, COLOR_POSSESSION,
    COLOR_HUD_TEXT, COLOR_HUD_SHADOW, COLOR_HUD_BACKGROUND,
    COLOR_POWER_BAR_BG, COLOR_POWER_BAR_LOW, COLOR_POWER_BAR_MED, COLOR_POWER_BAR_HIGH,
    COLOR_CELEBRATION
)


class Renderer:
    """Handles all drawing operations."""

    def __init__(self, screen: pygame.Surface, pitch: Pitch):
        self.screen = screen
        self.pitch = pitch

        # Initialize fonts
        pygame.font.init()
        self.font_large = pygame.font.Font(None, 56)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 18)

    def render(
        self,
        ball: Ball,
        teams: List[Team],
        score: dict,
        match_timer: float,
        game_state: str,
        message: Optional[str] = None
    ) -> None:
        """Render complete frame."""
        # Clear screen
        self.screen.fill((30, 30, 30))

        # Draw in layers (bottom to top)
        self._draw_pitch_background()
        self._draw_pitch_lines()
        self._draw_goals()
        self._draw_ball_shadow(ball)
        self._draw_teams(teams)
        self._draw_ball(ball)
        self._draw_effects(teams)
        self._draw_hud(score, match_timer, teams)

        # Draw state message if any
        if message:
            self._draw_message(message)

        # Flip display
        pygame.display.flip()

    def _draw_pitch_background(self) -> None:
        """Draw green field with stripes."""
        # Main pitch color
        pitch_rect = pygame.Rect(
            PITCH_MARGIN_X, PITCH_MARGIN_Y,
            PITCH_WIDTH, PITCH_HEIGHT
        )
        pygame.draw.rect(self.screen, COLOR_PITCH_GREEN, pitch_rect)

        # Draw stripes
        stripe_width = 75
        for i in range(PITCH_WIDTH // stripe_width + 1):
            if i % 2 == 0:
                stripe_rect = pygame.Rect(
                    PITCH_MARGIN_X + i * stripe_width,
                    PITCH_MARGIN_Y,
                    stripe_width,
                    PITCH_HEIGHT
                )
                # Clip to pitch bounds
                stripe_rect = stripe_rect.clip(pitch_rect)
                pygame.draw.rect(self.screen, COLOR_PITCH_LIGHT, stripe_rect)

    def _draw_pitch_lines(self) -> None:
        """Draw field markings."""
        bounds = self.pitch.boundary_rect
        center = self.pitch.center
        line_width = 3

        # Outer boundary
        pygame.draw.rect(self.screen, COLOR_PITCH_LINES, bounds, line_width)

        # Halfway line
        pygame.draw.line(
            self.screen, COLOR_PITCH_LINES,
            (center.x, bounds.top),
            (center.x, bounds.bottom),
            line_width
        )

        # Center circle
        pygame.draw.circle(
            self.screen, COLOR_PITCH_LINES,
            (int(center.x), int(center.y)),
            CENTER_CIRCLE_RADIUS,
            line_width
        )

        # Center spot
        pygame.draw.circle(
            self.screen, COLOR_PITCH_LINES,
            (int(center.x), int(center.y)),
            5
        )

        # Penalty areas
        pygame.draw.rect(
            self.screen, COLOR_PITCH_LINES,
            self.pitch.penalty_area_left,
            line_width
        )
        pygame.draw.rect(
            self.screen, COLOR_PITCH_LINES,
            self.pitch.penalty_area_right,
            line_width
        )

        # Goal area boxes (smaller boxes inside penalty areas)
        goal_area_width = 60
        goal_area_height = 140

        # Left goal area
        left_goal_area = pygame.Rect(
            bounds.left,
            center.y - goal_area_height // 2,
            goal_area_width,
            goal_area_height
        )
        pygame.draw.rect(self.screen, COLOR_PITCH_LINES, left_goal_area, line_width)

        # Right goal area
        right_goal_area = pygame.Rect(
            bounds.right - goal_area_width,
            center.y - goal_area_height // 2,
            goal_area_width,
            goal_area_height
        )
        pygame.draw.rect(self.screen, COLOR_PITCH_LINES, right_goal_area, line_width)

    def _draw_goals(self) -> None:
        """Draw goal posts and nets."""
        for goal in [self.pitch.goal_left, self.pitch.goal_right]:
            # Draw net (rectangle behind goal line)
            if goal.side == 'left':
                net_rect = pygame.Rect(
                    goal.back_x, goal.top_post.y,
                    GOAL_DEPTH, GOAL_WIDTH
                )
            else:
                net_rect = pygame.Rect(
                    goal.line_x, goal.top_post.y,
                    GOAL_DEPTH, GOAL_WIDTH
                )

            pygame.draw.rect(self.screen, COLOR_GOAL_NET, net_rect)
            pygame.draw.rect(self.screen, COLOR_PITCH_LINES, net_rect, 2)

            # Draw posts (circles at top and bottom)
            pygame.draw.circle(
                self.screen, COLOR_GOAL_POST,
                (int(goal.top_post.x), int(goal.top_post.y)),
                GOAL_POST_RADIUS
            )
            pygame.draw.circle(
                self.screen, COLOR_GOAL_POST,
                (int(goal.bottom_post.x), int(goal.bottom_post.y)),
                GOAL_POST_RADIUS
            )

            # Draw post shadows/outlines
            pygame.draw.circle(
                self.screen, COLOR_HUD_SHADOW,
                (int(goal.top_post.x), int(goal.top_post.y)),
                GOAL_POST_RADIUS, 2
            )
            pygame.draw.circle(
                self.screen, COLOR_HUD_SHADOW,
                (int(goal.bottom_post.x), int(goal.bottom_post.y)),
                GOAL_POST_RADIUS, 2
            )

    def _draw_ball_shadow(self, ball: Ball) -> None:
        """Draw shadow under ball (offset increases with height for aerial balls)."""
        shadow_offset = ball.get_shadow_offset()
        shadow_pos = ball.position + shadow_offset

        # Shadow gets larger and more transparent as ball gets higher
        if ball.is_aerial:
            from .constants import BALL_MAX_HEIGHT
            shadow_scale = 1.0 + (ball.height / BALL_MAX_HEIGHT) * 0.5
            shadow_alpha = max(30, 60 - int(ball.height * 0.5))
        else:
            shadow_scale = 1.0
            shadow_alpha = 60

        shadow_width = int(BALL_RADIUS * 3 * shadow_scale)
        shadow_height = int(BALL_RADIUS * 2 * shadow_scale)

        # Draw ellipse shadow
        shadow_surface = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        pygame.draw.ellipse(
            shadow_surface,
            (0, 0, 0, shadow_alpha),
            (0, 0, shadow_width, shadow_height)
        )
        self.screen.blit(
            shadow_surface,
            (shadow_pos.x - shadow_width / 2, shadow_pos.y - shadow_height / 2)
        )

    def _draw_ball(self, ball: Ball) -> None:
        """Draw the football with size variation for aerial state."""
        # Calculate visual position (ball appears higher when aerial)
        visual_y = ball.position.y
        if ball.is_aerial:
            # Ball drawn higher on screen when in air
            visual_y = ball.position.y - ball.height

        pos = (int(ball.position.x), int(visual_y))

        # Scale ball size based on height (appears larger when higher/closer)
        scale = ball.get_visual_scale()
        radius = int(BALL_RADIUS * scale)

        # White ball
        pygame.draw.circle(self.screen, COLOR_BALL, pos, radius)

        # Black outline
        pygame.draw.circle(self.screen, COLOR_BALL_PATTERN, pos, radius, 2)

        # Simple pattern (inner circle)
        pygame.draw.circle(self.screen, COLOR_BALL_PATTERN, pos, max(1, radius // 2), 1)

        # Draw height indicator when aerial (dotted line to ground position)
        if ball.is_aerial and ball.height > 10:
            ground_pos = (int(ball.position.x), int(ball.position.y))
            self._draw_dotted_line(pos, ground_pos, (100, 100, 100))

    def _draw_dotted_line(self, start: Tuple[int, int], end: Tuple[int, int],
                           color: Tuple[int, int, int]) -> None:
        """Draw a dotted line between two points."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            return

        dot_spacing = 6
        num_dots = int(dist / dot_spacing)

        for i in range(num_dots):
            t = i / max(num_dots - 1, 1)
            x = int(start[0] + dx * t)
            y = int(start[1] + dy * t)
            pygame.draw.circle(self.screen, color, (x, y), 1)

    def _draw_teams(self, teams: List[Team]) -> None:
        """Draw all players from both teams."""
        for team in teams:
            for player in team.players:
                self._draw_player(player, team.color, team.secondary_color)

    def _draw_player(
        self,
        player: Player,
        color: Tuple[int, int, int],
        secondary: Tuple[int, int, int]
    ) -> None:
        """Draw a single player."""
        pos = (int(player.position.x), int(player.position.y))

        # Draw stun indicator (darker color when stunned)
        if player.is_stunned:
            color = tuple(max(0, c - 80) for c in color)

        # Main circle
        pygame.draw.circle(self.screen, color, pos, PLAYER_RADIUS)

        # Outline
        pygame.draw.circle(self.screen, secondary, pos, PLAYER_RADIUS, 2)

        # Direction indicator (small triangle/dot in facing direction)
        facing = player.get_facing_direction()
        indicator_pos = player.position + facing * (PLAYER_RADIUS + 4)
        pygame.draw.circle(
            self.screen, secondary,
            (int(indicator_pos.x), int(indicator_pos.y)),
            3
        )

        # Selected player indicator (yellow ring)
        if player.is_selected:
            pygame.draw.circle(self.screen, COLOR_SELECTED, pos, PLAYER_RADIUS + 5, 3)

        # Possession indicator (small ball icon above)
        if player.has_ball:
            ball_indicator_pos = (pos[0], pos[1] - PLAYER_RADIUS - 10)
            pygame.draw.circle(self.screen, COLOR_POSSESSION, ball_indicator_pos, 4)

        # Jersey number
        number_text = self.font_tiny.render(str(player.number), True, (255, 255, 255))
        number_rect = number_text.get_rect(center=pos)
        self.screen.blit(number_text, number_rect)

    def _draw_effects(self, teams: List[Team]) -> None:
        """Draw special effects (power bar, celebrations)."""
        for team in teams:
            for player in team.players:
                # Shot power bar
                if player.is_charging_shot:
                    self._draw_power_bar(player)

                # Celebration
                if player.is_celebrating:
                    self._draw_celebration(player)

    def _draw_power_bar(self, player: Player) -> None:
        """Draw shot charging power bar above player."""
        bar_width = 40
        bar_height = 6
        x = player.position.x - bar_width // 2
        y = player.position.y - PLAYER_RADIUS - 18

        # Background
        pygame.draw.rect(
            self.screen, COLOR_POWER_BAR_BG,
            (x, y, bar_width, bar_height)
        )

        # Fill based on power
        fill_width = int(bar_width * player.shot_power)

        # Color gradient based on power
        if player.shot_power < 0.4:
            color = COLOR_POWER_BAR_LOW
        elif player.shot_power < 0.75:
            color = COLOR_POWER_BAR_MED
        else:
            color = COLOR_POWER_BAR_HIGH

        pygame.draw.rect(
            self.screen, color,
            (x, y, fill_width, bar_height)
        )

        # Border
        pygame.draw.rect(
            self.screen, (255, 255, 255),
            (x, y, bar_width, bar_height), 1
        )

    def _draw_celebration(self, player: Player) -> None:
        """Draw celebration effect."""
        # Pulsing ring effect
        time_factor = player.celebration_timer * 8
        radius = PLAYER_RADIUS + 12 + math.sin(time_factor) * 6

        pygame.draw.circle(
            self.screen, COLOR_CELEBRATION,
            (int(player.position.x), int(player.position.y)),
            int(radius), 3
        )

        # Sparkle effect (small dots around player)
        for i in range(8):
            angle = time_factor + i * (math.pi / 4)
            sparkle_dist = radius + 5
            sparkle_x = player.position.x + math.cos(angle) * sparkle_dist
            sparkle_y = player.position.y + math.sin(angle) * sparkle_dist
            pygame.draw.circle(
                self.screen, COLOR_CELEBRATION,
                (int(sparkle_x), int(sparkle_y)), 2
            )

    def _draw_hud(self, score: dict, match_timer: float, teams: List[Team]) -> None:
        """Draw heads-up display (score, timer)."""
        # Scoreboard background
        scoreboard_width = 180
        scoreboard_height = 60
        scoreboard_x = SCREEN_WIDTH // 2 - scoreboard_width // 2
        scoreboard_y = 8

        # Background with rounded corners
        scoreboard_rect = pygame.Rect(scoreboard_x, scoreboard_y, scoreboard_width, scoreboard_height)
        pygame.draw.rect(self.screen, COLOR_HUD_BACKGROUND, scoreboard_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PITCH_LINES, scoreboard_rect, 2, border_radius=8)

        # Team colors indicators
        home_color = teams[0].color
        away_color = teams[1].color

        pygame.draw.rect(
            self.screen, home_color,
            (scoreboard_x + 15, scoreboard_y + 12, 25, 25),
            border_radius=4
        )
        pygame.draw.rect(
            self.screen, away_color,
            (scoreboard_x + scoreboard_width - 40, scoreboard_y + 12, 25, 25),
            border_radius=4
        )

        # Score text
        score_text = f"{score['home']}  -  {score['away']}"
        text_surface = self.font_large.render(score_text, True, COLOR_HUD_TEXT)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, scoreboard_y + 25))
        self.screen.blit(text_surface, text_rect)

        # Timer
        minutes = int(match_timer // 60)
        seconds = int(match_timer % 60)
        timer_text = f"{minutes:02d}:{seconds:02d}"
        timer_surface = self.font_medium.render(timer_text, True, COLOR_HUD_TEXT)
        timer_rect = timer_surface.get_rect(center=(SCREEN_WIDTH // 2, scoreboard_y + 48))
        self.screen.blit(timer_surface, timer_rect)

        # Controls hint (bottom of screen)
        controls_text = "Arrows: Move | D: Shoot | S+Dir: Pass | W: Through | A: Lob | Tab: Switch | R: Reset"
        controls_surface = self.font_tiny.render(controls_text, True, (150, 150, 150))
        controls_rect = controls_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 12))
        self.screen.blit(controls_surface, controls_rect)

    def _draw_message(self, message: str) -> None:
        """Draw centered game state message."""
        # Background
        text_surface = self.font_large.render(message, True, COLOR_HUD_TEXT)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

        # Background box
        padding = 25
        bg_rect = text_rect.inflate(padding * 2, padding)
        pygame.draw.rect(self.screen, COLOR_HUD_BACKGROUND, bg_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_CELEBRATION, bg_rect, 3, border_radius=12)

        # Text
        self.screen.blit(text_surface, text_rect)

    def draw_winner_screen(self, score: dict, teams: List[Team]) -> None:
        """Draw end-of-match winner screen."""
        # Darken background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Determine winner
        if score['home'] > score['away']:
            winner_text = "RED TEAM WINS!"
            winner_color = teams[0].color
        elif score['away'] > score['home']:
            winner_text = "BLUE TEAM WINS!"
            winner_color = teams[1].color
        else:
            winner_text = "IT'S A DRAW!"
            winner_color = COLOR_HUD_TEXT

        # Winner text
        winner_surface = self.font_large.render(winner_text, True, winner_color)
        winner_rect = winner_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
        self.screen.blit(winner_surface, winner_rect)

        # Final score
        score_text = f"Final Score: {score['home']} - {score['away']}"
        score_surface = self.font_medium.render(score_text, True, COLOR_HUD_TEXT)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(score_surface, score_rect)

        # Restart instruction
        restart_text = "Press R to Play Again"
        restart_surface = self.font_small.render(restart_text, True, (180, 180, 180))
        restart_rect = restart_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
        self.screen.blit(restart_surface, restart_rect)

        pygame.display.flip()
