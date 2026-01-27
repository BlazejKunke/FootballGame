"""
Player entity with movement, shooting, passing, and tackling mechanics.
"""

from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
import math
import pygame

from ..constants import (
    PLAYER_RADIUS, PLAYER_MAX_SPEED, PLAYER_ACCELERATION, PLAYER_FRICTION,
    SHOT_POWER_MIN, SHOT_POWER_MAX, SHOT_CHARGE_RATE, SHOT_CHARGE_MAX,
    SHOT_INACCURACY, PASS_SPEED, PASS_LEAD_FACTOR,
    TACKLE_RANGE, TACKLE_SUCCESS_CHANCE, TACKLE_COOLDOWN, TACKLE_STUN_TIME,
    POSSESSION_OFFSET
)

if TYPE_CHECKING:
    from .team import Team
    from .ball import Ball


class PlayerRole(Enum):
    """Player position/role on the field."""
    GOALKEEPER = auto()
    DEFENDER = auto()
    MIDFIELDER = auto()
    STRIKER = auto()


class Player:
    """Individual football player with movement and actions."""

    def __init__(
        self,
        team: 'Team',
        role: PlayerRole,
        number: int,
        position: pygame.Vector2,
        home_position: pygame.Vector2
    ):
        self.team = team
        self.role = role
        self.number = number

        # Position and movement
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 0)
        self.home_position = pygame.Vector2(home_position)  # Formation position

        # Physics properties
        self.radius = PLAYER_RADIUS
        self.max_speed = PLAYER_MAX_SPEED
        self.acceleration = PLAYER_ACCELERATION
        self.friction = PLAYER_FRICTION

        # Facing direction (normalized, defaults to team's attacking direction)
        self._facing = pygame.Vector2(1, 0)

        # State flags
        self.has_ball = False
        self.is_selected = False
        self.is_stunned = False
        self.stun_timer = 0.0

        # Tackling
        self.tackle_cooldown = 0.0

        # Shooting
        self.is_charging_shot = False
        self.shot_power = 0.0

        # Celebration
        self.is_celebrating = False
        self.celebration_timer = 0.0

        # AI movement target (used by AI controller)
        self.ai_target: Optional[pygame.Vector2] = None
        self.ai_action: Optional[tuple] = None

    def update(self, dt: float) -> None:
        """Update player state each frame."""
        # Update timers
        if self.stun_timer > 0:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.is_stunned = False

        if self.tackle_cooldown > 0:
            self.tackle_cooldown -= dt

        if self.is_celebrating:
            self.celebration_timer -= dt
            if self.celebration_timer <= 0:
                self.is_celebrating = False

        # Update shot charging
        if self.is_charging_shot:
            self.shot_power = min(self.shot_power + SHOT_CHARGE_RATE * dt, SHOT_CHARGE_MAX)

        # Apply friction when not actively moving
        if self.velocity.length() > 0:
            friction_amount = self.friction * dt
            if self.velocity.length() <= friction_amount:
                self.velocity = pygame.Vector2(0, 0)
            else:
                self.velocity -= self.velocity.normalize() * friction_amount

        # Update position
        self.position += self.velocity * dt

        # Update facing direction based on velocity
        if self.velocity.length() > 10:
            self._facing = self.velocity.normalize()

    def move(self, direction: pygame.Vector2) -> None:
        """Apply acceleration in given direction."""
        if self.is_stunned:
            return

        if direction.length() > 0:
            # Normalize direction
            direction = direction.normalize()

            # Apply acceleration
            self.velocity += direction * self.acceleration * (1/60)  # Assuming fixed timestep

            # Cap speed
            if self.velocity.length() > self.max_speed:
                self.velocity = self.velocity.normalize() * self.max_speed

            # Update facing
            self._facing = direction

    def start_charging_shot(self) -> None:
        """Begin charging a shot."""
        if self.is_stunned or not self.has_ball:
            return
        self.is_charging_shot = True
        self.shot_power = 0.0

    def release_shot(self, ball: 'Ball', target: Optional[pygame.Vector2] = None) -> None:
        """Release shot toward target or facing direction."""
        if not self.is_charging_shot:
            return

        self.is_charging_shot = False

        if not self.has_ball:
            self.shot_power = 0.0
            return

        # Calculate direction
        if target:
            direction = (target - self.position)
        else:
            direction = self._facing

        if direction.length() > 0:
            direction = direction.normalize()
        else:
            direction = self._facing

        # Add some inaccuracy based on power
        angle = math.atan2(direction.y, direction.x)
        inaccuracy = (SHOT_INACCURACY * self.shot_power) * (2 * (hash((self.number, ball.position.x)) % 100) / 100 - 1)
        angle += inaccuracy
        direction = pygame.Vector2(math.cos(angle), math.sin(angle))

        # Calculate power
        power = SHOT_POWER_MIN + (SHOT_POWER_MAX - SHOT_POWER_MIN) * self.shot_power

        # Release ball and apply kick
        ball.release()
        ball.kick(direction, power)

        self.shot_power = 0.0

    def pass_ball(self, ball: 'Ball', teammate: 'Player') -> None:
        """Pass to teammate with slight lead."""
        if self.is_stunned or not self.has_ball:
            return

        # Calculate pass target with lead
        target = teammate.position + teammate.velocity * PASS_LEAD_FACTOR
        direction = target - self.position

        if direction.length() > 0:
            direction = direction.normalize()

        # Release and kick
        ball.release()
        ball.kick(direction, PASS_SPEED)

        # Stop any charging
        self.is_charging_shot = False
        self.shot_power = 0.0

    def attempt_tackle(self, opponent: 'Player', ball: 'Ball') -> bool:
        """
        Attempt to tackle and steal the ball.
        Returns True if successful.
        """
        if self.is_stunned or self.tackle_cooldown > 0:
            return False

        # Check range
        dist = (self.position - opponent.position).length()
        if dist > TACKLE_RANGE:
            return False

        # Must be tackling opponent with ball
        if not opponent.has_ball:
            return False

        # Start cooldown
        self.tackle_cooldown = TACKLE_COOLDOWN

        # Calculate success chance
        success = TACKLE_SUCCESS_CHANCE

        # Modifier based on approach angle
        approach = self.position - opponent.position
        if approach.length() > 0 and opponent._facing.length() > 0:
            dot = approach.normalize().dot(opponent._facing)
            # Front tackle is easier
            if dot > 0.5:  # From front
                success += 0.1
            elif dot < -0.5:  # From behind
                success -= 0.1

        # Modifier based on opponent speed
        if opponent.velocity.length() > PLAYER_MAX_SPEED * 0.7:
            success -= 0.1

        # Deterministic outcome based on positions (seeded randomness)
        seed_value = int(self.position.x * 100 + self.position.y + opponent.position.x)
        outcome = (seed_value % 100) / 100.0

        if outcome < success:
            # Success - knock ball loose
            ball.release()

            # Push ball toward tackler
            push_dir = (self.position - opponent.position)
            if push_dir.length() > 0:
                push_dir = push_dir.normalize()
            ball.velocity = push_dir * 60

            # Brief stun on opponent
            opponent.stun(TACKLE_STUN_TIME * 0.5)
            return True
        else:
            # Failed - tackler gets stunned
            self.stun(TACKLE_STUN_TIME)
            return False

    def stun(self, duration: float) -> None:
        """Apply stun effect."""
        self.is_stunned = True
        self.stun_timer = duration
        self.velocity *= 0.3  # Slow down on stun

    def celebrate(self) -> None:
        """Start celebration animation."""
        self.is_celebrating = True
        self.celebration_timer = 2.0

    def get_facing_direction(self) -> pygame.Vector2:
        """Return current facing direction (normalized)."""
        return pygame.Vector2(self._facing)

    def set_facing(self, direction: pygame.Vector2) -> None:
        """Set facing direction."""
        if direction.length() > 0:
            self._facing = direction.normalize()

    def reset_to_home(self) -> None:
        """Reset player to formation position."""
        self.position = pygame.Vector2(self.home_position)
        self.velocity = pygame.Vector2(0, 0)
        self.has_ball = False
        self.is_stunned = False
        self.stun_timer = 0.0
        self.is_charging_shot = False
        self.shot_power = 0.0
        self.tackle_cooldown = 0.0
        self.ai_target = None
        self.ai_action = None

    def distance_to(self, other: 'Player') -> float:
        """Distance to another player."""
        return (self.position - other.position).length()

    def distance_to_point(self, point: pygame.Vector2) -> float:
        """Distance to a point."""
        return (self.position - point).length()
