from otree.api import *
from itertools import chain, permutations, combinations
import json
import random


doc = """
This app matches prizes to participants using the Random Serial Dictatorship (RSD) mechanism.
"""


class C(BaseConstants):
    NAME_IN_URL = 'rsd_prolific_a'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    # Heterogeneous valuations for the 8 prizes
    VALUATIONS_1 = [10, 20, 30, 40, 50, 60, 70, 80]
    VALUATIONS_2 = [20, 10, 40, 30, 60, 50, 80, 70]
    VALUATIONS_3 = [30, 50, 10, 60, 20, 80, 40, 70]
    VALUATIONS_4 = [40, 30, 60, 10, 80, 20, 70, 50]
    VALUATIONS_5 = [10, 20, 30, 40, 50, 60, 70, 80]
    VALUATIONS_6 = [20, 10, 40, 30, 60, 50, 80, 70]
    VALUATIONS_7 = [30, 50, 10, 60, 20, 80, 40, 70]
    VALUATIONS_8 = [40, 30, 60, 10, 80, 20, 70, 50]
    VALUATION_TYPES = [VALUATIONS_1, VALUATIONS_2, VALUATIONS_3, VALUATIONS_4, VALUATIONS_5, VALUATIONS_6, VALUATIONS_7, VALUATIONS_8]
    NR_TYPES = len(VALUATION_TYPES) # number of types of preferences
    NR_PRIZES = len(VALUATIONS_1) # number of prizes
    # Common Priority orders across prizes, randomly generated but cannot guarantee participant 
    # has different rank in each round.
    PRIORITIES = [1, 2, 3, 4, 5, 6, 7, 8]
    #PRIORITIES = list(permutations(range(1, PLAYERS_PER_GROUP + 1))) 
    CAPACITIES = [1] * NR_PRIZES # each prize can only be assigned to one participant
    FIXED_PLAYER_RANKINGS = {
        2: 'ABCDEFGH',
        3: 'HGFEDCBA',
        4: 'BADCFEHG',
        5: 'DCBAHGFE',
        6: 'EFGHABCD',
        7: 'HGFEDCBA',
        8: 'BADCFEHG',
    }
    # Maybe delete later these conditions
    INSTRUCTIONS_EXAMPLE = True # Whether to show an example in the instructions
    CONFIRM_BUTTON = True # Whether to show a confirm button on the decision page
    SHOW_CAPACITIES = True # Whether to show capacities on the decision page and in the instructions
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
    for p in subsession.get_players():
        p.participant.vars['schedule'] = []
        p.participant.vars['successful'] = [False] * C.NR_PRIZES
        p.participant.vars['valuations'] = C.VALUATION_TYPES[0]
        p.participant.vars['player_prefs'] = [[rank] for rank in map_ranking_string_to_prefs(p.pref_ranking)]
        p.participant.total_payment = 0

    for bot_id, fixed_ranking in C.FIXED_PLAYER_RANKINGS.items():
        normalized = fixed_ranking.strip().upper()
        if not is_valid_ranking_string(normalized):
            raise ValueError(f'Invalid fixed ranking for virtual player {bot_id}: {fixed_ranking}')

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
    for p in group.get_players():
        p.payoff = 0

    player = group.get_player_by_id(1)

    rankings_by_agent = {1: (player.pref_ranking or '').strip().upper()}
    for bot_id, ranking in C.FIXED_PLAYER_RANKINGS.items():
        rankings_by_agent[bot_id] = ranking.strip().upper()

    priority_order = random.sample(range(1, C.NR_AGENTS + 1), C.NR_AGENTS)
    player.participant.vars['position'] = priority_order.index(1) + 1

    available_prizes = set(range(1, C.NR_PRIZES + 1))
    assigned_prize_by_agent = {}
    for agent_id in priority_order:
        ranking = rankings_by_agent.get(agent_id, '')
        for prize_letter in ranking:
            prize_id = ord(prize_letter) - ord('A') + 1
            if prize_id in available_prizes:
                assigned_prize_by_agent[agent_id] = prize_id
                available_prizes.remove(prize_id)
                break

    assigned_prize = assigned_prize_by_agent.get(1)
    if assigned_prize is None:
        player.participant.vars['schedule'] = []
        player.participant.vars['successful'] = [False] * C.NR_PRIZES
        return

    player.participant.vars['schedule'] = [[1, 1, assigned_prize]]
    player.participant.vars['successful'] = [i + 1 == assigned_prize for i in range(C.NR_PRIZES)]
    valuations = player.participant.vars.get('valuations', C.VALUATION_TYPES[0])
    player.payoff = valuations[assigned_prize - 1]
    
def set_payoffs(group: Group): # SET PAYOFFS
    # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
    players = group.get_players()
    indices = [j for j in range(1, C.NR_PRIZES + 1)]

    # ADD EVERY VALUE OF A COURSE TO PAYOFF IF IT IS IN THE PLAYERS SCHEDULE ================ #
    for p in players:
        for n in indices:
            if n in p.participant.player_resource:
                p.payoff += p.participant.valuations[n - 1]
                p.participant.successful[n - 1] = True
def allocation_and_payoffs(group: Group):
    """Run RSD mechanism and set players' payoffs"""
    get_allocation(group)
    set_payoffs(group)

def calculate_total_payment(player: Player):
    # """Randomly select one round from each 2-round pair and sum payoffs"""
    """Sum payoffs over all rounds"""
    if player.round_number != C.NUM_ROUNDS:
        return  # Only calculate on final round
    
    total_payoff = 0
    #selected_rounds = []
    for num in range(1, C.NUM_ROUNDS + 1):
        p = player.in_round(num)
        total_payoff += p.payoff
    player.participant.total_payment = total_payoff
# endregion
# region PAGES
class Instructions(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            nr_prizes = C.NR_PRIZES,
            players_per_group = C.PLAYERS_PER_GROUP,
            indices = [j for j in range(1, C.NR_PRIZES + 1)],
            letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            valuations = player.participant.valuations or [],
            priorities = C.PRIORITIES,
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
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            nr_prizes = C.NR_PRIZES,
            players_per_group = C.PLAYERS_PER_GROUP,
            indices = [j for j in range(1, C.NR_PRIZES + 1)],
            letters = [chr(ord('A') + j) for j in range(C.NR_PRIZES)],
            school_options = list(zip(range(1, C.NR_PRIZES + 1), [chr(ord('A') + j) for j in range(C.NR_PRIZES)])),
            valuations = player.participant.valuations or [],
            priorities = C.PRIORITIES,
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
        player.pref_ranking = (player.pref_ranking or '').strip().upper()
        player.participant.vars['player_prefs'] = [[rank] for rank in map_ranking_string_to_prefs(player.pref_ranking)]

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = get_allocation


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Calculate total payment only on final round
        if player.round_number == C.NUM_ROUNDS:
            calculate_total_payment(player)

    @staticmethod
    def vars_for_template(player: Player):
        app_total_payoff = sum(p.payoff for p in player.in_all_rounds())
        return dict(
            app_total_payoff=app_total_payoff,
            session_total_payoff=player.participant.total_payment,
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
        return dict(
            redemption_code=participant.label or participant.code,
            round_number = player.subsession.round_number,
            total_rounds = C.NUM_ROUNDS,
            payment = participant.total_payment
        )

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.round_number == C.NUM_ROUNDS
# endregion
page_sequence = [Instructions, Quiz, Decision, ResultsWaitPage, Demographics, Thanks, PaymentInfo]
