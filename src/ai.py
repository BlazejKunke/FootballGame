"""
AI Controller with role-based behaviors and decision cooldowns.
"""

import math
import random
from typing import Optional, List
import pygame

from .entities.player import Player, PlayerRole
from .entities.ball import Ball
from .entities.team import Team
from .pitch import Pitch
from .constants import (
    AI_DECISION_COOLDOWN, AI_SMOOTHING_FACTOR,
    AI_CHASE_BALL_DISTANCE, AI_PASS_PREFERENCE, AI_SHOT_DISTANCE, AI_SHOT_ANGLE_MAX,
    AI_ZONE_DEFENSE_RADIUS, AI_STRIKER_PUSH_UP, AI_MIDFIELDER_SUPPORT,
    AI_GOALKEEPER_RANGE_X, AI_GOALKEEPER_RANGE_Y,
    AI_PRESSURE_DISTANCE, AI_OPEN_SPACE_THRESHOLD,
    AI_DRIBBLE_SPEED, AI_THROUGH_BALL_CHANCE, AI_ONE_TWO_CHANCE,
    PLAYER_MAX_SPEED, POSSESSION_DISTANCE, TACKLE_RANGE,
    SHOT_POWER_MIN, SHOT_POWER_MAX, PASS_SPEED, RANDOM_SEED,
    PITCH_WIDTH, PITCH_HEIGHT
)


class AIController:
    """Controls AI team decision-making with role-based behaviors."""

    def __init__(self, team: Team, opponent_team: Team, ball: Ball, pitch: Pitch):
        self.team = team
        self.opponent_team = opponent_team
        self.ball = ball
        self.pitch = pitch

        # Decision cooldowns per player
        self.player_cooldowns: dict[Player, float] = {}
        for player in team.players:
            self.player_cooldowns[player] = 0.0

        # Random generator with seed for reproducibility
        self.rng = random.Random(RANDOM_SEED)

    def update(self, dt: float) -> None:
        """Update AI decisions for all players."""
        for player in self.team.players:
            # Update cooldown
            if player in self.player_cooldowns:
                self.player_cooldowns[player] = max(0, self.player_cooldowns[player] - dt)

            # Make decision if cooldown elapsed
            if self.player_cooldowns.get(player, 0) <= 0:
                self._make_decision(player)
                self.player_cooldowns[player] = AI_DECISION_COOLDOWN

            # Execute current action
            self._execute_action(player, dt)

    def _make_decision(self, player: Player) -> None:
        """Decide what action player should take."""
        if player.has_ball:
            self._decide_with_ball(player)
        elif self.ball.is_loose():
            self._decide_ball_loose(player)
        elif self.team.has_ball():
            self._decide_team_attacking(player)
        else:
            self._decide_team_defending(player)

    def _decide_with_ball(self, player: Player) -> None:
        """Decide action when player has ball - BE AGGRESSIVE!"""
        goal_center = self._get_opponent_goal_center()
        dist_to_goal = (player.position - goal_center).length()

        # PRIORITY 1: Always shoot if in good position!
        if self._should_shoot(player, goal_center, dist_to_goal):
            # Aim for corners of goal for better scoring chance
            target = self._get_shot_target(player, goal_center)
            power = self._calculate_shot_power(dist_to_goal)
            player.ai_action = ('shoot', target, power)
            return

        # PRIORITY 2: If very close to goal, always shoot!
        if dist_to_goal < 200:
            target = self._get_shot_target(player, goal_center)
            player.ai_action = ('shoot', target, 0.9)
            return

        # PRIORITY 3: Look for through ball to striker making a run
        if self.rng.random() < AI_THROUGH_BALL_CHANCE:
            through_target = self._get_through_ball_target(player)
            if through_target:
                player.ai_action = ('pass', through_target)
                return

        # PRIORITY 4: If under pressure, pass quickly
        if self._is_under_pressure(player):
            teammate = self._get_best_pass_target(player)
            if teammate:
                player.ai_action = ('pass', teammate)
                return
            # If no good pass, try to dribble out of pressure
            target = self._get_escape_dribble_target(player)
            player.ai_action = ('move', target)
            return

        # PRIORITY 5: Pass to better positioned teammate
        if self.rng.random() < AI_PASS_PREFERENCE:
            teammate = self._get_best_pass_target(player)
            if teammate and self._is_better_positioned(teammate, player, goal_center):
                player.ai_action = ('pass', teammate)
                return

        # PRIORITY 6: Dribble aggressively toward goal
        target = self._get_dribble_target(player, goal_center)
        player.ai_action = ('move', target)

    def _decide_ball_loose(self, player: Player) -> None:
        """Decide action when ball is loose - FIGHT FOR IT!"""
        ball_pos = self.ball.position
        dist_to_ball = (player.position - ball_pos).length()

        # Multiple players can chase if close enough
        if dist_to_ball < 150:  # Close to ball - definitely chase!
            player.ai_action = ('chase', ball_pos)
            return

        # Should this player chase based on role?
        should_chase = self._should_chase_ball(player)

        if should_chase:
            # Check if one of the closest to ball on team
            if self._is_among_closest_to_ball(player, 2):  # Top 2 closest can chase
                player.ai_action = ('chase', ball_pos)
                return

        # Move toward good position (but bias toward ball)
        target = self._get_positional_target(player)
        # Bias target toward ball
        ball_bias = (ball_pos - player.position) * 0.3
        target = target + ball_bias
        target = self.pitch.clamp_to_bounds(target, player.radius)
        player.ai_action = ('move', target)

    def _decide_team_attacking(self, player: Player) -> None:
        """Decide action when team has ball (but not this player)."""
        # Get attacking position
        target = self._get_attacking_position(player)
        player.ai_action = ('move', target)

    def _decide_team_defending(self, player: Player) -> None:
        """Decide action when opponent has ball."""
        ball_carrier = self.opponent_team.get_player_with_ball()

        # Goalkeeper behavior
        if player.role == PlayerRole.GOALKEEPER:
            target = self._get_goalkeeper_position(player)
            player.ai_action = ('move', target)
            return

        # Try to tackle if close to ball carrier
        if ball_carrier:
            dist = (player.position - ball_carrier.position).length()
            if dist < TACKLE_RANGE * 1.2:
                player.ai_action = ('tackle', ball_carrier)
                return

        # Move to defensive position
        target = self._get_defensive_position(player)
        player.ai_action = ('move', target)

    def _execute_action(self, player: Player, dt: float) -> None:
        """Execute the current AI action for player."""
        if not player.ai_action:
            return

        action_type = player.ai_action[0]

        if action_type == 'move':
            target = player.ai_action[1]
            self._move_toward(player, target, dt)

        elif action_type == 'chase':
            # Chase ball with prediction
            target = self._predict_ball_position()
            self._move_toward(player, target, dt)

        elif action_type == 'shoot':
            target = player.ai_action[1]
            power = player.ai_action[2]
            self._execute_shot(player, target, power)

        elif action_type == 'pass':
            teammate = player.ai_action[1]
            self._execute_pass(player, teammate)

        elif action_type == 'tackle':
            target_player = player.ai_action[1]
            self._move_toward(player, target_player.position, dt)

    def _move_toward(self, player: Player, target: pygame.Vector2, dt: float) -> None:
        """Move player toward target with smoothing."""
        direction = target - player.position
        dist = direction.length()

        if dist < 5:  # Close enough
            return

        direction = direction.normalize()

        # Apply smoothing to avoid jitter
        if player.velocity.length() > 0:
            current_dir = player.velocity.normalize()
            # Blend current direction with target direction
            direction = current_dir * AI_SMOOTHING_FACTOR + direction * (1 - AI_SMOOTHING_FACTOR)
            if direction.length() > 0:
                direction = direction.normalize()

        player.move(direction)

    def _execute_shot(self, player: Player, target: pygame.Vector2, power: float) -> None:
        """Execute a shot."""
        if not player.has_ball:
            return

        # Calculate direction with some randomness
        direction = target - player.position
        if direction.length() > 0:
            direction = direction.normalize()

        # Add slight inaccuracy
        angle = math.atan2(direction.y, direction.x)
        angle += (self.rng.random() - 0.5) * 0.2  # ±0.1 radians
        direction = pygame.Vector2(math.cos(angle), math.sin(angle))

        # Calculate actual power
        shot_power = SHOT_POWER_MIN + (SHOT_POWER_MAX - SHOT_POWER_MIN) * power

        self.ball.release()
        self.ball.kick(direction, shot_power)

        player.ai_action = None

    def _execute_pass(self, player: Player, teammate: Player) -> None:
        """Execute a pass to teammate."""
        if not player.has_ball:
            return

        player.pass_ball(self.ball, teammate)
        player.ai_action = None

    # =========================================================================
    # Helper methods for decision making
    # =========================================================================

    def _should_shoot(self, player: Player, goal_center: pygame.Vector2, dist: float) -> bool:
        """Determine if player should shoot - BE MORE AGGRESSIVE!"""
        if dist > AI_SHOT_DISTANCE:
            return False

        # Check angle to goal
        direction = goal_center - player.position
        if direction.length() == 0:
            return False

        # Calculate angle (how "straight" the shot is)
        angle = abs(math.atan2(direction.y, abs(direction.x)))

        if angle > AI_SHOT_ANGLE_MAX:
            return False

        # Count blockers - but don't be too cautious
        blockers = 0
        for opponent in self.opponent_team.players:
            if self._is_blocking_shot(player, opponent, goal_center):
                blockers += 1

        # Shoot anyway if close enough or few blockers
        if dist < 250:
            return blockers < 2  # Shoot if less than 2 blockers when close
        elif dist < 320:
            return blockers < 1  # Need clearer path for medium range
        else:
            return blockers == 0  # Need clear path for long range

    def _get_shot_target(self, player: Player, goal_center: pygame.Vector2) -> pygame.Vector2:
        """Get optimal shot target - aim for corners!"""
        # Find goalkeeper position
        gk = None
        for p in self.opponent_team.players:
            if p.role == PlayerRole.GOALKEEPER:
                gk = p
                break

        if gk:
            # Aim away from goalkeeper
            if gk.position.y > goal_center.y:
                # GK is low, aim high
                target_y = goal_center.y - 40
            else:
                # GK is high, aim low
                target_y = goal_center.y + 40
        else:
            # Random corner
            target_y = goal_center.y + (50 if self.rng.random() > 0.5 else -50)

        return pygame.Vector2(goal_center.x, target_y)

    def _get_through_ball_target(self, player: Player) -> Optional[Player]:
        """Find a teammate making a run for a through ball."""
        goal_center = self._get_opponent_goal_center()

        for teammate in self.team.get_teammates(player):
            if teammate.role == PlayerRole.GOALKEEPER:
                continue

            # Check if teammate is ahead of player and moving toward goal
            teammate_to_goal = (goal_center - teammate.position).length()
            player_to_goal = (goal_center - player.position).length()

            if teammate_to_goal < player_to_goal - 50:  # Teammate is ahead
                # Check if teammate is in good position
                if self._is_passing_lane_clear(player, teammate):
                    # Bonus if striker or attacking midfielder
                    if teammate.role in [PlayerRole.STRIKER, PlayerRole.MIDFIELDER]:
                        return teammate

        return None

    def _get_escape_dribble_target(self, player: Player) -> pygame.Vector2:
        """Find direction to escape pressure."""
        # Find the direction with least pressure
        best_direction = pygame.Vector2(0, 0)
        best_score = -1

        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            direction = pygame.Vector2(math.cos(rad), math.sin(rad))
            test_pos = player.position + direction * 80

            # Score based on distance from opponents
            min_dist = float('inf')
            for opponent in self.opponent_team.players:
                dist = (opponent.position - test_pos).length()
                min_dist = min(min_dist, dist)

            # Also prefer moving toward goal
            goal_center = self._get_opponent_goal_center()
            goal_bonus = 0
            if (test_pos - goal_center).length() < (player.position - goal_center).length():
                goal_bonus = 30

            score = min_dist + goal_bonus

            if score > best_score and self.pitch.is_in_bounds(test_pos, player.radius):
                best_score = score
                best_direction = direction

        return player.position + best_direction * AI_DRIBBLE_SPEED

    def _is_better_positioned(self, teammate: Player, player: Player, goal_center: pygame.Vector2) -> bool:
        """Check if teammate is in better position to attack."""
        teammate_dist = (teammate.position - goal_center).length()
        player_dist = (player.position - goal_center).length()

        # Teammate should be significantly closer to goal
        if teammate_dist < player_dist - 80:
            return True

        # Or teammate should be more central with good angle
        teammate_angle = abs(math.atan2(
            teammate.position.y - goal_center.y,
            abs(teammate.position.x - goal_center.x)
        ))
        player_angle = abs(math.atan2(
            player.position.y - goal_center.y,
            abs(player.position.x - goal_center.x)
        ))

        return teammate_angle < player_angle - 0.2 and teammate_dist < player_dist

    def _is_blocking_shot(self, shooter: Player, blocker: Player, target: pygame.Vector2) -> bool:
        """Check if blocker is in the way of shot."""
        # Simple check: is blocker between shooter and target?
        to_target = target - shooter.position
        to_blocker = blocker.position - shooter.position

        # Project blocker onto shot line
        if to_target.length() == 0:
            return False

        t = to_blocker.dot(to_target) / to_target.dot(to_target)

        if t < 0.1 or t > 0.9:  # Not between shooter and target
            return False

        # Check perpendicular distance
        closest_point = shooter.position + to_target * t
        dist = (blocker.position - closest_point).length()

        return dist < 40  # Within blocking range

    def _is_under_pressure(self, player: Player) -> bool:
        """Check if player is being pressured by opponents."""
        for opponent in self.opponent_team.players:
            dist = (opponent.position - player.position).length()
            if dist < AI_PRESSURE_DISTANCE:
                return True
        return False

    def _get_best_pass_target(self, player: Player) -> Optional[Player]:
        """Find best teammate to pass to."""
        best_target = None
        best_score = -1

        for teammate in self.team.get_teammates(player):
            if teammate.role == PlayerRole.GOALKEEPER:
                continue  # Avoid back passes to GK

            score = self._evaluate_pass_target(player, teammate)
            if score > best_score:
                best_score = score
                best_target = teammate

        return best_target if best_score > 0.2 else None

    def _evaluate_pass_target(self, passer: Player, receiver: Player) -> float:
        """Score a potential pass target (0-1)."""
        score = 0.5

        goal_center = self._get_opponent_goal_center()
        passer_dist = (passer.position - goal_center).length()
        receiver_dist = (receiver.position - goal_center).length()

        # Bonus for forward pass
        if receiver_dist < passer_dist:
            score += 0.2

        # Check if receiver is open
        min_defender_dist = float('inf')
        for opponent in self.opponent_team.players:
            dist = (receiver.position - opponent.position).length()
            min_defender_dist = min(min_defender_dist, dist)

        if min_defender_dist > AI_OPEN_SPACE_THRESHOLD:
            score += 0.2
        elif min_defender_dist < 40:
            score -= 0.3

        # Check passing lane
        if not self._is_passing_lane_clear(passer, receiver):
            score -= 0.25

        return max(0, min(1, score))

    def _is_passing_lane_clear(self, passer: Player, receiver: Player) -> bool:
        """Check if passing lane is relatively clear."""
        direction = receiver.position - passer.position
        dist = direction.length()

        if dist == 0:
            return True

        for opponent in self.opponent_team.players:
            to_opponent = opponent.position - passer.position

            # Project onto pass line
            t = to_opponent.dot(direction) / direction.dot(direction)

            if t < 0.1 or t > 0.9:
                continue

            closest = passer.position + direction * t
            perp_dist = (opponent.position - closest).length()

            if perp_dist < 35:
                return False

        return True

    def _calculate_shot_power(self, distance: float) -> float:
        """Calculate appropriate shot power based on distance."""
        # Normalize distance to 0-1 range
        normalized = min(distance / AI_SHOT_DISTANCE, 1.0)
        # Higher power for longer shots
        return 0.5 + normalized * 0.5

    def _get_dribble_target(self, player: Player, goal_center: pygame.Vector2) -> pygame.Vector2:
        """Get target position for dribbling - BE AGGRESSIVE!"""
        # Move toward goal aggressively
        direction = goal_center - player.position

        if direction.length() > 0:
            direction = direction.normalize()

        # Only avoid if defender is VERY close
        for opponent in self.opponent_team.players:
            to_opponent = opponent.position - player.position
            dist = to_opponent.length()

            if dist < 60 and dist > 0:  # Only avoid very close defenders
                # Try to go around them
                avoid = to_opponent.normalize() * -1
                # Add perpendicular component to go around
                perp = pygame.Vector2(-avoid.y, avoid.x)
                direction = direction + avoid * 0.2 + perp * 0.3
                if direction.length() > 0:
                    direction = direction.normalize()

        # More aggressive dribble distance
        return player.position + direction * AI_DRIBBLE_SPEED

    def _should_chase_ball(self, player: Player) -> bool:
        """Determine if this player should chase loose ball - BE AGGRESSIVE!"""
        ball_pos = self.ball.position
        dist = (player.position - ball_pos).length()

        if dist > AI_CHASE_BALL_DISTANCE:
            return False

        if player.role == PlayerRole.GOALKEEPER:
            # GK chases if ball in defensive area
            return self.pitch.is_in_defensive_third(ball_pos, self.team.attacking_direction) and dist < 120

        if player.role == PlayerRole.DEFENDER:
            # Defenders chase in defensive half or if close
            return self.pitch.is_in_defensive_third(ball_pos, self.team.attacking_direction) or dist < 180

        if player.role == PlayerRole.MIDFIELDER:
            return True  # Midfielders always contest

        if player.role == PlayerRole.STRIKER:
            # Strikers chase aggressively
            return dist < 250

        return True

    def _is_closest_to_ball(self, player: Player) -> bool:
        """Check if player is closest to ball on their team."""
        return self._is_among_closest_to_ball(player, 1)

    def _is_among_closest_to_ball(self, player: Player, n: int) -> bool:
        """Check if player is among the n closest to ball on their team."""
        ball_pos = self.ball.position
        player_dist = (player.position - ball_pos).length()

        closer_count = 0
        for teammate in self.team.players:
            if teammate == player:
                continue
            if teammate.role == PlayerRole.GOALKEEPER:
                continue

            teammate_dist = (teammate.position - ball_pos).length()
            if teammate_dist < player_dist - 10:
                closer_count += 1

        return closer_count < n

    def _get_positional_target(self, player: Player) -> pygame.Vector2:
        """Get tactical position based on role."""
        ball_pos = self.ball.position

        if player.role == PlayerRole.GOALKEEPER:
            return self._get_goalkeeper_position(player)

        # Base position with ball influence
        home = player.home_position
        ball_influence = (ball_pos - self.pitch.center) * 0.2

        target = home + ball_influence

        # Clamp to pitch
        target = self.pitch.clamp_to_bounds(target, player.radius)

        return target

    def _get_attacking_position(self, player: Player) -> pygame.Vector2:
        """Get position when team is attacking - PUSH FORWARD AGGRESSIVELY!"""
        ball_pos = self.ball.position
        goal_center = self._get_opponent_goal_center()
        ball_carrier = self.team.get_player_with_ball()

        if player.role == PlayerRole.GOALKEEPER:
            return self._get_goalkeeper_position(player)

        if player.role == PlayerRole.DEFENDER:
            # Push up to support but provide cover
            target = player.home_position.copy()
            # Push up more when ball is in attacking half
            if self.pitch.is_in_attacking_third(ball_pos, self.team.attacking_direction):
                # Push up significantly
                if self.team.attacking_direction == 1:
                    target.x = min(target.x + 150, self.pitch.center.x)
                else:
                    target.x = max(target.x - 150, self.pitch.center.x)
            target.y += (ball_pos.y - self.pitch.center.y) * 0.4
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.MIDFIELDER:
            # Get into dangerous positions to receive or shoot
            if ball_carrier:
                # Position to receive pass in space
                to_goal = goal_center - ball_pos
                if to_goal.length() > 0:
                    to_goal = to_goal.normalize()

                # Move ahead of ball and to the side for width
                target = ball_pos + to_goal * AI_MIDFIELDER_SUPPORT
                # Create width - go opposite side of ball carrier
                if ball_carrier.position.y < self.pitch.center.y:
                    target.y = self.pitch.center.y + 100  # Go low
                else:
                    target.y = self.pitch.center.y - 100  # Go high

                # Push forward more aggressively
                if self.team.attacking_direction == 1:
                    target.x = max(target.x, ball_pos.x + 50)
                else:
                    target.x = min(target.x, ball_pos.x - 50)
            else:
                target = self.pitch.center + (goal_center - self.pitch.center) * 0.5

            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.STRIKER:
            # Make aggressive runs toward goal - GET IN THE BOX!
            target = goal_center.copy()

            if ball_carrier and ball_carrier != player:
                # Make diagonal run across the box
                if ball_carrier.position.y < self.pitch.center.y:
                    # Ball is high, run low
                    target.y = self.pitch.center.y + 70
                else:
                    # Ball is low, run high
                    target.y = self.pitch.center.y - 70

                # Get very close to goal
                if self.team.attacking_direction == 1:
                    target.x = self.pitch.boundary_rect.right - 100
                else:
                    target.x = self.pitch.boundary_rect.left + 100
            else:
                # No ball carrier - position centrally near goal
                if self.team.attacking_direction == 1:
                    target.x = self.pitch.boundary_rect.right - 120
                else:
                    target.x = self.pitch.boundary_rect.left + 120

            return self.pitch.clamp_to_bounds(target, player.radius)

        return player.home_position

    def _get_defensive_position(self, player: Player) -> pygame.Vector2:
        """Get position when defending."""
        ball_pos = self.ball.position
        own_goal = self._get_own_goal_center()

        if player.role == PlayerRole.GOALKEEPER:
            return self._get_goalkeeper_position(player)

        if player.role == PlayerRole.DEFENDER:
            # Position between ball and goal
            to_ball = ball_pos - own_goal
            if to_ball.length() > 0:
                to_ball = to_ball.normalize()
            target = own_goal + to_ball * 150
            # Clamp vertically
            target.y = max(self.pitch.center.y - 100, min(self.pitch.center.y + 100, target.y))
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.MIDFIELDER:
            # Track ball carrier or position in midfield
            ball_carrier = self.opponent_team.get_player_with_ball()
            if ball_carrier:
                # Move toward ball carrier
                target = ball_carrier.position + (own_goal - ball_carrier.position).normalize() * 60
            else:
                target = self.pitch.center + (ball_pos - self.pitch.center) * 0.4
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.STRIKER:
            # Stay forward for counter-attack
            target = player.home_position.copy()
            # Slight shift toward ball
            target.y += (ball_pos.y - self.pitch.center.y) * 0.2
            return self.pitch.clamp_to_bounds(target, player.radius)

        return player.home_position

    def _get_goalkeeper_position(self, player: Player) -> pygame.Vector2:
        """Get goalkeeper position based on ball location."""
        ball_pos = self.ball.position
        own_goal = self._get_own_goal_center()

        # Position between ball and goal center
        to_ball = ball_pos - own_goal
        if to_ball.length() > 0:
            to_ball = to_ball.normalize()

        # Distance from goal line depends on ball distance
        ball_dist = (ball_pos - own_goal).length()
        gk_distance = min(AI_GOALKEEPER_RANGE_X, ball_dist * 0.15)

        target = own_goal + to_ball * gk_distance

        # Clamp vertical movement
        target.y = max(own_goal.y - AI_GOALKEEPER_RANGE_Y,
                       min(own_goal.y + AI_GOALKEEPER_RANGE_Y, target.y))

        # Clamp horizontal (stay near goal)
        if self.team.attacking_direction == 1:
            target.x = max(self.pitch.boundary_rect.left + 10,
                          min(self.pitch.boundary_rect.left + AI_GOALKEEPER_RANGE_X + 20, target.x))
        else:
            target.x = min(self.pitch.boundary_rect.right - 10,
                          max(self.pitch.boundary_rect.right - AI_GOALKEEPER_RANGE_X - 20, target.x))

        return target

    def _predict_ball_position(self) -> pygame.Vector2:
        """Predict where ball will be in near future."""
        # Simple prediction based on current velocity
        prediction_time = 0.3  # seconds
        predicted = self.ball.position + self.ball.velocity * prediction_time
        return self.pitch.clamp_to_bounds(predicted, self.ball.radius)

    def _get_opponent_goal_center(self) -> pygame.Vector2:
        """Get center of opponent's goal."""
        if self.team.attacking_direction == 1:
            return self.pitch.get_goal_center('right')
        else:
            return self.pitch.get_goal_center('left')

    def _get_own_goal_center(self) -> pygame.Vector2:
        """Get center of own goal."""
        if self.team.attacking_direction == 1:
            return self.pitch.get_goal_center('left')
        else:
            return self.pitch.get_goal_center('right')


class TeammateAIController:
    """
    Controls non-selected teammates on the player's team.
    These teammates move to support positions but don't shoot or pass autonomously.
    """

    def __init__(self, team: Team, opponent_team: Team, ball: Ball, pitch: Pitch):
        self.team = team
        self.opponent_team = opponent_team
        self.ball = ball
        self.pitch = pitch

        # Decision cooldowns per player
        self.player_cooldowns: dict[Player, float] = {}
        for player in team.players:
            self.player_cooldowns[player] = 0.0

    def update(self, dt: float) -> None:
        """Update AI decisions for non-selected teammates."""
        for player in self.team.players:
            # Skip the selected player - human controls that one
            if player.is_selected:
                continue

            # Update cooldown
            if player in self.player_cooldowns:
                self.player_cooldowns[player] = max(0, self.player_cooldowns[player] - dt)

            # Make decision if cooldown elapsed
            if self.player_cooldowns.get(player, 0) <= 0:
                self._make_decision(player)
                self.player_cooldowns[player] = AI_DECISION_COOLDOWN

            # Execute current action
            self._execute_action(player, dt)

    def _make_decision(self, player: Player) -> None:
        """Decide what action teammate should take."""
        # Teammates never have the ball for long - if they get it, they're waiting for switch
        if player.has_ball:
            # Just hold position, player will switch to them
            player.ai_action = ('hold', player.position)
            return

        if self.ball.is_loose():
            self._decide_ball_loose(player)
        elif self.team.has_ball():
            self._decide_team_attacking(player)
        else:
            self._decide_team_defending(player)

    def _decide_ball_loose(self, player: Player) -> None:
        """Decide action when ball is loose."""
        ball_pos = self.ball.position

        # Should this player chase based on role?
        should_chase = self._should_chase_ball(player)

        if should_chase and self._is_closest_to_ball(player):
            player.ai_action = ('chase', ball_pos)
            return

        # Move to tactical position
        target = self._get_positional_target(player)
        player.ai_action = ('move', target)

    def _decide_team_attacking(self, player: Player) -> None:
        """Decide action when team has ball - get open for passes!"""
        target = self._get_attacking_position(player)
        player.ai_action = ('move', target)

    def _decide_team_defending(self, player: Player) -> None:
        """Decide action when opponent has ball."""
        ball_carrier = self.opponent_team.get_player_with_ball()

        # Goalkeeper behavior
        if player.role == PlayerRole.GOALKEEPER:
            target = self._get_goalkeeper_position(player)
            player.ai_action = ('move', target)
            return

        # Try to tackle if close to ball carrier
        if ball_carrier:
            dist = (player.position - ball_carrier.position).length()
            if dist < TACKLE_RANGE * 1.5:
                player.ai_action = ('tackle', ball_carrier)
                return

        # Move to defensive position
        target = self._get_defensive_position(player)
        player.ai_action = ('move', target)

    def _execute_action(self, player: Player, dt: float) -> None:
        """Execute the current AI action for player."""
        if not player.ai_action:
            return

        action_type = player.ai_action[0]

        if action_type == 'move':
            target = player.ai_action[1]
            self._move_toward(player, target, dt)

        elif action_type == 'chase':
            target = self._predict_ball_position()
            self._move_toward(player, target, dt)

        elif action_type == 'tackle':
            target_player = player.ai_action[1]
            self._move_toward(player, target_player.position, dt)

        elif action_type == 'hold':
            pass  # Just stay in place

    def _move_toward(self, player: Player, target: pygame.Vector2, dt: float) -> None:
        """Move player toward target with smoothing."""
        direction = target - player.position
        dist = direction.length()

        if dist < 8:  # Close enough
            return

        direction = direction.normalize()

        # Apply smoothing to avoid jitter
        if player.velocity.length() > 0:
            current_dir = player.velocity.normalize()
            direction = current_dir * AI_SMOOTHING_FACTOR + direction * (1 - AI_SMOOTHING_FACTOR)
            if direction.length() > 0:
                direction = direction.normalize()

        player.move(direction)

    def _should_chase_ball(self, player: Player) -> bool:
        """Determine if this player should chase loose ball based on role."""
        ball_pos = self.ball.position
        dist = (player.position - ball_pos).length()

        if dist > AI_CHASE_BALL_DISTANCE:
            return False

        if player.role == PlayerRole.GOALKEEPER:
            return self.pitch.is_in_defensive_third(ball_pos, self.team.attacking_direction) and dist < 80

        if player.role == PlayerRole.DEFENDER:
            return self.pitch.is_in_defensive_third(ball_pos, self.team.attacking_direction) or dist < 100

        if player.role == PlayerRole.MIDFIELDER:
            return dist < 180  # Midfielders chase more actively

        if player.role == PlayerRole.STRIKER:
            return dist < 150

        return True

    def _is_closest_to_ball(self, player: Player) -> bool:
        """Check if player is closest non-selected teammate to ball."""
        ball_pos = self.ball.position
        player_dist = (player.position - ball_pos).length()

        for teammate in self.team.players:
            if teammate == player or teammate.is_selected:
                continue
            if teammate.role == PlayerRole.GOALKEEPER:
                continue

            teammate_dist = (teammate.position - ball_pos).length()
            if teammate_dist < player_dist - 15:
                return False

        return True

    def _get_positional_target(self, player: Player) -> pygame.Vector2:
        """Get tactical position based on role."""
        ball_pos = self.ball.position

        if player.role == PlayerRole.GOALKEEPER:
            return self._get_goalkeeper_position(player)

        # Base position with stronger ball influence
        home = player.home_position
        ball_influence = (ball_pos - self.pitch.center) * 0.3

        target = home + ball_influence
        return self.pitch.clamp_to_bounds(target, player.radius)

    def _get_attacking_position(self, player: Player) -> pygame.Vector2:
        """Get position when team is attacking - make runs, get open!"""
        ball_pos = self.ball.position
        goal_center = self._get_opponent_goal_center()

        if player.role == PlayerRole.GOALKEEPER:
            return self._get_goalkeeper_position(player)

        if player.role == PlayerRole.DEFENDER:
            # Push up slightly but stay back
            target = player.home_position.copy()
            # Shift toward ball side
            target.y += (ball_pos.y - self.pitch.center.y) * 0.4
            # Push up a bit when attacking
            if self.team.attacking_direction == 1:
                target.x = min(target.x + 60, self.pitch.center.x - 50)
            else:
                target.x = max(target.x - 60, self.pitch.center.x + 50)
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.MIDFIELDER:
            # Support attack - get into space
            ball_carrier = self.team.get_player_with_ball()
            if ball_carrier:
                # Position to receive pass - offset from ball carrier
                target = ball_pos + (goal_center - ball_pos) * 0.4
                # Move to opposite side of ball carrier for width
                if ball_carrier.position.y < self.pitch.center.y:
                    target.y = self.pitch.center.y + 80
                else:
                    target.y = self.pitch.center.y - 80
            else:
                target = self.pitch.center + (goal_center - self.pitch.center) * 0.3
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.STRIKER:
            # Make runs toward goal - get in scoring position
            ball_carrier = self.team.get_player_with_ball()
            if ball_carrier and ball_carrier != player:
                # Make diagonal run
                target = goal_center.copy()
                # Offset to not be directly in front of goal
                if ball_carrier.position.y < self.pitch.center.y:
                    target.y = self.pitch.center.y + 60
                else:
                    target.y = self.pitch.center.y - 60
                # Don't go too far forward
                if self.team.attacking_direction == 1:
                    target.x = min(target.x, self.pitch.boundary_rect.right - 80)
                else:
                    target.x = max(target.x, self.pitch.boundary_rect.left + 80)
            else:
                target = goal_center + pygame.Vector2(-100 * self.team.attacking_direction, 0)
            return self.pitch.clamp_to_bounds(target, player.radius)

        return player.home_position

    def _get_defensive_position(self, player: Player) -> pygame.Vector2:
        """Get position when defending."""
        ball_pos = self.ball.position
        own_goal = self._get_own_goal_center()

        if player.role == PlayerRole.GOALKEEPER:
            return self._get_goalkeeper_position(player)

        if player.role == PlayerRole.DEFENDER:
            # Position between ball and goal
            to_ball = ball_pos - own_goal
            if to_ball.length() > 0:
                to_ball = to_ball.normalize()
            target = own_goal + to_ball * 140
            target.y = max(self.pitch.center.y - 120, min(self.pitch.center.y + 120, target.y))
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.MIDFIELDER:
            # Track ball, provide cover
            ball_carrier = self.opponent_team.get_player_with_ball()
            if ball_carrier:
                # Position between ball and goal
                target = ball_carrier.position + (own_goal - ball_carrier.position).normalize() * 80
            else:
                target = self.pitch.center + (ball_pos - self.pitch.center) * 0.5
            return self.pitch.clamp_to_bounds(target, player.radius)

        if player.role == PlayerRole.STRIKER:
            # Stay forward but track play
            target = player.home_position.copy()
            target.y += (ball_pos.y - self.pitch.center.y) * 0.25
            return self.pitch.clamp_to_bounds(target, player.radius)

        return player.home_position

    def _get_goalkeeper_position(self, player: Player) -> pygame.Vector2:
        """Get goalkeeper position based on ball location."""
        ball_pos = self.ball.position
        own_goal = self._get_own_goal_center()

        to_ball = ball_pos - own_goal
        if to_ball.length() > 0:
            to_ball = to_ball.normalize()

        ball_dist = (ball_pos - own_goal).length()
        gk_distance = min(AI_GOALKEEPER_RANGE_X, ball_dist * 0.12)

        target = own_goal + to_ball * gk_distance

        target.y = max(own_goal.y - AI_GOALKEEPER_RANGE_Y,
                       min(own_goal.y + AI_GOALKEEPER_RANGE_Y, target.y))

        if self.team.attacking_direction == 1:
            target.x = max(self.pitch.boundary_rect.left + 10,
                          min(self.pitch.boundary_rect.left + AI_GOALKEEPER_RANGE_X + 15, target.x))
        else:
            target.x = min(self.pitch.boundary_rect.right - 10,
                          max(self.pitch.boundary_rect.right - AI_GOALKEEPER_RANGE_X - 15, target.x))

        return target

    def _predict_ball_position(self) -> pygame.Vector2:
        """Predict where ball will be in near future."""
        prediction_time = 0.25
        predicted = self.ball.position + self.ball.velocity * prediction_time
        return self.pitch.clamp_to_bounds(predicted, self.ball.radius)

    def _get_opponent_goal_center(self) -> pygame.Vector2:
        """Get center of opponent's goal."""
        if self.team.attacking_direction == 1:
            return self.pitch.get_goal_center('right')
        else:
            return self.pitch.get_goal_center('left')

    def _get_own_goal_center(self) -> pygame.Vector2:
        """Get center of own goal."""
        if self.team.attacking_direction == 1:
            return self.pitch.get_goal_center('left')
        else:
            return self.pitch.get_goal_center('right')
