"""
Team class managing a group of players with formation.
"""

from typing import List, Optional, Tuple
import pygame

from .player import Player, PlayerRole
from ..constants import (
    FORMATION_4V4, PITCH_WIDTH, PITCH_HEIGHT, PITCH_MARGIN_X, PITCH_MARGIN_Y
)


class Team:
    """A team of 4 players with formation and selection logic."""

    def __init__(
        self,
        name: str,
        color: Tuple[int, int, int],
        secondary_color: Tuple[int, int, int],
        attacking_direction: int,  # 1 = right, -1 = left
        is_player_controlled: bool
    ):
        self.name = name
        self.color = color
        self.secondary_color = secondary_color
        self.attacking_direction = attacking_direction
        self.is_player_controlled = is_player_controlled

        self.players: List[Player] = []
        self.goalkeeper: Optional[Player] = None
        self.selected_player: Optional[Player] = None

    def create_players(self) -> None:
        """Create all players in formation positions."""
        roles = [
            (PlayerRole.GOALKEEPER, 1),
            (PlayerRole.DEFENDER, 2),
            (PlayerRole.MIDFIELDER, 3),
            (PlayerRole.STRIKER, 4),
        ]

        for role, number in roles:
            position, home_position = self._get_formation_position(role)

            player = Player(
                team=self,
                role=role,
                number=number,
                position=position,
                home_position=home_position
            )

            # Set initial facing direction based on attacking direction
            player.set_facing(pygame.Vector2(self.attacking_direction, 0))

            self.players.append(player)

            if role == PlayerRole.GOALKEEPER:
                self.goalkeeper = player

        # Select striker by default for player-controlled team
        if self.is_player_controlled:
            for player in self.players:
                if player.role == PlayerRole.STRIKER:
                    self.selected_player = player
                    player.is_selected = True
                    break

    def _get_formation_position(self, role: PlayerRole) -> Tuple[pygame.Vector2, pygame.Vector2]:
        """
        Calculate world position from formation data.
        Returns (position, home_position) - both are the same initially.
        """
        role_name = role.name
        x_frac, y_frac = FORMATION_4V4[role_name]

        # Calculate position on pitch
        # For team attacking right (direction=1): x goes from left edge
        # For team attacking left (direction=-1): x goes from right edge, mirrored

        half_width = PITCH_WIDTH / 2

        if self.attacking_direction == 1:
            # Attacking right: positions are from left half
            x = PITCH_MARGIN_X + x_frac * half_width
        else:
            # Attacking left: positions are from right half, mirrored
            x = PITCH_MARGIN_X + PITCH_WIDTH - x_frac * half_width

        y = PITCH_MARGIN_Y + y_frac * PITCH_HEIGHT

        position = pygame.Vector2(x, y)
        return position, pygame.Vector2(position)

    def get_closest_player_to(self, point: pygame.Vector2) -> Player:
        """Find player nearest to given point."""
        closest = self.players[0]
        closest_dist = float('inf')

        for player in self.players:
            dist = (player.position - point).length()
            if dist < closest_dist:
                closest_dist = dist
                closest = player

        return closest

    def get_closest_player_to_ball(self, ball_pos: pygame.Vector2, exclude_gk: bool = False) -> Player:
        """Find player nearest to ball, optionally excluding goalkeeper."""
        closest = None
        closest_dist = float('inf')

        for player in self.players:
            if exclude_gk and player.role == PlayerRole.GOALKEEPER:
                continue

            dist = (player.position - ball_pos).length()
            if dist < closest_dist:
                closest_dist = dist
                closest = player

        return closest or self.players[0]

    def get_player_with_ball(self) -> Optional[Player]:
        """Return player currently possessing ball, or None."""
        for player in self.players:
            if player.has_ball:
                return player
        return None

    def select_player(self, player: Player) -> None:
        """Select a specific player."""
        if not self.is_player_controlled:
            return

        # Deselect current
        if self.selected_player:
            self.selected_player.is_selected = False

        # Select new
        self.selected_player = player
        player.is_selected = True

    def select_closest_to_ball(self, ball_pos: pygame.Vector2) -> Player:
        """Select and return player closest to ball."""
        closest = self.get_closest_player_to_ball(ball_pos, exclude_gk=True)
        self.select_player(closest)
        return closest

    def cycle_selection(self, ball_pos: pygame.Vector2) -> Player:
        """
        Switch to next best player to control.
        Prioritizes player closest to ball who isn't currently selected.
        """
        if not self.is_player_controlled:
            return self.players[0]

        # Get players sorted by distance to ball (excluding GK)
        field_players = [p for p in self.players if p.role != PlayerRole.GOALKEEPER]
        field_players.sort(key=lambda p: (p.position - ball_pos).length())

        # Find next player that isn't currently selected
        for player in field_players:
            if player != self.selected_player:
                self.select_player(player)
                return player

        # If all are the same, just return current
        return self.selected_player or field_players[0]

    def get_teammates(self, player: Player) -> List[Player]:
        """Return list of other players on team."""
        return [p for p in self.players if p != player]

    def get_open_teammate(self, player: Player, opponents: List[Player]) -> Optional[Player]:
        """Find a teammate who is relatively open (not closely marked)."""
        best_teammate = None
        best_score = -1

        for teammate in self.get_teammates(player):
            if teammate.role == PlayerRole.GOALKEEPER:
                continue  # Don't pass back to GK unless desperate

            # Calculate how "open" this teammate is
            min_defender_dist = float('inf')
            for opponent in opponents:
                dist = (teammate.position - opponent.position).length()
                min_defender_dist = min(min_defender_dist, dist)

            # Score based on openness and forward position
            openness_score = min(min_defender_dist / 100, 1.0)

            # Bonus for being ahead of ball carrier
            if self.attacking_direction == 1:
                forward_bonus = 0.2 if teammate.position.x > player.position.x else 0
            else:
                forward_bonus = 0.2 if teammate.position.x < player.position.x else 0

            score = openness_score + forward_bonus

            if score > best_score:
                best_score = score
                best_teammate = teammate

        return best_teammate if best_score > 0.3 else None

    def reset_formation(self) -> None:
        """Move all players back to starting positions."""
        for player in self.players:
            player.reset_to_home()

    def update(self, dt: float) -> None:
        """Update all players."""
        for player in self.players:
            player.update(dt)

    def has_ball(self) -> bool:
        """Return True if any player on team has the ball."""
        return any(p.has_ball for p in self.players)
