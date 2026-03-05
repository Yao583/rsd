from otree.api import *
import json
import random


doc = """
This app matches prizes to participants using the Random Serial Dictatorship (RSD) mechanism in the lab.
"""


class C(BaseConstants):
    NAME_IN_URL = 'rsd_lab_a_e'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 2
    # Heterogeneous valuations for the 8 prizes, 4 types for now
    # VALUATIONS_1 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_2 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_3 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_4 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_5 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_6 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_7 = [1, 3, 5, 7, 9, 11, 13, 15]
    # VALUATIONS_8 = [1, 3, 5, 7, 9, 11, 13, 15]
    VALUATIONS_1 = [1, 3, 5, 7]
    VALUATIONS_2 = [1, 3, 5, 7]
    VALUATIONS_3 = [1, 3, 5, 7]
    VALUATIONS_4 = [1, 3, 5, 7]
    VALUATION_TYPES = [VALUATIONS_1, VALUATIONS_2, VALUATIONS_3, VALUATIONS_4]#, VALUATIONS_5, VALUATIONS_6, VALUATIONS_7, VALUATIONS_8]
    NR_TYPES = len(VALUATION_TYPES) # number of types of preferences
    NR_PRIZES = len(VALUATIONS_1)
    # Common Priority orders across prizes
    # PRIORITIES_P1 = [1, 2, 3, 4, 5, 6, 7, 8]
    COMMON_PRIORITY = list(range(1, PLAYERS_PER_GROUP + 1))
    CAPACITIES = [1] * NR_PRIZES # each prize can only be assigned to one participant
    # Maybe delete later these conditions
    INSTRUCTIONS_EXAMPLE = True # Whether to show an example in the instructions
    CONFIRM_BUTTON = True # Whether to show a confirm button on the decision page
    SHOW_CAPACITIES = False # Whether to show capacities on the decision page and in the instructions
    SHOW_TYPES = True # Whether to tell players there are multiple types of players
    SHOW_VALUATIONS = False # Whether to show a player other players' valuations on the decision page
    SHOW_PRIORITIES = True # whetehr to show a player the schools' priorities for her



class Subsession(BaseSubsession):
    priorities_by_prize = models.LongStringField()


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pref_ranking = models.CharField(label="", max_length=C.NR_PRIZES, blank=False)
    # Quiz response field
    quiz_response = models.CharField(label="", max_length=500, blank=True)
    # Demographics fields
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
        blank=True
    )
    education = models.CharField(
        label="Highest level of education",
        choices=[
            ('', 'Please select...'),
            ('HS', 'High School'),
            ('BA', 'Bachelor\'s Degree'),
            ('MA', 'Master\'s Degree'),
            ('PhD', 'Doctoral Degree'),
            ('O', 'Other')
        ],
        max_length=20,
        blank=True
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
        blank=True
    )

# region functions
EXPECTED_PRIZE_SET = frozenset(chr(ord('A') + i) for i in range(C.NR_PRIZES))

def creating_session(subsession: Subsession):
    # subsession.group_randomly() # shuffle group each round
    # if subsession.round_number == 1:
    #     subsession.group_randomly()
    # else:
    #     subsession.group_like_round(1) # shuffle once and keep the same groups across rounds
    # Shuffle priority order randomly each round
    priorities = list(C.COMMON_PRIORITY)
    random.shuffle(priorities)
    subsession.priorities_by_prize = json.dumps(priorities)

    for p in subsession.get_players():
        if subsession.round_number == 1:
            p.participant.vars['e1_schedule'] = []
            p.participant.vars['e1_successful'] = [False] * C.NR_PRIZES
            p.participant.vars['e1_valuations'] = C.VALUATION_TYPES[(p.id_in_group - 1) % C.NR_TYPES]
            p.participant.vars['e1_player_prefs'] = []
            p.participant.vars['e1_selected_pay_round'] = None
            p.participant.vars['total_payment'] = cu(0)


def is_valid_ranking_string(ranking: str):
    ranking = (ranking or '').strip().upper()
    if not ranking or len(ranking) > C.NR_PRIZES:
        return False
    ranking_set = set(ranking)
    if len(ranking_set) != len(ranking):
        return False
    return ranking_set.issubset(EXPECTED_PRIZE_SET)

def map_ranking_string_to_prefs(ranking: str):
    """Map ranking string like 'BCA' to per-prize ranks like [3, 1, 2]."""
    prefs = [None] * C.NR_PRIZES
    ranking = (ranking or '').strip().upper()
    for rank, prize_letter in enumerate(ranking, start=1):
        prize_num = ord(prize_letter) - ord('A') + 1
        if 1 <= prize_num <= C.NR_PRIZES:
            prefs[prize_num - 1] = rank
    return prefs

def get_allocation(group: Group):
    players = group.get_players()
    for p in players:
        p.payoff = 0

    priorities = json.loads(group.subsession.priorities_by_prize)
    priority_map = {player_id: rank for rank, player_id in enumerate(priorities, start=1)}
    priority_order = sorted(players, key=lambda p: priority_map.get(p.id_in_group, 10**9))

    available_prizes = set(range(1, C.NR_PRIZES + 1))
    assigned_prize_by_player_id = {}

    for p in priority_order:
        ranking = (p.pref_ranking or '').strip().upper() # for example, "BCA"
        assigned_prize = None
        for prize_letter in ranking:
            prize_id = ord(prize_letter) - ord('A') + 1
            if prize_id in available_prizes:
                assigned_prize = prize_id
                available_prizes.remove(prize_id)
                break
        assigned_prize_by_player_id[p.id_in_group] = assigned_prize

        if assigned_prize is None:
            p.participant.vars['e1_successful'] = [False] * C.NR_PRIZES # unmatched
            continue

        schedule = p.participant.vars.get('e1_schedule', [])
        priority_position = priority_map[p.id_in_group]
        schedule.append([p.round_number, priority_position, assigned_prize])
        p.participant.vars['e1_schedule'] = schedule
        p.participant.vars['e1_successful'] = [i + 1 == assigned_prize for i in range(C.NR_PRIZES)]

        valuations = p.participant.vars.get('e1_valuations', C.VALUATION_TYPES[(p.id_in_group - 1) % C.NR_TYPES])
        p.payoff = valuations[assigned_prize - 1]

# endregion
# region PAGES
class Instructions(Page):
    @staticmethod
    def vars_for_template(player: Player):
        priorities = json.loads(player.subsession.priorities_by_prize)
        priority_map = {player_id: rank for rank, player_id in enumerate(priorities, start=1)}
        my_priority = priority_map[player.id_in_group]
        letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)]
        def ordinal(n):
            s = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10 * (n % 100 not in (11, 12, 13)), 'th')
            return f"{n}{s}"
        return dict(
            nr_prizes = C.NR_PRIZES,
            nr_prizes_ordinal = ordinal(C.NR_PRIZES),
            nr_others = C.PLAYERS_PER_GROUP - 1,
            players_per_group = C.PLAYERS_PER_GROUP,
            indices = [j for j in range(1, C.NR_PRIZES + 1)],
            letters = letters,
            letters_str = ','.join(letters),
            valuations = C.VALUATION_TYPES[player.id_in_group - 1],
            priorities = [my_priority] * C.NR_PRIZES,
            capacities = C.CAPACITIES,
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS
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
            nr_prizes = C.NR_PRIZES,
            players_per_group = C.PLAYERS_PER_GROUP,
            indices = [j for j in range(1, C.NR_PRIZES + 1)],
            letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS
        )
    @staticmethod
    def is_displayed(player):
        return player.subsession.round_number == 1
    
class Decision(Page):
    form_model = 'player'
    form_fields = ['pref_ranking']
    timeout_seconds = 90

    @staticmethod
    def vars_for_template(player: Player):
        priorities = json.loads(player.subsession.priorities_by_prize)
        priority_map = {player_id: rank for rank, player_id in enumerate(priorities, start=1)}
        my_priority = priority_map[player.id_in_group]
        return dict(
            nr_prizes = C.NR_PRIZES,
            players_per_group = C.PLAYERS_PER_GROUP,
            indices = [j for j in range(1, C.NR_PRIZES + 1)],
            letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            prize_options = list(zip(range(1, C.NR_PRIZES + 1), [chr(ord('A') + j) for j in range(C.NR_PRIZES)])),
            valuations = C.VALUATION_TYPES[player.id_in_group - 1],
            priorities = [my_priority]*C.NR_PRIZES,
            capacities = C.CAPACITIES,
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS
        )
    @staticmethod
    def is_displayed(player: Player):
        return True

    @staticmethod
    def error_message(player: Player, values):
        ranking = values.get('pref_ranking', '').strip().upper()
        if not is_valid_ranking_string(ranking):
            return 'Please enter a ranking using unique letters A-H only (for example: ABF or ABCDEFGH).'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            # Default ranking: alphabetical order (ABCD)
            player.pref_ranking = ''.join(chr(ord('A') + i) for i in range(C.NR_PRIZES))
        else:
            player.pref_ranking = (player.pref_ranking or '').strip().upper()
        player.participant.vars['e1_player_prefs'] = [[rank] for rank in map_ranking_string_to_prefs(player.pref_ranking)]

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = get_allocation


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        selected_pay_round = player.participant.vars.get('e1_selected_pay_round')
        if selected_pay_round is None:
            selected_pay_round = random.randint(1, C.NUM_ROUNDS)
            player.participant.vars['e1_selected_pay_round'] = selected_pay_round

        app_payoff = player.in_round(selected_pay_round).payoff
        player.participant.vars['e1_app_payoff'] = app_payoff
        priorities = json.loads(player.subsession.priorities_by_prize)
        priority_map = {player_id: rank for rank, player_id in enumerate(priorities, start=1)}
        my_priority = priority_map[player.id_in_group]
        return dict(
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS,
            selected_pay_round=selected_pay_round,
            letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            valuations = C.VALUATION_TYPES[player.id_in_group - 1],
            player_prefs = player.participant.vars.get('e1_player_prefs', []),
            players_per_group = C.PLAYERS_PER_GROUP,
            priorities = [my_priority]*C.NR_PRIZES,
            successful = player.participant.vars.get('e1_successful', []),
            app_payoff=app_payoff,
        )
class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education', 'field_of_study', 'experience']

    # METHOD: =================================================================================== #
    # CREATE VARIABLES TO DISPLAY ON DEMOGRAPHICS.HTML ========================================== #
    # =========================================================================================== #
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS
        )

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.round_number == C.NUM_ROUNDS

class Thanks(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS
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
        show_up_fee = cu(player.session.config.get('participation_fee', 0))
        total_payment = participant.vars.get('total_payment', cu(0))
        return dict(
            redemption_code=participant.label or participant.code,
            round_number=player.subsession.round_number,
            total_rounds=C.NUM_ROUNDS,
            e1_app_payoff=e1_app_payoff,
            e1_selected_pay_round=e1_selected_pay_round,
            show_up_fee=show_up_fee,
            total_payment=total_payment,
        )

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.round_number == C.NUM_ROUNDS
# endregion
page_sequence = [Instructions, Decision, ResultsWaitPage, Results]
