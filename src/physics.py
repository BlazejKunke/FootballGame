"""
Physics engine for collision detection and resolution.
"""

from typing import List
import pygame

from .entities.player import Player
from .entities.ball import Ball
from .pitch import Pitch
from .constants import PLAYER_RADIUS, BALL_RADIUS


class PhysicsEngine:
    """Handles all collision detection and physics updates."""

    def __init__(self, pitch: Pitch):
        self.pitch = pitch

    def update(self, dt: float, ball: Ball, players: List[Player]) -> None:
        """Run physics update for all entities."""
        # Update ball physics
        ball.update(dt)

        # Update player physics (movement is handled by update)
        for player in players:
            player.update(dt)

        # Handle collisions
        self._handle_ball_boundaries(ball)
        self._handle_ball_posts(ball)
        self._handle_player_boundaries(players)
        self._handle_player_collisions(players)

        # Check ball ownership
        ball.check_ownership(players)

    def _handle_ball_boundaries(self, ball: Ball) -> None:
        """Handle ball bouncing off pitch boundaries."""
        if ball.owner:
            return  # Ball follows owner, no boundary collision

        bounds = self.pitch.boundary_rect

        # Left boundary (check if not in goal opening)
        if ball.position.x - ball.radius < bounds.left:
            if not self._ball_in_goal_opening(ball, 'left'):
                ball.position.x = bounds.left + ball.radius
                ball.bounce(pygame.Vector2(1, 0))

        # Right boundary
        if ball.position.x + ball.radius > bounds.right:
            if not self._ball_in_goal_opening(ball, 'right'):
                ball.position.x = bounds.right - ball.radius
                ball.bounce(pygame.Vector2(-1, 0))

        # Top boundary
        if ball.position.y - ball.radius < bounds.top:
            ball.position.y = bounds.top + ball.radius
            ball.bounce(pygame.Vector2(0, 1))

        # Bottom boundary
        if ball.position.y + ball.radius > bounds.bottom:
            ball.position.y = bounds.bottom - ball.radius
            ball.bounce(pygame.Vector2(0, -1))

    def _ball_in_goal_opening(self, ball: Ball, side: str) -> bool:
        """Check if ball is within goal opening."""
        goal = self.pitch.goal_left if side == 'left' else self.pitch.goal_right
        return goal.top_post.y < ball.position.y < goal.bottom_post.y

    def _handle_ball_posts(self, ball: Ball) -> None:
        """Handle ball collision with goal posts."""
        if ball.owner:
            return

        for goal in [self.pitch.goal_left, self.pitch.goal_right]:
            normal, overlap = goal.get_post_overlap(ball.position, ball.radius)
            if normal and overlap > 0:
                # Push ball out
                ball.position += normal * overlap
                ball.bounce(normal)

    def _handle_player_boundaries(self, players: List[Player]) -> None:
        """Keep players within pitch bounds."""
        bounds = self.pitch.boundary_rect

        for player in players:
            # Clamp to bounds
            player.position.x = max(bounds.left + PLAYER_RADIUS,
                                   min(bounds.right - PLAYER_RADIUS, player.position.x))
            player.position.y = max(bounds.top + PLAYER_RADIUS,
                                   min(bounds.bottom - PLAYER_RADIUS, player.position.y))

            # Zero out velocity component if at boundary
            if player.position.x <= bounds.left + PLAYER_RADIUS or \
               player.position.x >= bounds.right - PLAYER_RADIUS:
                player.velocity.x = 0

            if player.position.y <= bounds.top + PLAYER_RADIUS or \
               player.position.y >= bounds.bottom - PLAYER_RADIUS:
                player.velocity.y = 0

    def _handle_player_collisions(self, players: List[Player]) -> None:
        """Handle player-player collisions (soft push apart)."""
        for i, p1 in enumerate(players):
            for p2 in players[i + 1:]:
                self._resolve_player_collision(p1, p2)

    def _resolve_player_collision(self, p1: Player, p2: Player) -> None:
        """Resolve collision between two players."""
        diff = p1.position - p2.position
        dist = diff.length()
        min_dist = PLAYER_RADIUS * 2

        if dist < min_dist and dist > 0:
            # Calculate overlap
            overlap = min_dist - dist
            normal = diff.normalize()

            # Push apart equally
            p1.position += normal * (overlap / 2)
            p2.position -= normal * (overlap / 2)

            # Reduce velocity in collision direction
            # This creates a "bumping" feel
            v1_normal = p1.velocity.dot(normal)
            v2_normal = p2.velocity.dot(normal)

            # Simple elastic collision (equal mass)
            p1.velocity -= normal * v1_normal * 0.5
            p2.velocity -= normal * v2_normal * 0.5

            # Exchange some momentum
            p1.velocity += normal * v2_normal * 0.3
            p2.velocity += normal * v1_normal * 0.3

    def check_tackle_opportunity(self, tackler: Player, ball_carrier: Player, ball: Ball) -> bool:
        """
        Check if tackle is possible and execute it.
        Returns True if tackle happened (success or fail).
        """
        if not ball_carrier.has_ball:
            return False

        dist = (tackler.position - ball_carrier.position).length()
        if dist > PLAYER_RADIUS * 2.5:  # Too far
            return False

        # Execute tackle attempt
        return tackler.attempt_tackle(ball_carrier, ball)

    def get_closest_opponent_to_ball(
        self,
        ball: Ball,
        team_players: List[Player],
        opponent_players: List[Player]
    ) -> tuple:
        """
        Find closest opponent to ball carrier (if any).
        Returns (closest_opponent, distance) or (None, inf).
        """
        ball_carrier = None
        for p in team_players:
            if p.has_ball:
                ball_carrier = p
                break

        if not ball_carrier:
            return None, float('inf')

        closest = None
        closest_dist = float('inf')

        for opponent in opponent_players:
            dist = (opponent.position - ball_carrier.position).length()
            if dist < closest_dist:
                closest_dist = dist
                closest = opponent

        return closest, closest_dist
