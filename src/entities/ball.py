"""
Ball entity with physics, bouncing, and ownership mechanics.
"""

from typing import TYPE_CHECKING, Optional, List
import pygame

from ..constants import (
    BALL_RADIUS, BALL_MAX_SPEED, BALL_FRICTION, BALL_BOUNCE_DAMPING,
    BALL_MIN_SPEED, POSSESSION_DISTANCE, POSSESSION_SPEED, POSSESSION_OFFSET
)

if TYPE_CHECKING:
    from .player import Player


class Ball:
    """The football with physics and ownership tracking."""

    def __init__(self, position: pygame.Vector2):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 0)
        self.radius = BALL_RADIUS

        # Physics properties
        self.max_speed = BALL_MAX_SPEED
        self.friction = BALL_FRICTION
        self.bounce_damping = BALL_BOUNCE_DAMPING

        # Ownership
        self.owner: Optional['Player'] = None
        self.last_owner: Optional['Player'] = None
        self.last_touch_team: Optional[str] = None  # 'home' or 'away'

    def update(self, dt: float) -> None:
        """Update ball physics."""
        if self.owner:
            # Ball follows owner
            self._follow_owner()
            return

        # Apply velocity
        self.position += self.velocity * dt

        # Apply friction
        if self.velocity.length() > 0:
            friction_force = self.friction * dt
            current_speed = self.velocity.length()

            if current_speed <= friction_force:
                self.velocity = pygame.Vector2(0, 0)
            else:
                self.velocity -= self.velocity.normalize() * friction_force

        # Stop if very slow
        if self.velocity.length() < BALL_MIN_SPEED:
            self.velocity = pygame.Vector2(0, 0)

        # Cap speed
        if self.velocity.length() > self.max_speed:
            self.velocity = self.velocity.normalize() * self.max_speed

    def _follow_owner(self) -> None:
        """Position ball in front of owning player."""
        if self.owner:
            facing = self.owner.get_facing_direction()
            self.position = self.owner.position + facing * POSSESSION_OFFSET
            self.velocity = pygame.Vector2(0, 0)

    def kick(self, direction: pygame.Vector2, power: float) -> None:
        """Apply kick impulse in given direction."""
        if direction.length() > 0:
            direction = direction.normalize()
        else:
            direction = pygame.Vector2(1, 0)

        self.velocity = direction * power

        # Cap speed
        if self.velocity.length() > self.max_speed:
            self.velocity = self.velocity.normalize() * self.max_speed

    def bounce(self, normal: pygame.Vector2) -> None:
        """Reflect velocity off surface with normal vector."""
        if normal.length() == 0:
            return

        normal = normal.normalize()

        # Reflect: v' = v - 2(v . n)n
        dot = self.velocity.dot(normal)

        # Only bounce if moving into the surface
        if dot < 0:
            self.velocity = self.velocity - 2 * dot * normal
            self.velocity *= self.bounce_damping

    def check_ownership(self, players: List['Player']) -> None:
        """Determine ball ownership based on proximity and speed."""
        # If ball is moving fast, can't be possessed
        if self.velocity.length() > POSSESSION_SPEED:
            return

        # If already owned, check if owner is still close enough
        if self.owner:
            dist = (self.position - self.owner.position).length()
            # Slightly larger distance to keep possession
            if dist <= POSSESSION_DISTANCE * 1.3:
                return  # Keep current owner
            else:
                self.release()

        # Find closest player within possession range
        closest_player = None
        closest_distance = float('inf')

        for player in players:
            if player.is_stunned:
                continue

            dist = (self.position - player.position).length()

            if dist < POSSESSION_DISTANCE and dist < closest_distance:
                closest_distance = dist
                closest_player = player

        # Transfer ownership
        if closest_player:
            self.attach_to(closest_player)

    def attach_to(self, player: 'Player') -> None:
        """Transfer possession to player."""
        if self.owner and self.owner != player:
            self.owner.has_ball = False

        self.owner = player
        self.last_owner = player
        self.last_touch_team = 'home' if player.team.is_player_controlled else 'away'
        player.has_ball = True
        self.velocity = pygame.Vector2(0, 0)

    def release(self) -> None:
        """Release ball from owner's control."""
        if self.owner:
            self.last_owner = self.owner
            self.owner.has_ball = False
            self.owner = None

    def is_loose(self) -> bool:
        """Return True if no one owns the ball."""
        return self.owner is None

    def reset(self, position: pygame.Vector2) -> None:
        """Reset ball to given position."""
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 0)
        self.release()

    def get_speed(self) -> float:
        """Return current speed."""
        return self.velocity.length()
