from otree.api import *
import json
import random


doc = """
Sequential RSD: players choose one prize each, in random priority order.
The highest-priority player picks first from all available prizes;
the lowest-priority player picks last from whatever remains.
"""


class C(BaseConstants):
    NAME_IN_URL = 'rsd_lab_live_na'
    PLAYERS_PER_GROUP = 8
    NUM_ROUNDS = 1
    VALUATIONS = [1, 3, 5, 7, 9, 11, 13, 15]
    NR_TYPES = len(VALUATIONS)
    NR_PRIZES = len(VALUATIONS)
    COMMON_PRIORITY = list(range(1, PLAYERS_PER_GROUP + 1))
    CAPACITIES = [1] * NR_PRIZES
    CONFIRM_BUTTON = True
    SHOW_CAPACITIES = False
    SHOW_TYPES = False
    SHOW_VALUATIONS = False
    SHOW_PRIORITIES = False
    ALIGNED = False  # Whether all participants have the same valuations
    priorities_by_prize = models.LongStringField()


class Group(BaseGroup):
    assignments_json = models.LongStringField(initial='{}')
    available_prizes_json = models.LongStringField(initial='[]')


class Player(BasePlayer):
    player_valuations = models.LongStringField()
    assigned_prize = models.IntegerField(initial=0)
    pref_ranking = models.CharField(label="", max_length=C.NR_PRIZES, blank=True)
    quiz_response = models.CharField(label="", max_length=500, blank=True)
    age = models.IntegerField(label="Age", min=18, max=120, blank=True)
    gender = models.CharField(
        label="Gender",
        choices=[
            ('', 'Please select...'),
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other'),
            ('P', 'Prefer not to say')
        ],
        max_length=20,
        blank=True,
    )
    education = models.CharField(
        label="Highest level of education",
        choices=[
            ('', 'Please select...'),
            ('HS', 'High School'),
            ('BA', "Bachelor's Degree"),
            ('MA', "Master's Degree"),
            ('PhD', 'Doctoral Degree'),
            ('O', 'Other')
        ],
        max_length=20,
        blank=True,
    )
    field_of_study = models.CharField(label="Field of Study", max_length=200, blank=True)
    experience = models.CharField(
        label="Have you participated in economics experiments before?",
        choices=[
            ('', 'Please select...'),
            ('Y', 'Yes'),
            ('N', 'No')
        ],
        max_length=20,
        blank=True,
    )

class Subsession(BaseSubsession):
    round_valuations = models.LongStringField()
    priorities_by_prize = models.LongStringField()
# --- helpers -----------------------------------------------------------------

def creating_session(subsession: Subsession):
    # Shuffle priority order randomly each round
    priorities = list(C.COMMON_PRIORITY)
    random.shuffle(priorities)
    subsession.priorities_by_prize = json.dumps(priorities)

    # Initialise group-level state for sequential choice
    for group in subsession.get_groups():
        group.available_prizes_json = json.dumps(list(range(1, C.NR_PRIZES + 1)))
        group.assignments_json = json.dumps({})

    for p in subsession.get_players():
        # Generate per-player valuations (different shuffle for each player each round)
        player_vals = list(C.VALUATIONS)
        random.shuffle(player_vals)
        p.player_valuations = json.dumps(player_vals)

        if subsession.round_number == 1:
            p.participant.vars['e2_schedule'] = []
            p.participant.vars['e2_successful'] = [False] * C.NR_PRIZES
            p.participant.vars['e2_app_payoff'] = 0


# --- pages -------------------------------------------------------------------
# region Pages
class Instructions(Page):
    @staticmethod
    def vars_for_template(player: Player):
        priorities = json.loads(player.subsession.priorities_by_prize)
        priority_map = {pid: rank for rank, pid in enumerate(priorities, start=1)}
        my_priority = priority_map[player.id_in_group]
        letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)]
        def ordinal(n):
            s = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10 * (n % 100 not in (11, 12, 13)), 'th')
            return f"{n}{s}"
        return dict(
            nr_prizes=C.NR_PRIZES,
            players_per_group=C.PLAYERS_PER_GROUP,
            nr_others = C.PLAYERS_PER_GROUP - 1,
            nr_rounds = C.NUM_ROUNDS,
            nr_prizes_ordinal = ordinal(C.NR_PRIZES),
            indices=list(range(1, C.NR_PRIZES + 1)),
            letters=letters,
            letters_str = ','.join(letters),
            valuations=json.loads(player.player_valuations),
            priorities=[my_priority] * C.NR_PRIZES,
            capacities=C.CAPACITIES,
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
        )

    @staticmethod
    def is_displayed(player):
        return player.subsession.round_number == 1


class Quiz(Page):
    form_model = 'player'
    form_fields = ['quiz_response']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            nr_prizes=C.NR_PRIZES,
            players_per_group=C.PLAYERS_PER_GROUP,
            indices=list(range(1, C.NR_PRIZES + 1)),
            letters=[chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
        )

    @staticmethod
    def is_displayed(player):
        return player.subsession.round_number == 1


class Envelope(Page):
    @staticmethod
    def is_displayed(player):
        return player.subsession.round_number == 1


class DecisionWaitPage(WaitPage):
    """Synchronise players before sequential choice begins."""
    pass


class Decision(Page):
    """
    Live page: players pick one prize each, sequentially in priority order.
    Uses WebSocket messages (liveSend / liveRecv) for real-time UI updates.
    """

    @staticmethod
    def vars_for_template(player: Player):
        priorities = json.loads(player.subsession.priorities_by_prize)
        priority_map = {pid: rank for rank, pid in enumerate(priorities, start=1)}
        my_priority = priority_map[player.id_in_group]
        def ordinal(n):
            s = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10 * (n % 100 not in (11, 12, 13)), 'th')
            return f"{n}{s}"
        return dict(
            nr_prizes=C.NR_PRIZES,
            nr_prizes_ordinal=ordinal(C.NR_PRIZES),
            nr_rounds=C.NUM_ROUNDS,
            nr_others = C.PLAYERS_PER_GROUP - 1,
            players_per_group=C.PLAYERS_PER_GROUP,
            indices=list(range(1, C.NR_PRIZES + 1)),
            letters=[chr(ord('A') + j) for j in range(C.NR_PRIZES)],
                        letters_str = ','.join([chr(ord('A') + j) for j in range(C.NR_PRIZES)]),
            valuations=json.loads(player.player_valuations),
            my_priority=my_priority,
            priorities=[my_priority] * C.NR_PRIZES,
            capacities=C.CAPACITIES,
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
        )

    @staticmethod
    def js_vars(player: Player):
        return dict(nr_prizes=C.NR_PRIZES)

    @staticmethod
    def live_method(player: Player, data):
        group = player.group
        priorities = json.loads(group.subsession.priorities_by_prize)
        priority_map = {pid: rank for rank, pid in enumerate(priorities, start=1)}

        players = group.get_players()
        priority_order = sorted(
            players, key=lambda p: priority_map.get(p.id_in_group, 10**9)
        )

        assignments = json.loads(group.assignments_json)
        available = json.loads(group.available_prizes_json)

        # Who should choose next?
        current_chooser = None
        for p in priority_order:
            if str(p.id_in_group) not in assignments:
                current_chooser = p
                break

        # -- process a choice -------------------------------------------------
        if (
            data.get('type') == 'choice'
            and current_chooser
            and current_chooser.id_in_group == player.id_in_group
        ):
            prize_id = int(data.get('prize_id', 0))
            if prize_id in available:
                available.remove(prize_id)
                assignments[str(player.id_in_group)] = prize_id
                player.assigned_prize = prize_id

                # payoff
                valuations = json.loads(player.player_valuations)
                player.payoff = valuations[prize_id - 1]

                # schedule / successful
                schedule = player.participant.vars.get('e2_schedule', [])
                schedule.append(
                    [player.round_number, priority_map[player.id_in_group], prize_id]
                )
                player.participant.vars['e2_schedule'] = schedule
                player.participant.vars['e2_successful'] = [
                    i + 1 == prize_id for i in range(C.NR_PRIZES)
                ]

                # persist group state
                group.available_prizes_json = json.dumps(available)
                group.assignments_json = json.dumps(assignments)

        # -- build response for every player ----------------------------------
        all_done = len(assignments) >= C.PLAYERS_PER_GROUP
        current_chooser_id = None
        current_chooser_priority = None
        if not all_done:
            for p in priority_order:
                if str(p.id_in_group) not in assignments:
                    current_chooser_id = p.id_in_group
                    current_chooser_priority = priority_map[p.id_in_group]
                    break

        response = {}
        for p in players:
            my_assign = assignments.get(str(p.id_in_group))
            response[p.id_in_group] = dict(
                available=sorted(available),
                current_chooser_id=current_chooser_id,
                current_chooser_priority=current_chooser_priority,
                is_my_turn=(p.id_in_group == current_chooser_id),
                all_done=all_done,
                my_assignment=my_assign,
                my_assignment_letter=(
                    chr(ord('A') + my_assign - 1) if my_assign else None
                ),
                my_priority=priority_map[p.id_in_group],
            )
        return response

    @staticmethod
    def is_displayed(player: Player):
        return True


class ResultsWaitPage(WaitPage):
    """Synchronise before results."""
    pass


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        selected_pay_round = player.participant.vars.get('e2_selected_pay_round')
        if selected_pay_round is None:
            selected_pay_round = random.randint(1, C.NUM_ROUNDS)
            player.participant.vars['e2_selected_pay_round'] = selected_pay_round

        app_payoff = player.in_round(selected_pay_round).payoff
        player.participant.vars['e2_app_payoff'] = app_payoff

        priorities = json.loads(player.subsession.priorities_by_prize)
        priority_map = {pid: rank for rank, pid in enumerate(priorities, start=1)}
        my_priority = priority_map[player.id_in_group]

        return dict(
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
            selected_pay_round=selected_pay_round,
            letters=[chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            valuations=json.loads(player.in_round(selected_pay_round).player_valuations),
            players_per_group=C.PLAYERS_PER_GROUP,
            priorities=[my_priority] * C.NR_PRIZES,
            successful=player.participant.vars.get('e2_successful', []),
            app_payoff=app_payoff,
        )


class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education', 'field_of_study', 'experience']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
        )

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.round_number == C.NUM_ROUNDS


class Thanks(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
        )

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.round_number == C.NUM_ROUNDS


class PaymentInfo(Page):
    @staticmethod
    def vars_for_template(player: Player):
        participant = player.participant
        e1_app_payoff = participant.vars.get('e1_app_payoff', cu(0))
        e1_selected_pay_round = participant.vars.get('e1_selected_pay_round', '?')
        e2_app_payoff = participant.vars.get('e2_app_payoff', cu(0))
        e2_selected_pay_round = participant.vars.get('e2_selected_pay_round', '?')
        show_up_fee = cu(player.session.config.get('participation_fee', 0))
        total_payment = e1_app_payoff + e2_app_payoff + show_up_fee
        participant.vars['total_payment'] = total_payment
        return dict(
            redemption_code=participant.label or participant.code,
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
            e1_app_payoff=e1_app_payoff,
            e1_selected_pay_round=e1_selected_pay_round,    
            e2_app_payoff=e2_app_payoff,
            e2_selected_pay_round=e2_selected_pay_round,
            show_up_fee=show_up_fee,
            total_payment=total_payment,
        )

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.round_number == C.NUM_ROUNDS
# endregion

page_sequence = [Instructions, DecisionWaitPage, Decision, ResultsWaitPage, Results, Demographics, Thanks, PaymentInfo]
