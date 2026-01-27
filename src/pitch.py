"""
Pitch and Goal classes for field boundaries and goal detection.
"""

from typing import Optional, Tuple
import pygame

from .constants import (
    PITCH_WIDTH, PITCH_HEIGHT, PITCH_MARGIN_X, PITCH_MARGIN_Y,
    GOAL_WIDTH, GOAL_DEPTH, GOAL_POST_RADIUS,
    CENTER_CIRCLE_RADIUS, PENALTY_AREA_WIDTH, PENALTY_AREA_HEIGHT,
    BALL_RADIUS
)


class Goal:
    """A goal with posts and scoring detection."""

    def __init__(self, side: str, pitch_rect: pygame.Rect):
        """
        Create a goal on the given side.
        side: 'left' or 'right'
        """
        self.side = side
        self.width = GOAL_WIDTH  # Vertical opening
        self.depth = GOAL_DEPTH  # Horizontal depth
        self.post_radius = GOAL_POST_RADIUS

        # Calculate positions
        pitch_center_y = pitch_rect.centery

        if side == 'left':
            self.line_x = pitch_rect.left
            self.back_x = self.line_x - self.depth
        else:
            self.line_x = pitch_rect.right
            self.back_x = self.line_x + self.depth

        # Goal posts (top and bottom)
        self.top_post = pygame.Vector2(self.line_x, pitch_center_y - self.width // 2)
        self.bottom_post = pygame.Vector2(self.line_x, pitch_center_y + self.width // 2)

        # Goal center
        self.center = pygame.Vector2(self.line_x, pitch_center_y)

        # Scoring area (rectangle inside the goal)
        if side == 'left':
            self.scoring_rect = pygame.Rect(
                self.back_x,
                pitch_center_y - self.width // 2,
                self.depth,
                self.width
            )
        else:
            self.scoring_rect = pygame.Rect(
                self.line_x,
                pitch_center_y - self.width // 2,
                self.depth,
                self.width
            )

    def is_goal(self, ball_pos: pygame.Vector2, ball_radius: float) -> bool:
        """Check if ball has crossed into goal."""
        # Ball center must be within scoring rect
        # For left goal, ball.x must be less than line_x
        # For right goal, ball.x must be greater than line_x

        if self.side == 'left':
            if ball_pos.x - ball_radius < self.line_x:
                # Check if within goal height
                if self.top_post.y < ball_pos.y < self.bottom_post.y:
                    return True
        else:
            if ball_pos.x + ball_radius > self.line_x:
                # Check if within goal height
                if self.top_post.y < ball_pos.y < self.bottom_post.y:
                    return True

        return False

    def check_post_collision(self, ball_pos: pygame.Vector2, ball_radius: float) -> Optional[pygame.Vector2]:
        """
        Check collision with goal posts.
        Returns normal vector if colliding, None otherwise.
        """
        for post in [self.top_post, self.bottom_post]:
            dist = (ball_pos - post).length()
            if dist < ball_radius + self.post_radius:
                # Collision! Return normal pointing away from post
                if dist > 0:
                    return (ball_pos - post).normalize()
                else:
                    return pygame.Vector2(1, 0)  # Default direction

        return None

    def get_post_overlap(self, ball_pos: pygame.Vector2, ball_radius: float) -> Tuple[Optional[pygame.Vector2], float]:
        """
        Check collision and return (normal, overlap) if colliding.
        """
        for post in [self.top_post, self.bottom_post]:
            dist = (ball_pos - post).length()
            min_dist = ball_radius + self.post_radius
            if dist < min_dist:
                overlap = min_dist - dist
                if dist > 0:
                    normal = (ball_pos - post).normalize()
                else:
                    normal = pygame.Vector2(1, 0)
                return normal, overlap

        return None, 0


class Pitch:
    """The football field with boundaries, center, and goals."""

    def __init__(self):
        self.width = PITCH_WIDTH
        self.height = PITCH_HEIGHT
        self.margin_x = PITCH_MARGIN_X
        self.margin_y = PITCH_MARGIN_Y

        # Main boundary rectangle
        self.boundary_rect = pygame.Rect(
            self.margin_x,
            self.margin_y,
            self.width,
            self.height
        )

        # Center point
        self.center = pygame.Vector2(
            self.margin_x + self.width // 2,
            self.margin_y + self.height // 2
        )

        # Center circle
        self.center_circle_radius = CENTER_CIRCLE_RADIUS

        # Halfway line x position
        self.halfway_x = self.center.x

        # Goals
        self.goal_left = Goal('left', self.boundary_rect)
        self.goal_right = Goal('right', self.boundary_rect)

        # Penalty areas
        self.penalty_area_left = pygame.Rect(
            self.boundary_rect.left,
            self.center.y - PENALTY_AREA_HEIGHT // 2,
            PENALTY_AREA_WIDTH,
            PENALTY_AREA_HEIGHT
        )

        self.penalty_area_right = pygame.Rect(
            self.boundary_rect.right - PENALTY_AREA_WIDTH,
            self.center.y - PENALTY_AREA_HEIGHT // 2,
            PENALTY_AREA_WIDTH,
            PENALTY_AREA_HEIGHT
        )

    def is_in_bounds(self, position: pygame.Vector2, radius: float = 0) -> bool:
        """Check if position (with radius) is within pitch bounds."""
        return (
            position.x - radius >= self.boundary_rect.left and
            position.x + radius <= self.boundary_rect.right and
            position.y - radius >= self.boundary_rect.top and
            position.y + radius <= self.boundary_rect.bottom
        )

    def clamp_to_bounds(self, position: pygame.Vector2, radius: float = 0) -> pygame.Vector2:
        """Clamp position to stay within bounds."""
        x = max(self.boundary_rect.left + radius,
                min(self.boundary_rect.right - radius, position.x))
        y = max(self.boundary_rect.top + radius,
                min(self.boundary_rect.bottom - radius, position.y))
        return pygame.Vector2(x, y)

    def get_boundary_collision(self, position: pygame.Vector2, radius: float) -> Optional[Tuple[str, pygame.Vector2]]:
        """
        Check if position hits a boundary.
        Returns (side, normal) if collision, None otherwise.
        side is 'left', 'right', 'top', or 'bottom'
        """
        bounds = self.boundary_rect

        # Check each boundary
        if position.x - radius < bounds.left:
            # Check if in goal area
            if not self._is_in_goal_opening(position, 'left'):
                return ('left', pygame.Vector2(1, 0))

        if position.x + radius > bounds.right:
            if not self._is_in_goal_opening(position, 'right'):
                return ('right', pygame.Vector2(-1, 0))

        if position.y - radius < bounds.top:
            return ('top', pygame.Vector2(0, 1))

        if position.y + radius > bounds.bottom:
            return ('bottom', pygame.Vector2(0, -1))

        return None

    def _is_in_goal_opening(self, position: pygame.Vector2, side: str) -> bool:
        """Check if position is within goal opening height."""
        goal = self.goal_left if side == 'left' else self.goal_right
        return goal.top_post.y < position.y < goal.bottom_post.y

    def check_goal(self, ball_pos: pygame.Vector2) -> Optional[str]:
        """
        Check if ball has scored.
        Returns 'left' or 'right' if goal scored, None otherwise.
        """
        if self.goal_left.is_goal(ball_pos, BALL_RADIUS):
            return 'left'
        if self.goal_right.is_goal(ball_pos, BALL_RADIUS):
            return 'right'
        return None

    def is_in_defensive_third(self, position: pygame.Vector2, attacking_direction: int) -> bool:
        """Check if position is in defensive third for given team."""
        third_width = self.width / 3

        if attacking_direction == 1:  # Attacking right
            return position.x < self.boundary_rect.left + third_width
        else:  # Attacking left
            return position.x > self.boundary_rect.right - third_width

    def is_in_attacking_third(self, position: pygame.Vector2, attacking_direction: int) -> bool:
        """Check if position is in attacking third for given team."""
        third_width = self.width / 3

        if attacking_direction == 1:  # Attacking right
            return position.x > self.boundary_rect.right - third_width
        else:  # Attacking left
            return position.x < self.boundary_rect.left + third_width

    def get_goal_center(self, side: str) -> pygame.Vector2:
        """Get center of goal on given side."""
        if side == 'left':
            return pygame.Vector2(self.goal_left.center)
        else:
            return pygame.Vector2(self.goal_right.center)
